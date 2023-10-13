import numpy as np

class IVideoRecorder:
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