from .IKeyPointSet import IKeypointSet

class SimpleKeypointSet(IKeypointSet):
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
    