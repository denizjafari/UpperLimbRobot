from typing import Optional
from random import randrange

from freegames import vector
from PySide6.QtCore import QTimer, Qt, QRect, QPoint, QSize
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPaintEvent, QPixmap, QPainter


SQUARE_SIZE = 30
SQUARE_COUNT = 20

class SnakeGame(QLabel):
    """
    The Snake Game. Handles the game logic and displays the result.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE * SQUARE_COUNT
        center = self.sideLength // 2

        self.food = vector(center, center)
        self.snake = [vector(center, center)]
        self.aim = vector(0, -SQUARE_SIZE)

        self.setFixedSize(self.sideLength, self.sideLength)
        self.lostGame = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.move)
        self.timer.start()

    def turnLeft(self) -> None:
        """
        Turn the snake left.
        """
        if self.aim.x == 0 and self.aim.y == SQUARE_SIZE:
            self.change(SQUARE_SIZE, 0)
        elif self.aim.x == 0 and self.aim.y == -SQUARE_SIZE:
            self.change(-SQUARE_SIZE, 0)
        elif self.aim.x == SQUARE_SIZE and self.aim.y == 0:
            self.change(0, -SQUARE_SIZE)
        elif self.aim.x == -SQUARE_SIZE and self.aim.y == 0:
            self.change(0, SQUARE_SIZE)
    
    def turnRight(self) -> None:
        """
        Turn the snake right.
        """
        if self.aim.x == 0 and self.aim.y == SQUARE_SIZE:
            self.change(-SQUARE_SIZE, 0)
        elif self.aim.x == 0 and self.aim.y == -SQUARE_SIZE:
            self.change(SQUARE_SIZE, 0)
        elif self.aim.x == SQUARE_SIZE and self.aim.y == 0:
            self.change(0, SQUARE_SIZE)
        elif self.aim.x == -SQUARE_SIZE and self.aim.y == 0:
            self.change(0, -SQUARE_SIZE)

    def change(self, x, y):
        """
        Change snake direction.
        """
        self.aim.x = x
        self.aim.y = y

    def inside(self, head):
        """R
        eturn True if head inside boundaries.
        """
        return 0 <= head.x <= self.sideLength and 0 <= head.y <= self.sideLength
    
    def head(self) -> vector:
        """
        Return the head of the snake.
        """
        return self.snake[-1]
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the snake and food if the game is not lost. If the game is lost,
        paint the head red instead.
        """
        painter = QPainter(self)

        for body in self.snake:
            painter.fillRect(body.x, body.y, SQUARE_SIZE, SQUARE_SIZE, Qt.black)

        if self.lostGame:
            painter.fillRect(self.head().x, self.head().y, SQUARE_SIZE, SQUARE_SIZE,  Qt.red)
        else:
            painter.fillRect(self.food.x, self.food.y, SQUARE_SIZE, SQUARE_SIZE,  Qt.green)
        
        painter.end()

    def move(self):
        """
        Move snake forward one segment.
        """
        if self.lostGame:
            return
        
        head = self.snake[-1].copy()
        head.move(self.aim)

        if not self.inside(head) or head in self.snake:
            self.lostGame = True
        else:
            self.snake.append(head)

            if head == self.food:
                self.food.x = randrange(1, SQUARE_COUNT) * SQUARE_SIZE
                self.food.y = randrange(1, SQUARE_COUNT) * SQUARE_SIZE
            else:
                self.snake.pop(0)

        self.repaint()
