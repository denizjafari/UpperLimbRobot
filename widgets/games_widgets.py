"""
Widgets for the game transformers.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import logging

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from events import Client
from pose_estimation.registry import WIDGET_REGISTRY

from pose_estimation.ui_utils import LabeledQSlider
from pose_estimation.games import DefaultMeasurementsTransformer, PongClient, PoseFeedbackTransformer, Snake, SnakeClient
from widgets.transformer_widgets import TransformerWidget

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

    def __str__(self) -> str:
        return "Feedback"

class SnakeWidget(TransformerWidget):
    """
    Widget controlling the snake game transformer and the game itself.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        TransformerWidget.__init__(self, "Snake Game", parent)
        self.transformer = Snake()

        self.hLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hLayout)

        self.hLayout.addWidget(QLabel("Timer Interval", self))
        
        self.timerIntervalSlider = LabeledQSlider(self, orientation=Qt.Orientation.Horizontal)
        self.timerIntervalSlider.setMinimum(100)
        self.timerIntervalSlider.setMaximum(3000)
        self.timerIntervalSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.timerIntervalSlider.setTickInterval(500)
        self.timerIntervalSlider.valueChanged.connect(self.transformer.setTimerInterval)
        self.hLayout.addWidget(self.timerIntervalSlider)


    def __str__(self) -> str:
        return "Snake"
    
class SnakeServerWidget(TransformerWidget):
    """
    Widget controlloing the sending of events to a snake game running remotely.
    """
    transformer: SnakeClient

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        TransformerWidget.__init__(self, "Snake Server", parent)

        self.transformer = SnakeClient()

        self.hLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hLayout)

        self.hLayout.addWidget(QLabel("Timer Interval", self))
        
        self.timerIntervalSlider = LabeledQSlider(self, orientation=Qt.Orientation.Horizontal)
        self.timerIntervalSlider.setMinimum(100)
        self.timerIntervalSlider.setMaximum(3000)
        self.timerIntervalSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.timerIntervalSlider.setTickInterval(500)
        #self.timerIntervalSlider.valueChanged.connect(self.transformer.setTimerInterval)
        self.hLayout.addWidget(self.timerIntervalSlider)

        self.connectButton = QPushButton("Connect", self)
        self.connectButton.clicked.connect(self.connectClient)
        self.vLayout.addWidget(self.connectButton)

    def connectClient(self) -> None:
        client = Client()
        self.transformer.setClient(client)
        client.start()

    def __str__(self) -> str:
        return "Snake Server"
    
class PongServerWidget(TransformerWidget):
    """
    Widget controlloing the sending of events to a snake game running remotely.
    """
    transformer: SnakeClient

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        TransformerWidget.__init__(self, "Snake Server", parent)

        self.transformer = PongClient()

        self.connectButton = QPushButton("Connect", self)
        self.connectButton.clicked.connect(self.connectClient)
        self.vLayout.addWidget(self.connectButton)

    def connectClient(self) -> None:
        client = Client()
        self.transformer.setClient(client)
        client.start()

    def __str__(self) -> str:
        return "Pong Server"


WIDGET_REGISTRY.register(DefaultMeasurementsWidget, "Default Measurements")
WIDGET_REGISTRY.register(PoseFeedbackWidget, "Feedback")
WIDGET_REGISTRY.register(SnakeWidget, "Snake Game")
WIDGET_REGISTRY.register(SnakeServerWidget, "Snake Server")
WIDGET_REGISTRY.register(PongServerWidget, "Pong Server")
