from typing import Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, \
    QLabel, QVBoxLayout, QComboBox
from PySide6.QtCore import Slot, Signal, QRunnable, QObject, QThreadPool
from PySide6.QtGui import QPixmap
import numpy as np
from pose_estimation.Models import KeypointSet
from pose_estimation.transform_widgets import ScalerWidget, TransformerWidget
from pose_estimation.transforms import Transformer

from pose_estimation.video import CVVideoSource, VideoSource, npArrayToQImage


class PipelineWidget(QWidget, Transformer):
    """
    Show a pipeline of transformer widgets and provide an interface to the
    full pipeline as if it was one transformer.
    """
    transformerWidgets: list[TransformerWidget]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PipelineWidget by adding
        """
        QWidget.__init__(self, parent)
        Transformer.__init__(self, True, None)
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.transformerWidgets = []

        self.transformerSelector = QComboBox(self)
        self.transformerSelector.addItem("Select Transformer")
        self.transformerSelector.addItem("Scaler")
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

        return image, keypointSet
    
    @Slot()
    def onAdd(self) -> None:
        """
        When the add button is clicked to add a transformer
        """
        index = self.transformerSelector.currentIndex()
        if index == 1:
            widget = ScalerWidget(self)
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
    frameReady = Signal(np.ndarray)

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

        self.frameReady.emit(image)


class ModularPoseProcessorWidget(QWidget):
    """
    Widget that allows building a pipeline of transformers modularly while
    keeping them editable.
    """
    videoSource: VideoSource

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModularProcessorWidget.
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.videoSource = CVVideoSource()

        self.displayLabel = QLabel()
        self.vLayout.addWidget(self.displayLabel)

        self.pipelineWidget = PipelineWidget(self)
        self.vLayout.addWidget(self.pipelineWidget)

        self.processFrame(None)


    @Slot(np.ndarray)
    def processFrame(self, frame: Optional[np.ndarray]) -> None:
        """
        Process a frame by running the transformation pipeline in a separate
        thread.
        """
        if frame is not None:
            self.displayLabel.setPixmap(QPixmap.fromImage(npArrayToQImage(frame)))

        processor = FrameProcessor(self.videoSource, self.pipelineWidget)
        processor.frameReady.connect(self.processFrame)
        QThreadPool.globalInstance().start(processor)
