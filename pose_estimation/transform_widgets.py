from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton
from PySide6.QtCore import Slot, Signal

from pose_estimation.transforms import Scaler, Transformer


class TransformerWidget(QWidget):
    """
    The base transformer widget including the title label and remove logic.
    """
    removed = Signal()

    titleLabel: QLabel
    vLayout: QVBoxLayout
    transformer: Transformer

    def __init__(self, title: str="Transformer", parent: Optional[QWidget] = None) -> None:
        """
        Initialize the TransformerWidget.
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.titleLabel = QLabel(title, self)
        self.vLayout.addWidget(self.titleLabel)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.removed)
        self.vLayout.addWidget(self.removeButton)


class ScalerWidget(TransformerWidget):
    """
    Widget wrapper around the Scaler transformer exposing the target size
    property in the ui.
    """
    transformer: Scaler

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ScalerWidget.
        """
        TransformerWidget.__init__(self, "Scaler", parent)

        self.transformer = Scaler(640, 640)

        self.heightSelector = QLineEdit(self)
        self.heightSelector.setText(str(640))
        self.vLayout.addWidget(self.heightSelector)

        self.applyButton = QPushButton("Apply", self)
        self.applyButton.clicked.connect(self.onApplyClicked)
        self.vLayout.addWidget(self.applyButton)

    @Slot()
    def onApplyClicked(self) -> None:
        """
        Apply the entered target size.
        """
        self.transformer.setTargetSize(int(self.heightSelector.text()))
