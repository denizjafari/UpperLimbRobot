"""
Transforms for modifying images, landmarks, and metadata in the pipeline via
the frame data object.
"""

from __future__ import annotations
from collections import defaultdict
import logging
import json
from typing import Optional

import io
import csv
import numpy as np
import tensorflow as tf
import cv2
import math
from cvzone.SelfiSegmentationModule import SelfiSegmentation
from scipy import signal

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from models.mediapipe import BlazePose
from app.models.IModel import IModel
from app.resource_management.video.IVideoRecorder import IVideoRecorder
from app.resource_management.video.IVideoSource import IVideoSource
from app.resource_management.video.utils import npArrayToQImage, NoMoreFrames
from app.transformers.ITransformerStage import ITransformerStage
from app.transformers.ITransformer import ITransformer
from app.transformers.utils import FrameData

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

    
class ImageMirror(ITransformerStage):
    """
    A transformer which mirrors the image along the y-axis. Useful when dealing
    with front cameras.
    """
    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)
    
    def transform(self, frameData: FrameData) -> None:
        """
        Transform the image by flipping it.
        """
        if self.active():
            frameData.image = cv2.flip(frameData.image, 1)
            for s in frameData.keypointSets:
                for keypoint in s.getKeypoints():
                    keypoint[1] = 1.0 - keypoint[1]
        self.next(frameData)

    def __str__(self) -> str:
        return "Mirror"

class LandmarkDrawer(ITransformerStage):
    """
    Draws the landmarks to the image.

    markerRadius - the radius of the markers
    """
    markerRadius: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

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
    
    def transform(self, frameData: FrameData) -> None:
        """
        Transform the image by adding circles to highlight the landmarks.
        """
        if self.active() and not frameData.dryRun:
            for s in frameData.keypointSets:
                for keypoint in s.getKeypoints():
                    y = round(keypoint[0] * frameData.height())
                    x = round(keypoint[1] * frameData.width())
                    cv2.circle(frameData.image,
                               (x, y),
                               self.markerRadius,
                               color=self.color,
                               thickness=-1)

        self.next(frameData)

    def __str__(self) -> str:
        return "Landmarks"
    
class SkeletonDrawer(ITransformerStage):
    """
    Draw the skeleton detected by some model.
    """
    lineThickness: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize the Drawer.
        """
        ITransformerStage.__init__(self, True, previous)

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
    
    def transform(self, frameData: FrameData) -> None:
        """
        Transform the image by connectin the body joints with straight lines.
        """
        if self.active() and not frameData.dryRun:
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

        self.next(frameData)
    
    def __str__(self) -> str:
        return "Skeleton"
    
class Scaler(ITransformerStage):
    """
    Scales the image up.
    """
    targetWidth: int
    targetHeight: int

    def __init__(self,
                 width: int,
                 height: int,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.targetWidth = width
        self.targetHeight = height

    def setTargetSize(self, targetSize: int) -> None:
        """
        Set targetWidth and targetHeight at the same time to scale a square.
        """
        self.targetWidth = targetSize
        self.targetHeight = targetSize

    def transform(self, frameData: FrameData) -> None:
        """
        Transform the image by scaling it up to the target dimensions.
        """
        if self.active():
            if not frameData.dryRun and frameData.image is not None:
                frameData.image = tf.image.resize_with_pad(frameData.image,
                                                self.targetWidth,
                                                self.targetHeight).numpy()
            else:
                frameData.setWidth(self.targetWidth)
                frameData.setHeight(self.targetHeight)

        self.next(frameData)

    def __str__(self) -> str:
        return "Scaler"
    

class ModelRunner(ITransformerStage):
    """
    Runs a model on the image and adds the keypoints to the list.
    """
    model: Optional[IModel]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.model = None

    def setModel(self, model: IModel) -> None:
        """
        Set the model to bs used for detection.
        """
        self.model = model

    def transform(self, frameData: FrameData) -> None:
        """
        Let the model detect the keypoints and add them as a new set of
        keypoints.
        """
        if self.active() and self.model is not None and not frameData.dryRun \
            and frameData.image is not None:
            frameData.keypointSets.append(self.model.detect(frameData.image))
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Model"
    
class CsvImporter(ITransformerStage):
    """
    Imports the keypoints frame by frame from a separate file. Currently only
    supports BlazePose-type model keypoints.
    """
    csvReader: Optional[csv._reader]
    keypointCount: int

    def __init__(self,
                 keypointCount: int,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.csvReader = None
        self.keypointCount = keypointCount

    def setFile(self, file: Optional[io.TextIOBase]) -> None:
        """
        Set the file that the csv should be read from.
        The previous file is NOT closed.
        """
        self.csvReader = iter(csv.reader(file)) if file is not None else None

    def transform(self, frameData: FrameData) -> None:
        """
        Import the keypoints for the current image from a file if the
        transformer is active and the file is set.
        """
        if self.active() \
            and self.csvReader is not None \
                and not frameData.dryRun:
            keypoints = []
            for _ in range(self.keypointCount):
                try:
                    keypoints.append([float(x) for x in next(self.csvReader)])
                except StopIteration:
                    keypoints.append([0.0, 0.0, 0.0])

            frameData.keypointSets.append(BlazePose.KeypointSet(keypoints))
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Importer"


class QImageProvider(ITransformerStage, QObject):
    """
    Emits a signal with the np.ndarray image converted to a QImage.
    """
    frameReady = Signal(QImage)

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize the image provider
        """
        ITransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

    def transform(self, frameData: FrameData) -> None:
        """
        Convert the image into a QImage and emit it with the signal.
        """
        if self.active():
            if frameData.image is not None:
                qImage = npArrayToQImage(frameData.image)
            else:
                qImage = None
            self.frameReady.emit(qImage)

        self.next(frameData)

    def __str__(self) -> str:
        return "Preview Image Provder"

