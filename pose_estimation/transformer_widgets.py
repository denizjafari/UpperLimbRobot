"""
Base class for transform widgets.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

from PySide6.QtWidgets import QGroupBox, QCheckBox, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Signal

from pose_estimation.transforms import Transformer

class TransformerWidget(QGroupBox):
    """
    The base transformer widget including the title label and remove logic.
    """
    removed = Signal()

    titleLabel: QLabel
    vSliderLayout: QVBoxLayout
    transformer: Transformer

    def __init__(self,
                 title: str="Transformer",
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the TransformerWidget.
        """
        QGroupBox.__init__(self, parent)
        self.setTitle(title)

        self.vSliderLayout = QVBoxLayout()
        self.setLayout(self.vSliderLayout)

        self.headLayout = QHBoxLayout()
        self.vSliderLayout.addLayout(self.headLayout)

        self.activeCheckBox = QCheckBox("Active")
        self.activeCheckBox.setChecked(True)
        self.activeCheckBox.clicked.connect(self.onActiveToggle)
        self.headLayout.addWidget(self.activeCheckBox)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.onRemove)
        self.headLayout.addWidget(self.removeButton)

    def onActiveToggle(self) -> None:
        self.transformer.setActive(self.activeCheckBox.isChecked())
    
    def onRemove(self) -> None:
        self.close()
        self.removed.emit()

    def close(self) -> None:
        pass