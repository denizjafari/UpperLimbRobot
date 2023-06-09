from typing import Optional
import logging
import math

import cv2

from pose_estimation.Models import KeypointSet
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


class ChickenWingGameTransformer(TransformerStage):
    """
    The chicken wing game: The player has their fist close to their shoulder
    and their elbow stretched out. The goal is to raise their elbow aboe a line
    parallel to their shoulders.
    """
    def __init__(self) -> None:
        TransformerStage.__init__(self)
        self._lineDistance = 0

    def setLineDistance(self, distance: int) -> None:
        """
        Set the distance between the elbow line and the average height of the shoulders.
        Negative values move the line down, positive values move it up.
        """
        self._lineDistance = distance

    def lineDistance(self) -> int:
        """
        Get the line distance.
        """
        return self._lineDistance
    
    def transform(self, frameData: FrameData) -> None:
        """
        If this transformer is active, the line is drawn.
        """
        if self.active():
            keypointSet = frameData.keypointSets[0]
            defaultMeasurements: PoseMeasurements = frameData["default_measurements"]
            shoulderHeight = round(frameData.height() * (keypointSet.getLeftShoulder()[0]
                             + keypointSet.getRightShoulder()[0]) / 2)
            lineHeight = shoulderHeight - self.lineDistance()

            cv2.line(frameData.image,
                     (0, lineHeight),
                     (frameData.width(), lineHeight),
                     color=(0, 255, 0), thickness=3)
            
            if defaultMeasurements is not None:
                length = defaultMeasurements.upperArmLength()
                circle_lx = round((keypointSet.getLeftShoulder()[1] + length)
                                  * frameData.width())
                circle_rx = round((keypointSet.getRightShoulder()[1] - length)
                                  * frameData.width())
                cv2.circle(frameData.image,
                        (circle_lx, lineHeight),
                        20,
                        (0, 255, 0),
                        thickness=-1)
                cv2.circle(frameData.image,
                        (circle_rx, lineHeight),
                        20,
                        (0, 255, 0),
                        thickness=-1)
            
        self.next(frameData)
            