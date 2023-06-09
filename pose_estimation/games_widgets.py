from typing import Optional

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

from pose_estimation.ui_utils import LabeledQSlider
from pose_estimation.games import ChickenWingGameTransformer
from pose_estimation.transform_widgets import TransformerWidget


class ChickenWingWidget(TransformerWidget):
    """
    Widget for the chicken wing game transformer.
    """
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ChickenWingWidget.
        """
        TransformerWidget.__init__(self, "Chicken Wing Game", parent)
        self.transformer = ChickenWingGameTransformer()

        self.selectorHLayout = QHBoxLayout()
        self.vLayout.addLayout(self.selectorHLayout)

        self.selectorLabel = QLabel("Height", self)
        self.selectorHLayout.addWidget(self.selectorLabel)

        self.selectorSlider = LabeledQSlider(self, orientation=Qt.Orientation.Horizontal)
        self.selectorSlider.setMinimum(-20)
        self.selectorSlider.setMaximum(20)
        self.selectorSlider.setValue(0)
        self.selectorHLayout.addWidget(self.selectorSlider)
        self.selectorSlider.valueChanged.connect(self.transformer.setLineDistance)
