from __future__ import annotations
from typing import Optional, Callable

import io
import csv
import numpy as np
import tensorflow as tf
import cv2
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from pose_estimation.Models import BlazePose, KeypointSet, PoseModel
from pose_estimation.video import VideoRecorder, npArrayToQImage

# The default radius used to draw a marker
MARKER_RADIUS = 3
# The default thickness for the skeleton lines
LINE_THICKNESS = 1

class Transformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images and/or the landmarks detected by the model.
    These transformers can be layered like neural networks, by wrapping
    previous layers in later layers.
    """
    isActive: bool
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
                  keypointSet: KeypointSet) -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Transform the input image. This can occur in place or as a copy.
        Therefore, always respect the return value.
        """
        return self.next(image, keypointSet)
    
    def setNextTransformer(self, nextTransformer: Optional[Transformer]) -> None:
        """
        Changes the next transformer in the pipeline.

        nextTransformer - the next transformer, can be None to make the
        pipeline end with this transformer
        """
        if nextTransformer is None:
            self.next = lambda x, y: (x, y)
        else:
            self.next = nextTransformer.transform
    
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
                  keypointSet: list[KeypointSet]) -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Transform the image by flipping it.
        """
        if self.isActive:
            image = cv2.flip(image, 1)
            for s in keypointSet:
                for keypoint in s.getKeypoints():
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

    def setMarkerRadius(self, markerRadius) -> None:
        """
        Set the marker radius.
        """
        self.markerRadius = markerRadius
    
    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Transform the image by adding circles to highlight the landmarks.f
        """
        if self.isActive:
            width = image.shape[0]
            height = image.shape[1]

            for s in keypointSet:
                for keypoint in s.getKeypoints():
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

    def setLineThickness(self, lineThickness) -> None:
        """
        Set the line thickness.
        """
        self.lineThickness = lineThickness
    
    
    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Transform the image by connectin the joints with straight lines.
        """
        if self.isActive:
            width = image.shape[0]
            height = image.shape[1]

            for s in keypointSet:
                color = (0, 0, 255)
                keypoints = s.getKeypoints()

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
                        
                for l in s.getSkeletonLines():
                    drawSequence(*l)

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

    def setTargetSize(self, targetSize: int) -> None:
        """
        Set targetWidth and targetHeight at the same time to scale a square.
        """
        self.targetWidth = targetSize
        self.targetHeight = targetSize

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Transform the image by scaling it up to the target dimensions.
        """
        if self.isActive:
            image = tf.image.resize_with_pad(image,
                                             self.targetWidth,
                                             self.targetHeight).numpy()

        return self.next(image, keypointSet)
    

class ModelRunner(Transformer):
    """
    Runs a model on the image and adds the keypoints to the list.
    """
    isActive: bool
    model: Optional[PoseModel]

    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, True, previous)

        self.model = None

    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to bs used for detection.
        """
        self.model = model

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Let the model detect the keypoints and add them as a new set of
        keypoints.
        """
        if self.isActive and self.model is not None:
            keypointSet.append(self.model.detect(image))
        
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

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
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

            keypointSet.append(BlazePose.KeypointSet(keypoints))
        
        return self.next(image, keypointSet)
    
class CsvExporter(Transformer):
    """
    Exports the keypoints frame by frame to a separate file.
    """
    isActive: bool
    index: int
    csvWriter: Optional[csv._writer]

    def __init__(self, index: int, previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, True, previous)

        self.csvWriter = None
        self.index = index

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.csvWriter = csv.writer(file) if file is not None else None

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Export the first set of keypoints from the list of keypoint sets. This
        set is subsequently popped from the list.
        """
        if self.isActive and self.csvWriter is not None:
            for k in keypointSet[self.index].getKeypoints():
                self.csvWriter.writerow(k)
        
        return self.next(image, keypointSet)
    
class QImageProvider(Transformer, QObject):
    """
    Emits a signal with the np.ndarray image converted to a QImage.
    """
    frameReady = Signal(QImage)
    isActive: bool

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        Transformer.__init__(self, True, previous)
        QObject.__init__(self)

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Convert the image into a QImage and emit it with the signal.
        """
        if self.isActive:
            if image is not None:
                qImage = npArrayToQImage(image)
            else:
                qImage = None
            self.frameReady.emit(qImage)

        return self.next(image, keypointSet)

class RecorderTransformer(Transformer):
    """
    Records the image.
    """
    isActive: bool
    recorder: Optional[VideoRecorder]
    width: int
    height: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        Transformer.__init__(self, False, previous)

        self.recorder = None
        self.width = 0
        self.height = 0

    def setVideoRecorder(self, recorder: VideoRecorder):
        self.recorder = recorder

    def transform(self, image: np.ndarray, keypointSet: list[KeypointSet]) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Export the first set of keypoints from the list of keypoint sets. This
        set is subsequently popped from the list.
        """
        self.width = image.shape[1]
        self.height = image.shape[0]
        
        if self.isActive and self.recorder is not None:
            self.recorder.addFrame(image)

        return self.next(image, keypointSet)
