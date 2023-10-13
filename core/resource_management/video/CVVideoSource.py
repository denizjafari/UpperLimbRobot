import cv2
import numpy as np

from .IVideoSource import IVideoSource
from .utils import FrameRateAccumulator

class CVVideoSource(IVideoSource):
    """
    Video Source that grabs the first camera available to OpenCV.

    videoCapture - the video capture object from OpenCV
    """
    videoCapture: cv2.VideoCapture

    def __init__(self) -> None:
        """
        Initialize the Video Capture by using the camera at index 0.
        """
        self.videoCapture = cv2.VideoCapture(0)
        self.frameRateAcc = FrameRateAccumulator()

    def nextFrame(self) -> np.ndarray:
        """
        Grab the next frame from the video capture.
        """
        ret, frame = self.videoCapture.read()
        if ret:
            return frame
        else:
            return None
        
    def width(self) -> int:
        return self.videoCapture.get(cv2.CAP_PROP_FRAME_WIDTH)

    def height(self) -> int:
        return self.videoCapture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
    def frameRate(self) -> int:
        return self.frameRateAcc.frameRate()
    
    def close(self) -> None:
        self.videoCapture.release()