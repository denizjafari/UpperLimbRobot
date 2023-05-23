from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton, QCheckBox, QSlider, QGroupBox
from PySide6.QtCore import Slot, Signal, Qt, QThreadPool, QRunnable, QObject

from pose_estimation.Models import ModelManager
from pose_estimation.video import FrameRateProvider
from pose_estimation.transforms import CsvExporter, ImageMirror, \
    LandmarkDrawer, ModelRunner, RecorderTransformer, Scaler, SkeletonDrawer, \
        Transformer
from pose_estimation.ui_utils import FileSelector, ModelSelector
from pose_estimation.video import CVVideoRecorder, VideoRecorder


class TransformerWidget(QGroupBox):
    """
    The base transformer widget including the title label and remove logic.
    """
    removed = Signal()

    titleLabel: QLabel
    vLayout: QVBoxLayout
    transformer: Transformer

    def __init__(self, title: str="Transformer", parent: Optional[QWidget] = None) -> None:
        """
        Initialize the TransformerWidget.
        """
        QGroupBox.__init__(self, parent)
        self.setTitle(title)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.activeCheckBox = QCheckBox("Active")
        self.activeCheckBox.clicked.connect(self.onActiveToggle)
        self.vLayout.addWidget(self.activeCheckBox)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.removed)
        self.vLayout.addWidget(self.removeButton)


    def onActiveToggle(self) -> None:
        self.transformer.isActive = self.activeCheckBox.isChecked()


class ScalerWidget(TransformerWidget):
    """
    Widget wrapper around the Scaler transformer exposing the target size
    property in the ui.
    """
    transformer: Scaler

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ScalerWidget.
        """
        TransformerWidget.__init__(self, "Scaler", parent)

        self.transformer = Scaler(640, 640)

        self.heightSelector = QLineEdit(self)
        self.heightSelector.setText(str(640))
        self.vLayout.addWidget(self.heightSelector)

        self.applyButton = QPushButton("Apply", self)
        self.applyButton.clicked.connect(self.onApplyClicked)
        self.vLayout.addWidget(self.applyButton)

    @Slot()
    def onApplyClicked(self) -> None:
        """
        Apply the entered target size.
        """
        self.transformer.setTargetSize(int(self.heightSelector.text()))


class ImageMirrorWidget(TransformerWidget):
    """
    Widget wrapper around the ImageMirror transformer exposing the target size
    property in the ui.
    """
    transformer: ImageMirror

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ImageMirrorWidget.
        """
        TransformerWidget.__init__(self, "Mirror", parent)

        self.transformer = ImageMirror()


class ModelRunnerWidget(TransformerWidget):
    """
    """
    transformer: ModelRunner

    def __init__(self, modelManager: ModelManager, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModelRunnerWidget.
        """
        TransformerWidget.__init__(self, "Model", parent)

        self.transformer = ModelRunner()

        self.modelSelector = ModelSelector(modelManager, self)
        self.modelSelector.modelSelected.connect(self.transformer.setModel)
        self.vLayout.addWidget(self.modelSelector)


class LandmarkDrawerWidget(TransformerWidget):
    """
    """
    transformer: LandmarkDrawer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the LandmarkDrawerWidget.
        """
        TransformerWidget.__init__(self, "Landmark Drawer", parent)

        self.transformer = LandmarkDrawer()

        self.markerRadiusSlider = QSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.markerRadiusSlider.setMinimum(1)
        self.markerRadiusSlider.setMaximum(10)
        self.markerRadiusSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.markerRadiusSlider.setTickInterval(1)
        self.markerRadiusSlider.valueChanged.connect(self.transformer.setMarkerRadius)
        self.vLayout.addWidget(self.markerRadiusSlider)


class SkeletonDrawerWidget(TransformerWidget):
    """
    """
    transformer: SkeletonDrawer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the SkeletonDrawerWidget.
        """
        TransformerWidget.__init__(self, "Skeleton Drawer", parent)

        self.transformer = SkeletonDrawer()
        self.lineThicknessSlider = QSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.lineThicknessSlider.setMinimum(1)
        self.lineThicknessSlider.setMaximum(10)
        self.lineThicknessSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lineThicknessSlider.setTickInterval(1)
        self.lineThicknessSlider.valueChanged.connect(self.transformer.setLineThickness)
        self.vLayout.addWidget(self.lineThicknessSlider)


class RecorderLoader(QRunnable, QObject):
    """
    Loads and prepares a recorder in a separate thread.

    recorderLoaded - A signal that is emitted with the fully prepared recorder
    selectedFile - the selected output file
    """
    recorderLoaded = Signal(VideoRecorder)
    frameRate: int
    width: int
    height: int
    selectedFile: str

    def __init__(self, frameRate: int, width: int, height: int, selectedFile: str) -> None:
        """
        Initialize the loader to load the selected file.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.frameRate = frameRate
        self.width = width
        self.height = height
        self.selectedFile = selectedFile

    def run(self) -> None:
        self.recorderLoaded.emit(CVVideoRecorder(self.frameRate,
                                                 self.width,
                                                 self.height,
                                                 self.selectedFile))

class RecorderTransformerWidget(TransformerWidget):
    """
    """
    videoRecorder: VideoRecorder
    csvExporter: Optional[CsvExporter]
    videoRecorder: Optional[VideoRecorder]
    isRecording: bool
    transformer: RecorderTransformer
    frameRate: int

    def __init__(self,
                 frameRateProvider: FrameRateProvider,
                 parent: Optional[QWidget] = None, ) -> None:
        """
        Initialize the RecorderTransformerWidget.
        """
        TransformerWidget.__init__(self, "Recorder", parent)

        frameRateProvider.frameRateUpdated.connect(self.setFrameRate)

        self.transformer = RecorderTransformer()
        self.csvExporter = None
        self.videoRecorder = None
        self.isRecording = False
        self.frameRate = 0

        self.outputFileSelector = FileSelector(self,
                                               mode=FileSelector.MODE_SAVE,
                                               title="Output File")
        self.vLayout.addWidget(self.outputFileSelector)

        self.recordingButton = QPushButton("Start Recording", self)
        self.recordingButton.clicked.connect(self.toggleRecording)
        self.vLayout.addWidget(self.recordingButton)

        self.threadpool = QThreadPool.globalInstance()

    @Slot(int)
    def setFrameRate(self, frameRate: int) -> None:
        self.frameRate = frameRate

    @Slot(VideoRecorder)
    def onRecordingToggled(self, videoRecorder: Optional[VideoRecorder]) -> None:
        self.isRecording = videoRecorder is not None
        if not self.isRecording and self.videoRecorder is not None:
            self.videoRecorder.close()
        self.videoRecorder = videoRecorder
        self.transformer.setVideoRecorder(videoRecorder)
        buttonText = ("Stop" if self.isRecording else "Start") + " Recording"
        self.recordingButton.setText(buttonText)

    @Slot()
    def toggleRecording(self) -> None:
        if self.isRecording:
            self.onRecordingToggled(None)
        else:
            loader = RecorderLoader(self.frameRate,
                                    self.transformer.width,
                                    self.transformer.height,
                                    self.outputFileSelector.selectedFile())
            loader.recorderLoaded.connect(self.onRecordingToggled)
            self.threadpool.start(loader)
