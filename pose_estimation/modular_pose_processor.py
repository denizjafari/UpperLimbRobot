from __future__ import annotations
from typing import Callable, Optional

import logging
import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox, QSizePolicy
from PySide6.QtCore import Slot, Signal, QRunnable, QObject, QThreadPool, Qt
from PySide6.QtGui import QPixmap, QImage

from pose_estimation.metric_widgets import MetricWidget, PyQtMetricWidget
from pose_estimation.registry import WIDGET_REGISTRY
from pose_estimation.transform_widgets import TransformerWidget, \
    TransformerWidgetsRegistry
from pose_estimation.transforms import FrameData, FrameDataProvider, Pipeline, \
    QImageProvider, Transformer, TransformerHead

class StatusLogHandler(QObject):
    """
    Log handler that makes the logged messages available to Qt slots.
    """
    messageEmitted = Signal(str)

    class Log(logging.Handler):
        def __init__(self, logHandler: StatusLogHandler) -> None:
            logging.Handler.__init__(self)
            self.logHandler = logHandler
            self.setLevel(logging.INFO)

        def emit(self, record: logging.LogRecord) -> None:
            self.logHandler.messageEmitted.emit(record.msg)
    
    def __init__(self) -> None:
        """
        Initialize the StatusLogHandler.
        """
        QObject.__init__(self)
        self._logHandler = StatusLogHandler.Log(self)

    def logHandler(self) -> StatusLogHandler.Log:
        """
        Return the log handler that interfaces with the Python logging module.
        """
        return self._logHandler


class PipelineWidget(QWidget):
    """
    Show a pipeline of transformer widgets and provide an interface to the
    full pipeline as if it was one transformer.
    """
    _pipeline: Pipeline

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PipelineWidget by adding
        """
        QWidget.__init__(self, parent)
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.frameDataProvider = FrameDataProvider()
        self.imageProvider = QImageProvider()
        self.qThreadPool = QThreadPool.globalInstance()
        self._pipeline = Pipeline()
        self._pipeline.setNextTransformer(self.imageProvider)
        self.imageProvider.setNextTransformer(self.frameDataProvider)

        self.hTransformerLayout = QHBoxLayout()
        self.hLayout.addLayout(self.hTransformerLayout)

        self.transformerSelector = QComboBox(self)
        self.hLayout.addWidget(self.transformerSelector)

        self.addButton = QPushButton("Add Transformer", self)
        self.addButton.clicked.connect(self.onAdd)
        self.hLayout.addWidget(self.addButton)

        self.hLayout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        WIDGET_REGISTRY.itemsChanged.connect(self.onTransformerWidgetsChanged)
        self.onTransformerWidgetsChanged()
    
    @Slot()
    def onAdd(self) -> None:
        """
        When the add button is clicked to add a transformer
        """
        text = self.transformerSelector.currentText()
        widget: TransformerWidget = WIDGET_REGISTRY.createItem(text)

        self._pipeline.append(widget.transformer)
        self.hTransformerLayout.addWidget(widget)
        widget.setParent(self)
        widget.removed.connect(lambda: self.removeTransformerWidget(widget))

    @Slot(TransformerWidget)
    def removeTransformerWidget(self, widget: TransformerWidget) -> None:
        """
        Remove a transformer widget from the ui and from the pipeline.
        """
        self._pipeline.remove(widget.transformer)
        self.hTransformerLayout.removeWidget(widget)
        widget.deleteLater()

    @Slot(object)
    def onTransformerWidgetsChanged(self) -> None:
        items = WIDGET_REGISTRY.items()
        newTransformerSelector = QComboBox(self)
        self.hLayout.replaceWidget(self.transformerSelector, newTransformerSelector)
        self.transformerSelector.deleteLater()
        self.transformerSelector = newTransformerSelector

        self.transformerWidgets = items.copy()

        for i in items:
            self.transformerSelector.addItem(i)

    def pipeline(self) -> Pipeline:
        """
        Return the pipeline of transformers.
        """
        return self._pipeline

class FrameProcessor(QRunnable, QObject):
    """
    Thread runnable that runs one transform.
    """

    def __init__(self, transformer: Transformer, dryRun: bool = False) -> None:
        """
        Initialize the frame processor to use some source and transformer.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.transformer = transformer
        self.frameData = FrameData(dryRun=dryRun)

    @Slot()
    def run(self) -> None:
        """
        Run the thread.
        """
        self.transformer.transform(self.frameData)

