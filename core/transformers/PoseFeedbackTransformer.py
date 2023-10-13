from typing import Optional

import logging

import cv2

from core.transformers.ITransformer import ITransformer
from core.transformers.ITransformerStage import ITransformerStage
from core.transformers.utils import FrameData
from core.resource_management.registry import REGISTRY

module_logger = logging.getLogger(__name__)


class PoseFeedbackTransformer(ITransformerStage):
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
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.keypointSetIndex = keypointSetIndex
        self.elevAngleLimit = 10
        self.leanForwardLimit = 1
        self.shoulderBaseDistance = 1

        self.wasLeaningTooFar = False
        self.shouldersWereNotLevel = False
        self.feedbackSound = REGISTRY.createItem("sounds.feedback")

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

    def transform(self, frameData: FrameData) -> None:
        """
        Determine the angle between the straight line connecting the two
        shoulder joints and the horizontal line. Then draw the border in
        the correct color.
        """
        if self.active() and not frameData.dryRun \
                and "metrics_max" in frameData \
                    and "metrics" in frameData:

            metrics = frameData["metrics"]
            metricsMax = frameData["metrics_max"]

            correct = True

            if correct and metrics["shoulder_distance"] > metricsMax["shoulder_distance"]:
                if not self.wasLeaningTooFar:
                    module_logger.info("User is leaning too far forward")
                    self.feedbackSound.play()
                    self.wasLeaningTooFar = True
                correct = False
            elif self.wasLeaningTooFar:
                module_logger.info("User corrected leaning too far forward")
                self.wasLeaningTooFar = False

            if correct and metrics["shoulder_elevation_angle"] > metricsMax["shoulder_elevation_angle"]:
                if not self.shouldersWereNotLevel:
                    module_logger.info("User is not keeping their shoulders level enough")
                    self.feedbackSound.play()
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