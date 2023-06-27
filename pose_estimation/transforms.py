"""
Transforms for modifying images, landmarks, and metadata in the pipeline via
the frame data object.
"""

from __future__ import annotations
import logging
from typing import Optional
from enum import Enum

import io
import csv
import numpy as np
import tensorflow as tf
import cv2
import math
from cvzone.SelfiSegmentationModule import SelfiSegmentation

from PySide6.QtCore import QObject, Signal, QMutex, QRunnable, QThreadPool
from PySide6.QtGui import QImage

from pose_estimation.metric_widgets import MetricWidget
from models.models import BlazePose, KeypointSet, PoseModel
from pose_estimation.video import NoMoreFrames, VideoRecorder, VideoSource, \
    npArrayToQImage

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class FrameData:
    """
    Contains image, keypoints and metadata to pass between transformers.
    This object is passed between transformers in the pipeline. The state
    of one frame data object should never directly affect the state of
    another frame data object. All persistence or tracking of data should
    occur in the transfomers themselves, or in UI Widgets.

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
    metrics: dict[str, MetricWidget]
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
        self._additional = {}

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

    def __getitem__(self, key: str) -> object:
        """
        Get the value for a key in the additional dictionary.
        """
        return self._additional[key]

    def __setitem__(self, key: str, val: object) -> None:
        """
        Set the value for a key in the additional dictionary.
        """
        self._additional[key] = val

    def __contains__(self, key: str) -> bool:
        """
        Check if a key is in the additional dictionary.
        """
        return key in self._additional

class Transformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images, the landmarks, and/or metadata in the pipeline.
    These transformers can be layered like neural networks, by wrapping
    previous layers in later layers.
    """
    _isActive: bool
    _next: Optional[Transformer]

    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize this transformer by setting whether it is active and
        optionally setting the next transformer in the chain.
        """
        self._isActive = isActive
        self._next = None if previous is None else previous._next

    def active(self) -> bool:
        """
        Return whether this transformer is active or not.
        """
        return self._isActive
    
    def setActive(self, isActive: bool) -> None:
        """
        Set whether this transformer is active or not.
        """
        self._isActive = isActive

    def next(self, frameData: FrameData) -> None:
        """
        Run the next stage in the pipeline. First acquire the lock of the next
        stage before unlockint this stage.
        """
        if self._next is not None:
            self._next.lock()
        self.unlock()
        if self._next is not None:
            self._next.transform(frameData)

    def lock(self) -> None:
        """
        Lock this stage to multithreading.
        """
        raise NotImplementedError

    def unlock(self) -> None:
        """
        Unlock this stage to multithreading.
        """
        raise NotImplementedError

    def transform(self, frameData: FrameData) -> None:
        """
        Transform the input image. This occurs in place.
        """
        self.next(frameData)
    
    def setNextTransformer(self,
                           nextTransformer: Optional[Transformer]) -> None:
        """
        Changes the next transformer in the pipeline.

        nextTransformer - the next transformer, can be None to make the
        pipeline end with this transformer
        """
        self._next = nextTransformer
    
    def getNextTransformer(self) -> None:
        """
        Get the transformer that comes after this one in the pipeline.
        """
        return self._next

class TransformerStage(Transformer):
    """
    One stage in a pipeline that can only be entered by one thread at a time.
    """
    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initilialize the stage.
        """
        Transformer.__init__(self, isActive, previous)

        self._mutex = QMutex()

    def lock(self) -> None:
        """
        Lock the stage. Now, no other thread can enter this stage.
        """
        self._mutex.lock()

    def unlock(self) -> None:
        """
        Unlock the stage. Allow other threads to enter this stage.
        """
        self._mutex.unlock()
    
