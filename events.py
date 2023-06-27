from __future__ import annotations
from typing import Optional

import selectors
from selectors import DefaultSelector
import socket
from time import sleep

from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool
from queue import Queue


PORT = 3000


class Event:
    def __init__(self, name: str, payload: Optional[list] = None) -> None:
        self.name = name
        self.payload = payload

    def toBytes(self) -> bytes:
        if self.payload is None or len(self.payload) == 0:
            return f"{self.name}\n".encode()
        else:
            return f"{self.name}:{':'.join(self.payload)}\n".encode()
        
    @staticmethod
    def fromBytes(data: bytes) -> Event:
        data = data.decode()[:-1]
        if ":" in data:
            data = data.split(":")
            name = data[0]
            payload = data[1:]
            return Event(name, payload)
        else:
            return Event(data)
        
    def __str__(self) -> None:
        return f"{self.name}:{self.payload}"
        

class ServerReceiver(QObject, QRunnable):
    eventReceived = Signal(Event)

    def __init__(self, conns: list[socket.socket]) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.sel = DefaultSelector()
        self.sock = socket.create_server(("localhost", PORT))
        self.sock.listen(5)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)
        self.conns = conns
        self.shutdown = False

    def run(self) -> None:
        while not self.shutdown:
            events = self.sel.select(0.02)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

        self.sel.close()

    def accept(self, sock: socket.socket, mask) -> None:
        conn, addr = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.conns.append(conn)

    def read(self, sock: socket.socket, mask) -> None:
        data = sock.recv(1000)

        if data:
            self.eventReceived.emit(Event.fromBytes(data))
        else:
            self.sel.unregister(sock)
            self.conns.remove(sock)
            sock.close()

    def close(self) -> None:
        self.shutdown = True

class ServerSender(QObject, QRunnable):
    def __init__(self, conns: list[socket.socket]) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.conns = conns
        self.shutdown = False

    def run(self) -> None:
        while not self.shutdown:
            sleep(1)

    def emit(self, event: Event) -> None:
        data = event.toBytes()

        for conn in self.conns:
            conn.send(data)

    def close(self) -> None:
        self.shutdown = True

        
class Server(QObject, QRunnable):
    eventReceived = Signal(Event)
    conns: list[socket.socket]

    def __init__(self) -> None:
        QObject.__init__(self)
        self.conns = []
        self.serverReceiver = ServerReceiver(self.conns)
        self.serverSender = ServerSender(self.conns)

        self.serverReceiver.eventReceived.connect(self.eventReceived)

        pool = QThreadPool.globalInstance()
        pool.start(self.serverReceiver)
        pool.start(self.serverSender)

    def send(self, e: Event) -> None:
        self.serverSender.emit(e)

    def close(self) -> None:
        for conn in self.conns:
            conn.close()
        self.conns.clear()

        self.serverReceiver.close()
        self.serverSender.close()


class Client(QObject, QRunnable):
    eventReceived = Signal(Event)

    def __init__(self) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.msgQueue: Queue[Event] = Queue()
        self.conn = socket.create_connection(("localhost", PORT))
        self.conn.settimeout(0.001)

        self.shutdown = False

    def run(self) -> None:
        while not self.shutdown:
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

    def send(self, e: Event) -> None:
        self.msgQueue.put(e)

    def close(self) -> None:
        self.shutdown = True
