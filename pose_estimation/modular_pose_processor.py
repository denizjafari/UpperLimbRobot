from typing import Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox
from PySide6.QtCore import Slot, QRunnable, QObject, QThreadPool, Qt, Signal
from PySide6.QtGui import QPixmap, QImage
import numpy as np

from pose_estimation.Models import KeypointSet, ModelManager
from pose_estimation.transform_widgets import ImageMirrorWidget, \
    LandmarkDrawerWidget, ModelRunnerWidget, RecorderTransformerWidget, ScalerWidget, \
        SkeletonDrawerWidget, TransformerWidget
from pose_estimation.transforms import QImageProvider, Transformer
from pose_estimation.ui_utils import CameraSelector
from pose_estimation.video import FrameRateProvider, QVideoSource, VideoSource


class PipelineWidget(QWidget, Transformer):
    """
    Show a pipeline of transformer widgets and provide an interface to the
    full pipeline as if it was one transformer.
    """
    modelManager: ModelManager
    frameRateProvider: FrameRateProvider
    transformerWidgets: list[TransformerWidget]

    def __init__(self,
                 modelManager: ModelManager,
                 frameRateProvider: FrameRateProvider,
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
        self.frameRateProvider = frameRateProvider

        self.imageProvider = QImageProvider()

        self.transformerSelector = QComboBox(self)
        self.transformerSelector.addItem("Scaler")
        self.transformerSelector.addItem("Mirror")
        self.transformerSelector.addItem("Model")
        self.transformerSelector.addItem("Landmarks")
        self.transformerSelector.addItem("Skeleton")
        self.transformerSelector.addItem("Recorder")
        self.hLayout.addWidget(self.transformerSelector)

        self.addButton = QPushButton("Add Transformer", self)
        self.addButton.clicked.connect(self.onAdd)
        self.hLayout.addWidget(self.addButton)

        self.hLayout.addStretch()

    def transform(self, image: np.ndarray, keypointSet: KeypointSet) \
        -> tuple[np.ndarray, list[KeypointSet]]:
        """
        Apply all transforms.
        """
        for t in self.transformerWidgets:
            image, keypointSet = t.transformer.transform(image, keypointSet)

        self.imageProvider.transform(image, keypointSet)

        return image, keypointSet
    
    @Slot()
    def onAdd(self) -> None:
        """
        When the add button is clicked to add a transformer
        """
        index = self.transformerSelector.currentIndex()
        if index == 0:
            widget = ScalerWidget(self)
        elif index == 1:
            widget = ImageMirrorWidget(self)
        elif index == 2:
            widget = ModelRunnerWidget(self.modelManager, self)
        elif index == 3:
            widget = LandmarkDrawerWidget(self)
        elif index == 4:
            widget = SkeletonDrawerWidget(self)
        elif index == 5:
            widget = RecorderTransformerWidget(self.frameRateProvider, self)
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

    def __init__(self, source: VideoSource, transformer: Transformer) -> None:
        """
        Initialize the frame processor to use some source and transformer.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.source = source
        self.transformer = transformer

    @Slot()
    def run(self) -> None:
        """
        Run the thread.
        """
        image = self.source.nextFrame()
        image, _ = self.transformer.transform(image, [])


class ModularPoseProcessorWidget(QWidget):
    """
    Widget that allows building a pipeline of transformers modularly while
    keeping them editable.
    """
    videoSource: VideoSource

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

        self.frameRateProvider = FrameRateProvider()
        self.frameRateProvider.frameRateUpdated.connect(self.onFrameRateUpdate)

        self.videoSource = QVideoSource()

        self.displayLabel = QLabel()
        self.vLayout.addWidget(self.displayLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.frameRateLabel = QLabel()
        self.vLayout.addWidget(self.frameRateLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.cameraSelector = CameraSelector(self)
        self.cameraSelector.selected.connect(self.videoSource.setCamera)
        self.vLayout.addWidget(self.cameraSelector, alignment=Qt.AlignmentFlag.AlignCenter)

        self.pipelineWidget = PipelineWidget(modelManager, self.frameRateProvider, self)
        self.vLayout.addWidget(self.pipelineWidget)
        self.qThreadPool = QThreadPool.globalInstance()

        self.pipelineWidget.imageProvider.frameReady.connect(self.showFrame)
        self.processNextFrame()

        
    def processNextFrame(self) -> None:
        processor = FrameProcessor(self.videoSource, self.pipelineWidget)
        self.qThreadPool.start(processor)


    @Slot(np.ndarray)
    def showFrame(self, qImage: Optional[QImage]) -> None:
        if qImage is not None:
            pixmap = QPixmap.fromImage(qImage)
            self.displayLabel.setPixmap(pixmap)
            self.frameRateProvider.onFrameReady()
        
        self.processNextFrame()

    @Slot(int)
    def onFrameRateUpdate(self, frameRate: int) -> None:
        self.frameRateLabel.setText(f"FPS: {frameRate}")
