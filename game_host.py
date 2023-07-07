import sys

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, \
    QStackedWidget, QPushButton

from events import Server
from game_hosts.pong import PongGameWindow, PongServerAdapter
from game_hosts.snake import SnakeGame, SnakeServerAdapter


def addSnakeGame(window: QStackedWidget, server: Server) -> None:
    global game, adapter
    game = SnakeGame()
    adapter = SnakeServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    window.addWidget(game)
    window.setCurrentWidget(game)

def addPongGame(window: QStackedWidget, server: Server) -> None:
    global game, adapter
    game = PongGameWindow()
    adapter = PongServerAdapter(game)
    server.eventReceived.connect(adapter.eventReceived)
    window.addWidget(game)
    window.setCurrentWidget(game)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QStackedWidget()

    selector = QWidget()
    selectorLayout = QVBoxLayout()
    selector.setLayout(selectorLayout)
    window.addWidget(selector)
    
    server = Server()
    server.start()

    snakeButton = QPushButton("Snake")
    snakeButton.clicked.connect(lambda: addSnakeGame(window, server))
    selectorLayout.addWidget(snakeButton)

    pongButton = QPushButton("Pong")
    pongButton.clicked.connect(lambda: addPongGame(window, server))
    selectorLayout.addWidget(pongButton)

    window.show()

    code = app.exec()
    server.close()

    sys.exit(code)