class FrameDataProvider(ITransformerStage, QObject):
    """
    Emits a signal with the np.ndarray image converted to a QImage.
    """
    frameDataReady = Signal(FrameData)

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize the image provider
        """
        ITransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

    def transform(self, frameData: FrameData) -> None:
        """
        Convert the image into a QImage and emit it with the signal.
        """
        if self.active():
            self.frameDataReady.emit(frameData)

        self.next(frameData)

    def __str__(self) -> str:
        return "Frame Data Provider"

class RecorderTransformer(ITransformerStage):
    """
    Records the image.
    """
    recorder: Optional[IVideoRecorder]
    frameRate: int
    width: int
    height: int

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize the image provider
        """
        ITransformerStage.__init__(self, True, previous)

        self.recorder = None
        self.width = 0
        self.height = 0
        self.frameRate = 20

    def setVideoRecorder(self, recorder: IVideoRecorder):
        """
        Set the video recorder with which frames should be recorded.
        """
        self.recorder = recorder

    def transform(self, frameData: FrameData) -> None:
        """
        Record the current frame if the transformer is active and the recorder
        is initialized.
        """
        self.width = frameData.width()
        self.height = frameData.height()
        self.frameRate = frameData.frameRate
        
        if self.active() \
            and self.recorder is not None \
                and not frameData.dryRun \
                    and not frameData.streamEnded \
                        and frameData.image is not None:
            self.recorder.addFrame(frameData.image)

        self.next(frameData)

    def __str__(self) -> str:
        return "Recorder"

class BackgroundRemover(ITransformerStage):
    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)
        self.segmentation = SelfiSegmentation(0)


    def transform(self, frameData: FrameData) -> None:
        """
        Remove the background
        """
        if self.active() and not frameData.dryRun:
           frameData.image = self.segmentation.removeBG(frameData.image.astype(np.uint8))

        self.next(frameData)

    def __str__(self) -> str:
        return "Background Remover"
    

class VideoSourceTransformer(ITransformerStage, QObject):
    """
    Grabs the next frame from the video source and puts it in the pipeline.
    """
    streamEnded = Signal()
    videoSource: Optional[IVideoSource]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

        self.videoSource = None
    
    def setVideoSource(self, videoSource: IVideoSource) -> None:
        """
        Set the source of the video.
        """
        self.videoSource = videoSource

    def transform(self, frameData: FrameData) -> None:
        """
        Add the frame rate property to the frameData object and process the
        next frame.
        """
        if self.videoSource is not None:
            frameData.frameRate = self.videoSource.frameRate()
            frameData.setWidth(self.videoSource.width())
            frameData.setHeight(self.videoSource.height())
            if self.active() and not frameData.dryRun:
                try:
                    frameData.image = self.videoSource.nextFrame()
                except NoMoreFrames:
                    frameData.streamEnded = True
            self.next(frameData)

    def __str__(self) -> str:
        return "Video Source"

class MetricTransformer(ITransformerStage):
    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

    def transform(self, frameData: FrameData) -> None:
        """
        Add the metrics to the frame data object.
        """
        if self.active() and len(frameData.keypointSets) > 0:
            if "metrics" not in frameData:
                metrics = {}
                frameData["metrics"] = metrics
            else:
                metrics = frameData["metrics"]

            keypoints = frameData.keypointSets[0]
            leftShoulder = keypoints.getLeftShoulder()
            rightShoulder = keypoints.getRightShoulder()

            metrics["nose_distance"] = keypoints.getNose()[2]
            metrics["shoulder_distance"] = math.sqrt(
                abs(leftShoulder[1] - rightShoulder[1]) ** 2 \
                    + abs(leftShoulder[0] - rightShoulder[0]) ** 2)

            delta_x = abs(rightShoulder[1] - leftShoulder[1])
            delta_y = abs(rightShoulder[0] - leftShoulder[0])

            if delta_x != 0:
                angle_rad = math.atan(delta_y / delta_x)
                angle_deg = math.degrees(angle_rad)
            else:
                angle_deg = 0

            metrics["shoulder_elevation_angle"] = angle_deg

            metrics["shoulder_height"] = 1 - (keypoints.getLeftShoulder()[0]
                 + keypoints.getRightShoulder()[0]) / 2
            metrics["left_elbow_height"] = 1 - keypoints.getLeftElbow()[0]
            metrics["right_elbow_height"] = 1 - keypoints.getRightElbow()[0]

            metrics["left_hand_elevation"] = 1 - keypoints.getLeftWrist()[0]
            metrics["right_hand_elevation"] = 1 - keypoints.getRightWrist()[0]

            metrics["left_hand_x"] = keypoints.getLeftWrist()[1]
            metrics["right_hand_x"] = keypoints.getRightWrist()[1]
        self.next(frameData)

