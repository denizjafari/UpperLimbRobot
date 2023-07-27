"""
Base class for transform widgets.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

from PySide6.QtWidgets import QGroupBox, QCheckBox, QPushButton, QHBoxLayout, \
    QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Signal

from pose_estimation.transforms import Transformer

class TransformerWidget(QGroupBox):
    """
    The base transformer widget including the title label and remove logic.
    """
    removed = Signal()

    titleLabel: QLabel
    vLayout: QVBoxLayout
    transformer: Transformer

    def __init__(self,
                 title: str="Transformer",
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the TransformerWidget.
        """
        QGroupBox.__init__(self, parent)
        self.setTitle(title)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.headLayout = QHBoxLayout()
        self.vLayout.addLayout(self.headLayout)

        self.activeCheckBox = QCheckBox("Active")
        self.activeCheckBox.setChecked(True)
        self.activeCheckBox.clicked.connect(self.onActiveToggle)
        self.headLayout.addWidget(self.activeCheckBox)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.onRemove)
        self.headLayout.addWidget(self.removeButton)

        self._key = "Transformer Widget"

    def onActiveToggle(self) -> None:
        """
        Called when the active checkbox is toggled.
        """
        self.transformer.setActive(self.activeCheckBox.isChecked())
    
    def onRemove(self) -> None:
        """
        Called when the remove button is clicked.
        """
        self.close()
        self.removed.emit()

    def close(self) -> None:
        """
        Any cleanup of the underlying transformer should be done here.
        """
        pass

    def save(self, d: dict) -> None:
        """
        Store the state of the widget in the given dictionary.
        """
        d["active"] = self.activeCheckBox.isChecked()

    def restore(self, d: dict) -> None:
        """
        Restore the state of the widget from the given dictionary.
        """
        self.activeCheckBox.setChecked(d["active"])

    
    def key(self) -> str:
        """
        Return the key of this tranformer widget. Used by the registry.
        """
        return self._key
    
    def setKey(self, key: str) -> None:
        """
        Set the key of the transformer widget. Used by the registry.
        """
        self._key = key

    def __str__(self) -> None:
        """
        Return a string representation of this widget. Simply the name of the
        widget.
        """
        return self.key()
    