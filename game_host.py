"""
Game Host from which games can be launched and clients can connect to.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import sys
from typing import Optional
import logging

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, \
    QStackedWidget, QPushButton, QFormLayout, QLineEdit
from PySide6.QtGui import QIntValidator

from events import GameAdapter, Server
from game_hosts.pong import PongGameWindow, PongServerAdapter, \
    SharedScreenPongGame, SoloBallStormPongGame, SplitScreenPongGame, TwoPlayerPongGame
from game_hosts.reach import ReachBoard, ReachServerAdapter, ReachWindow
from game_hosts.snake import SnakeGame, SnakeServerAdapter


def addGame(    window: QStackedWidget,
                adapter: GameAdapter,
                address: tuple[Optional[str], int]) -> None:
    """
    Add the snake game to the stacked widget window. Start the event server
    and connect it to the game.
    """
    global server, gameAdapter
    gameAdapter = adapter
    server = Server(address)
    server.start()
    server.eventReceived.connect(adapter.eventReceived)
    adapter.eventReady.connect(server.send)
    window.addWidget(adapter.widget())
    window.setCurrentWidget(adapter.widget())


if __name__ == "__main__":
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(loggingHandler)

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
    portField.setText("9876")
    formLayout.addRow("Port", portField)

    snakeButton = QPushButton("Snake")
    snakeButton.clicked.connect(lambda:
                                addGame(window,
                                        SnakeServerAdapter(SnakeGame()),
                                             address=(hostField.text(),
                                                      int(portField.text()))))
    selectorLayout.addWidget(snakeButton)

    soloPongButton = QPushButton("Solo Pong")
    soloPongButton.clicked.connect(lambda:
                               addGame(window,
                                       PongServerAdapter(PongGameWindow(SoloBallStormPongGame())),
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(soloPongButton)

    pongButton = QPushButton("Pong")
    pongButton.clicked.connect(lambda:
                               addGame(window,
                                       PongServerAdapter(PongGameWindow(TwoPlayerPongGame())),
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(pongButton)

    sharedPongButton = QPushButton("Shared Pong")
    sharedPongButton.clicked.connect(lambda:
                               addGame(window,
                                       PongServerAdapter(PongGameWindow(SharedScreenPongGame())),
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(sharedPongButton)

    splitPongButton = QPushButton("Split Pong")
    splitPongButton.clicked.connect(lambda:
                               addGame(window,
                                       PongServerAdapter(PongGameWindow(SplitScreenPongGame())),
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(splitPongButton)
    
    reachButton = QPushButton("Reach")
    reachButton.clicked.connect(lambda:
                               addGame(window,
                                       ReachServerAdapter(ReachWindow(ReachBoard())),
                                           address=(hostField.text(),
                                                    int(portField.text()))))
    selectorLayout.addWidget(reachButton)

    window.show()

    code = app.exec()

    if isinstance(server, Server):
        server.close()

    sys.exit(code)
