import io
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, \
    QCheckBox
from PySide6.QtCore import Slot, QRunnable, Signal, QThreadPool, QObject

from pose_estimation.Models import FeedThroughModel, ModelManager, PoseModel, SimpleKeypointSet
from pose_estimation.transforms import CsvImporter, ImageMirror, \
    LandmarkDrawer, ModelRunner, Scaler, SkeletonDrawer
from pose_estimation.ui_utils import FileSelector, OverlaySettingsWidget
from pose_estimation.video import CVVideoFileSource, CVVideoRecorder


class PoseReprocessor(QRunnable, QObject):
    """
    Process a video again. This can be executed in a separate thread with
    a QThreadPool.

    statusUpdate - a signal that emits strings on status changes.
    model - the model to be used for video processing.
    """
    statusUpdate = Signal(str)
    inputFileName: str
    outputFileName: str

    scaler: Scaler
    modelRunner: ModelRunner
    csvLoader: CsvImporter
    mirrorTransformer: ImageMirror
    keypointTransformer: LandmarkDrawer
    skeletonTransformer: SkeletonDrawer

    csvInputFile: Optional[io.TextIOBase]

    def __init__(self) -> None:
        """
        Initialize the object and thread runnable.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.scaler = Scaler(640, 640)
        self.modelRunner = ModelRunner(self.scaler)
        self.csvLoader = CsvImporter(33, self.modelRunner)
        self.mirrorTransformer = ImageMirror(self.csvLoader)
        self.keypointTransformer = LandmarkDrawer(self.mirrorTransformer)
        self.skeletonTransformer = SkeletonDrawer(self.keypointTransformer)

        self.inputFileName = ""
        self.outputFileName = ""   
        self.csvInputFile = None     
    
    @Slot(PoseModel)
    def setModel(self, model: PoseModel) -> None:
        """
        Set the model to be used.
        """
        self.modelRunner.setModel(model)

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

    @Slot(str)
    def setCsvInputFilename(self, filename: Optional[str]) -> None:
        """
        Set the csv input filename
        """
        self.csvInputFile = open(filename, "r", newline="")
        self.csvLoader.setFile(self.csvInputFile)

    @Slot(str)
    def setCsvOutputFilename(self, filename: Optional[str]) -> None:
        """
        Set the csv input filename
        """
        self.csvOutputFilename = filename

    @Slot(int)
    def setLineThickness(self, lineThickness: int) -> None:
        self.skeletonTransformer.lineThickness = lineThickness

    @Slot(int)
    def setMarkerRadius(self, markerRadius: int) -> None:
        self.keypointTransformer.markerRadius = markerRadius

    @Slot(bool)
    def setShowSkeleton(self, showSkeleton: bool) -> None:
        self.keypointTransformer.isActive = showSkeleton
        self.skeletonTransformer.isActive = showSkeleton

    @Slot(bool)
    def setMirror(self, mirror: bool) -> None:
        self.mirrorTransformer.isActive = mirror

    @Slot()
    def run(self) -> None:
        """
        Run the processing. Load the video from the source, process
        it and save it as after_processing.mp4.
        """
        self.statusUpdate.emit("Loading Video...")

        source = CVVideoFileSource(self.inputFileName)
        frameRate = source.frameRate()
        
        sink = CVVideoRecorder(frameRate, 640, 640, outputFile=self.outputFileName)

        frameIndex = 0

        while 1:
            frameIndex += 1
            frame = source.nextFrame()
            if frame is None: break

            image, keypoints = self.scaler.transform(frame, [])

            sink.addFrame(image)
            self.statusUpdate.emit(f"Processed frame #{frameIndex}")

        sink.close()
        if self.csvInputFile is not None: self.csvInputFile.close()
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

        self.useCsvFileInput = QCheckBox("Import CSV file", self)
        layout.addWidget(self.useCsvFileInput)

        self.csvInputFileSelector = FileSelector(self, title="CSV input file")
        layout.addWidget(self.csvInputFileSelector)

        self.overlaySettings = OverlaySettingsWidget(modelManager, self)
        self.overlaySettings.skeletonToggled.connect(self.onSkeletonToggled)
        self.overlaySettings.mirrorToggled.connect(self.onMirrorToggled)
        self.overlaySettings.markerRadiusChanged.connect(self.onMarkerRadiusChanged)
        self.overlaySettings.lineThicknessChanged.connect(self.onLineThicknessChanged)
        self.overlaySettings.modelSelected.connect(self.setModel)
        layout.addWidget(self.overlaySettings)

        self.processButton = QPushButton("Run", self)
        self.processButton.clicked.connect(self.process)
        layout.addWidget(self.processButton)

        self.statusLabel = QLabel(self)
        layout.addWidget(self.statusLabel)
        self.threadpool = threadpool

        self.inputFilename = ""
        self.model = FeedThroughModel()

        self.showSkeleton = False
        self.mirror = False

    @Slot(PoseModel)
    def setModel(self, model: PoseModel) -> None:
        """
        Set the model.
        """
        self.model = model

    @Slot()
    def onSkeletonToggled(self) -> None:
        """
        Toggle viewing the landmarks.
        """
        self.showSkeleton = not self.showSkeleton

    @Slot()
    def onMirrorToggled(self) -> None:
        """
        Toggle mirroring the frame.
        """
        self.mirror = not self.mirror

    @Slot(int)
    def onMarkerRadiusChanged(self, v) -> None:
        """
        Update the marker radius for the landmarks.
        """
        self.markerRadius = v

    @Slot(int)
    def onLineThicknessChanged(self, v) -> None:
        self.lineThickness = v

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
        reprocessor.setMarkerRadius(self.markerRadius)
        reprocessor.setLineThickness(self.lineThickness)
        reprocessor.setMirror(self.mirror)
        reprocessor.setShowSkeleton(self.showSkeleton)
        reprocessor.setCsvInputFilename(
            self.csvInputFileSelector.selectedFile() \
                if self.useCsvFileInput.isChecked() else None)
        reprocessor.statusUpdate.connect(self.onStatusUpdate)
        self.threadpool.start(reprocessor)
