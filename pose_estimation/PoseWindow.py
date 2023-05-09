from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, \
    QCheckBox, QRadioButton, QLabel, QSlider
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaDevices, \
    QMediaCaptureSession, QVideoSink, QVideoFrame
from PySide6.QtCore import Qt, Signal, Slot, QRunnable, QObject, QThreadPool
from PySide6.QtGui import QPixmap, QImage

from pose_estimation.Models import PoseModel, DisplayOptions


TARGET_FRAME_WIDTH = 296
TARGET_FRAME_HEIGHT = 296
TARGET_FRAME_RATE = 25

# The number of frames that should be allowed to processed at each point in time.
# Higher numbers allow for a smoother display, while additional lag is induced.
MAX_FRAMES_IN_PROCESSING = 5


class CameraSelectorButton(QRadioButton):
    cameraDevice: QCameraDevice
    selected = Signal(QCamera)

    def __init__(self, device: QCameraDevice) -> None:
        QRadioButton.__init__(self, device.description())
        self.cameraDevice = device

        self.toggled.connect(self.slotSelected)
        
    @Slot(bool)
    def slotSelected(self, isChecked) -> None:
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
    selected = Signal(QCamera)

    def __init__(self) -> None:
        QWidget.__init__(self)
        self.updateCameraDevices()


    def updateCameraDevices(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        cameraDevices = QMediaDevices.videoInputs()
        for camera in cameraDevices:
            button = CameraSelectorButton(camera)
            button.selected.connect(self.selected)
            layout.addWidget(button)


class VideoFrameProcessor(QRunnable, QObject):
    frameReady = Signal(QImage)
    poseEstimator: PoseModel
    displayOptions: DisplayOptions
    videoFrame: QVideoFrame

    def __init__(self,
                 model: PoseModel,
                 displayOptions: DisplayOptions,
                 videoFrame: QVideoFrame) -> None:
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.displayOptions = displayOptions
        self.videoFrame = videoFrame
        self.movenet = model

    @Slot()
    def run(self) -> None:
        image = self.videoFrame.toImage()

        if self.displayOptions.mirror:
            image = image.mirrored(horizontally=True, vertically=False)
        image = image.convertToFormat(QImage.Format.Format_RGB32)
        
        result = self.movenet.detect(image)
        image = result.toImage(displayOptions=self.displayOptions)
        self.frameReady.emit(image)


class PoseTracker(QObject):
    displayOptions: DisplayOptions
    model: PoseModel

    videoSink: QVideoSink
    framesInProcessing: int
    camera: Optional[QCamera]
    cameraSession: QMediaCaptureSession

    frameReady = Signal(QImage)

    def __init__(self) -> None:
        QObject.__init__(self)
        self.displayOptions = DisplayOptions()
        self.threadpool = QThreadPool()
        self.framesInProcessing = 0

        self.cameraSession = QMediaCaptureSession()
        self.videoSink = QVideoSink()
        self.videoSink.videoFrameChanged.connect(self.processVideoFrame)
        self.cameraSession.setVideoSink(self.videoSink)
        self.camera = None


    @Slot(QVideoFrame)
    def processVideoFrame(self, videoFrame: QVideoFrame) -> None:
        if self.framesInProcessing >= MAX_FRAMES_IN_PROCESSING: return
        self.framesInProcessing += 1
        processor = VideoFrameProcessor(self.model, self.displayOptions, videoFrame)
        processor.frameReady.connect(self.onFrameReady)
        self.threadpool.start(processor)

    @Slot(QCamera)
    def changeCamera(self, camera: QCamera) -> None:
        camera.start()
        self.cameraSession.setCamera(camera)
        if self.camera is not None: self.camera.stop()
        self.camera = camera

    @Slot()
    def onSkeletonToggled(self) -> None:
        self.displayOptions.showSkeleton = not self.displayOptions.showSkeleton

    @Slot()
    def onMirrorToggled(self) -> None:
        self.displayOptions.mirror = not self.displayOptions.mirror

    @Slot(int)
    def onMarkerRadiusChanged(self, v) -> None:
        self.displayOptions.markerRadius = v

    @Slot(int)
    def onConfidenceChanged(self, v) -> None:
        self.displayOptions.confidenceThreshold = v / 100

    @Slot(QImage)
    def onFrameReady(self, image: QImage) -> None:
        self.framesInProcessing -= 1
        self.frameReady.emit(image)

    def setModel(self, model: PoseModel) -> None:
        self.model = model


class PoseEstimationWindow(QWidget):
    poseTracker: PoseTracker
    skeletonButton: QCheckBox
    mirrorButton: QCheckBox
    displayLabel: QLabel    
    cameraSelector: CameraSelector

    def __init__(self) -> None:
        QWidget.__init__(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.displayLabel = QLabel()
        layout.addWidget(self.displayLabel, alignment=Qt.AlignmentFlag.AlignCenter)

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

    @Slot(QImage)
    def showVideoFrame(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        self.displayLabel.setPixmap(pixmap)

    def setPoseTracker(self, poseTracker: PoseTracker) -> None:
        self.cameraSelector.selected.connect(poseTracker.changeCamera)
        self.skeletonButton.toggled.connect(poseTracker.onSkeletonToggled)
        self.mirrorButton.toggled.connect(poseTracker.onMirrorToggled)
        self.markerRadiusSlider.valueChanged.connect(poseTracker.onMarkerRadiusChanged)
        self.confidenceSlider.valueChanged.connect(poseTracker.onConfidenceChanged)
        poseTracker.frameReady.connect(self.showVideoFrame)
