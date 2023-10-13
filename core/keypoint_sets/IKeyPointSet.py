class IKeypointSet:
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