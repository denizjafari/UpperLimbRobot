"""
The pong game implemented using the Qt framework. The common two player
version is included as well as an adaption for solo players.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Optional

import sys
import logging
import math
import random

from PySide6.QtCore import QTimer, Qt, QRect, Signal, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, \
    QPushButton
from PySide6.QtGui import QPaintEvent, QPainter, QKeyEvent, QBrush, QPen, \
    QColor

from app.protocols.events import Event, GameAdapter


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

SQUARE_SIZE = 300
DEFAULT_PADDLE_SIZE = 50
DEFAULT_PADDLE_THICKNESS = 12
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
    def __init__(self,
                 side:int=LEFT,
                 movementRange: tuple[int, int]=(0, SQUARE_SIZE),
                 active: bool = True) -> None:
        """
        Initialize the paddle.
        """
        self.size = DEFAULT_PADDLE_SIZE
        self.position = SQUARE_SIZE // 2
        self.thickness = DEFAULT_PADDLE_THICKNESS
        self.side = side
        self.offset = side
        self.setMovementRange(movementRange)
        self.speed = DEFAULT_PADDLE_SPEED
        self.movingUp = False
        self.movingDown = False
        self.useVariableSpeed = False

        self._active = active
        self.debouncing = False

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
        if self.side == LEFT:
            if self.offset == LEFT:
                return 0
            else:
                return self.thickness
        else:
            if self.offset == LEFT:
                return SQUARE_SIZE - 2 * self.thickness
            else:
                return SQUARE_SIZE - self.thickness
    
    def rightEdge(self) -> float:
        """
        Return the right x coordinate of the paddle.
        """
        if self.side == LEFT:
            if self.offset == LEFT:
                return self.thickness
            else:
                return 2 * self.thickness
        else:
            if self.offset == LEFT:
                return SQUARE_SIZE - self.thickness
            else:
                return SQUARE_SIZE
            

    def isInXRange(self, ball: Ball) -> None:
        """
        Return whether the paddle is in the y range of the ball.
        """
        if self.side == LEFT:
            return ball.leftEdge() <= self.rightEdge()
        else:
            return ball.rightEdge() >= self.leftEdge()
            

    def isInYRange(self, ball: Ball) -> None:
        """
        Return whether the paddle is in the y range of the ball.
        """
        return self.bottomEdge() >= ball.centerY() >= self.topEdge()
    
    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether this paddle is activea and the ball is hit by the
        paddle.
        """
        if not self.active(): return False
        
        inXRange = self.isInXRange(ball)
        inYRange = self.isInYRange(ball)
            
        if self.debouncing:
            if not (inXRange and inYRange):
                self.debouncing = False
            return False
        else:
            if inXRange and inYRange:
                self.debouncing = True
                return True
            else:
                return False
    
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

        self.placeBackInBounds()

    def moveTo(self, relativePosition: float) -> None:
        """
        Move the paddle immediately, so that the center of the paddle is at
        the specified relative position. Relative here means one a scale from
        0.0 to 1.0, where 0.0 is at the bottom and 1.0 is at the
        top.
        """
        delta = self.movementRange[1] - self.movementRange[0]
        self.position = self.movementRange[0] + \
            (1 - relativePosition) * delta
        
        self.placeBackInBounds()
        
    def placeBackInBounds(self) -> None:
        """
        Place the paddle back in the movement range if it is outside of it.
        """
        if self.topEdge() < self.movementRange[0]:
            self.position = self.movementRange[0] + self.size // 2
        elif self.bottomEdge() > self.movementRange[1]:
            self.position = self.movementRange[1] - self.size // 2

    def setMovementRange(self, range: tuple[int, int]) -> None:
        """
        Set the movement range for this paddle.
        """
        self.movementRange = range
        self.position = (range[0] + range[1]) // 2

    def setSpeedMultiplier(self, speedMultiplier: float) -> None:
        """
        Set the speed multiplier for the paddle. This is used for the relative
        movement mode. Set the speed to a value in the range between 0.0 to 1.0.
        """
        self.speedMultiplier = speedMultiplier

    def paint(self, painter: QPainter, color: QColor = Qt.black) -> None:
        """
        Paint the paddle to an active painter.
        """
        if not self.active(): return

        painter.fillRect(self.leftEdge(),
                         self.position - self.size // 2,
                         self.thickness,
                         self.size,
                         color)
        
    def active(self) -> bool:
        """
        Return whether the paddle is active. An inactive paddle is not painted
        and also does not influence the game.
        """
        return self._active
    
    def setActive(self, active: bool) -> bool:
        """
        Set the paddle to active or inactive. An inactive paddle is not painted
        and also does not influence the game.
        """
        self._active = active

