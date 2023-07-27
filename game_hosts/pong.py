"""
The pong game implemented using the Qt framework.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Optional

import sys
import logging
import math

from PySide6.QtCore import QTimer, Qt, QRect, Signal
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, \
    QPushButton
from PySide6.QtGui import QPaintEvent, QPainter, QKeyEvent

from events import Event, GameAdapter


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

SQUARE_SIZE = 300
DEFAULT_PADDLE_SIZE = 50
DEFAULT_PADDLE_THICKNESS = 10
DEFAULT_PADDLE_SPEED = 5

NEUTRAL = 0
LEFT = 1
RIGHT = 2
BOTTOM = 3
TOP = 4


class Paddle:
    """
    One paddle that can be moved up and down by the player.
    """
    def __init__(self, side:int=LEFT, active: bool = True) -> None:
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

        self._active = active

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
    
    def leftEdge(self) -> float:
        """
        Return the left x coordinate of the paddle.
        """
        return self.thickness
    
    def rightEdge(self) -> float:
        """
        Return the bottom y coordinate of the paddle.
        """
        return SQUARE_SIZE - self.thickness
    
    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether the ball is hit by the paddle.
        """
        if not self.active(): return False
        if self.side == LEFT:
            inXRange = ball.leftEdge() <= self.leftEdge()
        else:
            inXRange = ball.rightEdge() >= self.rightEdge()
        
        inYRange = self.bottomEdge() >= ball.centerY() >= self.topEdge()
            
        return inXRange and inYRange
    
    def move(self) -> None:
        """
        Move the paddle according to the moving up and down attributes.
        """
        if not self.active(): return

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
        if not self.active(): return
        painter.fillRect(0 if self.side == LEFT else SQUARE_SIZE - self.thickness,
                         self.position - self.size // 2,
                         self.thickness,
                         self.size,
                         Qt.black)
        
    def active(self) -> bool:
        return self._active
    
    def setActive(self, active: bool) -> bool:
        self._active = active

