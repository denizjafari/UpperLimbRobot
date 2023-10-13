"""
The reach game implemented using the Qt framework. A player (or two) can move
around to catch apples

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

import random
import logging


from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QPaintEvent, \
    QKeyEvent, QImage

from app.protocols.events import Event, GameAdapter

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)


SQUARE_SIZE = 500
APPLE_SIZE = 40
PLAYER_SIZE = 40

# The speed of the game in ticks per second
TICK_SPEED = 50

# The default apple lifetime in seconds
APPLE_DEFAULT_LIFETIME = 5


class ScoreBoard:
    """
    Basic Scoreboard capable of tracking the scores for both sides,
    left and right.
    """
    score: int

    def __init__(self, screenSize: int) -> None:
        """
        Initialize the scoreboard.
        """
        self.score = 0
        self.screenSize = screenSize

    def paint(self, painter: QPainter) -> None:
        """
        Paint the scoreboard to an active painter.
        """
        rect = QRect(self.screenSize / 2 - 30, 0, 60, 30)
        painter.drawRect(rect)
        boundings = painter.boundingRect(rect, "Score")
        painter.drawText((self.screenSize - boundings.width()) / 2,
                         12,
                         "Score")

        scoreStr = str(self.score)
        boundings = painter.boundingRect(rect, scoreStr)
        painter.drawText((self.screenSize - boundings.width()) / 2,
                         25,
                         scoreStr)

class Apple:
    """
    An apple that needs to be caught by the player.
    """

    def __init__(self) -> None:
        """
        Initialize the apple at the top left corner.
        """
        self.x = 0
        self.y = 0
        self.maxLifetime = APPLE_DEFAULT_LIFETIME * TICK_SPEED
        self.lifetime = self.maxLifetime

    def paint(self, painter: QPainter) -> None:
        """
        Paint the apple to the painter.
        """
        target = QRect(self.x - APPLE_SIZE / 2, self.y - APPLE_SIZE / 2,
                       APPLE_SIZE, APPLE_SIZE)
        source = QRect(0, 0, appleImage.width(), appleImage.height())
        painter.setOpacity(self.lifetime / self.maxLifetime)
        painter.drawImage(target, appleImage, source)
        painter.setOpacity(1.0)
        
    def age(self) -> None:
        """
        Age the apple by dt milliseconds.
        """
        self.lifetime -= 1

    def centerX(self) -> int:
        """
        Return the x coordinate of the center of the apple.
        """
        return self.x
    
    def centerY(self) -> int:
        """
        Return the y coordinate of the center of the apple.
        """
        return self.y


class Player:
    """
    The player that is controlled by the user.
    """
    
    def __init__(self) -> None:
        """
        Initialize the player at the center of the board.
        """
        self.x = SQUARE_SIZE / 2
        self.y = SQUARE_SIZE / 2
        self.movingUp = False
        self.movingDown = False
        self.movingLeft = False
        self.movingRight = False

        self.speed = 4

    def paint(self, painter: QPainter) -> None:
        """
        Paint the player to the painter.
        """
        painter.setBrush(QBrush(QColor(0, 255, 0)))
        painter.drawRect(self.x - PLAYER_SIZE / 2, self.y - PLAYER_SIZE / 2,
                         PLAYER_SIZE, PLAYER_SIZE)

    def move(self) -> None:
        """
        Move the player according to the current key presses.
        """
        if self.movingUp:
            if self.y > 0:
                self.y -= self.speed
        elif self.movingDown:
            if self.y < SQUARE_SIZE:
                self.y += self.speed

        if self.movingLeft:
            if self.x > 0:
                self.x -= self.speed
        elif self.movingRight:
            if self.x < SQUARE_SIZE:
                self.x += self.speed

    def moveToX(self, relativeX: float) -> None:
        """
        Move the player to the specified relative position along the x axis.
        0.0 is the left edge of the board, 1.0 is the right edge.
        """
        if relativeX < 0.0:
            relativeX = 0.0
        elif relativeX > 1.0:
            relativeX = 1.0
        self.x = relativeX * SQUARE_SIZE


    def moveToY(self, relativeY: float) -> None:
        """
        Move the player to the specified relative position along the y axis.
        0.0 is the bottom edge of the board, 1.0 is the top edge.
        """
        if relativeY < 0.0:
            relativeY = 0.0
        elif relativeY > 1.0:
            relativeY = 1.0
        self.y = (1 - relativeY) * SQUARE_SIZE


    def centerX(self) -> int:
        """
        Return the x coordinate of the center of the player.
        """
        return self.x
    
    def centerY(self) -> int:
        """
        Return the y coordinate of the center of the player.
        """
        return self.y

    def canConsume(self, apple: Apple) -> bool:
        """
        Determine whether this player is close enough to the apple to consume
        it.
        """
        return abs(self.centerX() - apple.centerX()) < 30 \
            and abs(self.centerY() - apple.centerY()) < 30


class ReachBoard(QLabel):
    """
    The playing board for the reach game.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initilize the board with one apple and one player.
        """
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE
        self.setFixedSize(self.sideLength, self.sideLength)

        self.scoreBoard = ScoreBoard(self.sideLength)

        self.apples: list[Apple] = []
        self.apples.append(Apple())
        
        self.players = [Player()]

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // TICK_SPEED)
        self._timer.timeout.connect(self.updateState)
        self.isRunning = False
        self._timer.start()

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()


    def updateState(self) -> None:
        """
        Update the state of the game by moving the player and checking whether
        any player can consume an apple. Apples are also "aged" and when their
        remaining lifetime is too low, they are removed. Then repaint the board.
        """
        for player in self.players:
            player.move()

        for apple in self.apples:
            apple.age()
            if apple.lifetime <= 0:
                self.apples.remove(apple)
                self.addApple()
            else:
                for player in self.players:
                    if player.canConsume(apple):
                        self.scoreBoard.score += 1
                        self.apples.remove(apple)
                        self.addApple()

        self.repaint()


    def addApple(self) -> None:
        """
        Add an apple to a random position on the board.
        """
        apple = Apple()

        apple.x = random.randint(0, SQUARE_SIZE - APPLE_SIZE)
        apple.y = random.randint(0, SQUARE_SIZE - APPLE_SIZE)

        self.apples.append(apple)


    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the board.
        """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, True)

        for apple in self.apples:
            apple.paint(painter)

        for player in self.players:
            player.paint(painter)

        pen = QPen()
        pen.setColor(QColor(0, 0, 0))
        pen.setWidth(5)
        painter.setPen(pen)
        painter.setBrush(QBrush())
        painter.drawRect(0, 0, SQUARE_SIZE, SQUARE_SIZE)

        self.scoreBoard.paint(painter)

        painter.end()

    
    def keyPressEvent(self, e: QKeyEvent) -> None:
        """
        Handle key presses.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.players[0].movingUp = True
        elif key == Qt.Key_S:
            self.players[0].movingDown = True
        elif key == Qt.Key_A:
            self.players[0].movingLeft = True
        elif key == Qt.Key_D:
            self.players[0].movingRight = True

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        """
        Handle key releases.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.players[0].movingUp = False
        elif key == Qt.Key_S:
            self.players[0].movingDown = False
        elif key == Qt.Key_A:
            self.players[0].movingLeft = False
        elif key == Qt.Key_D:
            self.players[0].movingRight = False


class ReachWindow(QWidget):
    """
    The window for the reach game. Contains the board itself and control buttons.
    """
    def __init__(self, board: ReachBoard) -> None:
        """
        Initialize the window with the given board.
        """
        QWidget.__init__(self)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.board = board
        self.vLayout.addWidget(board, alignment=Qt.AlignCenter)


class ReachServerAdapter(GameAdapter):
    """
    A wrapper around the reach window game that allows the game to be controlled
    by a pose tracking client.
    """
    def __init__(self, window: ReachWindow) -> None:
        """
        Initialize the adapter with the given window.
        """
        GameAdapter.__init__(self)

        self.window = window
        self.window.show()

    def widget(self) -> QWidget:
        """
        Return the window widget that is wrapped.
        """
        return self.window
    
    def eventReceived(self, e: Event) -> None:
        module_logger.debug("Received event: " + str(e))
        if e.name == "moveToY":
            self.window.board.players[0].moveToY(float(e.payload[0]))

appleImage = QImage()
appleImage.load("assets/graphics/apple.png")
