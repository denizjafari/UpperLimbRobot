from random import randrange
from turtle import *

from freegames import square, vector
from PySide6.QtCore import QRunnable

class SnakeGame(QRunnable):
    def __init__(self) -> None:
        QRunnable.__init__(self)
        self.food = vector(0, 0)
        self.snake = [vector(10, 0)]
        self.aim = vector(0, -10)

        setup(420, 420, 370, 0)
        hideturtle()
        tracer(False)
        listen()

    def run(self):
        self.move()
        done()

    def change(self, x, y):
        """Change snake direction."""
        self.aim.x = x
        self.aim.y = y


    def inside(self, head):
        """Return True if head inside boundaries."""
        return -200 < head.x < 190 and -200 < head.y < 190


    def move(self):
        """Move snake forward one segment."""
        head = self.snake[-1].copy()
        head.move(self.aim)

        if not self.inside(head) or head in self.snake:
            square(head.x, head.y, 9, 'red')
            self.update()
            return

        self.snake.append(head)

        if head == self.food:
            self.food.x = randrange(-15, 15) * 10
            self.food.y = randrange(-15, 15) * 10
        else:
            self.snake.pop(0)

        clear()

        for body in self.snake:
            square(body.x, body.y, 9, 'black')

        square(self.food.x, self.food.y, 9, 'green')
        self.update()
        ontimer(self.move, 200)
