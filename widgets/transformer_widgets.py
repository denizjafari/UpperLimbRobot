"""
Widgets for the default transformers.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Optional

from io import TextIOBase
import logging

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton, QSlider, QHBoxLayout, QColorDialog, QComboBox
from PySide6.QtCore import Slot, Signal, Qt, QThreadPool, QRunnable, QObject
from PySide6.QtGui import QColor

from pose_estimation.registry import WIDGET_REGISTRY
from pose_estimation.transformer_widgets import TransformerWidget
from pose_estimation.video import CVVideoFileSource, QVideoSource
from pose_estimation.transforms import BackgroundRemover, ButterworthTransformer, CsvExporter, \
    CsvImporter, DerivativeTransformer, ImageMirror, LandmarkDrawer, MetricTransformer, MinMaxTransformer, ModelRunner, Pipeline, \
        RecorderTransformer, Scaler, SkeletonDrawer, SlidingAverageTransformer, VideoSourceTransformer
from pose_estimation.ui_utils import CameraSelector, FileSelector, \
    LabeledQSlider, ModelSelector
from pose_estimation.video import CVVideoRecorder, VideoRecorder


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)


class ScalerWidget(TransformerWidget):
    """
    Scales an image to a square size using padding to keep the frame from
    tearing. Requires a frame source before it.
    """
    transformer: Scaler

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ScalerWidget.
        """
        TransformerWidget.__init__(self, "Scaler", parent)

        self.transformer = Scaler(400, 400)

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
        dim = int(self.heightSelector.text())
        self.transformer.setTargetSize(dim)
        module_logger.info(f"Applied dimensions {dim}x{dim} to Scaler")

    def save(self, d: dict) -> None:
        """
        Save the widget state to the given dictionary.
        """
        TransformerWidget.save(self, d)
        d["height"] = int(self.heightSelector.text())

    def restore(self, d: dict) -> None:
        """
        Restore the widget state from the given dictionary.
        """
        TransformerWidget.restore(self, d)
        self.heightSelector.setText(str(d["height"]))


class ImageMirrorWidget(TransformerWidget):
    """
    Mirrors the frame horizontally. Requires a frame source before it.
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
    Runs a model and injects the keypoints. Requires a frame source before it.
    """
    transformer: ModelRunner

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModelRunnerWidget.
        """
        TransformerWidget.__init__(self, "Model", parent)

        self.transformer = ModelRunner()

        self.modelSelector = ModelSelector(self)
        self.modelSelector.modelSelected.connect(self.transformer.setModel)
        self.vLayout.addWidget(self.modelSelector)

    def save(self, d: dict) -> None:
        """
        Save the widget state to the given dictionary.
        """
        TransformerWidget.save(self, d)
        d["model"] = self.modelSelector.selectedModel()

    def restore(self, d: dict) -> None:
        """
        Restore the widget state from the given dictionary.
        """
        TransformerWidget.restore(self, d)
        self.modelSelector.setSelectedModel(d["model"])


class LandmarkDrawerWidget(TransformerWidget):
    """
    Draws landmarks on the frame. Requires a frame source and a model before it.
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

    def save(self, d: dict) -> None:
        """
        Save the widget state to the given dictionary.
        """
        TransformerWidget.save(self, d)
        d["markerRadius"] = self.markerRadiusSlider.value()
        d["color"] = self.transformer.getRGBColor()

    def restore(self, d: dict) -> None:
        """
        Restore the widget state from the given dictionary.
        """
        TransformerWidget.restore(self, d)
        self.markerRadiusSlider.setValue(d["markerRadius"])
        self.colorDialog.setCurrentColor(QColor(*d["color"]))


