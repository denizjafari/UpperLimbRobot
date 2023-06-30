import numpy as np

class KeypointSet:
    """
    A set to store all keypoint sets recognized from a model / imported.
    """

    def getKeypoints(self) -> list[list[float]]:
        """
        Returns the underlying modifiable list of keypoints
        """
        raise NotImplementedError
    

    def getSkeletonLinesBody(self) -> list[list[int]]:
        """
        Returns a list of skeleton lines for the body. A skeleton line is a
        sequence of indices into the keypoint list that indicates in which
        order the indexed keypoints should be connected.
        """
        raise NotImplementedError
    
    def getSkeletonLinesFace(self) -> list[list[int]]:
        """
        Returns a list of skeleton lines for the face. A skeleton line is a
        sequence of indices into the keypoint list that indicates in which
        order the indexed keypoints should be connected.
        """
        raise NotImplementedError
    
    def getLeftShoulder(self) -> list[float]:
        """
        Return the coordinates and confidence for the left shoulder.
        """
        raise NotImplementedError

    def getRightShoulder(self) -> list[float]:
        """
        Return the coordinates and confidence for the right shoulder.
        """
        raise NotImplementedError
    
    def getLeftElbow(self) -> list[float]:
        """
        Return the coordinates and confidence for the left ellbow.
        """
        raise NotImplementedError
    
    def getRightElbow(self) -> list[float]:
        """
        Return the coordinates and confidence for the right ellbow
        """
        raise NotImplementedError
    
    def getNose(self) -> list[float]:
        """
        Return the coordinates and confidence for the nose.
        """
        raise NotImplementedError
    
    def getRightWrist(self) -> list[float]:
        """
        Return the coordinates and confidence for the right wrist.
        """
        raise NotImplementedError
        
    def getLeftWrist(self) -> list[float]:
        """
        Return the coordinates and confidence for the left wrist.
        """
        raise NotImplementedError

class PoseModel:
    """
    Abstract class to allow models to be exchanged easily.
    """
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        raise NotImplementedError  

class SimpleKeypointSet(KeypointSet):
    keypoints: list[list[float]]
    skeletonLines: list[list[int]]

    def __init__(self, keypoints: list[list[float]], skeletonLines: list[list[int]]) -> None:
        self.keypoints = keypoints
        self.skeletonLines = skeletonLines

    def getKeypoints(self) -> list[list[float]]:
        return self.keypoints
    
    def getSkeletonLinesBody(self) -> list[list[int]]:
        return self.skeletonLines
    
    def getSkeletonLinesFace(self) -> list[list[int]]:
        return self.skeletonLines

    def getLeftShoulder(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getRightShoulder(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getLeftElbow(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getRightElbow(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getNose(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getRightWrist(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    
    def getLeftWrist(self) -> list[float]:
        return [0.0, 0.0, 0.0, 0.0]
    