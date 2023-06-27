import sys

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, \
    QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import QThreadPool
from events import Client, Server, Event


def send(endpoint, event: Event) -> None:
    print(event.name)
    endpoint.send(event)


if __name__ == "__main__":
    app = QApplication()
    window = QWidget()

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        endpoint = Server()
        title = "Server"
    else:
        endpoint = Client()
        QThreadPool.globalInstance().start(endpoint)
        title = "Client"

    vBox = QVBoxLayout()
    window.setLayout(vBox)

    hBox = QHBoxLayout()
    vBox.addLayout(hBox)

    edit = QLineEdit()
    hBox.addWidget(edit)

    submit = QPushButton("Send")
    submit.clicked.connect(lambda: send(endpoint, Event(edit.text())))
    hBox.addWidget(submit)

    label = QLabel()
    endpoint.eventReceived.connect(lambda e: label.setText(e.name))
    vBox.addWidget(label)

    window.setWindowTitle(title)
    window.show()
    code = app.exec()
    endpoint.close()
    sys.exit(code)
