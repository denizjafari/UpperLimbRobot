"""
The pong game implemented using the Qt framework.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Optional

import sys

from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, \
    QPushButton
from PySide6.QtGui import QPaintEvent, QPainter, QKeyEvent

from events import Event


SQUARE_SIZE = 300
DEFAULT_PADDLE_SIZE = 50
DEFAULT_PADDLE_THICKNESS = 10
DEFAULT_PADDLE_SPEED = 5

NEUTRAL = 0
LEFT = 1
RIGHT = 2
UP = 3
DOWN = 4


class Paddle:
    """
    One paddle that can be moved up and down by the player.
    """
    def __init__(self, side:int=LEFT) -> None:
        """
        Initialize the paddle.
        """
        self.size = DEFAULT_PADDLE_SIZE
        self.position = SQUARE_SIZE // 2
        self.thickness = DEFAULT_PADDLE_THICKNESS
        self.side = side
        self.speed = DEFAULT_PADDLE_SPEED
        self.movingUp = False
        self.movingDown = False
        self.useVariableSpeed = False

    def topEdge(self) -> float:
        """
        Return the top y coordinate of the paddle.
        """
        return self.position - self.size // 2
    
    def bottomEdge(self) -> float:
        """
        Return the bottom y coordinate of the paddle.
        """
        return self.position + self.size // 2
    
    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether the ball is hit by the paddle.
        """
        if self.side == LEFT:
            inXRange = ball.leftEdge() <= self.thickness
        else:
            inXRange = ball.rightEdge() >= SQUARE_SIZE - self.thickness
        
        inYRange = self.bottomEdge() >= ball.centerY() >= self.topEdge()
            
        return inXRange and inYRange
    
    def move(self) -> None:
        """
        Move the paddle according to the moving up and down attributes.
        """
        if self.useVariableSpeed:
            self.position += self.speed * self.speedMultiplier
        else:
            if self.movingUp:
                self.position -= self.speed
            elif self.movingDown:
                self.position += self.speed

    def moveTo(self, relativePosition: float) -> None:
        self.position = (1 - relativePosition) * SQUARE_SIZE

    def setSpeedMultiplier(self, speedMultiplier: float) -> None:
        self.speedMultiplier = speedMultiplier

    def paint(self, painter: QPainter) -> None:
        """
        Paint the paddle to an active painter.
        """
        painter.fillRect(0 if self.side == LEFT else SQUARE_SIZE - self.thickness,
                         self.position - self.size // 2,
                         self.thickness,
                         self.size,
                         Qt.black)
        

class Ball:
    """
    The ball that bounds off the walls and paddles.
    """
    def __init__(self):
        """
        Initialize the ball.
        """
        self.radius = 10
        self.position = SQUARE_SIZE // 2, SQUARE_SIZE // 2
    
    def leftEdge(self) -> float:
        """
        Return the left x coordinate of the ball.
        """
        return self.position[0] - self.radius
    
    def rightEdge(self) -> float:   
        """
        Return the right x coordinate of the ball.
        """
        return self.position[0] + self.radius
    
    def centerY(self) -> float:
        """
        Return the y coordinate at the center of the ball.
        """
        return self.position[1]
    
    def bottomEdge(self) -> float:
        """
        Return the y coordinate at the bottom of the ball.
        """
        return self.position[1] + self.radius
    
    def topEdge(self) -> float:
        """
        Return the y coordinate at the tio of the ball.
        """
        return self.position[1] - self.radius
    
    def move(self, x, y):
        """
        Move the ball by the given x and y amounts.
        """
        self.position = self.position[0] + x, self.position[1] + y

    def paint(self, painter: QPainter) -> None:
        """
        Paint the ball to an active painter.
        """
        painter.drawEllipse(self.position[0] - self.radius,
                            self.position[1] - self.radius,
                            self.radius * 2,
                            self.radius * 2)
        

class ScoreBoard:
    """
    Basic Scoreboard capable of tracking the scores for both sides,
    left and right.
    """
    scoreLeft: int
    scoreRight: int

    def __init__(self, screenSize: int) -> None:
        self.scoreLeft = 0
        self.scoreRight = 0
        self.screenSize = screenSize

    def paint(self, painter: QPainter) -> None:
        rect = QRect(self.screenSize / 2 - 30, 0, 60, 30)
        painter.drawRect(rect)
        boundings = painter.boundingRect(rect, "Score")
        painter.drawText((self.screenSize - boundings.width()) / 2,
                         12,
                         "Score")

        scoreStr = str(self.scoreLeft) + " : " + str(self.scoreRight)
        boundings = painter.boundingRect(rect, scoreStr)
        painter.drawText((self.screenSize - boundings.width()) / 2,
                         25,
                         scoreStr)

