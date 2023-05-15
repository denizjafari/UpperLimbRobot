from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, \
    QCheckBox, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal, Slot, QObject, QThreadPool, QTimer
from PySide6.QtGui import QPixmap, QImage
from pose_estimation.transforms import LandmarkConfidenceFilter, LandmarkDrawer, ImageMirror, Scaler
from pose_estimation.ui_utils import CameraSelector, ModelSelector
from pose_estimation.video import CVVideoRecorder, QVideoSource, \
    VideoFrameProcessor, VideoRecorder, VideoSource, npArrayToQImage

from pose_estimation.Models import FeedThroughModel, PoseModel


class PoseTracker(QObject):
    """
    The Tracker that sets up the camera and analyzes frames as they come.

    frameReady - a signal that is issued when a resulting image is ready.

    displayOptions - the frame processing options.
    model - the model to use for detection.

    camera - the camera that is capturing the frames.
    cameraSession - the camera session that feeds camera input into the
                    video sink.
    videoSink - the video sink that provides the frames.
    framesInProcessing - the number of frames that are currently processed.
    """
    frameReady = Signal(QImage)
    frameRateUpdate = Signal(int)
    recordingToggle = Signal()

    model: PoseModel

    scaleTransformer: Scaler
    keypointFilter: LandmarkConfidenceFilter
    keypointTransformer: LandmarkDrawer
    mirrorTransformer: ImageMirror

    recorder: Optional[VideoRecorder]
    videoSource: Optional[VideoSource]

    frameRateTimer: QTimer
    frameCount: int
    lastFrameRate: int


    def __init__(self) -> None:
        """
        Initialize the pose tracker.
        """
        QObject.__init__(self)
        self.scaleTransformer = Scaler(640, 640)
        self.mirrorTransformer = ImageMirror(self.scaleTransformer)
        self.keypointFilter = LandmarkConfidenceFilter(self.mirrorTransformer)
        self.keypointTransformer = LandmarkDrawer(self.keypointFilter)

        self.threadpool = QThreadPool()
        self.framesInProcessing = 0

        self.frameRateTimer = QTimer()
        self.frameRateTimer.setInterval(1000)
        self.frameRateTimer.timeout.connect(self.onFrameRateUpdate)
        self.frameRateTimer.start()

        self.frameCount = 0
        self.lastFrameRate = 0
        self.recorder = None
        self.videoSource = None

        self.model = FeedThroughModel()

        self.pollNextFrame()

    @Slot()
    def onSkeletonToggled(self) -> None:
        """
        Toggle viewing the landmarks.
        """
        self.keypointTransformer.isActive = not self.keypointTransformer.isActive

    @Slot()
    def onMirrorToggled(self) -> None:
        """
        Toggle mirroring the frame.
        """
        self.mirrorTransformer.isActive = not self.mirrorTransformer.isActive

    @Slot(int)
    def onMarkerRadiusChanged(self, v) -> None:
        """
        Update the marker radius for the landmarks.
        """
        self.keypointTransformer.markerRadius = v

    @Slot(int)
    def onConfidenceChanged(self, v) -> None:
        """
        Update the confidence threshold for landmarks.
        """
        self.keypointFilter.confidenceThreshold = v / 100

    def processNextFrame(self) -> None:
        """
        Process the next available frame.
        """
        if self.videoSource is None:
            self.pollNextFrame()
        
        nextFrame = self.videoSource.nextFrame()
        if nextFrame is not None:
            processor = VideoFrameProcessor(self.model,
                                            self.scaleTransformer, 
                                            nextFrame)
            processor.frameReady.connect(lambda image, _:
                                         self.onFrameReady(npArrayToQImage(image)))
            processor.frameReady.connect(lambda image, _:
                                         self.recorder.addFrame(image)
                                         if self.recorder is not None else None)

            self.threadpool.start(processor)
        else:
            self.pollNextFrame()

    def pollNextFrame(self) -> None:
        """
        Wait 30ms and try again to see whether the next frame is available.
        TODO: Switch back from ugly polling to proper signal handling.
        """
        QTimer.singleShot(30, self.processNextFrame)

    @Slot(QImage)
    def onFrameReady(self, image: QImage) -> None:
        """
        Funnel through the image once it is reaady.
        """
        if image is not None:
            self.frameCount += 1
            self.frameReady.emit(image)
        self.processNextFrame()

    @Slot()
    def onFrameRateUpdate(self) -> None:
        """
        Signal the new frame rate after a frame rate determination frame (1s)
        has passed.
        """
        self.frameRateUpdate.emit(self.frameCount)
        self.lastFrameRate = self.frameCount
        self.frameCount = 0

    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to use for detection.
        """
        self.model = model

    def isRecording(self) -> bool:
        """
        Check whether a recording is in process.
        """
        return self.recorder is not None

    def startRecording(self) -> None:
        """
        Start a recording. If there is already a recording in process,
        do nothing.
        """
        if self.isRecording():
            return
        
        self.recorder = CVVideoRecorder(self.lastFrameRate, 640, 640)
        self.recordingToggle.emit()

    def endRecording(self) -> None:
        """
        End a recording. If there is no recording in process, do nothing.
        """
        if not self.isRecording():
            return
        
        self.recorder.close()
        self.recorder = None
        self.recordingToggle.emit()

    def setVideoSource(self, videoSource: VideoSource):
        """
        Set the source of the video stream.
        """
        self.videoSource = videoSource


class PoseTrackerWidget(QWidget):
    """
    The frontend widget to change pose tracker settings and preview the result.

    poseTracker - the pose tracker from which to get the input.
    skeletonButton - check box to determine whether to show the skeleton.
    mirrorButton - check box to determine whether to mirror the picture.
    displayLabel - the label on which to draw the frames.
    cameraSelector - the camera selector.
    """
    poseTracker: Optional[PoseTracker]
    skeletonButton: QCheckBox
    mirrorButton: QCheckBox
    displayLabel: QLabel    
    cameraSelector: CameraSelector
    frameRate: int

    def __init__(self) -> None:
        """
        Initialize the pose tracking settings and preview.
        """
        QWidget.__init__(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.displayLabel = QLabel()
        layout.addWidget(self.displayLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.frameRateLabel = QLabel()
        layout.addWidget(self.frameRateLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.cameraSelector = CameraSelector()
        layout.addWidget(self.cameraSelector, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.modelSelector = ModelSelector()
        layout.addWidget(self.modelSelector, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.skeletonButton = QCheckBox("Show Skeleton")
        layout.addWidget(self.skeletonButton, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.mirrorButton = QCheckBox("Mirror Image")
        layout.addWidget(self.mirrorButton, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.markerRadiusSlider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.markerRadiusSlider.setMinimum(1)
        self.markerRadiusSlider.setMaximum(10)
        self.markerRadiusSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.markerRadiusSlider.setTickInterval(1)
        layout.addWidget(self.markerRadiusSlider, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.confidenceSlider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.confidenceSlider.setMinimum(1)
        self.confidenceSlider.setMaximum(100)
        self.confidenceSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.confidenceSlider.setTickInterval(5)
        layout.addWidget(self.confidenceSlider, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.recorder = None
        self.recorderToggleButton = QPushButton("Start Recording")
        self.recorderToggleButton.clicked.connect(self.toggleRecording)
        layout.addWidget(self.recorderToggleButton, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.poseTracker = None


    @Slot(QImage)
    def setVideoFrame(self, image: QImage) -> None:
        """
        Show a given image.
        """
        pixmap = QPixmap.fromImage(image)
        self.displayLabel.setPixmap(pixmap)

    @Slot(int)
    def updateFrameRate(self, frameRate: int):
        """
        Updat the frame rate that is displayed in the UI.
        """
        self.frameRate = frameRate
        self.frameRateLabel.setText(f"FPS: {frameRate}")

    
    @Slot()
    def toggleRecording(self) -> None:
        """
        Start or stop the recording.
        """
        if self.poseTracker is None: return
        
        if self.poseTracker.isRecording():
            self.poseTracker.endRecording()
        else:
            self.poseTracker.startRecording()

    @Slot()
    def onRecordingToggled(self) -> None:
        """
        Update the UI after the recording has been toggled from start to stop
        or vice versa.
        """
        if self.poseTracker is None: return
        if self.poseTracker.isRecording():
            self.recorderToggleButton.setText("Stop Recording")
        else:
            self.recorderToggleButton.setText("Start Recording")

    def setQVideoSource(self, videoSource: QVideoSource) -> None:
        """
        Set the Qt video source if there is one, since this window
        has controls to select the camera.
        """
        self.cameraSelector.selected.connect(videoSource.setCamera)

    def setPoseTracker(self, poseTracker: PoseTracker) -> None:
        """
        Set the pose tracker by connectin all slots and signals between the
        pose tracker and this widget.
        """
        self.skeletonButton.toggled.connect(poseTracker.onSkeletonToggled)
        self.mirrorButton.toggled.connect(poseTracker.onMirrorToggled)
        self.markerRadiusSlider.valueChanged.connect(poseTracker.onMarkerRadiusChanged)
        self.confidenceSlider.valueChanged.connect(poseTracker.onConfidenceChanged)
        self.modelSelector.modelSelected.connect(poseTracker.setModel)

        poseTracker.recordingToggle.connect(self.onRecordingToggled)
        poseTracker.recordingToggle.connect(self.onRecordingToggled)
        poseTracker.frameReady.connect(self.setVideoFrame)
        poseTracker.frameRateUpdate.connect(self.updateFrameRate)

        self.poseTracker = poseTracker
