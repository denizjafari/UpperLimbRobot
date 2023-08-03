"""
The reach game implemented using the Qt framework. A player (or two) can move
around to catch apples

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""


import random
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPainter, QBrush, QColor, QPaintEvent, QKeyEvent

from events import GameAdapter


SQUARE_SIZE = 500
APPLE_SIZE = 20

class Apple:
    def __init__(self) -> None:
        self.x = 0
        self.y = 0

    def paint(self, painter: QPainter) -> None:
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        painter.drawRect(self.x, self.y, APPLE_SIZE, APPLE_SIZE)

    def centerX(self) -> int:
        return self.x + APPLE_SIZE / 2
    
    def centerY(self) -> int:
        return self.y + APPLE_SIZE / 2


class Player:
    def __init__(self) -> None:
        self.x = SQUARE_SIZE / 2
        self.y = SQUARE_SIZE / 2
        self.movingUp = False
        self.movingDown = False
        self.movingLeft = False
        self.movingRight = False

        self.speed = 4

    def paint(self, painter: QPainter) -> None:
        painter.setBrush(QBrush(QColor(0, 255, 0)))
        painter.drawRect(self.x, self.y, 40, 40)

    def move(self) -> None:
        if self.movingUp:
            self.y -= self.speed
        elif self.movingDown:
            self.y += self.speed

        if self.movingLeft:
            self.x -= self.speed
        elif self.movingRight:
            self.x += self.speed

    def centerX(self) -> int:
        return self.x + 20
    
    def centerY(self) -> int:
        return self.y + 20

    def canConsume(self, apple: Apple) -> bool:
        return abs(self.centerX() - apple.centerX()) < 30 and abs(self.centerY() - apple.centerY()) < 30


class ReachBoard(QLabel):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE
        self.setFixedSize(self.sideLength, self.sideLength)

        self.apples: list[Apple] = []
        self.apples.append(Apple())
        
        self.player = Player()

        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self.updateState)
        self.isRunning = False
        self._timer.start()

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()


    def updateState(self) -> None:
        self.player.move()

        for apple in self.apples:
            if self.player.canConsume(apple):
                self.apples.remove(apple)
                self.addApple()

        self.repaint()


    def addApple(self) -> None:
        apple = Apple()

        apple.x = random.randint(0, SQUARE_SIZE - APPLE_SIZE)
        apple.y = random.randint(0, SQUARE_SIZE - APPLE_SIZE)

        self.apples.append(apple)


    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, True)

        for apple in self.apples:
            apple.paint(painter)

        self.player.paint(painter)

        painter.end()

    
    def keyPressEvent(self, e: QKeyEvent) -> None:
        """
        Handle key presses.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.player.movingUp = True
        elif key == Qt.Key_S:
            self.player.movingDown = True
        elif key == Qt.Key_A:
            self.player.movingLeft = True
        elif key == Qt.Key_D:
            self.player.movingRight = True

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        """
        Handle key releases.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.player.movingUp = False
        elif key == Qt.Key_S:
            self.player.movingDown = False
        elif key == Qt.Key_A:
            self.player.movingLeft = False
        elif key == Qt.Key_D:
            self.player.movingRight = False


class ReachWindow(QWidget):
    def __init__(self, board: ReachBoard) -> None:
        QWidget.__init__(self)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.board = board
        self.vLayout.addWidget(board)



class ReachServerAdapter(GameAdapter):
    def __init__(self, window: ReachWindow) -> None:
        GameAdapter.__init__(self)

        self.window = window

        self.window.show()

    def widget(self) -> QWidget:
        return self.window
