from typing import Optional
from random import randrange

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPaintEvent, QPainter


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

        self.food = center, center
        self.snake = [(center, center)]
        self.aim = 0, -SQUARE_SIZE

        self.setFixedSize(self.sideLength, self.sideLength)
        self.lostGame = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.move)
        self._timer.start()

    def turnLeft(self) -> None:
        """
        Turn the snake left.
        """
        if self.aim[0] == 0 and self.aim[1] == SQUARE_SIZE:
            self.change(SQUARE_SIZE, 0)
        elif self.aim[0] == 0 and self.aim[1] == -SQUARE_SIZE:
            self.change(-SQUARE_SIZE, 0)
        elif self.aim[0] == SQUARE_SIZE and self.aim[1] == 0:
            self.change(0, -SQUARE_SIZE)
        elif self.aim[0] == -SQUARE_SIZE and self.aim[1] == 0:
            self.change(0, SQUARE_SIZE)
    
    def turnRight(self) -> None:
        """
        Turn the snake right.
        """
        if self.aim[0] == 0 and self.aim[1] == SQUARE_SIZE:
            self.change(-SQUARE_SIZE, 0)
        elif self.aim[0] == 0 and self.aim[1] == -SQUARE_SIZE:
            self.change(SQUARE_SIZE, 0)
        elif self.aim[0] == SQUARE_SIZE and self.aim[1] == 0:
            self.change(0, SQUARE_SIZE)
        elif self.aim[0] == -SQUARE_SIZE and self.aim[1] == 0:
            self.change(0, -SQUARE_SIZE)

    def setTimerInterval(self, timerInterval: int) -> None:
        """
        Set the wait interval between snake movements.
        """
        self._timer.setInterval(timerInterval)

    def change(self, x, y):
        """
        Change snake direction.
        """
        self.aim = (x, y)

    def inside(self, head):
        """
        Return True if head inside boundaries.
        """
        return 0 <= head[0] <= self.sideLength and 0 <= head[1] <= self.sideLength
    
    def head(self) -> tuple[int, int]:
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
            painter.fillRect(body[0], body[1], SQUARE_SIZE, SQUARE_SIZE, Qt.black)

        if self.lostGame:
            painter.fillRect(self.head()[0], self.head()[1], SQUARE_SIZE, SQUARE_SIZE,  Qt.red)
        else:
            painter.fillRect(self.food[0], self.food[1], SQUARE_SIZE, SQUARE_SIZE,  Qt.green)
        
        painter.end()

    def move(self):
        """
        Move snake forward one segment.
        """
        if not self.lostGame:
            head = self.head()[0] + self.aim[0], self.head()[1] + self.aim[1]

            if not self.inside(head) or head in self.snake:
                self.lostGame = True
            else:
                self.snake.append(head)

                if head == self.food:
                    self.food = randrange(1, SQUARE_COUNT) * SQUARE_SIZE, \
                        randrange(1, SQUARE_COUNT) * SQUARE_SIZE
                else:
                    self.snake.pop(0)

        self.repaint()
