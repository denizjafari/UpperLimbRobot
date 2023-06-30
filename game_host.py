import sys

from PySide6.QtWidgets import QApplication

from events import Server
from game_hosts.pong import PongGame, PongGameWindow, PongServerAdapter
from game_hosts.snake import SnakeGame, SnakeServerAdapter


if __name__ == "__main__":
    app = QApplication(sys.argv)

    server = Server()

    #game = SnakeGame()
    #adapter = SnakeServerAdapter(game)

    game = PongGameWindow()
    adapter = PongServerAdapter(game)

    server.eventReceived.connect(adapter.eventReceived)

    game.show()
    server.start()

    code = app.exec()
    server.close()

    sys.exit(code)