class SkeletonDrawerWidget(TransformerWidget):
    """
    Draws a skeleton on the image. Requires a frame source and a model before
    it.
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

    def save(self, d: dict) -> None:
        """
        Save the widget state to the given dictionary.
        """
        TransformerWidget.save(self, d)
        d["lineThickness"] = self.lineThicknessSlider.value()
        d["color"] = self.transformer.getRGBColor()

    def restore(self, d: dict) -> None:
        """
        Restore the widget state from the given dictionary.
        """
        TransformerWidget.restore(self, d)
        self.lineThicknessSlider.setValue(d["lineThickness"])
        self.colorDialog.setCurrentColor(QColor(*d["color"]))


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

    def __init__(self,
                 frameRate: int,
                 width: int,
                 height: int,
                 selectedFile: str) -> None:
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
    """
    videoRecorder: VideoRecorder
    csvExporter: Optional[CsvExporter]
    selectors: list[FileSelector]
    outputFiles: list[TextIOBase]
    videoRecorder: Optional[VideoRecorder]
    isRecording: bool
    transformer: Pipeline

    def __init__(self,
                 parent: Optional[QWidget] = None, ) -> None:
        """
        Initialize the RecorderTransformerWidget.
        """
        TransformerWidget.__init__(self, "Recorder", parent)

        self.transformer = Pipeline()
        self.exporters = []
        self.selectors = []
        self.outputFiles = []
        self.videoRecorder = None
        self.isRecording = False
        self.recorderTransformer = RecorderTransformer()
        self.transformer.append(self.recorderTransformer)

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
        selector = FileSelector(self,
                                title="CSV output",
                                mode=FileSelector.MODE_SAVE,
                                removable=True)
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
        self.recorderTransformer.setVideoRecorder(videoRecorder)
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
            for exporter in self.exporters:
                self.transformer.remove(exporter)
            self.outputFiles = []
            self.exporters = []
            self.onRecordingToggled(None)
            module_logger.info("Stopped recording")
        else:
            loader = RecorderLoader(self.recorderTransformer.frameRate,
                                    self.recorderTransformer.width,
                                    self.recorderTransformer.height,
                                    self.outputFileSelector.selectedFile())
            
            for index, selector in enumerate(self.selectors):
                exporter = CsvExporter(index)
                file = open(selector.selectedFile(), "w", newline="")
                exporter.setFile(file)
                self.outputFiles.append(file)
                self.exporters.append(exporter)
                self.transformer.append(exporter)

            loader.recorderLoaded.connect(self.onRecordingToggled)
            self.threadpool.start(loader)
            module_logger.info("Started recording")
    

class QCameraSourceWidget(TransformerWidget):
    """
    Grabs frames from a QCamera and injects them into the frameData.
    """
    
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
        self.vLayout.addWidget(self.cameraSelector,
                               alignment=Qt.AlignmentFlag.AlignCenter)

    def close(self) -> None:
        self.videoSource.close()

    def save(self, d: dict) -> None:
        """
        Save the widget state to the given dictionary.
        """
        TransformerWidget.save(self, d)
        d["camera"] = self.cameraSelector.selectedCamera()

    def restore(self, d: dict) -> None:
        """
        Restore the widget state from the given dictionary.
        """
        TransformerWidget.restore(self, d)
        self.cameraSelector.setSelectedCamera(d["camera"])


class BackgroundRemoverWidget(TransformerWidget):
    """
    Removes the background from a frame. Requires a video source before it.
    """
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
    transformer: Pipeline
    videoSourceTransformer: VideoSourceTransformer
    selectors: list[FileSelector]

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Video Source", parent)

        self.importers = []
        self.transformer = Pipeline()
        self.videoSourceTransformer = VideoSourceTransformer()
        self.transformer.append(self.videoSourceTransformer)

        self.fileSelector = FileSelector(self, title="Video Source")
        self.vLayout.addWidget(self.fileSelector)

        self.csvImporterLayout = QVBoxLayout()
        self.vLayout.addLayout(self.csvImporterLayout)

        self.hButtonLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hButtonLayout)

        self.addImporterButton = QPushButton("Add CSV Importer")
        self.addImporterButton.clicked.connect(self.addImporter)
        self.hButtonLayout.addWidget(self.addImporterButton)

        self.loadButton = QPushButton("Load", self)
        self.loadButton.clicked.connect(self.load)
        self.hButtonLayout.addWidget(self.loadButton)

        self.selectors = []

    def addImporter(self) -> None:
        """
        Add a csv importer to the widget and pipeline.
        """
        selector = FileSelector(self, title="CSV input", removable=True)
        self.selectors.append(selector)

        def remove() -> None:
            self.selectors.remove(selector)
            self.csvImporterLayout.removeWidget(selector)
            selector.deleteLater()

        selector.removeButton.clicked.connect(remove)
        self.csvImporterLayout.addWidget(selector)

    @Slot()
    def load(self) -> None:
        """
        Load the video by creating the appropriate video file source object
        and setting it in the transformer.
        """
        filename = self.fileSelector.selectedFile()
        self.videoSource = CVVideoFileSource(filename)
        if self.videoSourceTransformer.videoSource is not None:
            self.videoSourceTransformer.videoSource.close()
        self.videoSourceTransformer.setVideoSource(self.videoSource)

        for importer in self.importers:
            self.transformer.remove(importer)

        self.importers = []

        for selector in self.selectors:
            importer = CsvImporter(33)
            file = open(selector.selectedFile(), "r", newline="")
            importer.setFile(file)
            self.transformer.append(importer)
            self.importers.append(importer)

        module_logger.info(f"Loaded video file {filename}")
    
    def close(self) -> None:
        """
        Close the video source if it is set.
        """
        if self.videoSourceTransformer.videoSource:
            self.videoSourceTransformer.videoSource.close()
    

