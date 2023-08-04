"""
Widgets for the game transformers.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import logging

from PySide6.QtWidgets import QWidget, QLabel, QSlider, QPushButton, QHBoxLayout, \
    QButtonGroup, QRadioButton, QVBoxLayout, QFormLayout, QLineEdit, QComboBox
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from events import Client
from pose_estimation.pong_controllers import PongController
from pose_estimation.registry import PONG_CONTROLLER_REGISTRY, WIDGET_REGISTRY

from pose_estimation.ui_utils import ConnectionWidget, LabeledQSlider
from pose_estimation.games import PongClient, PongControllerWrapper, \
    PoseFeedbackTransformer, ReachClient, Snake, SnakeClient
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
    """
    transformer: PongClient
    client: Optional[Client]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PongServerWidget.
        """
        TransformerWidget.__init__(self, "Pong Server", parent)

        self.transformer = PongClient()
        self.transformer.availableMetricsUpdated.connect(self.updateMetricsList)

        self.formLayout = QFormLayout()
        self.vLayout.addLayout(self.formLayout)

        self.hostField = QLineEdit()
        self.hostField.setText("localhost")
        self.formLayout.addRow("Host", self.hostField)

        self.portField = QLineEdit()
        self.portField.setText("9876")
        self.portField.setValidator(QIntValidator(1024, 65535))
        self.formLayout.addRow("Port", self.portField)

        self.connectButton = QPushButton("Connect", self)
        self.connectButton.clicked.connect(self.connectClient)
        self.vLayout.addWidget(self.connectButton)

        self.metricDropdown = QComboBox(self)
        self.vLayout.addWidget(self.metricDropdown)

        self.buttonLayout = QVBoxLayout()
        self.vLayout.addLayout(self.buttonLayout)

        self.absolute = QRadioButton("absolute")
        self.threshold = QRadioButton("threshold")
        self.speed = QRadioButton("speed")
        self.buttonLayout.addWidget(self.absolute)
        self.buttonLayout.addWidget(self.threshold)
        self.buttonLayout.addWidget(self.speed)

        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.addButton(self.absolute)
        self.buttonGroup.addButton(self.threshold)
        self.buttonGroup.addButton(self.speed)
        self.buttonGroup.buttonClicked.connect(
            lambda btn: self.transformer.setMode(btn.text()))
        self.absolute.setChecked(True)
        
        self.client = None
        
        self.hDirectionLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hDirectionLayout)

        self.left = QRadioButton("left")
        self.right = QRadioButton("right")
        self.bottom = QRadioButton("bottom")
        self.hDirectionLayout.addWidget(self.left)
        self.hDirectionLayout.addWidget(self.right)
        self.hDirectionLayout.addWidget(self.bottom)

        self.directionButtonGroup = QButtonGroup(self)
        self.directionButtonGroup.addButton(self.left)
        self.directionButtonGroup.addButton(self.right)
        self.directionButtonGroup.addButton(self.bottom)
        self.directionButtonGroup.buttonClicked.connect(
            lambda btn: self.transformer.setOrientation(btn.text().upper()))
        self.left.setChecked(True)
        

    def updateMetricsList(self, metrics) -> None:
        """
        Update the metrics list.
        """
        newMetricDropdown = QComboBox(self)
        for metric in metrics:
            newMetricDropdown.addItem(metric)
            if metric == self.metricDropdown.currentText():
                newMetricDropdown.setCurrentText(metric)

        newMetricDropdown.currentTextChanged.connect(self.transformer.setFollowMetrics)
        
        self.vLayout.replaceWidget(self.metricDropdown, newMetricDropdown)
        self.metricDropdown.deleteLater()
        self.metricDropdown = newMetricDropdown

    def connectClient(self) -> None:
        """
        Create a client object and attempt to connect to the server with the
        host and port specified in the text fields.
        """
        if self.client is not None:
            self.client.close()

        address = (self.hostField.text(), int(self.portField.text()))
        self.client = Client(address)
        self.transformer.setClient(self.client)
        self.client.start()
        module_logger.info("Connecting to pong server")

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
        d["availableMetrics"] = [self.metricDropdown.itemText(i) \
                                 for i in range(self.metricDropdown.count())]
        d["selectedMetric"] = self.transformer.followMetric
        
        d["mode"] = self.buttonGroup.checkedButton().text()
        d["orientation"] = self.directionButtonGroup.checkedButton().text()

    def restore(self, d: dict) -> None:
        """
        Save the state of the widget to a dictionary.
        """
        TransformerWidget.save(self, d)
        self.updateMetricsList(d["availableMetrics"])
        self.metricDropdown.setCurrentText(d["selectedMetric"])

        if "mode" in d:
            mode = d["mode"]
            if mode == "absolute":
                self.absolute.setChecked(True)
            elif mode == "threshold":
                self.threshold.setChecked(True)
            elif mode == "speed":
                self.speed.setChecked(True)
        
        if "orientation" in d:
            orientation = d["orientation"]
            if orientation == "left":
                self.left.setChecked(True)
            elif orientation == "right":
                self.right.setChecked(True)
            elif orientation == "bottom":
                self.bottom.setChecked(True)

    def __str__(self) -> str:
        return "Pong Server"
    
class PongControllerWidget(TransformerWidget):
    """
    Widget controlling pong controllers. It allows the selection of a controller
    from the ones registered to the PONG_CONTROLLER_REGISTRY via a combobox.
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
        PONG_CONTROLLER_REGISTRY.itemsChanged.connect(self.updateControllerList)

    def updateControllerList(self) -> None:
        """
        Update the controller list when the registry changes.
        """
        self.controllerSelector.clear()
        self.controllerSelector.addItems(PONG_CONTROLLER_REGISTRY.items())

    def setController(self, controllerName: str) -> None:
        """
        Set the controller when it is selected in the combobox.
        """
        controller: PongController = PONG_CONTROLLER_REGISTRY.createItem(controllerName)
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
        self.transformer.metricsListProvider.availableMetricsUpdated.connect(
            self.updateMetricsList)

        self.connectionWidget = ConnectionWidget()
        self.connectionWidget.clientConnected.connect(self.setClient)
        self.vLayout.addWidget(self.connectionWidget)

        self.metricDropdown = QComboBox(self)
        self.vLayout.addWidget(self.metricDropdown)
        self.metricDropdown.currentTextChanged.connect(self.transformer.setFollowMetric)

        self.client = None

    def updateMetricsList(self, metrics) -> None:
        """
        Update the metrics list.
        """
        newMetricDropdown = QComboBox(self)
        for metric in metrics:
            newMetricDropdown.addItem(metric)
            if metric == self.metricDropdown.currentText():
                newMetricDropdown.setCurrentText(metric)

        newMetricDropdown.currentTextChanged.connect(self.transformer.setFollowMetric)
        
        self.vLayout.replaceWidget(self.metricDropdown, newMetricDropdown)
        self.metricDropdown.deleteLater()
        self.metricDropdown = newMetricDropdown

    def setClient(self, client: Client) -> None:
        """
        Set the client to use for the transformer.
        """
        self.transformer.setClient(client)

        if self.client:
            self.client.close()
        
        self.client = client

    def close(self) -> None:
        if self.client:
            self.client.close()


WIDGET_REGISTRY.register(PoseFeedbackWidget, "Feedback")
WIDGET_REGISTRY.register(SnakeWidget, "Snake Game")
WIDGET_REGISTRY.register(SnakeServerWidget, "Snake Server")
WIDGET_REGISTRY.register(PongServerWidget, "Pong Server")
WIDGET_REGISTRY.register(PongControllerWidget, "Pong Controller")
WIDGET_REGISTRY.register(ReachServerWidget, "Reach Server")
