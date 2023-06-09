import cv2

from pose_estimation.transforms import FrameData, TransformerStage


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
            shoulderHeight = round(frameData.height() * (keypointSet.getLeftShoulder()[0]
                             + keypointSet.getRightShoulder()[0]) / 2)
            cv2.line(frameData.image,
                     (0, shoulderHeight - self.lineDistance()),
                     (frameData.width(), shoulderHeight - self.lineDistance()),
                     color=(0, 255, 0), thickness=3)
            
        self.next(frameData)
            