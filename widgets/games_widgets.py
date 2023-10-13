"""
Widgets for the game transformers.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import logging

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QPushButton, QHBoxLayout, \
    QButtonGroup, QRadioButton, QVBoxLayout, QFormLayout, QComboBox, QGroupBox
from PySide6.QtCore import Qt
from app.protocols.events import Client
from pose_estimation.pong_controllers import PongController
from app.resource_management.registry import REGISTRY

from app.ui.utils import ConnectionWidget, LabeledQSlider, MetricSelector
from games.pong.client import PongClient, PongControllerWrapper
from games.reach.client import ReachClient
from games.snake.client import SnakeClient
from app.transformers.PoseFeedbackTransformer import PoseFeedbackTransformer
from widgets.transformer_widgets import TransformerWidget

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

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

class SnakeServerWidget(TransformerWidget):
    """
    Widget controlloing the sending of events to a snake game running remotely.
    """
    transformer: SnakeClient

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the SnakeServerWidget.
        """
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
        """
        Create a client object connect to the default hostname and port
        (localhost:9876).
        """
        client = Client()
        self.transformer.setClient(client)
        client.start()

    def __str__(self) -> str:
        return "Snake Server"
    
class PongServerWidget(TransformerWidget):
    """
    Widget controlling the sending of events to a pong game running remotely.
    For the connection, it allows selection the host and port of the server.
    For the game, it allows the selection of the metrics that should be followed.

    Orientation and paddle selection is also possible. Orientation means on
    which side the paddles appear. Paddle selection means which of the paddles
    the player controls. With split screen pong, the player might use the paddle
    on the top left (orientation: left, paddle: top).
    """
    transformer: PongClient
    client: Optional[Client]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PongServerWidget.
        """
        TransformerWidget.__init__(self, "Pong Server", parent)

        self.transformer = PongClient()

        self.formLayout = QFormLayout()
        self.vLayout.addLayout(self.formLayout)

        self.connectionWidget = ConnectionWidget()
        self.connectionWidget.clientConnected.connect(self.setClient)
        self.vLayout.addWidget(self.connectionWidget)

        self.metricSelector = MetricSelector()
        self.transformer.availableMetricsUpdated.connect(
            self.metricSelector.updateMetricsList)
        self.metricSelector.metricSelected.connect(self.transformer.setFollowMetric)
        self.vLayout.addWidget(self.metricSelector)

        self.buttonLayout = QVBoxLayout()
        self.vLayout.addLayout(self.buttonLayout)
        
        self.client = None

        self.orientationGroup = QGroupBox("Orientation", self)
        self.hOrientationLayout = QHBoxLayout()
        self.orientationGroup.setLayout(self.hOrientationLayout)
        self.vLayout.addWidget(self.orientationGroup)

        self.orientationLeft = QRadioButton("left")
        self.orientationRight = QRadioButton("right")
        self.orientationBottom = QRadioButton("bottom")
        self.hOrientationLayout.addWidget(self.orientationLeft)
        self.hOrientationLayout.addWidget(self.orientationRight)
        self.hOrientationLayout.addWidget(self.orientationBottom)

        self.orientationButtonGroup = QButtonGroup(self)
        self.orientationButtonGroup.addButton(self.orientationLeft)
        self.orientationButtonGroup.addButton(self.orientationRight)
        self.orientationButtonGroup.addButton(self.orientationBottom)
        self.orientationButtonGroup.buttonClicked.connect(
            lambda btn: self.transformer.setOrientation(btn.text().upper()))
        self.orientationLeft.setChecked(True)

        self.paddleGroup = QGroupBox("Paddle", self)
        self.hPaddleLayout = QHBoxLayout()
        self.paddleGroup.setLayout(self.hPaddleLayout)
        self.vLayout.addWidget(self.paddleGroup)

        self.paddleLeft = QRadioButton("left")
        self.paddleRight = QRadioButton("right")
        self.paddleTop = QRadioButton("top")
        self.paddleBottom = QRadioButton("bottom")
        self.hPaddleLayout.addWidget(self.paddleLeft)
        self.hPaddleLayout.addWidget(self.paddleRight)
        self.hPaddleLayout.addWidget(self.paddleTop)
        self.hPaddleLayout.addWidget(self.paddleBottom)

        self.paddleButtonGroup = QButtonGroup(self)
        self.paddleButtonGroup.addButton(self.paddleLeft)
        self.paddleButtonGroup.addButton(self.paddleRight)
        self.paddleButtonGroup.addButton(self.paddleTop)
        self.paddleButtonGroup.addButton(self.paddleBottom)
        self.paddleButtonGroup.buttonClicked.connect(
            lambda btn: self.transformer.setPaddle(btn.text().upper()))
        self.orientationLeft.setChecked(True)
        

    def setClient(self, client: Client) -> None:
        """
        Set the client connection in this widget and the transformer. Close any
        previous connection.
        """
        self.transformer.setClient(client)

        if self.client is not None:
            self.client.close()

        self.client = client


    def close(self) -> None:
        """
        Close the client connection.
        """
        if self.client is not None:
            self.client.close()

    def save(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        self.metricSelector.save(d)
        
        d["orientation"] = self.orientationButtonGroup.checkedButton().text()
        d["paddle"] = self.paddleButtonGroup.checkedButton().text()

    def restore(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        self.metricSelector.restore(d)
        
        if "orientation" in d:
            orientation = d["orientation"]
            if orientation == "left":
                self.orientationLeft.setChecked(True)
                self.transformer.setOrientation("LEFT")
            elif orientation == "right":
                self.orientationRight.setChecked(True)
                self.transformer.setOrientation("RIGHT")
            elif orientation == "bottom":
                self.orientationBottom.setChecked(True)
                self.transformer.setOrientation("BOTTOM")
        
        if "paddle" in d:
            paddle = d["paddle"]
            if paddle == "left":
                self.paddleLeft.setChecked(True)
                self.transformer.setPaddle("LEFT")
            elif paddle == "right":
                self.paddleRight.setChecked(True)
                self.transformer.setPaddle("RIGHT")
            elif paddle == "top":
                self.paddleTop.setChecked(True)
                self.transformer.setPaddle("TOP")
            elif paddle == "bottom":
                self.paddleBottom.setChecked(True)
                self.transformer.setPaddle("BOTTOM")

    def __str__(self) -> str:
        return "Pong Server"
    
class PongControllerWidget(TransformerWidget):
    """
    Widget controlling pong controllers. It allows the selection of a controller
    from the ones registered to the REGISTRY via a combobox.
    """
    transformer: PongControllerWrapper

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PongControllerWidget.
        """
        super().__init__("Pong Controller", parent)

        self.transformer = PongControllerWrapper()

        self.controllerSelector = QComboBox(self)
        self.vLayout.addWidget(self.controllerSelector)

        self.controllerWidget = QLabel("No controller selected")
        self.vLayout.addWidget(self.controllerWidget)

        self._controller = None

        self.controllerSelector.currentTextChanged.connect(self.setController)
        self.updateControllerList()
        REGISTRY.itemsChanged.connect(self.updateControllerList)

    def updateControllerList(self, category: str) -> None:
        """
        Update the controller list when the registry changes.
        """
        if category != "pong_controllers":
            return

        self.controllerSelector.clear()
        self.controllerSelector.addItems(REGISTRY.items("pong_controllers"))

    def setController(self, controllerName: str) -> None:
        """
        Set the controller when it is selected in the combobox.
        """
        controller: PongController = REGISTRY.createItem(controllerName)
        self._controller = controller
        widget = controller.widget()
        self.transformer.setController(controller)
        self.vLayout.replaceWidget(self.controllerWidget, widget)
        self.controllerWidget.deleteLater()
        self.controllerWidget = widget

    def controller(self) -> PongController:
        """
        Get the currently selected controller.
        """
        return self._controller
        
    def __str__(self) -> str:
        return "Pong Controller"
    

    def save(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        d["selected_controller"] = self.controllerSelector.currentText()
        d["controller_state"] = {}
        self.controller().save(d["controller_state"])


    def restore(self, d: dict) -> None:
        """
        Restore the state of the widget from a dictionary.
        """
        TransformerWidget.restore(self, d)
        if "selected_controller" in d:
            self.controllerSelector.setCurrentText(d["selected_controller"])
            self.setController(d["selected_controller"])
        if "controller_state" in d:
            self.controller().restore(d["controller_state"])


class ReachServerWidget(TransformerWidget):
    """
    Widget for controlling a reach server.
    """
    transformer: ReachClient

    def __init__(self) -> None:
        """
        Initialize the ReachServerWidget.
        """
        super().__init__("Reach Server")

        self.transformer = ReachClient()

        self.connectionWidget = ConnectionWidget()
        self.connectionWidget.clientConnected.connect(self.setClient)
        self.vLayout.addWidget(self.connectionWidget)

        self.metricSelector = MetricSelector()
        self.metricSelector.metricSelected.connect(self.transformer.setFollowMetric)
        self.transformer.metricsListProvider.availableMetricsUpdated.connect(
            self.metricSelector.updateMetricsList)
        self.vLayout.addWidget(self.metricSelector)

        self.client = None

    def setClient(self, client: Client) -> None:
        """
        Set the client connection in this widget and the transformer. Close any
        previous connection.
        """
        self.transformer.setClient(client)

        if self.client:
            self.client.close()
        
        self.client = client

    def close(self) -> None:
        """
        Close the client to free up resources.
        """
        if self.client:
            self.client.close()

    def restore(self, d: dict) -> None:
        """
        Restore the state of the widget from a dictionary.
        """
        self.metricSelector.restore(d)

    def save(self, d: dict) -> None:
        """
        Save the state of the widget to the dictionary.
        """
        self.metricSelector.save(d)


REGISTRY.register(PoseFeedbackWidget, "widgets.Feedback")
REGISTRY.register(SnakeServerWidget, "widgets.Snake Server")
REGISTRY.register(PongServerWidget, "widgets.Pong Server")
REGISTRY.register(PongControllerWidget, "widgets.Pong Controller")
REGISTRY.register(ReachServerWidget, "widgets.Reach Server")