class SlidingAverageTransformer(ITransformerStage):
    _metrics: dict[str, list[float]]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)
        self.sequenceLength = 10
        self._metrics = defaultdict(lambda: [0.0] * self.sequenceLength)

    def setSequenceLength(self, length: int) -> None:
        """
        Set the sequence length.
        """
        self.sequenceLength = length

    def transform(self, frameData: FrameData) -> None:
        """
        Collect the metrics. Average them and override the metrics value if the
        transformer is active.
        """
        active = self.active()
        metrics = frameData["metrics"]
        
        for key in metrics:
            while len(self._metrics[key]) >= self.sequenceLength:
                self._metrics[key].pop(0)
            self._metrics[key].append(metrics[key])
            if active:
                metrics[key] = sum(self._metrics[key]) / len(self._metrics[key])

        self.next(frameData)


class ButterworthTransformer(ITransformerStage):
    _metrics: dict[str, list[float]]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)
        self.filters = {}

    def transform(self, frameData: FrameData) -> None:
        """
        Apply the Butterworth filter on each signal.
        """
        if self.active():
            metrics = frameData["metrics"]

            sampleRate = 20
            filterFrequency = 5
            nyquistFreq = sampleRate / 2
            Wn = filterFrequency / nyquistFreq

            for metric in metrics.keys():
                if metric not in self.filters:
                    b, a = signal.butter(2, Wn, "lowpass", analog=True, output='ba')
                    self.filters[metric] = (b, a, signal.lfilter_zi(b, a))

                b, a, zi = self.filters[metric]
                val, zi = signal.lfilter(b,
                                         a,
                                         [metrics[metric]],
                                         zi=zi)
                metrics[metric] = val[0]
                self.filters[metric] = (b, a, zi)

        self.next(frameData)

class MinMaxTransformer(ITransformerStage, QObject):
    metrics: Optional[dict[str, list[float]]]
    _min: dict[str, float]
    _max: dict[str, float]
    availableMetricsUpdated = Signal(object)

    def __init__(self) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True)
        QObject.__init__(self)
        self.metrics = None
        self._min = {}
        self._max = {}
        self._availableMetrics = []

    def setMinForMetric(self, metric: str) -> None:
        """
        Set the minimum value for a metric.
        """
        self._min[metric] = self.metrics[metric]

    def setMaxForMetric(self, metric: str) -> None:
        """
        Set the minimum value for a metric.
        """
        self._max[metric] = self.metrics[metric]

    def availableMetrics(self) -> None:
        """
        Get the available metrics.
        """
        return self._availableMetrics

    def transform(self, frameData: FrameData) -> None:
        """
        Inject min and max for each metric.
        """
        if "metrics" in frameData:
            self.metrics = frameData["metrics"].copy()
            newAvailableMetrics = set(self.metrics)
            if len(newAvailableMetrics) != len(self._availableMetrics):
                self._availableMetrics = list(newAvailableMetrics)
                self.availableMetricsUpdated.emit(self._availableMetrics)
            else:
                for metric in self._availableMetrics:
                    if metric not in newAvailableMetrics:
                        self._availableMetrics = list(newAvailableMetrics)
                        self.availableMetricsUpdated.emit(self._availableMetrics)
                        break

        if self.active():
            frameData["metrics_max"] = self._max.copy()
            frameData["metrics_min"] = self._min.copy()

        self.next(frameData)


class DerivativeTransformer(ITransformerStage):
    prev_metrics: dict[str, list[tuple[float, float]]]

    def __init__(self) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True)
        self.prev_metrics = {}

    
    def transform(self, frameData: FrameData) -> None:
        """
        Inject the first two derivatives of each metric.
        """
        if "metrics" in frameData and self.active():
            metrics = frameData["metrics"]
            derivatives = {}
            for key in metrics.keys():
                if key in self.prev_metrics:
                    values = self.prev_metrics[key]
                else:
                    values = [(0, 0), (0, 0), (0, 0)]

                for degree in range(len(values)):
                    if degree == 0:
                        values[0] = (values[0][1], metrics[key])
                        derivatives[key] = [metrics[key]]
                    else:
                        previous = values[degree - 1]
                        delta = previous[1] - previous[0]
                        values[degree] = (values[degree][1], delta)
                        derivatives[key].append(delta)

                self.prev_metrics[key] = values

            frameData["metrics_derivatives"] = derivatives

        self.next(frameData)
