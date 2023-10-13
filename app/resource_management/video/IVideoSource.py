
import numpy as np

from .utils import FrameRateAccumulator

class IVideoSource:
    """
    An interface that acts as a source of frames.
    """
    frameRateAcc: FrameRateAccumulator

    def nextFrame(self) -> np.ndarray:
        """
        Retrieve the most recent frame available
        """
        raise NotImplementedError
    
    def width(self) -> int:
        """
        Get the width of the source.
        """
        raise NotImplementedError

    def height(self) -> int:
        """
        Get the height of the source.
        """
        raise NotImplementedError
    
    def frameRate(self) -> int:
        """
        Get the frame rate of the source.
        """
        raise NotImplementedError
    
    def close(self) -> None:
        """
        Stop the video source and release all resources associated with it.
        """
        raise NotImplementedError