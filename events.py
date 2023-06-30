"""
Implementation of a simple event-based network protocol.
"""

from __future__ import annotations
from typing import Optional

import selectors
from selectors import DefaultSelector
import socket
from queue import Queue
import sys

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, \
    QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import QThreadPool

# The port that is used by clients and servers.
PORT = 3000

# The timeout for blocking reads in the client and select in the server.
TIMEOUT = 0.001


class Event:
    """
    One event that is sent between the client and the server.
    """
    name: str
    payload: Optional[list]


    def __init__(self, name: str, payload: Optional[list] = None) -> None:
        """
        Initialize a new event with the given name and payload.
        """
        self.name = name
        self.payload = payload

    def toBytes(self) -> bytes:
        """
        Convert this event into a sequence of bytes that can be sent over the
        network.
        """
        if self.payload is None or len(self.payload) == 0:
            return f"{self.name}\n".encode()
        else:
            return f"{self.name}:{':'.join(str(x) for x in self.payload)}\n".encode()
        
    @staticmethod
    def fromBytes(data: bytes) -> Event:
        """
        Create an event from the given sequence of bytes.
        """
        data = data.decode()[:-1]
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
    to all clients at once.
    """
    eventReceived = Signal(Event)
    conns: list[socket.socket]
    msgQueue: Queue[Event]

    def __init__(self) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.conns = []

        self.msgQueue = Queue()

        self.sel = DefaultSelector()
        self.sock = socket.create_server(("localhost", PORT))
        self.sock.listen(5)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)
        self.shouldClose = False

    def run(self) -> None:
        """
        Run the server until it is closed. Select for the client connections
        and process the message queue repeatedly.
        """
        while not self.shouldClose:
            events = self.sel.select(0.001)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

            if not self.msgQueue.empty():
                e = self.msgQueue.get()
                data = e.toBytes()
                for conn in self.conns:
                    conn.send(data)

        self.sel.close()
        
        for conn in self.conns:
            conn.close()
        self.conns.clear()
        self.sock.close()

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
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.conns.append(conn)

    def read(self, sock: socket.socket, mask) -> None:
        """
        Read from a connection and emit the event that was received.
        """
        data = sock.recv(1024)

        if data:
            self.eventReceived.emit(Event.fromBytes(data))
        else:
            self.sel.unregister(sock)
            self.conns.remove(sock)
            sock.close()

    def close(self) -> None:
        """
        Initiate the shutdown of the server. Messages remaining in the queue
        are dropped.
        """
        self.shouldClose = True


class Client(QObject, QRunnable):
    eventReceived = Signal(Event)

    def __init__(self) -> None:
        """
        Initialize a new client. It connects to localhost:PORT.
        """
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.msgQueue: Queue[Event] = Queue()
        self.conn = socket.create_connection(("localhost", PORT))
        self.conn.settimeout(0.001)

        self.shouldClose = False

    def run(self) -> None:
        """
        Run the client until it is closed. Receive events and send events
        repeatedly.
        """
        while not self.shouldClose:
            timedOut = False
            try:
                data = self.conn.recv(1024)
            except socket.timeout:
                timedOut = True

            if not timedOut:
                if data is None:
                    self.conn.close()
                    break
                elif len(data) != 0:
                    event = Event.fromBytes(data)
                    print(event)
                    self.eventReceived.emit(event)

            if not self.msgQueue.empty():
                e = self.msgQueue.get()
                self.conn.send(e.toBytes())

        self.conn.close()

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
