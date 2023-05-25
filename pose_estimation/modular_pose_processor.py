from typing import Optional

import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox
from PySide6.QtCore import Slot, QRunnable, QObject, QThreadPool, Qt
from PySide6.QtGui import QPixmap, QImage

from pose_estimation.Models import ModelManager
from pose_estimation.transform_widgets import ImageMirrorWidget, \
    LandmarkDrawerWidget, ModelRunnerWidget, PoseFeedbackWidget, \
        QCameraSourceWidget, RecorderTransformerWidget, ScalerWidget, \
        SkeletonDrawerWidget, TransformerWidget, VideoSourceWidget
from pose_estimation.transforms import FrameData, QImageProvider, Transformer

class PipelineWidget(QWidget, Transformer):
    """
    Show a pipeline of transformer widgets and provide an interface to the
    full pipeline as if it was one transformer.
    """
    modelManager: ModelManager
    lastFrameData: FrameData
    transformerWidgets: list[TransformerWidget]

    def __init__(self,
                 modelManager: ModelManager,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PipelineWidget by adding
        """
        QWidget.__init__(self, parent)
        Transformer.__init__(self, True, None)
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.transformerWidgets = []
        self.modelManager = modelManager
        self.qThreadPool = QThreadPool.globalInstance()

        self.imageProvider = QImageProvider()

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
        self.hLayout.addWidget(self.transformerSelector)

        self.addButton = QPushButton("Add Transformer", self)
        self.addButton.clicked.connect(self.onAdd)
        self.hLayout.addWidget(self.addButton)

        self.lastFrameData = FrameData()

        self.hLayout.addStretch()

    def transform(self, frameData: FrameData) -> FrameData:
        """
        Apply all transforms.
        """
        for t in self.transformerWidgets:
            frameData = t.transformer.transform(frameData)

        frameData = self.imageProvider.transform(frameData)
        self.lastFrameData = frameData

        return frameData
    
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
        else:
            widget = None

        if widget is not None:
            self.transformerWidgets.append(widget)
            self.hLayout.insertWidget(len(self.transformerWidgets) - 1, widget)
            widget.removed.connect(lambda: self.removeTransformerWidget(widget))

    @Slot(TransformerWidget)
    def removeTransformerWidget(self, widget: TransformerWidget) -> None:
        """
        Remove a transformer widget from the ui and from the pipeline.
        """
        self.transformerWidgets.remove(widget)
        self.hLayout.removeWidget(widget)
        widget.deleteLater()


class FrameProcessor(QRunnable, QObject):
    """
    Thread runnable that grabs one frame from a source and transforms it.
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
        self.vLayout.addWidget(self.displayLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.frameRateLabel = QLabel()
        self.vLayout.addWidget(self.frameRateLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.startButton = QPushButton("Start", self)
        self.startButton.clicked.connect(self.toggleRunning)
        self.vLayout.addWidget(self.startButton)

        self.pipelineWidget = PipelineWidget(modelManager, self)
        self.vLayout.addWidget(self.pipelineWidget)
        self.qThreadPool = QThreadPool.globalInstance()

        self.pipelineWidget.imageProvider.frameReady.connect(self.showFrame)
        self.lastFrameRate = 0
        self.isRunning = False

    def toggleRunning(self) -> None:
        if not self.isRunning:
            self.dryRun()
            self.startButton.setText("Stop")
        else:
            self.startButton.setText("Start")
        
        self.isRunning = not self.isRunning

    def dryRun(self) -> None:
        processor = FrameProcessor(self.pipelineWidget, dryRun=True)
        self.qThreadPool.start(processor)

    def processNextFrame(self) -> None:
        processor = FrameProcessor(self.pipelineWidget)
        self.qThreadPool.start(processor)

    @Slot(np.ndarray)
    def showFrame(self, qImage: Optional[QImage]) -> None:
        if qImage is not None:
            pixmap = QPixmap.fromImage(qImage)
            self.displayLabel.setPixmap(pixmap)
            nextFrameRate = self.pipelineWidget.lastFrameData.frameRate
            if self.pipelineWidget.lastFrameData.streamEnded:
                self.toggleRunning()
            if nextFrameRate != self.lastFrameRate:
                self.lastFrameRate = nextFrameRate
                self.onFrameRateUpdate(self.lastFrameRate)
        
        if self.isRunning:
            self.processNextFrame()

    @Slot(int)
    def onFrameRateUpdate(self, frameRate: int) -> None:
        self.frameRateLabel.setText(f"FPS: {frameRate}")
