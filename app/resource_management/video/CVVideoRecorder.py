import logging

import numpy as np
import cv2

from .IVideoRecorder import IVideoRecorder

module_logger = logging.getLogger(__name__)

class CVVideoRecorder(IVideoRecorder):
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
        module_logger.info(f"Recording to {outputFile} with {width}x{height}@{frameRate}")
        self.recorder = cv2.VideoWriter(outputFile,
                                        cv2.VideoWriter_fourcc(*"mp4v"),
                                        frameRate,
                                        (width, height))

    def addFrame(self, image: np.ndarray) -> None:
        self.recorder.write(image.astype(np.uint8))

    def close(self) -> None:
        self.recorder.release()