import cv2
import numpy as np

from .IVideoSource import IVideoSource
from .utils import NoMoreFrames

class CVVideoFileSource(IVideoSource):
    """
    Video source that loads from a file.
    """
    videoCapture: cv2.VideoCapture
    originalFrameRate: int

    def __init__(self, filename: str) -> None:
        self.videoCapture = cv2.VideoCapture(filename)
        self.originalFrameRate = round(self.videoCapture.get(cv2.CAP_PROP_FPS))

    def frameRate(self) -> int:
        return self.originalFrameRate
    
    def width(self) -> int:
        return int(self.videoCapture.get(cv2.CAP_PROP_FRAME_WIDTH))

    def height(self) -> int:
        return int(self.videoCapture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def nextFrame(self) -> np.ndarray:
        ret, frame = self.videoCapture.read()

        if ret:
            return frame
        else:
            raise NoMoreFrames
        
    def close(self) -> None:
        self.videoCapture.release()