class ModularPoseProcessorWidget(QWidget):
    """
    Widget that allows building a pipeline of transformers modularly while
    keeping them editable.
    """

    vLayout: QVBoxLayout
    displayLabel: QLabel
    pipelineWidget: PipelineWidget
    metricViews: dict[str, MetricWidget]

    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModularProcessorWidget.

        transformerWidgetRegistry - the registry of all the transfomer widgets
        parent - the parent of this widget
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.hCenterLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hCenterLayout)

        self.displayLabel = QLabel()
        self.hCenterLayout.addWidget(self.displayLabel,
                               alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.vSideLayout = QVBoxLayout()
        self.hCenterLayout.addLayout(self.vSideLayout)

        self.metricViews = {}

        self.frameRateLabel = QLabel()
        self.vLayout.addWidget(self.frameRateLabel,
                               alignment=Qt.AlignmentFlag.AlignCenter)

        self.buttonHLayout = QHBoxLayout()
        self.vLayout.addLayout(self.buttonHLayout)

        self.linkButton = QPushButton("Link", self)
        self.linkButton.clicked.connect(self.dryRun)
        self.buttonHLayout.addWidget(self.linkButton)

        self.startButton = QPushButton("Start", self)
        self.startButton.clicked.connect(self.toggleRunning)
        self.buttonHLayout.addWidget(self.startButton)

        self.pipelineWidget = PipelineWidget(self)
        self.vLayout.addWidget(self.pipelineWidget)

        self.statusBar = QLabel(self)
        self.vLayout.addWidget(self.statusBar)
        self.statusBar.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        self.qThreadPool = QThreadPool.globalInstance()
        self.transformerHead = TransformerHead(
            self.pipelineWidget.pipeline(),
            threadingModel=TransformerHead.MultiThreading.PER_STAGE)

        self.pipelineWidget.imageProvider.frameReady.connect(self.showFrame)
        self.pipelineWidget.frameDataProvider.frameDataReady.connect(self.setFrameData)
        self.lastFrameRate = 0
        self.frameData = FrameData()

        handler = StatusLogHandler()
        handler.messageEmitted.connect(self.statusBar.setText)
        logging.getLogger().addHandler(handler.logHandler())

    def setFrameData(self, frameData: FrameData) -> None:
        """
        Set the frame data to be used by the transformer head.
        """
        self.frameData = frameData
        if "metrics" in frameData:
            self.onMetricsUpdated(frameData["metrics"])

    def toggleRunning(self) -> None:
        """
        Toggle between the pipeline running and processing images and not
        running.
        """
        if not self.transformerHead.isRunning():
            self.transformerHead.start()
            self.startButton.setText("Stop")
        else:
            self.transformerHead.stop()
            self.startButton.setText("Start")

    def dryRun(self) -> None:
        """
        Perform a dry run to set resolutions and framerates for recorders.
        """
        processor = FrameProcessor(self.pipelineWidget.pipeline(), dryRun=True)
        self.qThreadPool.start(processor)

    @Slot(np.ndarray)
    def showFrame(self, qImage: Optional[QImage]) -> None:
        """
        If the qImage is not None, draw it to the application window.
        """
        if qImage is not None:
            pixmap = QPixmap.fromImage(qImage)
            self.displayLabel.setPixmap(pixmap)
            nextFrameRate = self.frameData.frameRate
            if self.frameData.streamEnded:
                self.toggleRunning()
            if nextFrameRate != self.lastFrameRate:
                self.lastFrameRate = nextFrameRate
                self.onFrameRateUpdate(self.lastFrameRate)
                

    @Slot(int)
    def onFrameRateUpdate(self, frameRate: int) -> None:
        """
        Update the label displaying the current frame rate.
        """
        self.frameRateLabel.setText(f"FPS: {frameRate}")

    @Slot(QWidget)
    def onMetricsUpdated(self, metrics: dict[str, list[float]]) -> None:
        for col in metrics:
            if col not in self.metricViews:
                widget = PyQtMetricWidget(col)
                self.metricViews[col] = widget
                self.vSideLayout.addWidget(widget)
            else:
                widget = self.metricViews[col]
            self.metricViews[col].addValue(metrics[col])