class MetricViewWidget(TransformerWidget):
    """
    Calculates the metrics from a model's output. Requires a model before it.
    """
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Metric View", parent)
        self.transformer = MetricTransformer()

    
class SlidingAverageWidget(TransformerWidget):
    """
    Smoothes out metrics data using a sliding average over the most recent
    values. Requires a metrics transformer before it.
    """
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Sliding Average", parent)
        self.transformer = SlidingAverageTransformer()


class ButterworthWidget(TransformerWidget):
    """
    Smoothes out metrics data using a Butterworth filter. Requires a metrics
    transformer before it.
    """
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Butterworth Transformer", parent)
        self.transformer = ButterworthTransformer()
    
    
class MinMaxWidget(TransformerWidget):
    """
    Injects minimum and maximum into the frame data object. Requires a metrics
    transformer before it.
    """
    transformer: MinMaxTransformer

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Min/Max Selector", parent)
        self.transformer = MinMaxTransformer()

        self.updateButton = QPushButton("Update Metrics")
        self.updateButton.clicked.connect(lambda: \
                                          self.updateMetricsList(
            self.transformer.availableMetrics()))
        self.vLayout.addWidget(self.updateButton)

        self.transformerSelector = QComboBox(self)
        self.vLayout.addWidget(self.transformerSelector)

        self.maxButton = QPushButton("Set Maximum")
        self.maxButton.clicked.connect(lambda: \
                                       self.transformer.setMaxForMetric(
            self.transformerSelector.currentText()))
        self.vLayout.addWidget(self.maxButton)

        self.minButton = QPushButton("Set Minimum")
        self.minButton.clicked.connect(lambda: \
                                       self.transformer.setMinForMetric(
            self.transformerSelector.currentText()))
        self.vLayout.addWidget(self.minButton)

        self.updateMetricsList(self.transformer.availableMetrics())


    def updateMetricsList(self, metrics) -> None:
        """
        Updates the list of available metrics.
        """
        newTransformerSelector = QComboBox(self)
        for metric in metrics:
            newTransformerSelector.addItem(metric)
        
        self.vLayout.replaceWidget(self.transformerSelector, newTransformerSelector)
        self.transformerSelector.deleteLater()
        self.transformerSelector = newTransformerSelector


    def save(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        d["availableMetrics"] = self.transformer.availableMetrics()
        d["selectedMetric"] = self.transformerSelector.currentText()
        d["min"] = self.transformer._min
        d["max"] = self.transformer._max
    

    def restore(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        self.updateMetricsList(d["availableMetrics"])
        self.transformerSelector.setCurrentText(d["selectedMetric"])
        self.transformer._min = d["min"]
        self.transformer._max = d["max"]

class DerivativeWidget(TransformerWidget):
    """
    Calculates derivatives for metrics. Requires a Metrics Transformer before
    before it in the pipeline.
    """
    
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize it.
        """
        TransformerWidget.__init__(self, "Derivatives", parent)
        self.transformer = DerivativeTransformer()

    
WIDGET_REGISTRY.register(QCameraSourceWidget, "Camera Source")
WIDGET_REGISTRY.register(VideoSourceWidget, "Video Source")
WIDGET_REGISTRY.register(ImageMirrorWidget, "Mirror")
WIDGET_REGISTRY.register(ScalerWidget, "Scaler")
WIDGET_REGISTRY.register(BackgroundRemoverWidget, "Background Remover")
WIDGET_REGISTRY.register(ModelRunnerWidget, "Model")
WIDGET_REGISTRY.register(SkeletonDrawerWidget, "Skeleton")
WIDGET_REGISTRY.register(LandmarkDrawerWidget, "Landmarks")
WIDGET_REGISTRY.register(RecorderTransformerWidget, "Recorder")
WIDGET_REGISTRY.register(MetricViewWidget, "Metrics")
WIDGET_REGISTRY.register(SlidingAverageWidget, "Sliding Average")
WIDGET_REGISTRY.register(ButterworthWidget, "Butterworth Filter")
WIDGET_REGISTRY.register(MinMaxWidget, "Min/Max Selector")
WIDGET_REGISTRY.register(DerivativeWidget, "Derivatives")
