from __future__ import annotations
from typing import Optional, Callable

import io
import csv
import numpy as np
import cv2

from pose_estimation.Models import BlazePose, KeypointSet

# The default radius used to draw a marker
MARKER_RADIUS = 3

LINE_THICKNESS = 1

class Transformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images and/or the landmarks detected by the model.
    These transformers can be layered like neural networks, by wrapping
    previous layers in later layers.
    """
    active: bool
    next: Callable[[np.ndarray, KeypointSet], np.ndarray]

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
                  keypointSet: KeypointSet) -> tuple[np.ndarray, KeypointSet]:
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
                  keypointSet: KeypointSet) -> tuple[np.ndarray, KeypointSet]:
        """
        Transform the image by flipping it.
        """
        if self.isActive:
            image = cv2.flip(image, 1)
            for keypoint in keypointSet.getKeypoints():
                keypoint[1] = 1.0 - keypoint[1]
        return self.next(image, keypointSet)

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
    
    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, KeypointSet]:
        """
        Transform the image by adding circles to highlight the landmarks.f
        """
        if self.isActive:
            width = image.shape[0]
            height = image.shape[1]

            for keypoint in keypointSet.getKeypoints():
                x = round(keypoint[0] * width)
                y = round(keypoint[1] * height)
                cv2.circle(image, (y, x), self.markerRadius, color=(255, 255, 255), thickness=-1)

        return self.next(image, keypointSet)
    
class SkeletonDrawer(Transformer):
    """
    Draw the skeleton detected by some model.
    """
    isActive: bool
    lineThickness: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the Drawer.
        """
        Transformer.__init__(self, False, previous)

        self.lineThickness = LINE_THICKNESS
    
    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, KeypointSet]:
        """
        Transform the image by connectin the joints with straight lines.
        """
        if self.isActive:
            width = image.shape[0]
            height = image.shape[1]
            color = (0, 0, 255)
            keypoints = keypointSet.getKeypoints()

            def getCoordinates(index: int) -> tuple[int, int]:
                return (round(width * keypoints[index][1]),
                        round(height * keypoints[index][0]))
            
            def drawSequence(*args):
                for i in range(1, len(args)):
                    cv2.line(image,
                             getCoordinates(args[i - 1]),
                             getCoordinates(args[i]),
                             color,
                             thickness=self.lineThickness)
                    
            for s in keypointSet.getSkeletonLines():
                drawSequence(*s)

        return self.next(image, keypointSet)
    
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

    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, KeypointSet]:
        """
        Transform the image by scaling it up to the target dimensions.
        """
        if self.isActive:
            image = cv2.resize(image,
                               (self.targetWidth, self.targetHeight),
                               interpolation=cv2.INTER_NEAREST)

        return self.next(image, keypointSet)
    
class CsvImporter(Transformer):
    """
    Imports the keypoints frame by frame to a separate file.
    """
    isActive: bool
    csvReader: Optional[csv._reader]
    keypointCount: int

    def __init__(self, keypointCount: int, previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, True, previous)

        self.csvReader = None
        self.keypointCount = keypointCount

    def setFile(self, file: Optional[io.TextIOBase]) -> None:
        """
        Set the file that the csv should be read from.
        The previous file is NOT closed.
        """
        self.csvReader = iter(csv.reader(file)) if file is not None else None

    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, KeypointSet]:
        """
        Import the keypoints for the current image from a file if the transformer
        is active and the file is set.
        """
        if self.isActive and self.csvReader is not None:
            keypoints = []
            for _ in range(self.keypointCount):
                try:
                    keypoints.append([float(x) for x in next(self.csvReader)])
                except StopIteration:
                    keypoints.append([0.0, 0.0, 0.0])
        
        return self.next(image, BlazePose.KeypointSet(keypoints))
    
class CsvExporter(Transformer):
    """
    Exports the keypoints frame by frame to a separate file.
    """
    isActive: bool
    csvWriter: Optional[csv._writer]

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, True, previous)

        self.csvWriter = None

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.csvWriter = csv.writer(file) if file is not None else None

    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, KeypointSet]:
        """
        Export the keypoints of the current image to a file if the transformer
        is active and the file is set.
        """
        if self.isActive and self.csvWriter is not None:
            for k in keypointSet.getKeypoints():
                self.csvWriter.writerow(k)
        
        return self.next(image, keypointSet)
    