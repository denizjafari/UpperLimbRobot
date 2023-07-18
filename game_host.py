"""
Game Host from which games can be launched and clients can connect to.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import sys
from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, \
    QStackedWidget, QPushButton, QFormLayout, QLineEdit
from PySide6.QtGui import QIntValidator

from events import Server
from game_hosts.pong import PongGameWindow, PongServerAdapter
from game_hosts.snake import SnakeGame, SnakeServerAdapter


def addSnakeGame(window: QStackedWidget,
                 address: tuple[Optional[str], int]) -> None:
    """
    Add the snake game to the stacked widget window. Start the event server
    and connect it to the game.
    """
    global game, adapter, server
    server = Server(address)
    server.start()
    game = SnakeGame()
    adapter = SnakeServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    window.addWidget(game)
    window.setCurrentWidget(game)

def addPongGame(window: QStackedWidget,
                address: tuple[Optional[str], int]) -> None:
    """
    Add the pong game to the stacked widget window. Start the event server
    and connect it to the game.
    """
    global game, adapter, server
    server = Server(address)
    server.start()
    game = PongGameWindow()
    adapter = PongServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    adapter.eventReady.connect(server.send)
    window.addWidget(game)
    window.setCurrentWidget(game)

if __name__ == "__main__":
    server = None
    app = QApplication(sys.argv)

    window = QStackedWidget()

    selector = QWidget()
    selectorLayout = QVBoxLayout()
    selector.setLayout(selectorLayout)
    window.addWidget(selector)

    formLayout = QFormLayout()
    selectorLayout.addLayout(formLayout)

    hostField = QLineEdit()
    hostField.setText("localhost")
    formLayout.addRow("Host", hostField)

    portField = QLineEdit()
    portField.setValidator(QIntValidator(1024, 65535))
    portField.setText("3000")
    formLayout.addRow("Port", portField)

    snakeButton = QPushButton("Snake")
    snakeButton.clicked.connect(lambda:
                                addSnakeGame(window,
                                             address=(hostField.text(),
                                                      int(portField.text()))))
    selectorLayout.addWidget(snakeButton)

    pongButton = QPushButton("Pong")
    pongButton.clicked.connect(lambda:
                               addPongGame(window,
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(pongButton)

    window.show()

    code = app.exec()

    if isinstance(server, Server):
        server.close()

    sys.exit(code)
