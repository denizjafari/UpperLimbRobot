import sys

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, \
    QStackedWidget, QPushButton

from events import Server
from game_hosts.pong import PongGameWindow, PongServerAdapter
from game_hosts.snake import SnakeGame, SnakeServerAdapter


def addSnakeGame(window: QStackedWidget) -> None:
    game = SnakeGame()
    adapter = SnakeServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    window.addWidget(game)
    window.setCurrentWidget(game)

def addPongGame(window: QStackedWidget) -> None:
    game = PongGameWindow()
    adapter = PongServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    window.addWidget(game)
    window.setCurrentWidget(game)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    server = Server()

    window = QStackedWidget()

    selector = QWidget()
    selectorLayout = QVBoxLayout()
    selector.setLayout(selectorLayout)
    window.addWidget(selector)

    snakeButton = QPushButton("Snake")
    snakeButton.clicked.connect(lambda: addSnakeGame(window))
    selectorLayout.addWidget(snakeButton)

    pongButton = QPushButton("Pong")
    pongButton.clicked.connect(lambda: addPongGame(window))
    selectorLayout.addWidget(pongButton)

    server.start()
    window.show()

    code = app.exec()
    server.close()

    sys.exit(code)
