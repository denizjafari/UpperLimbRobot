"""
Games transformers that are used to start and manage games, passing information
from the frame data objects to the games.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import logging
import math

import cv2

from PySide6.QtCore import QObject, Signal

from models.models import KeypointSet
from pose_estimation.snake import SnakeGame
from pose_estimation.transforms import FrameData, Transformer, TransformerStage


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class PoseMeasurements:
    """
    Extracts relevant measurements from a keypoint set.
    """
    _shoulderDistanceX: float
    _shoulderDistanceY: float
    _leftUpperArmLength: float
    _rightUpperArmLength: float

    def __init__(self, keypointSet: KeypointSet):
        """
        Calculate baseline measures from the keypoint set.
        """
        leftShoulder = keypointSet.getLeftShoulder()
        rightShoulder = keypointSet.getRightShoulder()
        self._shoulderDistanceX = abs(leftShoulder[1] - rightShoulder[1])
        self._shoulderDistanceY = abs(leftShoulder[0] - rightShoulder[0])

        leftElbow = keypointSet.getLeftElbow()
        rightElbow = keypointSet.getRightElbow()
        self._leftUpperArmLength = abs(leftElbow[1] - leftShoulder[1])
        self._rightUpperArmLength = abs(rightElbow[1] - rightShoulder[1])

    def leftUpperArmLength(self) -> float:
        """
        Return the length of the left arm between shoulder and elbow.
        """
        return self._leftUpperArmLength
    
    def rightUpperArmLength(self) -> float:
        """
        Return the length of the right arm between shoulder and elbow.
        """
        return self._rightUpperArmLength
    
    def upperArmLength(self) -> float:
        """
        Return the average between left and right upper arm lengths.
        """
        return (self.leftUpperArmLength() + self.rightUpperArmLength()) / 2
    
    def shoulderDistanceX(self) -> float:
        """
        Return the distance between the left and right shoulders.
        """
        return self._shoulderDistanceX
    
    def shoulderDistanceY(self) -> float:
        """
        Return the distance between the left and right shoulders.
        """
        return self._shoulderDistanceY
    
    def shoulderDistance(self) -> float:
        return math.sqrt(self.shoulderDistanceX() ** 2
                         + self.shoulderDistanceY() ** 2)

class DefaultMeasurementsTransformer(TransformerStage):
    """
    Takes the default measurements and repeatedly injects them into the frame
    data object.
    """
    _lastKeypointSet: list[list[float]]
    baselineMeasurements: Optional[PoseMeasurements]

    def __init__(self, isActive: bool = True,
                 previous: Optional[Transformer] = None) -> None:
        TransformerStage.__init__(self, isActive, previous)
        self.baselineMeasurements = None
        self._lastKeypointSet = None
    
    def captureDefaultPoseMeasurements(self) -> None:
        if self._lastKeypointSet is not None:
            self.baselineMeasurements = PoseMeasurements(self._lastKeypointSet)
            module_logger.info("Set baseline measurements")
        else:
            module_logger.warning(
                "Cannot set baseline measures without any detected keypoints")

    def transform(self, frameData: FrameData) -> None:
        if self.active():
            self._lastKeypointSet = frameData.keypointSets[0]
            frameData["default_measurements"] = self.baselineMeasurements

        self.next(frameData)

class GestureDetector:
    """
    Interface for all GestureDetectors.
    """
    def detect(self, metrics: dict[str, float]) -> None:
        raise NotImplementedError

class ChickenWingDetector(GestureDetector):
    """
    Abstract class for chicken wing detection. Detects whether a chicken wing
    is performed.
    """
    def __init__(self) -> None:
        """
        Initialize the detector.
        """
        self.has_recovered = False

    def elbowHeight(self, metrics: dict) -> float:
        """
        Return the elbow height from the metrics. Needs to be implemented by
        the subclass to return the left or right elbow height.
        """
        raise NotImplementedError
    
    def shoulderHeight(self, metrics: dict) -> float:
        """
        Return the shoulder height from the metrics.
        """
        return metrics["shoulder_height"]

    def detect(self, metrics: dict) -> bool:
        """
        Detect whether a chicken wing is performed.
        """
        over_threshold = self.elbowHeight(metrics) > self.shoulderHeight(metrics)
        if over_threshold and self.has_recovered:
            module_logger.info("Chicken wing detected")
            self.has_recovered = False
            return True
        elif not self.has_recovered and \
                self.elbowHeight(metrics) < self.shoulderHeight(metrics) - 0.1:
            module_logger.info("Chicken wing recovered")
            self.has_recovered = True
            return False
        else:
            return False
        
class LeftChickenWingDetector(ChickenWingDetector):
    def elbowHeight(self, metrics: dict):
        return metrics["left_elbow_height"]
    
class RightChickenWingDetector(ChickenWingDetector):
    def elbowHeight(self, metrics: dict):
        return metrics["right_elbow_height"]


class PoseFeedbackTransformer(TransformerStage):
    """
    Adds feedback on compensation to the image. Measures the angle between a
    straight line connecting the two shoulder joints and the horizontal axis.
    If the angle is within the defined angleLimit, a green border is added to
    the image, otherwise a red border is drawn.

    keypointSetIndex - the index into the keypointSet list from which the
    shoulder joint coordinates should be taken.
    angleLimit - the maximum angle (in degrees) that is accepted.
    """
    keypointSetIndex: int
    elevAngleLimit: int
    leanForwardLimit: int
    shoulderBaseDistance: float
    lastShoulderDistance: float

    def __init__(self,
                 keypointSetIndex: int = 0,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

        self.keypointSetIndex = keypointSetIndex
        self.elevAngleLimit = 10
        self.leanForwardLimit = 1
        self.shoulderBaseDistance = 1

        self.wasLeaningTooFar = False
        self.shouldersWereNotLevel = False

    def setAngleLimit(self, angleLimit: int) -> None:
        """
        Set the angleLimit to this angle (in degrees).
        """
        self.elevAngleLimit = angleLimit

    def setLeanForwardLimit(self, lfLimit: int) -> None:
        """
        Set the lf limit to (1 + lfLimit / 10).
        """
        self.leanForwardLimit = 1 + (lfLimit / 10)

    def _checkShoulderElevation(self, keypointSet: KeypointSet) -> bool:
        leftShoulder = keypointSet.getLeftShoulder()
        rightShoulder = keypointSet.getRightShoulder()

        delta_x = abs(rightShoulder[1] - leftShoulder[1])
        delta_y = abs(rightShoulder[0] - leftShoulder[0])

        if delta_x != 0:
            angle_rad = math.atan(delta_y / delta_x)
            angle_deg = math.degrees(angle_rad)
        else:
            angle_deg = 0

        return angle_deg <= self.elevAngleLimit
    
    def _checkLeanForward(self, keypointSet: KeypointSet,
                          defaultMeasures: PoseMeasurements) -> bool:
        leftShoulder = keypointSet.getLeftShoulder()
        rightShoulder = keypointSet.getRightShoulder()

        delta_x = abs(rightShoulder[1] - leftShoulder[1])
        delta_y = abs(rightShoulder[0] - leftShoulder[0])

        delta = math.sqrt(delta_x ** 2 + delta_y ** 2)

        self.lastShoulderDistance = delta

        return delta / defaultMeasures.shoulderDistance() <= self.leanForwardLimit

    def transform(self, frameData: FrameData) -> None:
        """
        Determine the angle between the straight line connecting the two
        shoulder joints and the horizontal line. Then draw the border in
        the correct color.
        """
        if self.active() and not frameData.dryRun \
            and isinstance(frameData["default_measurements"], PoseMeasurements):
            keypointSet = frameData.keypointSets[self.keypointSetIndex]

            if "metrics_max" not in frameData:
                metricsMax = {}
                frameData["metrics_max"] = metricsMax
            else:
                metricsMax = frameData["metrics_max"]

            metricsMax["shoulder_elevation_angle"] = self.elevAngleLimit
            correct = True

            if correct and not self._checkLeanForward(keypointSet,
                                                      frameData["default_measurements"]):
                if not self.wasLeaningTooFar:
                    module_logger.info("User is leaning too far forward")
                    self.wasLeaningTooFar = True
                correct = False
            elif self.wasLeaningTooFar:
                module_logger.info("User corrected leaning too far forward")
                self.wasLeaningTooFar = False

            if correct and not self._checkShoulderElevation(keypointSet):
                if not self.shouldersWereNotLevel:
                    module_logger.info("User is not keeping their shoulders level enough")
                    self.shouldersWereNotLevel = True
                correct = False
            elif self.shouldersWereNotLevel:
                module_logger.info("User corrected not keeping their shoulder level enough")
                self.shouldersWereNotLevel = False
            
            cv2.rectangle(frameData.image,
                            (0,0),
                            (frameData.width(), frameData.height()),
                            (0, 255, 0) if correct else (0, 0, 255),
                            thickness=10)

        self.next(frameData)

    def __str__(self) -> str:
        return "Feedback"


class Snake(TransformerStage, QObject):
    """
    The snake game. The snake is controlled by the user's body. A right chicken
    wing turns the snake to the right, a left chicken wing turns the snake to
    left.
    """
    leftChickenWing = Signal()
    rightChickenWing = Signal()
    timeIntervalChanged = Signal(int)

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        TransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

        self.leftChickenWingDetector = LeftChickenWingDetector()
        self.rightChickenWingDetector = RightChickenWingDetector()

        self.game = SnakeGame()
        self.leftChickenWing.connect(self.game.turnLeft)
        self.rightChickenWing.connect(self.game.turnRight)
        self.game.show()

    def setTimerInterval(self, timerInterval) -> None:
        """
        Set the timer interval between the snake moves.
        """
        self.game.setTimerInterval(timerInterval)

    def transform(self, frameData: FrameData) -> None:
        """
        Check wether the user has performed a chicken wing. If so, emit the
        corresponding signal. The signal is emitted when the elbow is above the
        shoulder. Before the signal is emitted, the elbow must be below the shoulder
        plus some margin.
        """
        if self.active() and not frameData.dryRun and "metrics" in frameData:
            if self.leftChickenWingDetector.detect(frameData["metrics"]):
                self.leftChickenWing.emit()
            if self.rightChickenWingDetector.detect(frameData["metrics"]):
                self.rightChickenWing.emit()

        self.next(frameData)