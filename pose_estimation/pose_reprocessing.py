from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Slot, QRunnable, Signal, QThreadPool, QObject

from pose_estimation.Models import FeedThroughModel, ModelManager, PoseModel
from pose_estimation.transforms import LandmarkConfidenceFilter, LandmarkDrawer, Scaler
from pose_estimation.ui_utils import FileSelector, ModelSelector
from pose_estimation.video import CVVideoFileSource, CVVideoRecorder


class PoseReprocessor(QRunnable, QObject):
    """
    Process a video again. This can be executed in a separate thread with
    a QThreadPool.

    statusUpdate - a signal that emits strings on status changes.
    model - the model to be used for video processing.
    """
    statusUpdate = Signal(str)
    model: PoseModel
    inputFileName: str
    outputFileName: str

    def __init__(self) -> None:
        """
        Initialize the object and thread runnable.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)
        self.model = FeedThroughModel()

        self.transformer = LandmarkConfidenceFilter()
        self.transformer.confidenceThreshold = 0.5
        self.transformer = LandmarkDrawer(self.transformer)
        self.transformer = Scaler(1280, 1280, self.transformer)

        self.inputFileName = ""
        self.outputFileName = ""
    
    @Slot(PoseModel)
    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to be used.
        """
        self.model = model

    @Slot(str)
    def setInputFilename(self, filename: str) -> None:
        """
        Set the video file input.
        """
        self.inputFileName = filename

    @Slot(str)
    def setOutputFilename(self, filename: str) -> None:
        """
        Set the video file output.
        """
        self.outputFileName = filename

    @Slot()
    def run(self) -> None:
        """
        Run the processing. Load the video from the source, process
        it and save it as after_processing.mp4.
        """
        self.statusUpdate.emit("Loading Video...")

        source = CVVideoFileSource(self.inputFileName)
        frameRate = source.frameRate()
        
        sink = CVVideoRecorder(frameRate, 1280, 1280, outputFile=self.outputFileName)

        frameIndex = 0

        while 1:
            frameIndex += 1
            frame = source.nextFrame()
            if frame is None: break

            image, keypoints = self.model.detect(frame)
            image, keypoints = self.transformer.transform(image, keypoints)

            sink.addFrame(image)
            self.statusUpdate.emit(f"Processed frame #{frameIndex}")

        sink.close()
        self.statusUpdate.emit("Done")

class PoseReprocessingWidget(QWidget):
    """
    A widget that acts as the frontend to the PoseReprocessor.

    threadpool - the threadpool in which the processing step should run.
    inputFilename - the path to the input file.
    model - the pose model to be used
    """
    threadpool: QThreadPool
    inputFilename: str
    outputFilename: str
    model: Optional[PoseModel]

    inFileSelector: FileSelector
    outFileSelector: FileSelector

    def __init__(self, modelManager: ModelManager, threadpool=QThreadPool()) -> None:
        """
        Initialize the widget.
        """
        QWidget.__init__(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.inFileSelector = FileSelector(self, title="Input File")
        self.inFileSelector.fileSelected.connect(self.setInputFilename)
        layout.addWidget(self.inFileSelector)

        self.outFileSelector = FileSelector(self, mode=FileSelector.MODE_SAVE, title="Output File")
        self.outFileSelector.fileSelected.connect(self.setOutputFilename)
        layout.addWidget(self.outFileSelector)

        self.modelSelector = ModelSelector(modelManager, self)
        self.modelSelector.modelSelected.connect(self.setModel)
        layout.addWidget(self.modelSelector)

        self.processButton = QPushButton("Run", self)
        self.processButton.clicked.connect(self.process)
        layout.addWidget(self.processButton)

        self.statusLabel = QLabel(self)
        layout.addWidget(self.statusLabel)
        self.threadpool = threadpool

        self.inputFilename = ""
        self.model = FeedThroughModel()

    @Slot(PoseModel)
    def setModel(self, model: PoseModel) -> None:
        """
        Set the model.
        """
        self.model = model

    @Slot(str)
    def setInputFilename(self, inputFilename: str) -> None:
        """
        Set the input file path.
        """
        self.inputFilename = inputFilename

    @Slot(str)
    def setOutputFilename(self, outputFilename: str) -> None:
        """
        Set the output file path.
        """
        self.outputFilename = outputFilename

    @Slot(str)
    def onStatusUpdate(self, statusUpdate: str) -> None:
        """
        Update the status label.
        """
        self.statusLabel.setText(statusUpdate)

    @Slot()
    def process(self) -> None:
        """
        Create and configure the pose reprocessor and run it.
        """
        reprocessor = PoseReprocessor()
        reprocessor.setInputFilename(self.inputFilename)
        reprocessor.setOutputFilename(self.outputFilename)
        reprocessor.setModel(self.model)
        reprocessor.statusUpdate.connect(self.onStatusUpdate)
        self.threadpool.start(reprocessor)
