import sys, time

from events import Server, Client, Event

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, \
    QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import QThreadPool

if __name__ == "__main__":
    app = QApplication()
    window = QWidget()

    server = Server()
    client = Client()
    
    QThreadPool.globalInstance().start(client)
    QThreadPool.globalInstance().start(server)

    def timeEnd():
        global endTime
        endTime = time.time()
        print(endTime - startTime)

    def timeStart():
        global startTime
        startTime = time.time()
        client.send(Event("test"))

    server.eventReceived.connect(timeEnd)

    widget = QPushButton("Send")
    widget.clicked.connect(timeStart)
    widget.show()

    sys.exit(app.exec())
