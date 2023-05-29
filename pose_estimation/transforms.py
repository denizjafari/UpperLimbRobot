from __future__ import annotations
from typing import Optional, Callable

import math
import io
import csv
import numpy as np
import tensorflow as tf
import cv2
import cvzone
from cvzone.SelfiSegmentationModule import SelfiSegmentation

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from pose_estimation.Models import BlazePose, KeypointSet, PoseModel
from pose_estimation.video import NoMoreFrames, VideoRecorder, VideoSource, \
    npArrayToQImage

class FrameData:
    """
    Contains image, keypoints and metadata to pass between transformers.

    dryRun - whether this run is a dry run. If true, no complex processing
    should take place. Instead, format changes like image resolution
    adjustments should take place.
    _width - the width of the proprosed image if the image is None.
    _height - the height of the proposed image if the image is None.

    streamEnded - whether the stream of frames is ended.
    image - the image/frame that should be processed (if it exists).
    keypointSets - a list of all detected keypointSets.
    """
    dryRun: bool
    _width: int
    _height: int

    streamEnded: bool
    image: Optional[np.ndarray]
    keypointSets: list[KeypointSet]

    def __init__(self,
                 width: int = -1,
                 height: int = -1,
                 dryRun: bool = False,
                 image: Optional[np.ndarray] = None,
                 streamEnded: bool = False,
                 frameRate: int = -1,
                 keypointSets: Optional[list[KeypointSet]] = None):
        """
        Initialize the FrameData object.
        """
        self.dryRun = dryRun
        self.image = image
        self._width = width
        self._height = height
        self.frameRate = frameRate
        self.streamEnded = streamEnded
        self.keypointSets = keypointSets if keypointSets is not None else []

    def width(self) -> int:
        """
        Determine the width of the (proposed) image.
        """
        if self.image is not None:
            return self.image.shape[1]
        else:
            return self._width
        
    def height(self) -> int:
        """
        Determine the height of the (proposed) image.
        """
        if self.image is not None:
            return self.image.shape[0]
        else:
            return self._width

    def setWidth(self, width) -> None:
        """
        If the image is None, set the proposed image width.
        """
        self._width = width
    
    def setHeight(self, height) -> None:
        """
        If the image is None, set the proposed image height.
        """
        self._height = height


class Transformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images, the landmarks, and/or metadata in the pipeline.
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
        self.next = lambda x: x
        if previous is not None:
            previous.next = self.transform

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Transform the input image. This can occur in place or as a copy.
        Therefore, always respect the return value.
        """
        return self.next(frameData)
    
    def setNextTransformer(self,
                           nextTransformer: Optional[Transformer]) -> None:
        """
        Changes the next transformer in the pipeline.

        nextTransformer - the next transformer, can be None to make the
        pipeline end with this transformer
        """
        if nextTransformer is None:
            self.next = lambda x: x
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
        Transformer.__init__(self, True, previous)
    
    def transform(self, frameData: FrameData) -> FrameData:
        """
        Transform the image by flipping it.
        """
        if self.isActive:
            frameData.image = cv2.flip(frameData.image, 1)
            for s in frameData.keypointSets:
                for keypoint in s.getKeypoints():
                    keypoint[1] = 1.0 - keypoint[1]
        return self.next(frameData)

class LandmarkDrawer(Transformer):
    """
    Draws the landmarks to the image.

    markerRadius - the radius of the markers
    """
    isActive: bool
    markerRadius: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.markerRadius = 1
        self.color = (255, 255, 255)

    def setMarkerRadius(self, markerRadius) -> None:
        """
        Set the marker radius.
        """
        self.markerRadius = markerRadius

    def setRGBColor(self, color: tuple[int, int, int]) -> None:
        """
        Set the color of the markers. Takes in a tuple of three values 0-255
        for the r, g abd b channels.
        """
        self.color = (color[2], color[1], color[0])
    
    def getRGBColor(self) -> tuple[int, int, int]:
        """
        Get the color of the markers. Returns a tuple of three values 0-255
        for the r, g abd b channels.
        """
        return (self.color[2], self.color[1], self.color[0])
    
    def transform(self, frameData: FrameData) -> FrameData:
        """
        Transform the image by adding circles to highlight the landmarks.
        """
        if self.isActive and not frameData.dryRun:
            for s in frameData.keypointSets:
                for keypoint in s.getKeypoints():
                    x = round(keypoint[0] * frameData.width())
                    y = round(keypoint[1] * frameData.height())
                    cv2.circle(frameData.image,
                               (y, x),
                               self.markerRadius,
                               color=self.color,
                               thickness=-1)

        return self.next(frameData)
    
class SkeletonDrawer(Transformer):
    """
    Draw the skeleton detected by some model.
    """
    isActive: bool
    lineThickness: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the Drawer.
        """
        Transformer.__init__(self, True, previous)

        self.lineThickness = 1
        self.color = (0, 0, 255)

    def setLineThickness(self, lineThickness) -> None:
        """
        Set the line thickness.
        """
        self.lineThickness = lineThickness
    
    def setRGBColor(self, color: tuple[int, int, int]) -> None:
        """
        Set the color of the lines. Takes in a tuple of three values 0-255
        for the r, g abd b channels.
        """
        self.color = (color[2], color[1], color[0])
    
    def getRGBColor(self) -> tuple[int, int, int]:
        """
        Get the color of the lines. Returns a tuple of three values 0-255
        for the r, g abd b channels.
        """
        return (self.color[2], self.color[1], self.color[0])
    
    def transform(self, frameData: FrameData) -> FrameData:
        """
        Transform the image by connectin the body joints with straight lines.
        """
        if self.isActive and not frameData.dryRun:
            for s in frameData.keypointSets:
                keypoints = s.getKeypoints()

                def getCoordinates(index: int) -> tuple[int, int]:
                    return (round(frameData.width() * keypoints[index][1]),
                            round(frameData.height() * keypoints[index][0]))
                
                def drawSequence(*args):
                    for i in range(1, len(args)):
                        cv2.line(frameData.image,
                                getCoordinates(args[i - 1]),
                                getCoordinates(args[i]),
                                self.color,
                                thickness=self.lineThickness)
                        
                for l in s.getSkeletonLinesBody():
                    drawSequence(*l)

        return self.next(frameData)
    
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
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.targetWidth = width
        self.targetHeight = height

    def setTargetSize(self, targetSize: int) -> None:
        """
        Set targetWidth and targetHeight at the same time to scale a square.
        """
        self.targetWidth = targetSize
        self.targetHeight = targetSize

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Transform the image by scaling it up to the target dimensions.
        """
        if self.isActive:
            if not frameData.dryRun and frameData.image is not None:
                frameData.image = tf.image.resize_with_pad(frameData.image,
                                                self.targetWidth,
                                                self.targetHeight).numpy()
            else:
                frameData.setWidth(self.targetWidth)
                frameData.setHeight(self.targetHeight)

        return self.next(frameData)
    

class ModelRunner(Transformer):
    """
    Runs a model on the image and adds the keypoints to the list.
    """
    isActive: bool
    model: Optional[PoseModel]

    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.model = None

    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to bs used for detection.
        """
        self.model = model

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Let the model detect the keypoints and add them as a new set of
        keypoints.
        """
        if self.isActive and self.model is not None and not frameData.dryRun \
            and frameData.image is not None:
            frameData.keypointSets.append(self.model.detect(frameData.image))
        
        return self.next(frameData)
        
    
class CsvImporter(Transformer):
    """
    Imports the keypoints frame by frame from a separate file. Currently only
    supports BlazePose-type model keypoints.
    """
    isActive: bool
    csvReader: Optional[csv._reader]
    keypointCount: int

    def __init__(self,
                 keypointCount: int,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.csvReader = None
        self.keypointCount = keypointCount

    def setFile(self, file: Optional[io.TextIOBase]) -> None:
        """
        Set the file that the csv should be read from.
        The previous file is NOT closed.
        """
        self.csvReader = iter(csv.reader(file)) if file is not None else None

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Import the keypoints for the current image from a file if the
        transformer is active and the file is set.
        """
        if self.isActive \
            and self.csvReader is not None \
                and not frameData.dryRun:
            keypoints = []
            for _ in range(self.keypointCount):
                try:
                    keypoints.append([float(x) for x in next(self.csvReader)])
                except StopIteration:
                    keypoints.append([0.0, 0.0, 0.0])

            frameData.keypointSets.append(BlazePose.KeypointSet(keypoints))
        
        return self.next(frameData)
    
