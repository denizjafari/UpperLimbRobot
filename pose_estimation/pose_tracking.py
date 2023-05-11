from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, \
    QCheckBox, QRadioButton, QLabel, QSlider, QPushButton
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaDevices
from PySide6.QtCore import Qt, Signal, Slot, QObject, QThreadPool, QTimer
from PySide6.QtGui import QPixmap, QImage
from pose_estimation.video import CVVideoRecorder, QVideoSource, \
    VideoFrameProcessor, VideoRecorder, VideoSource

from pose_estimation.Models import PoseModel, DisplayOptions


# The frame dimensions and rate for which a suitable format is selected.
TARGET_FRAME_WIDTH = 296
TARGET_FRAME_HEIGHT = 296
TARGET_FRAME_RATE = 25

# The number of frames that should be allowed to processed at each point in time.
# Higher numbers allow for a smoother display, while additional lag is induced.
MAX_FRAMES_IN_PROCESSING = 1


class CameraSelectorButton(QRadioButton):
    """
    A Radio button that allows selection of one camera.
    """
    cameraDevice: QCameraDevice
    selected = Signal(QCamera)

    def __init__(self, device: QCameraDevice) -> None:
        """
        Initialize the selector for a given camera device.
        """
        QRadioButton.__init__(self, device.description())
        self.cameraDevice = device

        self.toggled.connect(self.slotSelected)
        
    @Slot(bool)
    def slotSelected(self, isChecked) -> None:
        """
        Pepare the camera for recording by selecting an appropriate
        format and issue a 'selected' signal.
        """
        if isChecked:
            camera = QCamera(self.cameraDevice)
            formats = self.cameraDevice.videoFormats()
            formats.sort(key=lambda f: f.resolution().height())
            formats.sort(key=lambda f: f.resolution().width())
            formats.sort(key=lambda f: f.maxFrameRate())

            usable_formats = [f for f in formats
                              if f.resolution().width() >= TARGET_FRAME_WIDTH
                              and f.resolution().height() >= TARGET_FRAME_HEIGHT
                              and f.maxFrameRate() >= TARGET_FRAME_RATE]
            if len(usable_formats) == 0:
                print("No suitable video format exists")
            else:
                format = usable_formats[0]
                print(f"Recording in {format.resolution().width()}x{format.resolution().height()}@{format.maxFrameRate()}")
                camera.setCameraFormat(format)

            self.selected.emit(camera)


class CameraSelector(QWidget):
    """
    A group of radio buttons to select a camera from the inputs.
    """
    selected = Signal(QCamera)

    def __init__(self) -> None:
        """
        Intitialize the selector and update the list of cameras.
        """
        QWidget.__init__(self)
        self.updateCameraDevices()


    def updateCameraDevices(self) -> None:
        """
        Update the list of available cameras and add radio buttons.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        cameraDevices = QMediaDevices.videoInputs()
        for camera in cameraDevices:
            button = CameraSelectorButton(camera)
            button.selected.connect(self.selected)
            layout.addWidget(button)


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

    displayOptions: DisplayOptions
    model: PoseModel

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
        self.displayOptions = DisplayOptions()
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

        self.pollNextFrame()

    @Slot()
    def onSkeletonToggled(self) -> None:
        """
        Toggle viewing the landmarks.
        """
        self.displayOptions.showSkeleton = not self.displayOptions.showSkeleton

    @Slot()
    def onMirrorToggled(self) -> None:
        """
        Toggle mirroring the frame.
        """
        self.displayOptions.mirror = not self.displayOptions.mirror

    @Slot(int)
    def onMarkerRadiusChanged(self, v) -> None:
        """
        Update the marker radius for the landmarks.
        """
        self.displayOptions.markerRadius = v

    @Slot(int)
    def onConfidenceChanged(self, v) -> None:
        """
        Update the confidence threshold for landmarks.
        """
        self.displayOptions.confidenceThreshold = v / 100

    def processNextFrame(self) -> None:
        if self.videoSource is None:
            self.pollNextFrame()
        
        nextFrame = self.videoSource.nextFrame()
        if nextFrame is not None:
            processor = VideoFrameProcessor(self.model,
                                            self.displayOptions, 
                                            nextFrame,
                                            self.recorder)
            processor.frameReady.connect(self.onFrameReady)
            self.threadpool.start(processor)
        else:
            self.pollNextFrame()

    def pollNextFrame(self) -> None:
        QTimer.singleShot(30, self.processNextFrame)

    @Slot(QImage)
    def onFrameReady(self, image: Optional[QImage]) -> None:
        """
        Funnel through the image once it is reaady.
        """
        if image is not None:
            self.frameCount += 1
            self.frameReady.emit(image)
        self.processNextFrame()

    @Slot()
    def onFrameRateUpdate(self) -> None:
        self.frameRateUpdate.emit(self.frameCount)
        self.lastFrameRate = self.frameCount
        self.frameCount = 0

    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to use for detection.
        """
        self.model = model

    def isRecording(self) -> bool:
        return self.recorder is not None

    def startRecording(self) -> None:
        if self.isRecording():
            return
        
        self.recorder = CVVideoRecorder(self.lastFrameRate, 640, 640)
        self.recordingToggle.emit()

    def endRecording(self) -> None:
        if not self.isRecording():
            return
        
        self.recorder.close()
        self.recorder = None
        self.recordingToggle.emit()

    def setVideoSource(self, videoSource: VideoSource):
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
        self.frameRate = frameRate
        self.frameRateLabel.setText(f"FPS: {frameRate}")

    
    @Slot()
    def toggleRecording(self) -> None:
        if self.poseTracker is None: return
        
        if self.poseTracker.isRecording():
            self.poseTracker.endRecording()
        else:
            self.poseTracker.startRecording()

    @Slot()
    def onRecordingToggled(self) -> None:
        if self.poseTracker is None: return
        if self.poseTracker.isRecording():
            self.recorderToggleButton.setText("Stop Recording")
        else:
            self.recorderToggleButton.setText("Start Recording")

    def setQVideoSource(self, videoSource: QVideoSource) -> None:
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

        poseTracker.recordingToggle.connect(self.onRecordingToggled)
        poseTracker.recordingToggle.connect(self.onRecordingToggled)
        poseTracker.frameReady.connect(self.setVideoFrame)
        poseTracker.frameRateUpdate.connect(self.updateFrameRate)

        self.poseTracker = poseTracker
