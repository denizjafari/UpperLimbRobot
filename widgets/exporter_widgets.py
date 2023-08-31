"""
Widgets for exporting videos and data.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal

from pose_estimation.registry import EXPORTER_REGISTRY, GLOBAL_PROPS
from pose_estimation.transforms import RecorderTransformer, Transformer
from pose_estimation.ui_utils import FileSelector
from pose_estimation.video import CVVideoRecorder


class ExporterWidget(QWidget):
    removed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.fileSelector = FileSelector()
        self.removeButton = QPushButton("Remove")
        self.removeButton.clicked.connect(self.removed)

        self.hLayout.addWidget(self.fileSelector)
        self.hLayout.addWidget(self.removeButton)

        self._key = ""

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def transformer(self) -> Transformer:
        raise NotImplementedError
    
    def setKey(self, key: str) -> None:
        self._key = key

    def key(self) -> str:
        return self._key
    

class VideoExporterWidget(ExporterWidget):
    videoRecorder: Optional[CVVideoRecorder]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        ExporterWidget.__init__(self, parent)
        self.videoRecorder = None

        self.recorderTransformer = RecorderTransformer()

    def load(self) -> None:
        self.videoRecorder = CVVideoRecorder(self.recorderTransformer.frameRate,
                                             self.recorderTransformer.width,
                                             self.recorderTransformer.height,
                                             self.fileSelector.selectedFile())
        self.recorderTransformer.setVideoRecorder(self.videoRecorder)
        
    def unload(self) -> None:
        if self.videoRecorder is not None:
            self.videoRecorder.close()
        self.recorderTransformer.setVideoRecorder(None)
        
    def transformer(self) -> None:
        return self.recorderTransformer
    

EXPORTER_REGISTRY.register(VideoExporterWidget, "Video Exporter")