class HorizontalPaddle(Paddle):
    """
    Paddle, but horizontal.
    """
    def __init__(self, side: int = BOTTOM) -> None:
        Paddle.__init__(self, side=side)

        self.offset = side

    def leftEdge(self) -> float:
        """
        Return the left most x coordinate of the paddle.
        """
        return self.position - self.size // 2
    
    def rightEdge(self) -> float:
        """
        Return the right most x coordinate of the paddle.
        """
        return self.position + self.size // 2
    
    def topEdge(self) -> float:
        """
        Return the top most y coordinate.
        """
        if self.side == TOP:
            if self.offset == TOP:
                return 0
            else:
                return self.thickness
        else:
            if self.offset == TOP:
                return SQUARE_SIZE - 2 * self.thickness
            else:
                return SQUARE_SIZE - self.thickness
    
    def bottomEdge(self) -> float:
        """
        Return the bottom most y coordinate.
        """
        if self.side == TOP:
            if self.offset == TOP:
                return self.thickness
            else:
                return 2 * self.thickness
        else:
            if self.offset == TOP:
                return SQUARE_SIZE - self.thickness
            else:
                return SQUARE_SIZE
    
    def moveTo(self, relativePosition: float) -> None:
        """
        Move the paddle immediately, so that the center of the paddle is at
        the specified relative position. Relative here means one a scale from
        0.0 to 1.0, where 0.0 is at the left and 1.0 is at the
        right.
        """
        delta = self.movementRange[1] - self.movementRange[0]
        self.position = self.movementRange[0] + relativePosition * delta
        self.placeBackInBounds()

    def placeBackInBounds(self) -> None:
        """
        Place the paddle back in the movement range if it is outside of it.
        """
        if self.leftEdge() < self.movementRange[0]:
            self.position = self.movementRange[0] + self.size // 2
        elif self.rightEdge() > self.movementRange[1]:
            self.position = self.movementRange[1] - self.size // 2

    def isInYRange(self, ball: Ball) -> None:
        """
        Return whether the paddle is in the y range of the ball
        """
        if self.side == BOTTOM:
            return ball.bottomEdge() >= self.topEdge()
        else:
            return ball.topEdge() <= self.bottomEdge()

    def isInXRange(self, ball: Ball) -> None:
        """
        Return whether the paddle is in the x range of the ball.
        """
        return self.leftEdge() <= ball.centerX() <= self.rightEdge()

    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether the paddle is active and the ball is hit by the
        paddle.
        """
        if not self.active(): return False

        inYRange = self.isInYRange(ball)
        inXRange = self.isInXRange(ball)

        if self.debouncing:
            if not (inXRange and inYRange):
                self.debouncing = False
            return False
        else:
            if inXRange and inYRange:
                self.debouncing = True
                return True
            else:
                return False
    
    def paint(self, painter: QPainter, color: QColor = Qt.black) -> None:
        """
        Paint the paddle to an active painter.
        """
        if not self.active(): return
        painter.fillRect(self.position - self.size // 2,
                         self.topEdge(),
                         self.size,
                         self.thickness,
                         color)

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
        """
        Reflect the ball horizontally by inverting its x direction.
        """
        self.direction = -self.direction[0], self.direction[1]

    def reflectVertically(self):
        """
        Reflect the ball horizontally by inverting its y direction.
        """
        self.direction = self.direction[0], -self.direction[1]

    def paint(self, painter: QPainter) -> None:
        """
        Paint the ball to an active painter.
        """
        painter.setBrush(QBrush(Qt.red))
        painter.drawEllipse(self.position[0] - self.radius,
                            self.position[1] - self.radius,
                            self.radius * 2,
                            self.radius * 2)
        

SCOREBOARD_WIDTH = 60
SCOREBOARD_HEIGHT = 30

class ScoreBoard:
    """
    Basic Scoreboard capable of tracking the scores for both sides,
    left and right.

    Scores to show indicates which of the scores should be shown in the UI.
    By default, both scores are shown. If only the left score should be shown,
    set scoresToShow to LEFT. If only the right score should be shown, set
    scoresToShow to RIGHT.
    """
    scoreLeft: int
    scoreRight: int
    scoresToShow: int

    def __init__(self, screenSize: int) -> None:
        """
        Initialize the scoreboard.
        """
        self.scoreLeft = 0
        self.scoreRight = 0
        self.width = SCOREBOARD_WIDTH
        self.height = SCOREBOARD_HEIGHT
        self.screenSize = screenSize
        self.position = TOP
        self.scoresToShow = NEUTRAL

    def y(self, height: int = None) -> None:
        """
        Determine the y coordinate of the top left corner of the score board.
        By default assumes the true height of the score board is self.height.
        """
        if height is None: height = self.height

        if self.position == TOP:
            return 0
        elif self.position == BOTTOM:
            return self.screenSize - self.height
        else:
            return (self.screenSize - self.height) / 2
    
    def x(self, width: int = None) -> None:
        """
        Determine the x coordinate of the top left corner of the score board.
        By default assumes the true width of the score board is self.width.
        """
        if width is None: width = self.width

        if self.position == LEFT:
            return 0
        elif self.position == RIGHT:
            return self.screenSize - self.width
        else:
            return (self.screenSize - self.width) / 2

    def paint(self, painter: QPainter) -> None:
        """
        Paint the scoreboard to an active painter.
        """
        rect = QRect(self.x(), self.y(), self.width, self.height)
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.black)

        painter.drawRect(rect)
        boundings = painter.boundingRect(rect, "Score")
        painter.drawText(self.x() + (self.width - boundings.width()) / 2,
                         self.y() + 12,
                         "Score")

        if self.scoresToShow == LEFT:
            scoreStr = str(self.scoreLeft)
        elif self.scoresToShow == RIGHT:
            scoreStr = str(self.scoreRight)
        else:
            scoreStr = str(self.scoreLeft) + " : " + str(self.scoreRight)
        boundings = painter.boundingRect(rect, scoreStr)
        painter.drawText(self.x() + (self.width - boundings.width()) / 2,
                         self.y() + 25,
                         scoreStr)

class PongGame(QLabel):
    """
    The Pong Game. Handles the game logic and displays the result.
    """
    eventReady = Signal(Event)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE

        self.balls = []
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.topPaddle = HorizontalPaddle(side=TOP)
        self.bottomPaddle = HorizontalPaddle()
        self.scoreBoard = ScoreBoard(self.sideLength)

        self.ballSpeed = 2.0

        self._orientation = "LEFT"

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

    def onTopPaddleHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the top paddle.
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
    
    def onBottomEdgeHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the bottom edge of the playing field.
        """
        pass

    def onTopEdgeHit(self, ball: Ball) -> None:
        """
        Handle the event when a ball hits the top edge of the playing field.
        """
        pass
    
    def setBallSpeed(self, speed: float) -> None:
        """
        Set the speed of current and future balls.
        """ 
        self.ballSpeed = speed
        for ball in self.balls:
            ball.speed = speed

    def setOrientation(self, orientation: str) -> None:
        """
        Set the orientation of the playing field.
        """
        if orientation == "TOP" or orientation == "BOTTOM":
            self.scoreBoard.position = LEFT
        else:
            self.scoreBoard.position = TOP

    def orientation(self) -> None:
        """
        Return the orientation of the playing field.
        """
        return self._orientation

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
            elif ball.topEdge() <= 0:
                self.onTopEdgeHit(ball)
            elif ball.bottomEdge() >= self.sideLength:
                self.onBottomEdgeHit(ball)
            elif self.leftPaddle.isHit(ball):
                self.onLeftPaddleHit(ball)
            elif self.rightPaddle.isHit(ball):
                self.onRightPaddleHit(ball)
            elif self.bottomPaddle.isHit(ball):
                self.onBottomPaddleHit(ball)
            elif self.topPaddle.isHit(ball):
                self.onTopPaddleHit(ball)
            
            if self.isRunning:
                ball.move()

        self.leftPaddle.move()
        self.rightPaddle.move()
        self.topPaddle.move()
        self.bottomPaddle.move()

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
        self.eventReady.emit(Event("scoreUpdated", [scoreLeft, scoreRight]))
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
        """
        Reset the game state.
        """
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

        pen = QPen(Qt.black)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(QRect(0, 0, self.sideLength, self.sideLength))

        pen = QPen()
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)

        if self.orientation() == "LEFT" or self.orientation() == "RIGHT":
            painter.drawLine(QPoint(self.sideLength // 2, 0),
                             QPoint(self.sideLength // 2, self.sideLength))
        else:
            painter.drawLine(QPoint(0, self.sideLength // 2),
                             QPoint(self.sideLength, self.sideLength // 2))

        self.scoreBoard.paint(painter)

        for ball in self.balls:
            ball.paint(painter)
        self.leftPaddle.paint(painter, color=Qt.blue)
        self.rightPaddle.paint(painter, color=Qt.red)
        self.topPaddle.paint(painter, color=Qt.green)
        self.bottomPaddle.paint(painter, color=Qt.yellow)
        
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
        elif key == Qt.Key_A:
            self.bottomPaddle.movingUp = True
        elif key == Qt.Key_D:
            self.bottomPaddle.movingDown = True
        elif key == Qt.Key_Left:
            self.topPaddle.movingUp = True
        elif key == Qt.Key_Right:
            self.topPaddle.movingDown = True

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
        elif key == Qt.Key_A:
            self.bottomPaddle.movingUp = False
        elif key == Qt.Key_D:
            self.bottomPaddle.movingDown = False
        elif key == Qt.Key_Left:
            self.topPaddle.movingUp = False
        elif key == Qt.Key_Right:
            self.topPaddle.movingDown = False


class TwoPlayerPongGame(PongGame):
    """
    A two player game of pong. The left paddle is controlled by the W and S
    keys, the right paddle is controlled by the up and down arrow keys.
    If a player connects via the pose detection software, they control the
    left paddle.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        super().__init__(parent)

        ball = Ball()
        ball.direction = 1, 2
        ball.speed = 2.5

        self.balls.append(ball)
        self.bottomPaddle.setActive(False)
        self.topPaddle.setActive(False)

    def onLeftPaddleHit(self, ball: Ball) -> None:
        """
        Update the score: The left player has scored.
        """
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        ball.reflectHorizontally()

    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Update the score: The right player has scored.
        """
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        ball.reflectHorizontally()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        """
        End the game because the left player has lost.
        """
        self.stop()

    def onRightEdgeHit(self, ball: Ball) -> None:
        """
        End the game because the right player has lost
        """
        self.stop()

    def setOrientation(self, orientation: str) -> None:
        """
        Do nothing. Orientation is not supported in the two player game.
        """
        pass

class SoloBallStormPongGame(PongGame):
    """
    A solo player game similar to pong. The player just needs to hit the balls
    which are trhown from the other side. No reflections are possible. Also,
    the game does not end if the player misses a ball.
    """
    
    def __init__(self) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        PongGame.__init__(self)
        
        self.rightPaddle.setActive(False)
        self.bottomPaddle.setActive(False)
        self.topPaddle.setActive(False)
        self.lastBallUp = True
        self._orientation = "LEFT"

        self.addBall()

    def reset(self) -> None:
        """
        Restore the original state of the game, but keep the orientation.
        """
        self.lostGame = False
        self.isRunning = False

        self.balls.clear()
        self.addBall()
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.bottomPaddle = HorizontalPaddle(side=BOTTOM)
        self.topPaddle = HorizontalPaddle(side=TOP)
        
        self.setOrientation(self.orientation)

        self.scoreBoard = ScoreBoard(self.sideLength)

        self.setFocus()

    def onLeftPaddleHit(self, ball: Ball) -> None:
        """
        The player has scored. Replace the ball at its original position.
        """
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        if self.orientation() == "LEFT":
            self.eventReady.emit(Event("hit", ["LEFT"]))
        self.balls.remove(ball)
        self.addBall()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        """
        The player missed the ball. Replace the ball at its original position.
        """
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        if self.orientation() == "LEFT":
            self.eventReady.emit(Event("miss", ["LEFT"]))
        self.balls.remove(ball)
        self.addBall()

    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Same as onLeftPaddleHit, but happens when the orientation is reversed.
        """
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        if self.orientation() == "RIGHT":
            self.eventReady.emit(Event("hit", ["RIGHT"]))
        self.balls.remove(ball)
        self.addBall()

    def onRightEdgeHit(self, ball: Ball) -> None:
        """
        Same as onLeftEdgeHit, but happens when the orientation is reversed.
        """
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        if self.orientation() == "RIGHT":
            self.eventReady.emit(Event("miss", ["RIGHT"]))
        self.balls.remove(ball)
        self.addBall()

    def onBottomPaddleHit(self, ball: Ball) -> None:
        """
        Same as onLeftPaddleHit, but happens when the orientation is changed
        to BOTTOM.
        """
        if self.orientation() == "BOTTOM":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.eventReady.emit(Event("hit", ["BOTTOM"]))
            self.balls.remove(ball)
            self.addBall()

    def onTopEdgeHit(self, ball: Ball) -> None:
        """
        Same as onLeftEdgeHit, but happens when the orientation is changed
        to BOTTOM.
        """
        if self.orientation() == "BOTTOM":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.eventReady.emit(Event("miss", ["BOTTOM"]))
            self.balls.remove(ball)
            self.addBall()
        else:
            ball.reflectVertically()

    def addBall(self) -> None:
        """
        Add a ball at the correct entry point (left, right, or top),
        alternating the sides it travels to.
        """
        ball = Ball()
        if self.orientation() == "LEFT":
            ball.position = SQUARE_SIZE - 20, SQUARE_SIZE // 2
            ball.direction = -2, 1 if self.lastBallUp else -1
        elif self.orientation() == "RIGHT":
            ball.position = 20, SQUARE_SIZE // 2
            ball.direction = 2, 1 if self.lastBallUp else -1
        elif self.orientation() == "BOTTOM":
            ball.position = SQUARE_SIZE // 2, 30
            ball.direction = 1 if self.lastBallUp else -1, 2

        ball.speed = self.ballSpeed
        self.lastBallUp = not self.lastBallUp
        self.balls.append(ball)

    def setOrientation(self, orientation: str) -> None:
        """
        Set the orientation of the playing field (LEFT, RIGHT, or BOTTOM).
        Replace the ball at its new start point.
        """
        super().setOrientation(orientation)

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

        if orientation != self.orientation():
            self._orientation = orientation
            self.updateScore(self.scoreBoard.scoreRight, self.scoreBoard.scoreLeft)
            self.balls.clear()
            self.addBall()

        self._orientation = orientation
        
class SameSidePongGame(PongGame):
    """
    A game of pong where the paddles for both players are on the same side of
    the playing field.
    """
    
    def __init__(self) -> None:
        PongGame.__init__(self)

        self.topPaddle.setActive(False)
        self.bottomPaddle.setActive(False)

        self._orientation = "LEFT"
        
        self.addBall()

    def reset(self) -> None:
        """
        Restore the original state of the game, but keep the orientation.
        """
        self.lostGame = False
        self.isRunning = False

        self.balls.clear()
        self.addBall()
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.bottomPaddle = HorizontalPaddle(side=BOTTOM)
        self.topPaddle = HorizontalPaddle(side=TOP)
        
        self.setOrientation(self.orientation())

        self.scoreBoard = ScoreBoard(self.sideLength)

        self.setFocus()

    def addBall(self) -> None:
        """
        Add a ball at the correct entry point (left, right, or top).
        """
        ball = Ball()
        spread = random.uniform(0.5, 1.5)
        if self.orientation() == "LEFT":
            ball.position = SQUARE_SIZE - 20, SQUARE_SIZE // 2
            ball.direction = -2, spread
        elif self.orientation() == "RIGHT":
            ball.position = 20, SQUARE_SIZE // 2
            ball.direction = 2, spread
        elif self.orientation() == "BOTTOM":
            ball.position = SQUARE_SIZE // 2, 30
            ball.direction = spread, 2

        ball.speed = self.ballSpeed
        self.balls.append(ball)

    def setOrientation(self, orientation: str) -> None:
        """
        Set the orientation of the playing field (LEFT, RIGHT, or BOTTOM).
        """
        super().setOrientation(orientation)

        if orientation == "LEFT":
            self.rightPaddle.side = LEFT
            self.leftPaddle.side = LEFT
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.bottomPaddle.setActive(False)
            self.topPaddle.setActive(False)
            self.scoreBoard.scoresToShow = LEFT
        elif orientation == "RIGHT":
            self.rightPaddle.side = RIGHT
            self.leftPaddle.side = RIGHT
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.bottomPaddle.setActive(False)
            self.topPaddle.setActive(False)
            self.scoreBoard.scoresToShow = RIGHT
        elif orientation == "BOTTOM":
            self.topPaddle.side = BOTTOM
            self.bottomPaddle.side = BOTTOM
            self.rightPaddle.setActive(False)
            self.leftPaddle.setActive(False)
            self.topPaddle.setActive(True)
            self.bottomPaddle.setActive(True)
            self.scoreBoard.scoresToShow = LEFT

        self._orientation = orientation
        self.balls.clear()
        self.addBall()

    def onRightEdgeHit(self, ball: Ball) -> None:
        """
        Reflect unless the paddles are on the right.
        """
        if self.orientation() == "RIGHT":
            self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
            self.balls.remove(ball)
            self.addBall()
        else:
            ball.reflectHorizontally()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        """
        Reflect unless the paddles are on the left.
        """
        if self.orientation() == "LEFT":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.balls.remove(ball)
            self.addBall()
        else:
            ball.reflectHorizontally()

    def onTopEdgeHit(self, ball: Ball) -> None:
        """
        Reflect unless the paddles are on the top.
        """
        if self.orientation() == "TOP":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.balls.remove(ball)
            self.addBall()
        else:
            ball.reflectVertically()

    def onBottomEdgeHit(self, ball: Ball) -> None:
        """
        Reflect unless the paddles are on the bottom.
        """
        if self.orientation() == "BOTTOM":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.balls.remove(ball)
            self.addBall()
        else:
            ball.reflectVertically()

    def onLeftPaddleHit(self, ball: Ball) -> None:
        """
        Reflect.
        """
        self.onRightPaddleHit(ball)

    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Reflect.
        """
        if self.orientation() == "LEFT":
            self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        else:
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        ball.reflectHorizontally()

    def onBottomPaddleHit(self, ball: Ball) -> None:
        """
        Reflect.
        """
        self.onTopPaddleHit(ball)

    def onTopPaddleHit(self, ball: Ball) -> None:
        """
        Reflect.
        """
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        ball.reflectVertically()
        
class SharedScreenPongGame(SameSidePongGame):
    def __init__(self) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        SameSidePongGame.__init__(self)
        
        self.rightPaddle.side = LEFT
        self._orientation = "LEFT"

    def onLeftPaddleHit(self, ball: Ball) -> None:
        """
        Reflect. Count double points if both paddles where behind the ball.
        """
        self.onRightPaddleHit(ball)

    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Reflect. Count double points if both paddles where behind the ball.
        """
        points = self.leftPaddle.isInYRange(ball) + self.rightPaddle.isInYRange(ball)
        if self.orientation() == "LEFT":
            self.updateScore(self.scoreBoard.scoreLeft + points, self.scoreBoard.scoreRight)
        else:
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + points)

        ball.reflectHorizontally()

    def onTopPaddleHit(self, ball: Ball) -> None:
        """
        Reflect. Count double points if both paddles where behind the ball.
        """
        self.onBottomPaddleHit(ball)

    def onBottomPaddleHit(self, ball: Ball) -> None:
        """
        Reflect. Count double points if both paddles where behind the ball.
        """
        points = self.topPaddle.isInXRange(ball) + self.bottomPaddle.isInXRange(ball)
        self.updateScore(self.scoreBoard.scoreLeft + points, self.scoreBoard.scoreRight)
        ball.reflectVertically()

class SplitScreenPongGame(SameSidePongGame):
    def __init__(self) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        SameSidePongGame.__init__(self)

        self._orientation = "LEFT"

        self.reset()

    def reset(self) -> None:
        """
        Reset the board to its original state, keeping orientation.
        """
        super().reset()

        self.leftPaddle = HorizontalPaddle(side=BOTTOM)
        self.rightPaddle = HorizontalPaddle(side=BOTTOM)
        self.topPaddle = Paddle(side=self.orientation)
        self.bottomPaddle = Paddle(side=self.orientation)
        
        if self.orientation() == "BOTTOM":
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.topPaddle.setActive(False)
            self.bottomPaddle.setActive(False)
        else:
            self.leftPaddle.setActive(False)
            self.rightPaddle.setActive(False)
            self.topPaddle.setActive(True)
            self.bottomPaddle.setActive(True)

        self.leftPaddle.setMovementRange((0, SQUARE_SIZE // 2))
        self.topPaddle.setMovementRange((0, SQUARE_SIZE // 2))

        self.rightPaddle.setMovementRange((SQUARE_SIZE // 2, SQUARE_SIZE))
        self.bottomPaddle.setMovementRange((SQUARE_SIZE // 2, SQUARE_SIZE))

    def setOrientation(self, orientation: str) -> None:
        """
        Set the orientation of the playing field (LEFT, RIGHT, or BOTTOM).
        This affects which paddles are active and respond to inputs.
        """
        super().setOrientation(orientation)

        if orientation == "BOTTOM":
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.topPaddle.setActive(False)
            self.bottomPaddle.setActive(False)
        else:
            if orientation == "LEFT":
                self.topPaddle.side = LEFT
                self.bottomPaddle.side = LEFT
                self.topPaddle.offset = LEFT
                self.bottomPaddle.offset = LEFT
            else:
                self.topPaddle.side = RIGHT
                self.bottomPaddle.side = RIGHT
                self.topPaddle.offset = RIGHT
                self.bottomPaddle.offset = RIGHT
            self.leftPaddle.setActive(False)
            self.rightPaddle.setActive(False)
            self.topPaddle.setActive(True)
            self.bottomPaddle.setActive(True)

        self._orientation = orientation
        self.balls.clear()
        self.addBall()

    def onLeftPaddleHit(self, ball) -> None:
        """
        When the left paddle (at the bottom left!) is hit, the ball is
        reflected vertically.
        """
        ball.reflectVertically()

    def onRightPaddleHit(self, ball) -> None:
        """
        When the right paddle (at the bottom right!) is hit, the ball is
        reflected vertically.
        """
        ball.reflectVertically()

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
        self.window.game.eventReady.connect(self.eventReady.emit)
        self.addrToOrientation = {}

    def widget(self) -> QWidget:
        """
        Return the window of the underlying game.
        """
        return self.window
    
    def eventReceived(self, e: Event) -> None:
        """
        Handle an event received from the client.
        """
        module_logger.debug(f"Executing {str(e)} from {e.source}")

        if e.name == "setBallSpeed":
            self.window.game.setBallSpeed(float(e.payload[0]))
            self.eventReady.emit(e.reply(
                Event("ballSpeedUpdated", [float(e.payload[0])])))
        elif e.name == "setPaddle":
            self.eventReady.emit(e.reply(
                Event("paddleUpdated", [e.payload[0]])))
            self.addrToOrientation[e.source] = e.payload[0]
        elif e.name == "setOrientation":
            self.window.game.setOrientation(e.payload[0])
            self.eventReady.emit(e.reply(
                Event("orientationUpdated", [e.payload[0]])))
        elif e.source in self.addrToOrientation:
            orientation = self.addrToOrientation[e.source]

            if orientation == "LEFT":
                paddle = self.window.game.leftPaddle
            elif orientation == "RIGHT":
                paddle = self.window.game.rightPaddle
            elif orientation == "BOTTOM":
                paddle = self.window.game.bottomPaddle
            else:
                paddle = self.window.game.topPaddle

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PongGameWindow()

    window.show()
    sys.exit(app.exec())
