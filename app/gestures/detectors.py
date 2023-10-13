import logging

from .IDetector import IDetector

module_logger = logging.getLogger(__name__)

class ChickenWingDetector(IDetector):
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