class CsvExporter(Transformer):
    """
    Exports the keypoints frame by frame to a separate file.
    """
    isActive: bool
    index: int
    csvWriter: Optional[csv._writer]

    def __init__(self,
                 index: int,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.csvWriter = None
        self.index = index

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.csvWriter = csv.writer(file) if file is not None else None

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Export the first set of keypoints from the list of keypoint sets. This
        set is subsequently popped from the list.
        """
        if self.isActive \
            and self.csvWriter is not None \
                and not frameData.dryRun:
            for k in frameData.keypointSets[self.index].getKeypoints():
                self.csvWriter.writerow(k)
        
        return self.next(frameData)
    
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

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Convert the image into a QImage and emit it with the signal.
        """
        if self.isActive:
            if frameData.image is not None:
                qImage = npArrayToQImage(frameData.image)
            else:
                qImage = None
            self.frameReady.emit(qImage)

        return self.next(frameData)

class RecorderTransformer(Transformer):
    """
    Records the image.
    """
    isActive: bool
    recorder: Optional[VideoRecorder]
    frameRate: int
    width: int
    height: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        Transformer.__init__(self, True, previous)

        self.recorder = None
        self.width = 0
        self.height = 0

    def setVideoRecorder(self, recorder: VideoRecorder):
        """
        Set the video recorder with which frames should be recorded.
        """
        self.recorder = recorder

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Record the current frame if the transformer is active and the recorder
        is initialized.
        """
        self.width = frameData.width()
        self.height = frameData.height()
        self.frameRate = frameData.frameRate
        
        if self.isActive \
            and self.recorder is not None \
                and not frameData.dryRun:
            self.recorder.addFrame(frameData.image)

        return self.next(frameData)
    

class PoseFeedbackTransformer(Transformer):
    """
    Adds feedback on compensation to the image. Measures the angle between a
    straight line connecting the two shoulder joints and the horizontal axis.
    If the angle is within the defined angleLimit, a green border is added to
    the image, otherwise a red border is drawn.

    keypointSetIndex - the index into the keypointSet list from which the
    shoulder joint coordinates should be taken.
    angleLimit - the maximum angle (in degrees) that is accepted.
    """
    keypointSetIndex: int
    angleLimit: int

    def __init__(self,
                 keypointSetIndex: int = 0,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)

        self.keypointSetIndex = keypointSetIndex
        self.angleLimit = 10

    def setAngleLimit(self, angleLimit: int) -> None:
        """
        Set the angleLimit to this angle (in degrees).
        """
        self.angleLimit = angleLimit

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Determine the angle between the straight line connecting the two
        shoulder joints and the horizontal line. Then draw the border in
        the correct color.
        """
        if self.isActive and not frameData.dryRun:
            keypointSet = frameData.keypointSets[self.keypointSetIndex]
            leftShoulder = keypointSet.getLeftShoulder()
            rightShoulder = keypointSet.getRightShoulder()

            delta_x = abs(rightShoulder[1] - leftShoulder[1])
            delta_y = abs(rightShoulder[0] - leftShoulder[0])

            if delta_x != 0:
                angle_rad = math.atan(delta_y / delta_x)
                angle_deg = math.degrees(angle_rad)

                if angle_deg > self.angleLimit:
                    color = (0, 0, 255)
                else:
                    color = (0, 255, 0)
                
                cv2.rectangle(frameData.image,
                              (0,0),
                              (frameData.width(), frameData.height()),
                              color,
                              thickness=10)

        return self.next(frameData)
    

class BackgroundRemover(Transformer):
    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)
        self.segmentation = SelfiSegmentation(0)


    def transform(self, frameData: FrameData) -> FrameData:
        """
        Remove the background
        """
        if self.isActive and not frameData.dryRun:
           frameData.image = self.segmentation.removeBG(frameData.image.astype(np.uint8))
        
        return frameData
    

class VideoSourceTransformer(Transformer, QObject):
    """
    Grabs the next frame from the video source and puts it in the pipeline.
    """
    streamEnded = Signal()
    videoSource: Optional[VideoSource]

    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        Transformer.__init__(self, True, previous)
        QObject.__init__(self)

        self.videoSource = None
    
    def setVideoSource(self, videoSource: VideoSource) -> None:
        """
        Set the source of the video.
        """
        self.videoSource = videoSource

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Add the frame rate property to the frameData object and process the
        next frame.
        """
        if self.videoSource is not None:
            frameData.frameRate = self.videoSource.frameRate()
            if self.isActive:
                try:
                    frameData.image = self.videoSource.nextFrame()
                except NoMoreFrames:
                    frameData.streamEnded = True
            return self.next(frameData)
        
        return frameData
