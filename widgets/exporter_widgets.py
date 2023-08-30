"""
Widgets for exporting videos and data.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal

from pose_estimation.registry import GLOBAL_PROPS
from pose_estimation.transforms import RecorderTransformer, Transformer
from pose_estimation.ui_utils import FileSelector
from pose_estimation.video import CVVideoRecorder


class ExporterWidget(QWidget):
    removed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        
        self.hLayout = QHBoxLayout()
        self.setLayout(self.hLayout)

        self.fileSelector = FileSelector(GLOBAL_PROPS["WORKING_DIR"], "file.txt")
        self.removeButton = QPushButton("Remove")

        self.hLayout.addWidget(self.fileSelector)
        self.hLayout.addWidget(self.removeButton)

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def transformer(self) -> Transformer:
        raise NotImplementedError
    

class VideoExporterWidget(ExporterWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        ExporterWidget.__init__(self, parent)

        self.recorderTransformer = RecorderTransformer()

    def load(self) -> None:
        self.recorderTransformer.setVideoRecorder(
            CVVideoRecorder(self.recorderTransformer.frameRate,
                            self.recorderTransformer.width,
                            self.recorderTransformer.height,
                            self.fileSelector.selectedFile()))
        
    def unload(self) -> None:
        self.recorderTransformer.setVideoRecorder(None)
        
    def transformer(self) -> None:
        return self.recorderTransformer
