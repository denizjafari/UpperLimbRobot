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
    
    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether this paddle is activea and the ball is hit by the
        paddle.
        """
        if not self.active(): return False
        if self.side == LEFT:
            inXRange = ball.leftEdge() <= self.rightEdge()
        else:
            inXRange = ball.rightEdge() >= self.leftEdge()
        
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

    def paint(self, painter: QPainter) -> None:
        """
        Paint the paddle to an active painter.
        """
        if not self.active(): return
        painter.fillRect(self.leftEdge(),
                         self.position - self.size // 2,
                         self.thickness,
                         self.size,
                         Qt.black)
        
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

    def isHit(self, ball: Ball) -> bool:
        """
        Determine whether the paddle is active and the ball is hit by the
        paddle.
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
                         self.topEdge(),
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
        """
        Initialize the scoreboard.
        """
        self.scoreLeft = 0
        self.scoreRight = 0
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

        scoreStr = str(self.scoreLeft) + " : " + str(self.scoreRight)
        boundings = painter.boundingRect(rect, scoreStr)
        painter.drawText((self.screenSize - boundings.width()) / 2,
                         25,
                         scoreStr)

class PongGame(QLabel):
    """
    The Pong Game. Handles the game logic and displays the result.
    """
    eventReady = Signal(Event)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QLabel.__init__(self, parent)
        self.sideLength = SQUARE_SIZE

        self.balls = []
        self.leftPaddle = Paddle()
        self.rightPaddle = Paddle(side=RIGHT)
        self.topPaddle = HorizontalPaddle(side=TOP)
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
        self.topPaddle.paint(painter)
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

    def userControlledPaddle(self) -> Paddle:
        """
        Always return the left paddle.
        """
        return self.leftPaddle

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
        self.orientation = "LEFT"

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
        if self.orientation == "LEFT":
            self.eventReady.emit(Event("hit", ["LEFT"]))
        self.balls.remove(ball)
        self.addBall()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        """
        The player missed the ball. Replace the ball at its original position.
        """
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        if self.orientation == "LEFT":
            self.eventReady.emit(Event("miss", ["LEFT"]))
        self.balls.remove(ball)
        self.addBall()

    def onRightPaddleHit(self, ball: Ball) -> None:
        """
        Same as onLeftPaddleHit, but happens when the orientation is reversed.
        """
        self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
        if self.orientation == "RIGHT":
            self.eventReady.emit(Event("hit", ["RIGHT"]))
        self.balls.remove(ball)
        self.addBall()

    def onRightEdgeHit(self, ball: Ball) -> None:
        """
        Same as onLeftEdgeHit, but happens when the orientation is reversed.
        """
        self.updateScore(self.scoreBoard.scoreLeft + 1, self.scoreBoard.scoreRight)
        if self.orientation == "RIGHT":
            self.eventReady.emit(Event("miss", ["RIGHT"]))
        self.balls.remove(ball)
        self.addBall()

    def onBottomPaddleHit(self, ball: Ball) -> None:
        """
        Same as onLeftPaddleHit, but happens when the orientation is changed
        to BOTTOM.
        """
        if self.orientation == "BOTTOM":
            self.updateScore(self.scoreBoard.scoreLeft, self.scoreBoard.scoreRight + 1)
            self.eventReady.emit(Event("hit", ["BOTTOM"]))
            self.balls.remove(ball)
            self.addBall()

    def onTopEdgeHit(self, ball: Ball) -> None:
        """
        Same as onLeftEdgeHit, but happens when the orientation is changed
        to BOTTOM.
        """
        if self.orientation == "BOTTOM":
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
        """
        Set the orientation of the playing field (LEFT, RIGHT, or BOTTOM).
        Replace the ball at its new start point.
        """
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
            self.updateScore(self.scoreBoard.scoreRight, self.scoreBoard.scoreLeft)
            self.balls.clear()
            self.addBall()

        self.orientation = orientation

    def userControlledPaddle(self) -> Paddle:
        """
        Return the paddle that is currently controlled by the user.
        """
        if self.orientation == "LEFT":
            return self.leftPaddle
        elif self.orientation == "RIGHT":
            return self.rightPaddle
        elif self.orientation == "BOTTOM":
            return self.bottomPaddle
        
