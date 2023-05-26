from __future__ import annotations
from typing import Optional

import numpy as np
import cv2
import tensorflow as tf

from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QVideoSink, QVideoFrame
from PySide6.QtGui import QImage
from PySide6.QtCore import Slot, Signal, QObject, QTimer


def qImageToNpArray(image: QImage) -> np.ndarray:
    """
    Convert a QImage to an ndarray with dimensions (height, width, channels)
    """
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    image = np.array(image.bits()).reshape(image.height(), image.width(), 4)
    image = np.delete(image, np.s_[-1:], axis=2)

    return image

def npArrayToQImage(image: np.ndarray) -> QImage:
    """
    Convert an ndarray with dimensions (height, width, channels) back
    into a QImage.
    """
    padding = [[0, 0], [0, 0], [0, 1]]
    image = tf.pad(image, padding, constant_values=255).numpy()
    buffer = image.astype(np.uint8).tobytes()
    image = QImage(buffer, image.shape[1], image.shape[0], QImage.Format.Format_RGB32)

    return image

class NoMoreFrames(Exception):
    pass

class FrameRateAccumulator(QObject):
    """
    Keeps track of the frame rate. Emits a signal to update the frame rate
    every second with the number of frames that were rendered in the previous
    second.
    """
    frameRateUpdated = Signal(int)
    frameCount: int
    lastFrameRate: int

    def __init__(self, baseFrameRate: int = 0) -> None:
        """
        Initialize the frame rate provider.
        """
        QObject.__init__(self)
        self.frameRateTimer = QTimer()
        self.frameRateTimer.setInterval(1000)
        self.frameRateTimer.timeout.connect(self._onFrameRateUpdate)
        self.frameRateTimer.start()

        self.frameCount = 0
        self.lastFrameRate = baseFrameRate

    def frameRate(self) -> int:
        return self.lastFrameRate

    @Slot()
    def onFrameReady(self) -> None:
        """
        Slot to be called whenever a frame is ready to be displayed.
        """
        self.frameCount += 1

    @Slot()
    def _onFrameRateUpdate(self) -> None:
        """
        Emit a signal carrying the number of frames that were processed in the
        previous second.
        """
        self.lastFrameRate = self.frameCount
        self.frameCount = 0

class VideoSource:
    """
    An interface that acts as a source of frames.
    """
    frameRateAcc: FrameRateAccumulator

    def nextFrame(self) -> np.ndarray:
        """
        Retrieve the most recent frame available
        """
        raise NotImplementedError
    
    def frameRate(self) -> int:
        raise NotImplementedError
    

class CVVideoSource(VideoSource):
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
        
    def frameRate(self) -> int:
        return self.frameRateAcc.frameRate()
        
        
class CVVideoFileSource(VideoSource):
    """
    Video source that loads from a file.
    TODO: Closing/Releasing
    """
    videoCapture: cv2.VideoCapture
    originalFrameRate: int

    def __init__(self, filename: str) -> None:
        self.videoCapture = cv2.VideoCapture(filename)
        self.originalFrameRate = round(self.videoCapture.get(cv2.CAP_PROP_FPS))

    def frameRate(self) -> int:
        return self.originalFrameRate

    def nextFrame(self) -> np.ndarray:
        ret, frame = self.videoCapture.read()

        if ret:
            return frame
        else:
            raise NoMoreFrames


class QVideoSource(VideoSource):
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


class VideoRecorder:
    """
    An interface that allows to assemble a video from frames ans save it to
    disk.
    """
    
    def addFrame(self, image: np.ndarray) -> None:
        """
        Add a frame to the video. Image has to be of the format
        (width, height, channels).

        image - the frame that should be added.
        """
        raise NotImplementedError
    
    def close(self) -> None:
        """
        Close the video stream and save the video to disk.
        """
        raise NotImplementedError
    

class CVVideoRecorder(VideoRecorder):
    """
    Light implementation of the video recorder by default
    outputting to output.mp4.

    recorder - the opencv video writer
    """
    recorder: cv2.VideoWriter

    def __init__(self,
                 frameRate: int,
                 width: int,
                 height: int,
                 outputFile: str = "output.mp4",) -> None:
        """
        Create the VideoWriter accepting frames with dimensions width x height
        and stitching to a frame rate of frameRate.

        frameRate - the frame rate of the resulting video
        width - the width of each frame in pixels
        height - the height of each fram in pixels
        """
        self.recorder = cv2.VideoWriter(outputFile, -1, frameRate, (width, height))

    def addFrame(self, image: np.ndarray) -> None:
        self.recorder.write(image.astype(np.uint8))

    def close(self) -> None:
        self.recorder.release()
