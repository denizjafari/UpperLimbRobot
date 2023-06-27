import sys

from PySide6.QtWidgets import QApplication

from events import Server
from game_hosts.snake import SnakeGame, SnakeServerAdapter


if __name__ == "__main__":
    app = QApplication(sys.argv)

    server = Server()
    snakeGame = SnakeGame()
    adapter = SnakeServerAdapter(snakeGame)
    server.eventReceived.connect(adapter.eventReceived)

    snakeGame.show()
    server.start()

    code = app.exec()
    server.close()

    sys.exit(code)
