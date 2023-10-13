from typing import Optional

import numpy as np

from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QVideoSink, QVideoFrame
from PySide6.QtCore import Slot

from .IVideoSource import IVideoSource
from .utils import FrameRateAccumulator, qImageToNpArray


class QVideoSource(IVideoSource):
    """
    Video Source that uses a cameras available via Qt. The camera must be set
    via setCamera.

    camera - the camera from which frames are grabbed
    cameraSession - the media camera session
    videoSink- the endpoint through which images are funnelled and made available
    videoFrame - the most recent video frame available
    """
    camera: Optional[QCamera]
    cameraSession: QMediaCaptureSession
    videoSink: QVideoSink
    videoFrame: QVideoFrame

    def __init__(self) -> None:
        """
        Initialize the video source. Only the camera is still missing and can
        be set using setCamera.
        """
        self.cameraSession = QMediaCaptureSession()
        self.videoSink = QVideoSink()
        self.videoSink.videoFrameChanged.connect(self.setVideoFrame)
        self.cameraSession.setVideoSink(self.videoSink)
        self.camera = None
        self.videoFrame = None
        self.frameRateAcc = FrameRateAccumulator()
    
    def frameRate(self) -> int:
        return self.frameRateAcc.frameRate()
    
    def width(self) -> int:
        return self.videoFrame.width() if self.videoFrame is not None else -1

    def height(self) -> int:
        return self.videoFrame.height() if self.videoFrame is not None else -1

    def nextFrame(self) -> np.ndarray:
        """
        Retrieve the most recent frame available
        """
        if self.videoFrame is not None:
            self.frameRateAcc.onFrameReady()
            image = self.videoFrame.toImage()        
            return qImageToNpArray(image)
        else:
            return None
        
    @Slot(QVideoFrame)
    def setVideoFrame(self, videoFrame: QVideoFrame) -> None:
        """
        Update the current video frame.
        """
        self.videoFrame = videoFrame

    @Slot(QCamera)
    def setCamera(self, camera: QCamera) -> None:
        """
        Change the camera to the given camera
        """
        camera.start()
        self.cameraSession.setCamera(camera)
        if self.camera is not None: self.camera.stop()
        self.camera = camera

    def close(self) -> None:
        if self.camera is not None:
            self.camera.stop()