import numpy as np
import cv2

class VideoRecorder:
    def addFrame(self, image: np.ndarray) -> None:
        raise NotImplementedError
    
    def close(self) -> None:
        raise NotImplementedError
    

class CVVideoRecorder(VideoRecorder):
    recorder: cv2.VideoWriter

    def __init__(self, frameRate: int, width: int, height: int) -> None:
        self.recorder = cv2.VideoWriter("output.mp4", -1, frameRate, (width, height))

    def addFrame(self, image: np.ndarray) -> None:
        self.recorder.write(image.astype(np.uint8))

    def close(self) -> None:
        self.recorder.release()
