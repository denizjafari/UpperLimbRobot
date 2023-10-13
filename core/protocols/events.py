"""
Implementation of a simple event-based network protocol. Server and client
both can send and receive events in a full-duplex configuration. They
each run in a separate Qt thread by themselves.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Optional

import selectors
from selectors import DefaultSelector
import socket
from queue import Queue
import sys
import logging

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, \
    QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import QThreadPool


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)


# The port that is used by clients and servers.
PORT = 9876

# The timeout for blocking reads in the client and select in the server.
TIMEOUT = 0.001


class Event:
    """
    One event that is sent between the client and the server.
    """
    name: str
    payload: Optional[list]
    source: Optional[tuple[str, int]]
    destination: Optional[tuple[int, str]]

    def __init__(self, name: str, payload: Optional[list] = None) -> None:
        """
        Initialize a new event with the given name and payload.
        """
        self.name = name
        self.payload = payload

        self.source = None
        self.destination = None

    def toBytes(self) -> bytes:
        """
        Convert this event into a sequence of bytes that can be sent over the
        network.
        """
        if self.payload is None or len(self.payload) == 0:
            return f"{self.name}\n".encode()
        else:
            return f"{self.name}:{':'.join(str(x) for x in self.payload)}\n".encode()
        
    def reply(self, e: Event) -> Event:
        """
        Set the source and destination of the passed in event to the
        destination and source of this event, respectively.
        """
        e.source, e.destination = self.destination, self.source
        return e
        
    @staticmethod
    def fromBytes(data: bytes) -> Event:
        """
        Create an event from the given sequence of bytes.
        """
        return Event.fromString(data.decode())
    
    @staticmethod
    def fromString(data: str) -> Event:
        """
        Create an event from the given sequence of bytes.
        """
        data = data[:-1]
        if ":" in data:
            data = data.split(":")
            name = data[0]
            payload = data[1:]
            return Event(name, payload)
        else:
            return Event(data)
        
    def __str__(self) -> None:
        """
        Return a string representation of this event.
        """
        return f"{self.name}:{self.payload}"

        
class Server(QObject, QRunnable):
    """
    The server that excepts events from all clients and broadcasts events
    to all clients at once. It must be started after initialization by
    calling start() and runs in a separate thread. It can be closed by
    calling close().
    """
    eventReceived = Signal(Event)
    connToBuffer: dict[socket.socket, str]
    connToAddr: dict[socket.socket, tuple[str, int]]
    msgQueue: Queue[Event]

    def __init__(self,
                 address:tuple[Optional[str], int]=("localhost", PORT)) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.connToBuffer = {}
        self.connToAddr = {}

        self.msgQueue = Queue()

        self.address = address
        self.sel = DefaultSelector()
        self.sock = socket.create_server(address)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.listen(5)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)
        self.shouldClose = False
        module_logger.debug(f"Setup Event Server listening on {self.address}")

    def run(self) -> None:
        """
        Run the server until it is closed. Select for the client connections
        and process the message queue repeatedly.
        """
        module_logger.debug(f"Started Event Server listening on {self.address}")

        while not self.shouldClose:
            events = self.sel.select(0.001)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

            if not self.msgQueue.empty():
                e = self.msgQueue.get()
                data = e.toBytes()
                if e.destination is None:
                    for conn in self.connToBuffer:
                        conn.send(data)
                    module_logger.debug(f"Sent event {e} to all connected clients")
                else:
                    for conn in self.connToBuffer:
                        if self.connToAddr[conn] == e.destination:
                            conn.send(data)
                            module_logger.debug(f"Sent event {e} to {e.destination}")
                            break
                        

        self.sel.close()
        
        for conn in self.connToBuffer:
            conn.close()
        self.connToBuffer.clear()
        self.sock.close()

        module_logger.debug(f"Closed Event Server listening on {self.address}")

    def start(self, threadPool = QThreadPool.globalInstance()) -> None:
        """
        Start the server in a new thread.
        """
        threadPool.start(self)

    def send(self, e: Event) -> None:
        """
        Put an event in the message queue to be broadcast to all clients.
        """
        self.msgQueue.put(e)

    def accept(self, sock: socket.socket, mask) -> None:
        """
        Accept a new connection and register it with the selector.
        """
        conn, addr = sock.accept()
        module_logger.info(f"Accepted connection from {addr}")
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.connToBuffer[conn] = ""
        self.connToAddr[conn] = addr

    def read(self, sock: socket.socket, mask) -> None:
        """
        Read from a connection and emit the event that was received.
        """
        data = sock.recv(1024)

        if data:
            string = self.connToBuffer[sock] + data.decode()
            index = string.find("\n")

            while index != -1:
                evt = Event.fromString(string[:index + 1])
                evt.source = self.connToAddr[sock]
                
                module_logger.debug(f"Received event {str(evt)}")
                self.eventReceived.emit(evt)

                string = string[index + 1:]
                index = string.find("\n")
            
            self.connToBuffer[sock] = string
        else:
            self.sel.unregister(sock)
            sock.close()

            module_logger.debug(f"Disconnected {self.connToAddr[sock]}")
            
            del self.connToBuffer[sock]
            del self.connToAddr[sock]

    def close(self) -> None:
        """
        Initiate the shutdown of the server. Messages remaining in the queue
        are dropped.
        """
        self.shouldClose = True


class Client(QObject, QRunnable):
    """
    The client side of the network protocol. It connects to the server and
    can send as well as receive events. It must be started after initialization
    by calling start() and runs in a separate thread. It can be closed by
    calling close().
    """
    eventReceived = Signal(Event)
    conn: socket.socket
    shouldClose: bool
    buffer: str

    def __init__(self,
                 address:tuple[Optional[str], int]=("localhost", PORT)) -> None:
        """
        Initialize a new client. It connects to localhost:PORT.
        """
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.msgQueue: Queue[Event] = Queue()
        self.conn = socket.create_connection(address)
        self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.conn.settimeout(0.001)
        self.address = address

        module_logger.debug(f"Setup Event Client connected to {self.address}")

        self.shouldClose = False
        self.buffer = ""

    def run(self) -> None:
        """
        Run the client until it is closed. Receive events and send events
        repeatedly.
        """
        module_logger.debug(f"Started Event Client connected to {self.address}")
        while not self.shouldClose:
            timedOut = False
            try:
                data = self.conn.recv(1024)
            except socket.timeout:
                timedOut = True
            except Exception:
                timedOut = True
                break

            if not timedOut:
                if data is None:
                    break
                elif len(data) != 0:
                    self.buffer += data.decode()
                    index = self.buffer.find("\n")

                    while index != -1:
                        evt = Event.fromString(self.buffer[:index + 1])
                        module_logger.debug(f"Received event {str(evt)}")
                        self.eventReceived.emit(evt)

                        self.buffer = self.buffer[index + 1:]
                        index = self.buffer.find("\n")

            if not self.msgQueue.empty():
                e = self.msgQueue.get()
                try:
                    self.conn.send(e.toBytes())
                except ConnectionAbortedError:
                    break
                except BrokenPipeError:
                    break

        self.conn.close()
        module_logger.debug(f"Closed Event Client connected to {self.address}")

    def start(self, threadPool = QThreadPool.globalInstance()) -> None:
        """
        Start the client in a new thread.
        """
        threadPool.start(self)

    def send(self, e: Event) -> None:
        """
        Enqueue a message to be sent to the server.
        """
        self.msgQueue.put(e)

    def close(self) -> None:
        """
        Initialize the shutdown of the client. Messages remaining in the queue
        are dropped.
        """
        self.shouldClose = True

class GameAdapter(QObject):
    """
    An adapter for games that handles the event receiving and sending layer.
    """
    eventReady = Signal(Event)

    def __init__(self) -> None:
        """
        Initilize a new game adapter.
        """
        QObject.__init__(self)

    def widget(self) -> QWidget:
        """
        Return the underlying widget that runs the game.
        """
        raise NotImplementedError

    def eventReceived(self, e: Event) -> None:
        """
        Handle an event that was received from the network.
        """
        raise NotImplementedError

if __name__ == "__main__":
    """
    A sample application that can act as server or client.
    """

    app = QApplication()
    window = QWidget()

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        endpoint = Server()
        title = "Server"
    else:
        endpoint = Client()
        title = "Client"
    
    QThreadPool.globalInstance().start(endpoint)

    vBox = QVBoxLayout()
    window.setLayout(vBox)

    hBox = QHBoxLayout()
    vBox.addLayout(hBox)

    edit = QLineEdit()
    hBox.addWidget(edit)

    submit = QPushButton("Send")
    submit.clicked.connect(lambda: endpoint.send(Event(edit.text())))
    hBox.addWidget(submit)

    label = QLabel()
    endpoint.eventReceived.connect(lambda e: label.setText(e.name))
    vBox.addWidget(label)

    window.setWindowTitle(title)
    window.show()
    code = app.exec()
    endpoint.close()
    sys.exit(code)