class Pipeline(Transformer):
    """
    A pipeline of transformer stages. It can act as a transformer by itself,
    but multiple threads can be in it at the same time. Only the stages the
    pipeline is made of are locked to only one thread.
    """
    transformers: list[Transformer]

    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[Transformer] = None) -> None:
        Transformer.__init__(self, isActive, previous)
        self.transformers = []

    def append(self, transformer: Transformer) -> None:
        """
        Append a Transformer to the end of the pipeline.
        """
        module_logger.debug(f"Appended transformer {transformer} to the pipeline")
        if len(self.transformers) > 0:
            self.transformers[-1].setNextTransformer(transformer)
        self.transformers.append(transformer)
        transformer.setNextTransformer(self._next)

    def remove(self, transformer: Transformer) -> None:
        """
        Remove the given transformer from the pipeline.
        """
        module_logger.debug(f"Removed transformer {transformer} from the pipeline")
        index = self.transformers.index(transformer)
        if index > 0:
            self.transformers[index - 1].setNextTransformer(transformer.getNextTransformer())
        transformer.setNextTransformer(None)
        self.transformers.pop(index)

    def setNextTransformer(self, nextTransformer: Transformer | None) -> None:
        """
        Set the transformer that should be run after the pipeline is completed.
        """
        if len(self.transformers) > 0:
            self.transformers[-1].setNextTransformer(nextTransformer)
        super().setNextTransformer(nextTransformer)

    def getNextTransformer(self) -> None:
        """
        Get the transformer that is run after the pipeline is completed.
        """
        return self.transformers[-1].getNextTransformer() \
            if len(self.transformers) > 0 else None

    def start(self, frameData: FrameData) -> None:
        """
        Stat the pipeline by locking the first stage and beginning
        transformation.
        """
        self.lock()
        self.transform(frameData)

    def lock(self) -> None:
        """
        Lock the first stage in the pipeline.
        """
        if len(self.transformers) > 0:
            self.transformers[0].lock()

    def unlock(self) -> None:
        """
        Do nothing. Unlocking the first stage is done by the first stage itself
        upon completion of its transformation.
        """
        pass

    def next(self, frameData: FrameData) -> None:
        """
        Do nothing. Running the first stage after this pipeline is coordinated
        by the last stage in this pipeline.
        """
        pass
    
    def transform(self, frameData: FrameData) -> None:
        """
        Start transformation with the frst transformer in the pipeline.
        """
        if self.active() and len(self.transformers) > 0:
            self.transformers[0].transform(frameData)
    
class ImageMirror(TransformerStage):
    """
    A transformer which mirrors the image along the y-axis. Useful when dealing
    with front cameras.
    """
    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)
    
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

class LandmarkDrawer(TransformerStage):
    """
    Draws the landmarks to the image.

    markerRadius - the radius of the markers
    """
    markerRadius: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

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
                    x = round(keypoint[0] * frameData.width())
                    y = round(keypoint[1] * frameData.height())
                    cv2.circle(frameData.image,
                               (y, x),
                               self.markerRadius,
                               color=self.color,
                               thickness=-1)

        self.next(frameData)

    def __str__(self) -> str:
        return "Landmarks"
    
class SkeletonDrawer(TransformerStage):
    """
    Draw the skeleton detected by some model.
    """
    lineThickness: int
    color: tuple[int, int, int]

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the Drawer.
        """
        TransformerStage.__init__(self, True, previous)

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
    
class Scaler(TransformerStage):
    """
    Scales the image up.
    """
    targetWidth: int
    targetHeight: int

    def __init__(self,
                 width: int,
                 height: int,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

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
    

class ModelRunner(TransformerStage):
    """
    Runs a model on the image and adds the keypoints to the list.
    """
    model: Optional[PoseModel]

    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

        self.model = None

    def setModel(self, model: PoseModel) -> None:
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
    
class CsvImporter(TransformerStage):
    """
    Imports the keypoints frame by frame from a separate file. Currently only
    supports BlazePose-type model keypoints.
    """
    csvReader: Optional[csv._reader]
    keypointCount: int

    def __init__(self,
                 keypointCount: int,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

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
    
    
class CsvExporter(TransformerStage):
    """
    Exports the keypoints frame by frame to a separate file.
    """
    index: int
    csvWriter: Optional[csv._writer]

    def __init__(self,
                 index: int,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

        self.csvWriter = None
        self.index = index

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.csvWriter = csv.writer(file) if file is not None else None

    def transform(self, frameData: FrameData) -> None:
        """
        Export the first set of keypoints from the list of keypoint sets. This
        set is subsequently popped from the list.
        """
        if self.active() \
            and self.csvWriter is not None \
                and not frameData.dryRun:
            for k in frameData.keypointSets[self.index].getKeypoints():
                self.csvWriter.writerow(k)
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Exporter"
    
class QImageProvider(TransformerStage, QObject):
    """
    Emits a signal with the np.ndarray image converted to a QImage.
    """
    frameReady = Signal(QImage)

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        TransformerStage.__init__(self, True, previous)
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

class FrameDataProvider(TransformerStage, QObject):
    """
    Emits a signal with the np.ndarray image converted to a QImage.
    """
    frameDataReady = Signal(FrameData)

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        TransformerStage.__init__(self, True, previous)
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

class RecorderTransformer(TransformerStage):
    """
    Records the image.
    """
    recorder: Optional[VideoRecorder]
    frameRate: int
    width: int
    height: int

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the image provider
        """
        TransformerStage.__init__(self, True, previous)

        self.recorder = None
        self.width = 0
        self.height = 0

    def setVideoRecorder(self, recorder: VideoRecorder):
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

