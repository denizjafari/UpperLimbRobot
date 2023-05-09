from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, \
    QCheckBox, QRadioButton, QLabel, QSlider
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaDevices, \
    QMediaCaptureSession, QVideoSink, QVideoFrame
from PySide6.QtCore import Qt, Signal, Slot, QRunnable, QObject, QThreadPool
from PySide6.QtGui import QPixmap, QImage

import numpy as np

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


class VideoFrameProcessor(QRunnable, QObject):
    """
    One task that processes one video frame and signals the completion
    of that frame.

    frameReady - the signal that is emitted with the processed image.
    model - the model to use to detect the pose.
    displayOptions - the display options to use.
    videoFrame - the video frame from the video sink.
    """
    frameReady = Signal(QImage)
    model: PoseModel
    displayOptions: DisplayOptions
    videoFrame: QVideoFrame

    def __init__(self,
                 model: PoseModel,
                 displayOptions: DisplayOptions,
                 videoFrame: QVideoFrame) -> None:
        """
        Initialize the runner.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.displayOptions = displayOptions
        self.videoFrame = videoFrame
        self.model = model

    def qImageToNpArray(self, image: QImage) -> np.ndarray:
        """
        Convert a QImage to an ndarray with dimensions (height, width, channels)
        """
        image = image.convertToFormat(QImage.Format.Format_RGB32)
        image = np.array(image.bits()).reshape(image.height(), image.width(), 4)
        image = np.delete(image, np.s_[-1:], axis=2)

        return image
    
    def npArrayToQImage(self, image: np.ndarray) -> QImage:
        """
        Convert an ndarray with dimensions (height, width, channels) back
        into a QImage.
        """
        buffer = image.astype(np.uint8).tobytes()
        image = QImage(buffer, image.shape[1], image.shape[0], QImage.Format.Format_RGB32)

        return image

    @Slot()
    def run(self) -> None:
        """
        Convert the video frame to an image, analyze it and emit a signal with
        the processed image.
        """
        image = self.videoFrame.toImage()

        if self.displayOptions.mirror:
            image = image.mirrored(horizontally=True, vertically=False)
        
        result = self.model.detect(self.qImageToNpArray(image))
        image = result.toImage(displayOptions=self.displayOptions)

        self.frameReady.emit(self.npArrayToQImage(image))


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

    displayOptions: DisplayOptions
    model: PoseModel

    camera: Optional[QCamera]
    cameraSession: QMediaCaptureSession
    videoSink: QVideoSink
    framesInProcessing: int


    def __init__(self) -> None:
        """
        Initialize the pose tracker.
        """
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
        """
        Process a video frame if there are less than the maximum number of
        frames in processing. Otherwise, drop it.
        """
        if self.framesInProcessing >= MAX_FRAMES_IN_PROCESSING: return
        self.framesInProcessing += 1
        processor = VideoFrameProcessor(self.model, self.displayOptions, videoFrame)
        processor.frameReady.connect(self.onFrameReady)
        self.threadpool.start(processor)

    @Slot(QCamera)
    def setCamera(self, camera: QCamera) -> None:
        """
        Change the camera to the given camera
        """
        camera.start()
        self.cameraSession.setCamera(camera)
        if self.camera is not None: self.camera.stop()
        self.camera = camera

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

    @Slot(QImage)
    def onFrameReady(self, image: QImage) -> None:
        """
        Funnel through the image once it is reaady.
        """
        self.framesInProcessing -= 1
        self.frameReady.emit(image)

    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to use for detection.
        """
        self.model = model


class PoseTrackerWidget(QWidget):
    """
    The frontend widget to change pose tracker settings and preview the result.

    poseTracker - the pose tracker from which to get the input.
    skeletonButton - check box to determine whether to show the skeleton.
    mirrorButton - check box to determine whether to mirror the picture.
    displayLabel - the label on which to draw the frames.
    cameraSelector - the camera selector.
    """
    poseTracker: PoseTracker
    skeletonButton: QCheckBox
    mirrorButton: QCheckBox
    displayLabel: QLabel    
    cameraSelector: CameraSelector

    def __init__(self) -> None:
        """
        Initialize the pose tracking settings and preview.
        """
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
    def setVideoFrame(self, image: QImage) -> None:
        """
        Show a given image.
        """
        pixmap = QPixmap.fromImage(image)
        self.displayLabel.setPixmap(pixmap)

    def setPoseTracker(self, poseTracker: PoseTracker) -> None:
        """
        Set the pose tracker by connectin all slots and signals between the
        pose tracker and this widget.
        """
        self.cameraSelector.selected.connect(poseTracker.setCamera)
        self.skeletonButton.toggled.connect(poseTracker.onSkeletonToggled)
        self.mirrorButton.toggled.connect(poseTracker.onMirrorToggled)
        self.markerRadiusSlider.valueChanged.connect(poseTracker.onMarkerRadiusChanged)
        self.confidenceSlider.valueChanged.connect(poseTracker.onConfidenceChanged)
        poseTracker.frameReady.connect(self.setVideoFrame)
