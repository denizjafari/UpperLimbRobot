"""
Widgets for exporting videos and data.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import io

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal

from core.resource_management.registry import REGISTRY
from core.transformers.transformers import RecorderTransformer
from core.transformers.exporters import CsvExporter, PongDataExporter, MetricsExporter
from core.transformers.ITransformer import ITransformer
from core.ui.utils import FileSelector
from core.resource_management.video.CVVideoRecorder import CVVideoRecorder


class ExporterWidget(QWidget):
    """
    Abstract base class fot exporter widgets.
    """
    removed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the exporter widget.
        """
        QWidget.__init__(self, parent)
        
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.typeLabel = QLabel("Exporter")
        self.hLayout.addWidget(self.typeLabel)

        self.fileSelector = FileSelector(mode=FileSelector.MODE_SAVE)
        self.hLayout.addWidget(self.fileSelector)
        
        self.removeButton = QPushButton("Remove")
        self.removeButton.clicked.connect(self.removed)

        self.hLayout.addWidget(self.removeButton)

        self._key = ""

    def load(self) -> None:
        """
        Load the exporter and prepare it for recording.
        """
        pass

    def unload(self) -> None:
        """
        Unload the exporters and save the data.
        """
        pass

    def transformer(self) -> ITransformer:
        """
        Return the transformer for the exporter.
        """
        raise NotImplementedError
    
    def setKey(self, key: str) -> None:
        """
        Set the key of this exporter for registry purposes.
        """
        self._key = key

    def key(self) -> str:
        """
        Return the key of this exporter for registry purposes.
        """
        return self._key
    
    def save(self, d: dict) -> None:
        """
        Save the exporter to a dictionary.
        """
        d["file"] = self.fileSelector.selectedFile()

    def restore(self, d: dict) -> None:
        """
        Restore the exporter from a dictionary.
        """
        if "file" in d:
            self.fileSelector.setPath(d["file"])

class VideoExporterWidget(ExporterWidget):
    """
    Exporter for the video stream.
    """

    videoRecorder: Optional[CVVideoRecorder]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the video exporter.
        """
        ExporterWidget.__init__(self, parent)
        self.videoRecorder = None
        self.recorderTransformer = RecorderTransformer()
        self.typeLabel.setText("Video Exporter")

    def load(self) -> None:
        """
        Load the exporter by creating a video recorder.
        """
        self.videoRecorder = CVVideoRecorder(self.recorderTransformer.frameRate,
                                             self.recorderTransformer.width,
                                             self.recorderTransformer.height,
                                             self.fileSelector.selectedFile())
        self.recorderTransformer.setVideoRecorder(self.videoRecorder)
        
    def unload(self) -> None:
        """
        Unload the exporter and save the video.
        """
        if self.videoRecorder is not None:
            self.videoRecorder.close()
        self.recorderTransformer.setVideoRecorder(None)
        
    def transformer(self) -> None:
        """
        Return the transformer for the video recorder.
        """
        return self.recorderTransformer
    
    def save(self, d: dict) -> None:
        """
        Save the exporter to a dictionary.
        """
        ExporterWidget.save(self, d)
        d["frameRate"] = self.recorderTransformer.frameRate
        d["width"] = self.recorderTransformer.width
        d["height"] = self.recorderTransformer.height

    def restore(self, d: dict) -> None:
        """
        Restore the exporter from a dictionary.
        """
        ExporterWidget.restore(self, d)
        if "frameRate" in d:
            self.recorderTransformer.frameRate = d["frameRate"]
        if "width" in d:
            self.recorderTransformer.width = d["width"]
        if "height" in d:
            self.recorderTransformer.height = d["height"]


class CsvExporterWidget(ExporterWidget):
    """
    Exporter for the CSV data.
    """
    csvTransformer: CsvExporter
    file: Optional[io.TextIOBase]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the CSV exporter.
        """
        ExporterWidget.__init__(self, parent)
        self.typeLabel.setText("CSV Exporter")

        self.csvTransformer = CsvExporter(0)
        self.file = None

    def transformer(self) -> None:
        """
        Return the transformer for the CSV exporter.
        """
        return self.csvTransformer
    
    def load(self) -> None:
        """
        Open the file and set the CSV transformer.
        """
        self.unload()
        self.file = open(self.fileSelector.selectedFile(), "w", newline="")
        self.csvTransformer.setFile(self.file)

    def unload(self) -> None:
        """
        Close the file
        """
        if self.file is not None:
            self.file.close()
        self.csvTransformer.setFile(None)

class PongDataExporterWidget(ExporterWidget):
    """
    Exporter for the pong data.
    """
    pongDataTransformer: PongDataExporter
    file: Optional[io.TextIOBase]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the CSV exporter.
        """
        ExporterWidget.__init__(self, parent)
        self.typeLabel.setText("Pong Data Exporter")

        self.pongDataTransformer = PongDataExporter()
        self.file = None

    def transformer(self) -> None:
        """
        Return the transformer for the CSV exporter.
        """
        return self.pongDataTransformer
    
    def load(self) -> None:
        """
        Open the file and set the CSV transformer.
        """
        self.file = open(self.fileSelector.selectedFile(), "w", newline="")
        self.pongDataTransformer.setFile(self.file)
        self.pongDataTransformer.startRecording()

    def unload(self) -> None:
        """
        Close the file
        """
        self.pongDataTransformer.endRecording()
        self.pongDataTransformer.setFile(None)

        if self.file is not None:
            self.file.close()


class MetricsExporterWidget(ExporterWidget):
    """
    Exporter for the metrics.
    """
    metricsTransformer: MetricsExporter
    file: Optional[io.TextIOBase]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the CSV exporter.
        """
        ExporterWidget.__init__(self, parent)
        self.typeLabel.setText("Metrics Exporter")

        self.metricsTransformer = MetricsExporter()
        self.file = None

    def transformer(self) -> None:
        """
        Return the transformer for the CSV exporter.
        """
        return self.metricsTransformer
    
    def load(self) -> None:
        """
        Open the file and set the CSV transformer.
        """
        self.file = open(self.fileSelector.selectedFile(), "w", newline="")
        self.metricsTransformer.setFile(self.file)
        self.metricsTransformer.startRecording()

    def unload(self) -> None:
        """
        Close the file
        """
        self.metricsTransformer.endRecording()
        self.metricsTransformer.setFile(None)

        if self.file is not None:
            self.file.close()
    

REGISTRY.register(VideoExporterWidget, "exporters.Video Exporter")
REGISTRY.register(CsvExporterWidget, "exporters.CSV Exporter")
REGISTRY.register(PongDataExporterWidget, "exporters.Pong Data Exporter")
REGISTRY.register(MetricsExporterWidget, "exporters.Metrics Exporter")