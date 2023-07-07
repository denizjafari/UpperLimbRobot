"""
The core of the application. Contains the main window and pipeline building ui.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
import time
from typing import  Callable, Optional

import logging
import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox, QSizePolicy
from PySide6.QtCore import Slot, Signal, QRunnable, QObject, QThreadPool, Qt
from PySide6.QtGui import QPixmap, QImage, QCloseEvent

from pose_estimation.metric_widgets import GridMetricWidgetGroup, MetricWidgetGroup
from pose_estimation.registry import WIDGET_REGISTRY
from pose_estimation.transformer_widgets import TransformerWidget
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
        self.addButton.clicked.connect(lambda: self.onAdd(self.transformerSelector.currentText()))
        self.hLayout.addWidget(self.addButton)

        self.hLayout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        WIDGET_REGISTRY.itemsChanged.connect(self.onTransformerWidgetsChanged)
        self.onTransformerWidgetsChanged()
    
    @Slot()
    def onAdd(self, key: str) -> TransformerWidget:
        """
        When the add button is clicked to add a transformer
        """
        widget: TransformerWidget = WIDGET_REGISTRY.createItem(key)

        self._pipeline.append(widget.transformer)
        self.hTransformerLayout.addWidget(widget)
        widget.setParent(self)
        widget.removed.connect(lambda: self.removeTransformerWidget(widget))

        return widget

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
    
    def save(self, d: dict) -> None:
        lst = []

        for widget in self.children():
            if isinstance(widget, TransformerWidget):
                inner_d = {}
                widget.save(inner_d)
                lst.append([str(widget), inner_d])

        d["widgets"] = lst

    def restore(self, d: dict) -> None:
        for widget in self.children():
            if isinstance(widget, TransformerWidget):
                widget.deleteLater()

        for widgetName, widgetDict in d["widgets"]:
            widget = self.onAdd(widgetName)
            widget.restore(widgetDict)

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
    metricWidgets: MetricWidgetGroup

    def __init__(self,
                 onClose: Callable[[], None],
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModularProcessorWidget.

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
        
        self.metricWidgets = GridMetricWidgetGroup(self)
        self.hCenterLayout.addWidget(self.metricWidgets)

        self.frameRateLabel = QLabel()
        self.vLayout.addWidget(self.frameRateLabel,
                               alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.latencyLabel = QLabel()
        self.vLayout.addWidget(self.latencyLabel,
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
            threadingModel=TransformerHead.MultiThreading.PER_FRAME)

        self.pipelineWidget.imageProvider.frameReady.connect(self.showFrame)
        self.pipelineWidget.frameDataProvider.frameDataReady.connect(self.setFrameData)
        self.lastFrameRate = 0
        self.frameData = FrameData()
        self.latency = 0.1
        self.lastLatency = 0.1

        self.onClose = onClose

        handler = StatusLogHandler()
        handler.messageEmitted.connect(self.statusBar.setText)
        logging.getLogger().addHandler(handler.logHandler())

    def setFrameData(self, frameData: FrameData) -> None:
        """
        Set the frame data to be used by the transformer head.
        """
        self.frameData = frameData
        if "metrics" in frameData:
            self.metricWidgets.updateMetrics(frameData["metrics"],
                                             minimumMetrics=frameData["metrics_min"] \
                                                if "metrics_min" in frameData else None,
                                             maximumMetrics=frameData["metrics_max"] \
                                                if "metrics_max" in frameData else None)
            
        nextFrameRate = self.frameData.frameRate

        latency = time.time() - self.frameData["timings"][0][1]
        """
        timings = self.frameData["timings"]
        formattedTimings = [str(int(1000 * round(timings[x][1] - timings[x-1][1], 3))) \
                            for x in range(1, len(timings))]
        formattedTimings.append(str(int(1000 * round(time.time() - timings[-1][1], 3))))
        print(" ".join(formattedTimings))
        """
        
        self.latency = (10 * self.latency + latency) / 11

        if abs(self.latency - self.lastLatency) > 0.002:
            self.lastLatency = self.latency
            self.onLatencyUpdate(self.latency)

        if nextFrameRate != self.lastFrameRate:
            self.lastFrameRate = nextFrameRate
            self.onFrameRateUpdate(self.lastFrameRate)

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

            if self.frameData.streamEnded:
                self.toggleRunning()
                

    @Slot(int)
    def onFrameRateUpdate(self, frameRate: int) -> None:
        """
        Update the label displaying the current frame rate.
        """
        self.frameRateLabel.setText(f"FPS: {frameRate}")

    @Slot(float)
    def onLatencyUpdate(self, latency: float) -> None:
        self.latencyLabel.setText(f"Latency: {int(1000 * round(latency, 3))}ms")

    def save(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        d["pipeline"] = {}
        self.pipelineWidget.save(d["pipeline"])
        print(d)

    def restore(self, d: dict) -> None:
        """
        Restore the state of the widget from a dictionary.
        """
        self.pipelineWidget.restore(d["pipeline"])

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        """
        self.onClose()
        event.accept()
