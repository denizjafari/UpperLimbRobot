"""
Interfaces to work with videos.
"""

import numpy as np
import tensorflow as tf

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