class SameSidePongGame(PongGame):
    def __init__(self) -> None:
        PongGame.__init__(self)

        self.topPaddle.setActive(False)
        self.bottomPaddle.setActive(False)

        self.orientation = "LEFT"
        
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

    def addBall(self) -> None:
        """
        Add a ball at the correct entry point (left, right, or top).
        """
        ball = Ball()
        spread = random.uniform(0.5, 1.5)
        if self.orientation == "LEFT":
            ball.position = SQUARE_SIZE - 20, SQUARE_SIZE // 2
            ball.direction = -2, spread
        elif self.orientation == "RIGHT":
            ball.position = 20, SQUARE_SIZE // 2
            ball.direction = 2, spread
        elif self.orientation == "BOTTOM":
            ball.position = SQUARE_SIZE // 2, 30
            ball.direction = spread, 2

        ball.speed = self.ballSpeed
        self.balls.append(ball)

    def setOrientation(self, orientation: str) -> None:
        if orientation == "LEFT":
            self.rightPaddle.side = LEFT
            self.leftPaddle.side = LEFT
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.bottomPaddle.setActive(False)
            self.topPaddle.setActive(False)
        elif orientation == "RIGHT":
            self.rightPaddle.side = RIGHT
            self.leftPaddle.side = RIGHT
            self.leftPaddle.setActive(True)
            self.rightPaddle.setActive(True)
            self.bottomPaddle.setActive(False)
            self.topPaddle.setActive(False)
        elif orientation == "BOTTOM":
            self.topPaddle.side = BOTTOM
            self.bottomPaddle.side = BOTTOM
            self.rightPaddle.setActive(False)
            self.leftPaddle.setActive(False)
            self.topPaddle.setActive(True)
            self.bottomPaddle.setActive(True)

        self.orientation = orientation
        self.balls.clear()
        self.addBall()

    def onRightEdgeHit(self, ball: Ball) -> None:
        if self.orientation == "RIGHT":
            self.stop()
        else:
            ball.reflectHorizontally()

    def onLeftEdgeHit(self, ball: Ball) -> None:
        if self.orientation == "LEFT":
            self.stop()
        else:
            ball.reflectHorizontally()

    def onTopEdgeHit(self, ball: Ball) -> None:
        if self.orientation == "TOP":
            self.stop()
        else:
            ball.reflectVertically()

    def onBottomEdgeHit(self, ball: Ball) -> None:
        if self.orientation == "BOTTOM":
            self.stop()
        else:
            ball.reflectVertically()

    def onLeftPaddleHit(self, ball: Ball) -> None:
        ball.reflectHorizontally()

    def onRightPaddleHit(self, ball: Ball) -> None:
        ball.reflectHorizontally()

    def onBottomPaddleHit(self, ball: Ball) -> None:
        ball.reflectVertically()

    def onTopPaddleHit(self, ball: Ball) -> None:
        ball.reflectVertically()
        
class SharedScreenPongGame(SameSidePongGame):
    def __init__(self) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        SameSidePongGame.__init__(self)
        
        self.rightPaddle.side = LEFT
        self.orientation = "LEFT"

class SplitScreenPongGame(SameSidePongGame):
    def __init__(self) -> None:
        """
        Initialize the game by creating the paddles and the ball.
        """
        SameSidePongGame.__init__(self)

        self.orientation = "LEFT"

        self.reset()

    def reset(self) -> None:
        super().reset()

        self.leftPaddle = HorizontalPaddle(side=BOTTOM)
        self.rightPaddle = HorizontalPaddle(side=BOTTOM)
        self.topPaddle = Paddle(side=self.orientation)
        self.bottomPaddle = Paddle(side=self.orientation)
        
        if self.orientation == "BOTTOM":
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

        self.orientation = orientation
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