class PongGame(QLabel):
    """
    The Pong Game. Handles the game logic and displays the result.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE

        self.ball = Ball()
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.scoreBoard = ScoreBoard(self.sideLength)

        self.setFixedSize(self.sideLength, self.sideLength)
        self.ballDirection = 1, 2
        self.lostGame = False
        self.debounce = ""

        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self.updateState)
        self.isRunning = False
        self._timer.start()

        self.setFocus()

    def updateState(self) -> None:
        """
        Move the ball and paddles and check for collisions. Then paint the new
        state.
        """
        if self.ball.leftEdge() <= 0 \
            or self.ball.rightEdge() >= self.sideLength:
            self.stop()
        elif self.ball.topEdge() <= 0 \
            or self.ball.bottomEdge() >= self.sideLength:
            self.ballDirection = self.ballDirection[0], \
                -self.ballDirection[1]
        elif self.leftPaddle.isHit(self.ball) and self.debounce != "left":
            self.scoreBoard.scoreLeft += 1
            self.debounce = "left"
            self.ballDirection = abs(self.ballDirection[0]), \
                self.ballDirection[1]
        elif self.rightPaddle.isHit(self.ball) and self.debounce != "right":
            self.scoreBoard.scoreRight += 1
            self.debounce = "right"
            self.ballDirection = -abs(self.ballDirection[0]), \
                self.ballDirection[1]
        
        if self.isRunning:
            self.ball.move(*self.ballDirection)

        self.leftPaddle.move()
        self.rightPaddle.move()

        self.repaint()

    def start(self) -> None:
        """
        Start the game or resume it if it is paused.
        """
        #self._timer.start()
        self.isRunning = True

    def stop(self) -> None:
        """
        Pause the game.
        """
        #self._timer.stop()
        self.isRunning = False

    def toggle(self) -> None:
        """
        Toggle the game between running and paused.
        """
        if self.isRunning:
            self.stop()
        else:
            self.start()

        self.setFocus()

    def reset(self) -> None:
        self.ballDirection = 1, 2
        self.lostGame = False
        self.isRunning = False

        self.ball = Ball()
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)

        self.setFocus()


    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the game state to the screen.
        """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, True)

        self.scoreBoard.paint(painter)

        self.ball.paint(painter)
        self.leftPaddle.paint(painter)
        self.rightPaddle.paint(painter)
        
        painter.end()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """
        Handle key presses.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.leftPaddle.movingUp = True
        elif key == Qt.Key_S:
            self.leftPaddle.movingDown = True
        elif key == Qt.Key_Up:
            self.rightPaddle.movingUp = True
        elif key == Qt.Key_Down:
            self.rightPaddle.movingDown = True

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        """
        Handle key releases.
        """
        key = e.key()
        if key == Qt.Key_W:
            self.leftPaddle.movingUp = False
        elif key == Qt.Key_S:
            self.leftPaddle.movingDown = False
        elif key == Qt.Key_Up:
            self.rightPaddle.movingUp = False
        elif key == Qt.Key_Down:
            self.rightPaddle.movingDown = False


class PongGameWindow(QWidget):
    def __init__(self) -> None:
        """
        Initialize the window for playing pong.
        """
        QWidget.__init__(self)
        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.game = PongGame()
        self.vLayout.addWidget(self.game)

        self.toggleButton = QPushButton("Toggle")
        self.toggleButton.clicked.connect(self.game.toggle)
        self.vLayout.addWidget(self.toggleButton)

        self.toggleButton = QPushButton("Reset")
        self.toggleButton.clicked.connect(self.game.reset)
        self.vLayout.addWidget(self.toggleButton)

class PongServerAdapter:
    def __init__(self, pongGame: PongGameWindow) -> None:
        self.window = pongGame
    
    def eventReceived(self, e: Event) -> None:
        leftPaddle = self.window.game.leftPaddle
        if e.name == "clearMovement":
            leftPaddle.movingUp = False
            leftPaddle.movingDown = False
            leftPaddle.useVariableSpeed = False
            leftPaddle.setSpeedMultiplier(0.0)
        elif e.name == "moveTo":
            leftPaddle.moveTo(float(e.payload[0]))
        elif e.name == "setSpeed":
            leftPaddle.useVariableSpeed = True
            leftPaddle.setSpeedMultiplier(float(e.payload[0]))
        elif e.name == "moveUp":
            leftPaddle.useVariableSpeed = False
            leftPaddle.movingUp = True
            leftPaddle.movingDown = False
        elif e.name == "neutral":
            leftPaddle.useVariableSpeed = False
            leftPaddle.movingUp = False
            leftPaddle.movingDown = False
        elif e.name == "moveDown":
            leftPaddle.useVariableSpeed = False
            leftPaddle.movingDown= True
            leftPaddle.movingUp = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PongGameWindow()

    window.show()
    sys.exit(app.exec())
