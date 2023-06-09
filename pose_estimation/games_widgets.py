from typing import Optional
import logging

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSlider, QPushButton
from PySide6.QtCore import Qt

from pose_estimation.ui_utils import LabeledQSlider
from pose_estimation.games import ChickenWingGameTransformer, \
    DefaultMeasurementsTransformer, PoseFeedbackTransformer
from pose_estimation.transform_widgets import TransformerWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class DefaultMeasurementsWidget(TransformerWidget):
    """
    Widget for the default measurements transformer.
    """
    transformer: DefaultMeasurementsTransformer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        TransformerWidget.__init__(self, "Default Measurements", parent)

        self.transformer = DefaultMeasurementsTransformer()

        self.defaultsButton = QPushButton("Set defaults", self)
        self.defaultsButton.clicked.connect(self.transformer.captureDefaultPoseMeasurements)
        self.vLayout.addWidget(self.defaultsButton)

class PoseFeedbackWidget(TransformerWidget):
    """
    Widget for the pose feedback transformer.
    """
    transformer: PoseFeedbackTransformer

    def __init__(self,
                 parent: Optional[QWidget] = None, ) -> None:
        """
        Initialize the RecorderTransformerWidget.
        """
        TransformerWidget.__init__(self, "Feedback", parent)

        self.transformer = PoseFeedbackTransformer()

        self.elevSliderLabel = QLabel("Max Shoulder Elevation Angle", self)
        self.vLayout.addWidget(self.elevSliderLabel)

        self.elevAngleLimitSlider = LabeledQSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.elevAngleLimitSlider.setMinimum(0)
        self.elevAngleLimitSlider.setMaximum(40)
        self.elevAngleLimitSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.elevAngleLimitSlider.setTickInterval(5)
        self.elevAngleLimitSlider.valueChanged.connect(self.transformer.setAngleLimit)
        self.vLayout.addWidget(self.elevAngleLimitSlider)

        self.lfSliderLabel = QLabel("Max Lean Forward", self)
        self.vLayout.addWidget(self.lfSliderLabel)

        self.lfLimitSlider = LabeledQSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.lfLimitSlider.setMinimum(0)
        self.lfLimitSlider.setMaximum(20)
        self.lfLimitSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lfLimitSlider.setTickInterval(5)
        self.lfLimitSlider.valueChanged.connect(self.transformer.setLeanForwardLimit)
        self.vLayout.addWidget(self.lfLimitSlider)

    def captureShoulderBaseDistance(self) -> None:
        self.transformer.captureShoulderBaseDistance()
        module_logger.info("Captured shoulder base distance")

    def __str__(self) -> str:
        return "Feedback"


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