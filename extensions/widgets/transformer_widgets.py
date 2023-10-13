"""
Widgets for the default transformers.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
import os
from typing import Optional

import logging

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton, QSlider, QHBoxLayout, QColorDialog, QComboBox
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QColor

from core.resource_management.registry import GLOBAL_PROPS, REGISTRY
from core.ui.ITransformerWidget import TransformerWidget
from core.resource_management.video.CVVideoFileSource import CVVideoFileSource
from core.resource_management.video.QVideoSource import QVideoSource

from core.transformers.transformers import BackgroundRemover, ButterworthTransformer, \
    CsvImporter, DerivativeTransformer, ImageMirror, LandmarkDrawer, \
        MetricTransformer, MinMaxTransformer, ModelRunner, \
            Scaler, SkeletonDrawer, SlidingAverageTransformer, \
                VideoSourceTransformer
from core.transformers.Pipeline import Pipeline
from core.ui.utils import CameraSelector, FileSelector, \
    LabeledQSlider, MetricSelector, ModelSelector
from extensions.widgets.exporter_widgets import ExporterWidget


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

        self.transformer = Pipeline()
        self.modelTransformer = ModelRunner()
        self.metricTransformer = MetricTransformer()
        self.derivativeTransformer = DerivativeTransformer()

        self.transformer.append(self.modelTransformer)
        self.transformer.append(self.metricTransformer)
        self.transformer.append(self.derivativeTransformer)

        self.modelSelector = ModelSelector(self)
        self.modelSelector.modelSelected.connect(self.modelTransformer.setModel)
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


class ExporterTransformerWidget(TransformerWidget):
    transformer: Pipeline
    exporters: list[ExporterWidget]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initiaize the ExporterTransformerWidget.
        """
        TransformerWidget.__init__(self, title="Exporter", parent=parent)
        self.exporters: list[ExporterWidget] = []
        self.recordingActive = False

        self.transformer = Pipeline()

        self.vExportersLayout = QVBoxLayout()
        self.vLayout.addLayout(self.vExportersLayout)
        
        self.exporterTypeSelector = QComboBox()
        self.exporterTypeSelector.addItems(REGISTRY.items("exporters"))
        REGISTRY.itemsChanged.connect(self.onExporterItemsChanged)
        self.vLayout.addWidget(self.exporterTypeSelector)

        self.addExporterButton = QPushButton("Add Exporter")
        self.addExporterButton.clicked.connect(
            lambda: self.addExporter(REGISTRY.createItem(
                self.exporterTypeSelector.currentText())))
        self.vLayout.addWidget(self.addExporterButton)

        self.toggleRecordingButton = QPushButton("Start Recording")
        self.toggleRecordingButton.clicked.connect(self.toggleRecording)
        self.vLayout.addWidget(self.toggleRecordingButton)


    def onExporterItemsChanged(self, category: str) -> None:
        """
        When the available exporters have been updated, update the dropdown.
        """
        if category != "exporters":
            return
        
        self.exporterTypeSelector.clear()
        self.exporterTypeSelector.addItems(REGISTRY.items("category"))
    
    def removeExporter(self, exporter: ExporterWidget) -> None:
        """
        Remove an exporter from the display.
        """
        transformer = exporter.transformer()

        self.transformer.remove(transformer)
        self.exporters.remove(exporter)

        exporter.deleteLater()

    def addExporter(self, exporter: ExporterWidget) -> None:
        """
        Add an exporter to the display.
        """
        exporter.removed.connect(lambda: self.removeExporter(exporter))
        self.exporters.append(exporter)
        self.vExportersLayout.addWidget(exporter)

        self.transformer.append(exporter.transformer())
    
    def toggleRecording(self) -> None:
        """
        Start/stop recording by simultaneously loading/unloading transformers.
        """
        if not self.recordingActive:
            self.transformer.recursiveLock()
            for exporter in self.exporters:
                exporter.load()
            self.transformer.recursiveUnlock()

            self.toggleRecordingButton.setText("Stop Recording")
            self.recordingActive = True
        else:
            self.transformer.recursiveLock()
            for exporter in self.exporters:
                exporter.unload()
            self.transformer.recursiveUnlock()

            self.toggleRecordingButton.setText("Start Recording")
            self.recordingActive = False

    def save(self, d: dict) -> None:
        super().save(d)

        exporterStates = []
        for exporter in self.exporters:
            exporterState = {}
            exporter.save(exporterState)
            exporterStates.append([exporter.key(), exporterState])

        d["exporters"] = exporterStates

    def restore(self, d: dict) -> None:
        super().restore(d)

        if "exporters" in d:
            for exporter in d["exporters"]:
                if isinstance(exporter, list) and len(exporter) == 2:
                    exporterWidget: ExporterWidget = \
                        REGISTRY.createItem(exporter[0])
                    exporterWidget.restore(exporter[1])
                    self.addExporter(exporterWidget)


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

        defaultPath = os.path.join(GLOBAL_PROPS["WORKING_DIR"], "input.mp4")
        self.fileSelector = FileSelector(self,
                                         title="Video Source",
                                         defaultPath=defaultPath)
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
        defaultPath = os.path.join(GLOBAL_PROPS["WORKING_DIR"],
                                   f"input_{len(self.selectors) + 1}.csv")
        selector = FileSelector(self,
                                title="CSV input",
                                removable=True,
                                defaultPath=defaultPath)
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

        self.selectedMetric = ""

        self.metricSelector = MetricSelector()
        self.transformer.availableMetricsUpdated.connect(
            self.metricSelector.updateMetricsList)
        self.metricSelector.metricSelected.connect(self.setSelectedMetric)
        self.vLayout.addWidget(self.metricSelector)

        self.maxButton = QPushButton("Set Maximum")
        self.maxButton.clicked.connect(lambda: \
                                       self.transformer.setMaxForMetric(
            self.selectedMetric))
        self.vLayout.addWidget(self.maxButton)

        self.minButton = QPushButton("Set Minimum")
        self.minButton.clicked.connect(lambda: \
                                       self.transformer.setMinForMetric(
            self.selectedMetric))
        self.vLayout.addWidget(self.minButton)

    
    def setSelectedMetric(self, metric: str) -> None:
        self.selectedMetric = metric


    def save(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        self.metricSelector.save(d)
        d["min"] = self.transformer._min
        d["max"] = self.transformer._max
    

    def restore(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.restore(self, d)
        self.metricSelector.restore(d)
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

    
REGISTRY.register(QCameraSourceWidget, "widgets.Camera Source")
REGISTRY.register(VideoSourceWidget, "widgets.Video Source")
REGISTRY.register(ImageMirrorWidget, "widgets.Mirror")
REGISTRY.register(ScalerWidget, "widgets.Scaler")
REGISTRY.register(BackgroundRemoverWidget, "widgets.Background Remover")
REGISTRY.register(ModelRunnerWidget, "widgets.Model")
REGISTRY.register(SkeletonDrawerWidget, "widgets.Skeleton")
REGISTRY.register(LandmarkDrawerWidget, "widgets.Landmarks")
REGISTRY.register(ExporterTransformerWidget, "widgets.Exporter")
REGISTRY.register(MetricViewWidget, "widgets.Metrics")
REGISTRY.register(SlidingAverageWidget, "widgets.Sliding Average")
REGISTRY.register(ButterworthWidget, "widgets.Butterworth Filter")
REGISTRY.register(MinMaxWidget, "widgets.Min/Max Selector")
REGISTRY.register(DerivativeWidget, "widgets.Derivatives")
