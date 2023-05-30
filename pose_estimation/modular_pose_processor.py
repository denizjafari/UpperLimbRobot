from typing import Optional

import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox
from PySide6.QtCore import Slot, QRunnable, QObject, QThreadPool, Qt
from PySide6.QtGui import QPixmap, QImage

from pose_estimation.Models import ModelManager
from pose_estimation.transform_widgets import BackgroundRemoverWidget, \
    ImageMirrorWidget, LandmarkDrawerWidget, ModelRunnerWidget, \
        PoseFeedbackWidget, QCameraSourceWidget, RecorderTransformerWidget, \
            ScalerWidget, SkeletonDrawerWidget, TransformerWidget, \
                VideoSourceWidget
from pose_estimation.transforms import FrameData, FrameDataProvider, Pipeline, \
    QImageProvider, Transformer

class PipelineWidget(QWidget):
    """
    Show a pipeline of transformer widgets and provide an interface to the
    full pipeline as if it was one transformer.
    """
    modelManager: ModelManager
    lastFrameData: FrameData
    pipeline: Pipeline

    def __init__(self,
                 modelManager: ModelManager,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PipelineWidget by adding
        """
        QWidget.__init__(self, parent)
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.frameDataProvider = FrameDataProvider()
        self.imageProvider = QImageProvider()
        self.modelManager = modelManager
        self.qThreadPool = QThreadPool.globalInstance()
        self.pipeline = Pipeline()
        self.pipeline.setNextTransformer(self.imageProvider)
        self.imageProvider.setNextTransformer(self.frameDataProvider)

        self.hTransformerLayout = QHBoxLayout()
        self.hLayout.addLayout(self.hTransformerLayout)

        self.transformerSelector = QComboBox(self)
        self.transformerSelector.addItem("Camera Source")
        self.transformerSelector.addItem("Video Source")
        self.transformerSelector.addItem("Scaler")
        self.transformerSelector.addItem("Mirror")
        self.transformerSelector.addItem("Model")
        self.transformerSelector.addItem("Landmarks")
        self.transformerSelector.addItem("Skeleton")
        self.transformerSelector.addItem("Recorder")
        self.transformerSelector.addItem("Feedback")
        self.transformerSelector.addItem("Background Remover")
        self.hLayout.addWidget(self.transformerSelector)

        self.addButton = QPushButton("Add Transformer", self)
        self.addButton.clicked.connect(self.onAdd)
        self.hLayout.addWidget(self.addButton)

        self.lastFrameData = FrameData()

        self.hLayout.addStretch()
    
    @Slot()
    def onAdd(self) -> None:
        """
        When the add button is clicked to add a transformer
        """
        index = self.transformerSelector.currentIndex()
        if index == 0:
            widget = QCameraSourceWidget(self)
        elif index == 1:
            widget = VideoSourceWidget(self)
        elif index == 2:
            widget = ScalerWidget(self)
        elif index == 3:
            widget = ImageMirrorWidget(self)
        elif index == 4:
            widget = ModelRunnerWidget(self.modelManager, self)
        elif index == 5:
            widget = LandmarkDrawerWidget(self)
        elif index == 6:
            widget = SkeletonDrawerWidget(self)
        elif index == 7:
            widget = RecorderTransformerWidget(self)
        elif index == 8:
            widget = PoseFeedbackWidget(self)
        elif index == 9:
            widget = BackgroundRemoverWidget(self)
        else:
            widget = None

        if widget is not None:
            self.pipeline.append(widget.transformer)
            self.hTransformerLayout.addWidget(widget)
            widget.removed.connect(lambda: self.removeTransformerWidget(widget))

    @Slot(TransformerWidget)
    def removeTransformerWidget(self, widget: TransformerWidget) -> None:
        """
        Remove a transformer widget from the ui and from the pipeline.
        """
        self.pipeline.remove(widget.transformer)
        self.hTransformerLayout.removeWidget(widget)
        widget.deleteLater()


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

    def __init__(self,
                 modelManager: ModelManager,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModularProcessorWidget.
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.displayLabel = QLabel()
        self.vLayout.addWidget(self.displayLabel,
                               alignment=Qt.AlignmentFlag.AlignCenter)

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

        self.pipelineWidget = PipelineWidget(modelManager, self)
        self.vLayout.addWidget(self.pipelineWidget)
        self.qThreadPool = QThreadPool.globalInstance()

        self.pipelineWidget.imageProvider.frameReady.connect(self.showFrame)
        self.pipelineWidget.frameDataProvider.frameDataReady.connect(self.setFrameData)
        self.lastFrameRate = 0
        self.isRunning = False
        self.frameData = FrameData()

    def setFrameData(self, frameData) -> None:
        self.frameData = frameData

    def toggleRunning(self) -> None:
        """
        Toggle between the pipeline running and processing images and not
        running.
        """
        if not self.isRunning:
            self.processNextFrame()
            self.startButton.setText("Stop")
        else:
            self.startButton.setText("Start")
        
        self.isRunning = not self.isRunning

    def dryRun(self) -> None:
        """
        Perform a dry run to set resolutions and framerates for recorders.
        """
        processor = FrameProcessor(self.pipelineWidget.pipeline, dryRun=True)
        self.qThreadPool.start(processor)

    def processNextFrame(self) -> None:
        """
        Process the next frame that is available.
        """
        processor = FrameProcessor(self.pipelineWidget.pipeline)
        self.qThreadPool.start(processor)

    @Slot(np.ndarray)
    def showFrame(self, qImage: Optional[QImage]) -> None:
        """
        IF the qImage is not None, draw it to the application window.
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
        
        if self.isRunning:
            self.processNextFrame()

    @Slot(int)
    def onFrameRateUpdate(self, frameRate: int) -> None:
        """
        Update the label displaying the current frame rate.
        """
        self.frameRateLabel.setText(f"FPS: {frameRate}")
