from typing import Optional

from io import TextIOBase

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton, QCheckBox, QSlider, QGroupBox, QHBoxLayout, QColorDialog
from PySide6.QtCore import Slot, Signal, Qt, QThreadPool, QRunnable, QObject

from pose_estimation.Models import ModelManager
from pose_estimation.video import CVVideoFileSource, QVideoSource
from pose_estimation.transforms import BackgroundRemover, CsvExporter, ImageMirror, \
    LandmarkDrawer, ModelRunner, PoseFeedbackTransformer, RecorderTransformer, \
        Scaler, SkeletonDrawer, Transformer, VideoSourceTransformer
from pose_estimation.ui_utils import CameraSelector, FileSelector, \
    LabeledQSlider, ModelSelector
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

        self.headLayout = QHBoxLayout()
        self.vLayout.addLayout(self.headLayout)

        self.activeCheckBox = QCheckBox("Active")
        self.activeCheckBox.setChecked(True)
        self.activeCheckBox.clicked.connect(self.onActiveToggle)
        self.headLayout.addWidget(self.activeCheckBox)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.removed)
        self.headLayout.addWidget(self.removeButton)


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

        self.sliderLabel = QLabel("Marker Radius", self)
        self.vLayout.addWidget(self.sliderLabel)

        self.colorDialog = QColorDialog(self, self.transformer.getRGBColor())
        self.colorDialog.currentColorChanged.connect(
            lambda qColor: self.transformer.setRGBColor((qColor.red(),
                                                        qColor.green(),
                                                        qColor.blue())))

        self.markerRadiusSlider = LabeledQSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.markerRadiusSlider.setMinimum(1)
        self.markerRadiusSlider.setMaximum(10)
        self.markerRadiusSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.markerRadiusSlider.setTickInterval(1)
        self.markerRadiusSlider.valueChanged.connect(self.transformer.setMarkerRadius)
        self.vLayout.addWidget(self.markerRadiusSlider)

        self.chooseColorButton = QPushButton("Change color...", self)
        self.chooseColorButton.clicked.connect(self.colorDialog.open)
        self.vLayout.addWidget(self.chooseColorButton)


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

        self.sliderLabel = QLabel("Line Thickness", self)
        self.vLayout.addWidget(self.sliderLabel)

        self.colorDialog = QColorDialog(self, self.transformer.getRGBColor())
        self.colorDialog.currentColorChanged.connect(
            lambda qColor: self.transformer.setRGBColor((qColor.red(),
                                                        qColor.green(),
                                                        qColor.blue())))

        self.lineThicknessSlider = LabeledQSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.lineThicknessSlider.setMinimum(1)
        self.lineThicknessSlider.setMaximum(10)
        self.lineThicknessSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lineThicknessSlider.setTickInterval(1)
        self.lineThicknessSlider.valueChanged.connect(self.transformer.setLineThickness)
        self.vLayout.addWidget(self.lineThicknessSlider)

        self.chooseColorButton = QPushButton("Change color...", self)
        self.chooseColorButton.clicked.connect(self.colorDialog.open)
        self.vLayout.addWidget(self.chooseColorButton)


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
    Widget for the recorder and csv exporter widgets
    TODO: Fix mess with csv exporters when not recordin / inactive
    """
    videoRecorder: VideoRecorder
    csvExporter: Optional[CsvExporter]
    selectors: list[FileSelector]
    outputFiles: list[TextIOBase]
    videoRecorder: Optional[VideoRecorder]
    isRecording: bool
    transformer: RecorderTransformer

    def __init__(self,
                 parent: Optional[QWidget] = None, ) -> None:
        """
        Initialize the RecorderTransformerWidget.
        """
        TransformerWidget.__init__(self, "Recorder", parent)

        self.transformer = RecorderTransformer()
        self.selectors = []
        self.outputFiles = []
        self.videoRecorder = None
        self.isRecording = False

        self.outputFileSelector = FileSelector(self,
                                               mode=FileSelector.MODE_SAVE,
                                               title="Output File")
        self.vLayout.addWidget(self.outputFileSelector)

        self.csvExporterLayout = QVBoxLayout()
        self.vLayout.addLayout(self.csvExporterLayout)

        self.hButtonLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hButtonLayout)

        self.addExporterButton = QPushButton("Add CSV Exporter")
        self.addExporterButton.clicked.connect(self.addExporter)
        self.hButtonLayout.addWidget(self.addExporterButton)

        self.recordingButton = QPushButton("Start Recording", self)
        self.recordingButton.clicked.connect(self.toggleRecording)
        self.hButtonLayout.addWidget(self.recordingButton)

        self.threadpool = QThreadPool.globalInstance()

    @Slot()
    def addExporter(self) -> None:
        """
        Add a csv exporter to the widget and pipeline.
        """
        selector = FileSelector(self, title="CSV output",removable=True)
        self.selectors.append(selector)

        def remove() -> None:
            self.selectors.remove(selector)
            self.csvExporterLayout.removeWidget(selector)
            selector.deleteLater()

        selector.removeButton.clicked.connect(remove)
        self.csvExporterLayout.addWidget(selector)

    @Slot(VideoRecorder)
    def onRecordingToggled(self, videoRecorder: Optional[VideoRecorder]) -> None:
        """
        A slot to be called when the recording has been toggled. Prepare the
        recorder transformer and update the user interface.
        """
        self.isRecording = videoRecorder is not None
        if not self.isRecording and self.videoRecorder is not None:
            self.videoRecorder.close()

        self.videoRecorder = videoRecorder
        self.transformer.setVideoRecorder(videoRecorder)
        buttonText = ("Stop" if self.isRecording else "Start") + " Recording"
        self.recordingButton.setText(buttonText)

    @Slot()
    def toggleRecording(self) -> None:
        """
        Toggle the recording between start and stop.
        """
        if self.isRecording:
            for file in self.outputFiles:
                file.close()
            self.files = []
            self.onRecordingToggled(None)
        else:
            loader = RecorderLoader(self.transformer.frameRate,
                                    self.transformer.width,
                                    self.transformer.height,
                                    self.outputFileSelector.selectedFile())
            
            previousExporter = self.transformer
            self.transformer.setNextTransformer(None)
            for index, selector in enumerate(self.selectors):
                exporter = CsvExporter(index, previousExporter)
                file = open(selector.selectedFile(), "w", newline="")
                exporter.setFile(file)
                previousExporter = exporter
                print(previousExporter)

            loader.recorderLoaded.connect(self.onRecordingToggled)
            self.threadpool.start(loader)


class PoseFeedbackWidget(TransformerWidget):
    """
    Widget for the pose feedback transformer.
    """

    def __init__(self,
                 parent: Optional[QWidget] = None, ) -> None:
        """
        Initialize the RecorderTransformerWidget.
        """
        TransformerWidget.__init__(self, "Feedback", parent)

        self.transformer = PoseFeedbackTransformer()

        self.sliderLabel = QLabel("Angle Limit", self)
        self.vLayout.addWidget(self.sliderLabel)

        self.angleLimitSlider = LabeledQSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.angleLimitSlider.setMinimum(0)
        self.angleLimitSlider.setMaximum(40)
        self.angleLimitSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.angleLimitSlider.setTickInterval(5)
        self.angleLimitSlider.valueChanged.connect(self.transformer.setAngleLimit)
        self.vLayout.addWidget(self.angleLimitSlider)


class QCameraSourceWidget(TransformerWidget):
    videoSource: QVideoSource
    transformer: VideoSourceTransformer

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the QCameraSourceWidget.
        """
        TransformerWidget.__init__(self, "Camera Source", parent)
        self.videoSource = QVideoSource()

        self.transformer = VideoSourceTransformer()
        self.transformer.videoSource = self.videoSource
        
        self.cameraSelector = CameraSelector(self)
        self.cameraSelector.selected.connect(self.videoSource.setCamera)
        self.vLayout.addWidget(self.cameraSelector, alignment=Qt.AlignmentFlag.AlignCenter)


class BackgroundRemoverWidget(TransformerWidget):
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Background Remover", parent)
        
        self.transformer = BackgroundRemover()


class VideoSourceWidget(TransformerWidget):
    """
    Selects a video file as source.
    """
    videoSource: CVVideoFileSource
    transformer: VideoSourceTransformer

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Video Source", parent)

        self.transformer = VideoSourceTransformer()

        self.fileSelector = FileSelector(self, title="Video Source")
        self.vLayout.addWidget(self.fileSelector)

        self.loadButton = QPushButton("Load", self)
        self.loadButton.clicked.connect(self.load)
        self.vLayout.addWidget(self.loadButton)

    @Slot()
    def load(self) -> None:
        """
        Load the video by creating the appropriate video file source object
        and setting it in the transformer.
        """
        self.videoSource = CVVideoFileSource(self.fileSelector.selectedFile())
        self.transformer.setVideoSource(self.videoSource)