class HorizontalPaddle(Paddle):
    def leftEdge(self) -> float:
        return self.position - self.size // 2
    
    def rightEdge(self) -> float:
        return self.position + self.size // 2
    
    def topEdge(self) -> float:
        return SQUARE_SIZE - self.thickness
    
    def bottomEdge(self) -> float:
        return SQUARE_SIZE

    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether the ball is hit by the paddle.
        """
        if not self.active(): return False
        if self.side == BOTTOM:
            inYRange = ball.bottomEdge() >= self.topEdge()
        else:
            inYRange = ball.topEdge() <= self.bottomEdge()

        inXRange = self.leftEdge() <= ball.centerX() <= self.rightEdge()
            
        return inXRange and inYRange
    
    def paint(self, painter: QPainter) -> None:
        """
        Paint the paddle to an active painter.
        """
        if not self.active(): return
        painter.fillRect(self.position - self.size // 2,
                         0 if self.side == TOP else SQUARE_SIZE - self.thickness,
                         self.size,
                         self.thickness,
                         Qt.black)

class Ball:
    """
    The ball that bounds off the walls and paddles.
    """
    radius: int
    position: tuple[float, float]
    direction: tuple[float, float]
    speed: float

    def __init__(self):
        """
        Initialize the ball.
        """
        self.radius = 10
        self.position = SQUARE_SIZE // 2, SQUARE_SIZE // 2
        self.speed = 1.0
        self.direction = 1, 0
    
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
    
    def centerX(self) -> float:
        """
        Return the x coordinate at the center of the ball.
        """
        return self.position[0]
    
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
    
    def move(self):
        """
        Move the ball along its direction with itsspeed.
        """
        length = math.sqrt(self.direction[0] ** 2 + self.direction[1] ** 2)
        factor = self.speed / length

        self.position = self.position[0] + factor * self.direction[0], \
            self.position[1] + factor * self.direction[1]

    def reflectHorizontally(self):
        self.direction = -self.direction[0], self.direction[1]

    def reflectVertically(self):
        self.direction = self.direction[0], -self.direction[1]

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
    scoreUpdated = Signal(int, int)
    leftHit = Signal()
    leftMissed = Signal()
    rightHit = Signal()
    rightMissed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE

        self.balls = []
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.bottomPaddle = HorizontalPaddle()
        self.scoreBoard = ScoreBoard(self.sideLength)

        self.ballSpeed = 2.0

        self.setFixedSize(self.sideLength, self.sideLength)
        self.lostGame = False

        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self.updateState)
        self.isRunning = False
        self._timer.start()

        self.setFocus()

    def onLeftPaddleHit(self, ball: Ball) -> None:
        """
        Handle the event when the ball hits the left paddle.
        """
        pass
    
    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the right paddle.
        """
        pass

    def onBottomPaddleHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the bottom paddle.
        """
        pass
    
    def onLeftEdgeHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the left edge of the playing field.
        """
        pass
    
    def onRightEdgeHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the right edge of the playing field.
        """
        pass
    
    def onHorizontalEdgeHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the bottom or top edge of the playing field.
        """
        pass
    
    def setBallSpeed(self, speed: float) -> None:
        """
        Set the speed of current and future balls.
        """ 
        self.ballSpeed = speed
        for ball in self.balls:
            ball.speed = speed

    def setOrientation(self) -> None:
        """
        Set the orientation of the paddles.
        """
        raise NotImplementedError
    
    def userControlledPaddle(self) -> None:
        """
        Return the paddle that is controlled by the user.
        """
        raise NotImplementedError

    def updateState(self) -> None:
        """
        Move the ball and paddles and check for collisions. Then paint the new
        state.
        """
        for ball in self.balls:
            if ball.leftEdge() <= 0:
                self.onLeftEdgeHit(ball)
            elif ball.rightEdge() >= self.sideLength:
                self.onRightEdgeHit(ball)
            elif ball.topEdge() <= 0 \
                    or ball.bottomEdge() >= self.sideLength:
                self.onHorizontalEdgeHit(ball)
                ball.reflectVertically()
            elif self.leftPaddle.isHit(ball):
                self.onLeftPaddleHit(ball)
            elif self.rightPaddle.isHit(ball):
                self.onRightPaddleHit(ball)
            elif self.bottomPaddle.isHit(ball):
                self.onBottomPaddleHit(ball)
            
            if self.isRunning:
                ball.move()

        self.leftPaddle.move()
        self.rightPaddle.move()

        self.repaint()

    def start(self) -> None:
        """
        Start the game or resume it if it is paused.
        """
        #self._timer.start()
        self.isRunning = True

    def updateScore(self, scoreLeft: int, scoreRight: int) -> None:
        """
        Update the score on the scoreboard.
        """
        self.scoreUpdated.emit(scoreLeft, scoreRight)
        self.scoreBoard.scoreLeft = scoreLeft
        self.scoreBoard.scoreRight = scoreRight

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
        self.lostGame = False
        self.isRunning = False

        self.balls = [Ball()]
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.scoreBoard = ScoreBoard(self.sideLength)

        self.setFocus()


    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the game state to the screen.
        """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, True)

        self.scoreBoard.paint(painter)

        for ball in self.balls:
            ball.paint(painter)
        self.leftPaddle.paint(painter)
        self.rightPaddle.paint(painter)
        self.bottomPaddle.paint(painter)
        
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


class TwoPlayerPongGame(PongGame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.balls.append(Ball())
        self.bottomPaddle.setActive(False)

    def onLeftPaddleHit(self, ball: Ball) -> None:
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        ball.reflectHorizontally()

    def onRightPaddleHit(self, ball: Ball) -> None:
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        ball.reflectHorizontally()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        self.stop()

    def onRightEdgeHit(self, ball: Ball) -> None:
        self.stop()

    def setOrientation(self) -> None:
        pass

    def userControlledPaddle(self) -> Paddle:
        return self.leftPaddle

class SoloBallStormPongGame(PongGame):
    def __init__(self) -> None:
        PongGame.__init__(self)
        
        self.rightPaddle.setActive(False)
        self.bottomPaddle.setActive(False)
        self.lastBallUp = True
        self.orientation = "LEFT"

        self.addBall()

    def reset(self) -> None:
        self.lostGame = False
        self.isRunning = False

        self.balls.clear()
        self.addBall()
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT, active=False)
        self.scoreBoard = ScoreBoard(self.sideLength)

        self.setFocus()

    def onLeftPaddleHit(self, ball: Ball) -> None:
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        self.leftHit.emit()
        self.balls.remove(ball)
        self.addBall()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        self.leftMissed.emit()
        self.balls.remove(ball)
        self.addBall()

    def onRightPaddleHit(self, ball: Ball) -> None:
        self.onLeftPaddleHit(ball)

    def onRightEdgeHit(self, ball: Ball) -> None:
        self.onRightPaddleHit(ball)

    def onBottomPaddleHit(self, ball: Ball) -> None:
        self.onLeftPaddleHit(ball)

    def onHorizontalEdgeHit(self, ball: Ball) -> None:
        if self.orientation == "BOTTOM":
            self.onLeftEdgeHit(ball)

    def addBall(self) -> None:
        ball = Ball()
        if self.orientation == "LEFT":
            ball.position = SQUARE_SIZE - 20, SQUARE_SIZE // 2
            ball.direction = -2, 1 if self.lastBallUp else -1
        elif self.orientation == "RIGHT":
            ball.position = 20, SQUARE_SIZE // 2
            ball.direction = 2, 1 if self.lastBallUp else -1
        elif self.orientation == "BOTTOM":
            ball.position = SQUARE_SIZE // 2, 30
            ball.direction = 1 if self.lastBallUp else -1, 2

        ball.speed = self.ballSpeed
        self.lastBallUp = not self.lastBallUp
        self.balls.append(ball)

    def setOrientation(self, orientation: str) -> None:
        if orientation == "LEFT":
            self.rightPaddle.setActive(False)
            self.bottomPaddle.setActive(False)
            self.leftPaddle.setActive(True)
        elif orientation == "RIGHT":
            self.leftPaddle.setActive(False)
            self.bottomPaddle.setActive(False)
            self.rightPaddle.setActive(True)
        elif orientation == "BOTTOM":
            self.leftPaddle.setActive(False)
            self.rightPaddle.setActive(False)
            self.bottomPaddle.setActive(True)

        if orientation != self.orientation:
            self.orientation = orientation
            self.balls.clear()
            self.addBall()

        self.orientation = orientation

    def userControlledPaddle(self) -> Paddle:
        if self.orientation == "LEFT":
            return self.leftPaddle
        elif self.orientation == "RIGHT":
            return self.rightPaddle
        elif self.orientation == "BOTTOM":
            return self.bottomPaddle

class PongGameWindow(QWidget):
    def __init__(self, pongGame: Optional[PongGame] = None) -> None:
        """
        Initialize the window for playing pong.
        """
        QWidget.__init__(self)
        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        if pongGame is None:
            pongGame = TwoPlayerPongGame()

        self.game = pongGame
        self.vLayout.addWidget(self.game)

        self.toggleButton = QPushButton("Toggle")
        self.toggleButton.clicked.connect(self.game.toggle)
        self.vLayout.addWidget(self.toggleButton)

        self.toggleButton = QPushButton("Reset")
        self.toggleButton.clicked.connect(self.game.reset)
        self.vLayout.addWidget(self.toggleButton)

class PongServerAdapter(GameAdapter):
    """
    The universal adapter for the pong game, so it can be controlled by a
    separate client application.
    """
    def __init__(self, pongGame: PongGameWindow) -> None:
        """
        Initialize the adapter. Connect the game's signals to the adapter's
        slots.
        """
        GameAdapter.__init__(self)
        self.window = pongGame
        self.window.game.scoreUpdated.connect(self.onScoreUpdated)
        self.window.game.leftHit.connect(
            lambda: self.eventReady.emit(Event("leftHit"))
        )
        self.window.game.leftMissed.connect(
            lambda: self.eventReady.emit(Event("leftMissed"))
        )
        self.window.game.rightHit.connect(
            lambda: self.eventReady.emit(Event("rightHit"))
        )
        self.window.game.rightMissed.connect(
            lambda: self.eventReady.emit(Event("rightMissed"))
        )

    def widget(self) -> QWidget:
        """
        Return the window of the underlying game.
        """
        return self.window

    def onScoreUpdated(self, scoreLeft: int, scoreRight: int) -> None:
        """
        Send the scoreUpdated event to the client.
        """
        self.eventReady.emit(Event("scoreUpdated", [scoreLeft, scoreRight]))

    def onAccuracyUpdated(self, accuracy: float) -> None:
        """
        Send the accuracyUpdated event to the client.
        """
        self.eventReady.emit(Event("accuracyUpdated", [accuracy]))
    
    def eventReceived(self, e: Event) -> None:
        """
        Handle an event received from the client.
        """
        module_logger.debug(f"Executing {str(e)}")
        paddle = self.window.game.userControlledPaddle()
        if e.name == "clearMovement":
            paddle.movingUp = False
            paddle.movingDown = False
            paddle.useVariableSpeed = False
            paddle.setSpeedMultiplier(0.0)
        elif e.name == "moveTo":
            paddle.moveTo(float(e.payload[0]))
        elif e.name == "setSpeed":
            paddle.useVariableSpeed = True
            paddle.setSpeedMultiplier(float(e.payload[0]))
        elif e.name == "moveUp":
            paddle.useVariableSpeed = False
            paddle.movingUp = True
            paddle.movingDown = False
        elif e.name == "neutral":
            paddle.useVariableSpeed = False
            paddle.movingUp = False
            paddle.movingDown = False
        elif e.name == "moveDown":
            paddle.useVariableSpeed = False
            paddle.movingDown= True
            paddle.movingUp = False
        elif e.name == "setBallSpeed":
            self.window.game.setBallSpeed(float(e.payload[0]))
            self.eventReady.emit(Event("ballSpeedUpdated", [float(e.payload[0])]))
        elif e.name == "setOrientation":
            self.window.game.setOrientation(e.payload[0])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PongGameWindow()

    window.show()
    sys.exit(app.exec())