class BackgroundRemover(TransformerStage):
    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)
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
    

class VideoSourceTransformer(TransformerStage, QObject):
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
        TransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

        self.videoSource = None
    
    def setVideoSource(self, videoSource: VideoSource) -> None:
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

class TransformerRunner(QRunnable, QObject):
    """
    Runs the transformer and emits a signal when the next thread can start
    execution.
    """
    transformerStarted = Signal(FrameData)
    transformerCompleted = Signal(FrameData)
    _transformer: Transformer

    def __init__(self, transformer: Transformer, frameData: Optional[FrameData] = None) -> None:
        """
        Initialize the Runner with the transformer it should execute.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)
        if frameData is None:
            frameData = FrameData()
        self._transformer = transformer
        self.frameData = frameData

    def run(self) -> None:
        """
        Acquire the lock of the transformer. As soon as the lock could be acquired,
        the stage cleared signal is emitted and the first transformer stage starts
        executing.
        """
        self._transformer.lock()
        self.transformerStarted.emit(self.frameData)
        self._transformer.transform(self.frameData)
        self.transformerCompleted.emit(self.frameData)

class TransformerHead:
    """
    The Transformer head managing the creation of new runners for the
    transformer.
    """
    _isRunning: bool
    _transformer: Transformer
    _threadingModel: MultiThreading

    class MultiThreading(Enum):
        """
        How the transformers use multiple threads.
        PER_FRAME - one thread processes the frame from beginning to end
        before another thread is spawned.
        PER_STAGE - one thread is spawned every time there is an empty stage.
        """
        PER_FRAME = 0
        PER_STAGE = 1


    def __init__(self,
                 transformer: Transformer,
                 threadingModel: MultiThreading = MultiThreading.PER_FRAME,
                 qThreadPool: QThreadPool = QThreadPool.globalInstance()) -> None:
        """
        Initialize the TransformerHead.
        """
        self._transformer = transformer
        self._isRunning = False
        self._qThreadPool = qThreadPool
        self._threadingModel = threadingModel

    def start(self) -> None:
        """
        Start execution of the transformer
        """
        self._isRunning = True
        self.startNext()
    
    def stop(self) -> None:
        """
        Stop execution of the transformer. This stops the creation of new
        runners. Existing runners will continue to run until completion, however.
        """
        self._isRunning = False

    def isRunning(self) -> bool:
        """
        Return whether this transformer head is running or in a pause.
        """
        return self._isRunning
    
    def threadingModel(self) -> MultiThreading:
        """
        Return the threading model that is used.
        """
        return self._threadingModel
    
    def setThreadingModel(self, threadingModel: MultiThreading) -> MultiThreading:
        """
        Set the threshold model
        """
        self._threadingModel = threadingModel

    def onStageCleared(self) -> None:
        """
        Called when the first stage in the transformer is cleared.
        The next transformer will be run if the threading model is per stage
        and the execution has not been stopped.
        """
        if self._isRunning \
            and self.threadingModel() \
                == TransformerHead.MultiThreading.PER_STAGE:
            self.startNext()

    def onTransformCompleted(self) -> None:
        """
        Called when the transformer is completed.
        The next transformer will be run if the threading model is per frame
        and the execution has not been stopped.
        """
        if self._isRunning \
            and self.threadingModel() \
                == TransformerHead.MultiThreading.PER_FRAME:
            self.startNext()

    def startNext(self) -> None:
        """
        Start the next TransformerRunner and connect to its signals.
        """
        runner = TransformerRunner(self._transformer)
        runner.transformerStarted.connect(self.onStageCleared)
        runner.transformerCompleted.connect(self.onTransformCompleted)
        self._qThreadPool.start(runner)

class MetricTransformer(TransformerStage):
    def __init__(self,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

    def transform(self, frameData: FrameData) -> None:
        """
        Add the metrics to the frame data object.
        """
        if self.active():
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
                abs(leftShoulder[1] - rightShoulder[1]) ** 2
                    + abs(leftShoulder[0]) - abs(rightShoulder[0]) ** 2)

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

        self.next(frameData)
