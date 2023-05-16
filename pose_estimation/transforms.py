from __future__ import annotations
from typing import Optional, Callable
import numpy as np
import cv2

# The default radius used to draw a marker
MARKER_RADIUS = 3
# The level of confidence above which a marker is drawn
MARKER_CONFIDENCE_THRESHOLD = 0.0

LINE_THICKNESS = 1

class Transformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images and/or the landmarks detected by the model.
    These transformers can be layered like neural networks, by wrapping
    previous layers in later layers.
    """
    active: bool
    next: Callable[[np.ndarray, np.ndarray], np.ndarray]

    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize this transformer by setting whether it is active and
        optionally setting the next transformer in the chain.
        """
        self.isActive = isActive
        self.next = lambda x, y: (x, y)
        if previous is not None:
            previous.next = self.transform

    def transform(self,
                  image: np.ndarray,
                  keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the input image. This can occur in place or as a copy.
        Therefore, always respect the return value.
        """
        raise NotImplementedError
    
class ImageMirror(Transformer):
    """
    A transformer which mirrors the image along the y-axis. Useful when dealing
    with front cameras.
    """
    isActive: True

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, False, previous)
    
    def transform(self,
                  image: np.ndarray,
                  keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the image by flipping it.
        """
        if self.isActive:
            image = cv2.flip(image, 1)
            for keypoint in keypoints:
                keypoint[1] = 1.0 - keypoint[1]
        return self.next(image, keypoints)
    
class LandmarkConfidenceFilter(Transformer):
    """
    A transformer which filters out landmarks whose confidence level is not
    sufficient.

    confidenceThreshold - landmarks with values below this will be filtered out
    """
    isActive: bool
    confidenceThreshold: float

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the filter.
        """
        Transformer.__init__(self, False, previous)

        self.confidenceThreshold = MARKER_CONFIDENCE_THRESHOLD

    def transform(self, image: np.ndarray, keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the filtering by modifying the keypoints list.
        """
        # Filter out all keypoints with too little confidence
        keypoints = [k for k in keypoints if k[2] > self.confidenceThreshold]
        return self.next(image, keypoints)

class LandmarkDrawer(Transformer):
    """
    Draws the landmarks to the image.

    markerRadius - the radius of the markers
    """
    isActive: bool
    markerRadius: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, False, previous)

        self.markerRadius = MARKER_RADIUS
    
    def transform(self, image: np.ndarray, keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the image by adding circles to highlight the landmarks.
        """
        if self.isActive:
            width = image.shape[0]
            height = image.shape[1]

            for keypoint in keypoints:
                x = round(keypoint[0] * width)
                y = round(keypoint[1] * height)
                cv2.circle(image, (y, x), self.markerRadius, color=(255, 255, 255), thickness=-1)

        return self.next(image, keypoints)
    
class BlazePoseSkeletonDrawer(Transformer):
    """
    Draw the skeleton detected by the BlaePose model.
    """
    isActive: bool
    lineThickness: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the Drawer.
        """
        Transformer.__init__(self, False, previous)

        self.lineThickness = LINE_THICKNESS
    
    def transform(self, image: np.ndarray, keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the image by connectin the joints with straight lines.
        """
        if self.isActive and len(keypoints) == 33:
            width = image.shape[0]
            height = image.shape[1]
            color = (0, 0, 255)

            def getCoordinates(index: int) -> tuple[int, int]:
                return (round(width * keypoints[index][1]), round(height * keypoints[index][0]))
            
            def drawSequence(*args):
                for i in range(1, len(args)):
                    cv2.line(image,
                             getCoordinates(args[i - 1]),
                             getCoordinates(args[i]),
                             color,
                             thickness=self.lineThickness)
            
            drawSequence(8, 6, 5, 4, 0, 1, 2, 3, 7)
            drawSequence(9, 10)
            drawSequence(21, 15, 17, 19, 15, 13, 11, 23, 25, 27, 31, 29, 27)
            drawSequence(22, 16, 18, 20, 16, 14, 12, 24, 26, 28, 32, 30)
            drawSequence(11, 12)
            drawSequence(23, 24)


        return self.next(image, keypoints)
    
class Scaler(Transformer):
    """
    Scales the image up.
    """
    isActive: bool
    targetWidth: int
    targetHeight: int

    def __init__(self,
                 width: int,
                 height: int,
                 previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, True, previous)

        self.targetWidth = width
        self.targetHeight = height

    def transform(self, image: np.ndarray, keypoints: list[list[float]]) -> tuple[np.ndarray, list[list[float]]]:
        """
        Transform the image by scaling it up to the target dimensions.
        """
        if self.isActive:
            image = cv2.resize(image, (self.targetWidth, self.targetHeight), interpolation=cv2.INTER_NEAREST)

        return self.next(image, keypoints)
    