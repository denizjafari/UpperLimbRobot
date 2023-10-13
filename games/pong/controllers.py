"""
Controllers for the pong game. The controllers change the difficulty of the
pong game based on game data.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QWidget, QFormLayout
from PySide6.QtCore import Qt

from app.protocols.events import Event, Client
from app.resource_management.registry import REGISTRY
from app.ui.utils import LabeledQSlider

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class PongController:
    """
    Interface for all the pong controllers.
    """
    def __init__(self) -> None:
        """
        Initialize the pong controller.
        """
        self._key = ""

    def key(self) -> str:
        """
        Return the key for the registry.
        """
        return self._key
    
    def setKey(self, key: str) -> None:
        """
        Set the key for the registry.
        """
        self._key = key

    def widget(self) -> None:
        """
        Return the widget for the pong controller.
        """
        raise NotImplementedError("widget() not implemented")

    def control(self, pongData: dict[str, object]) -> None:
        """
        Control the pong game.
        """
        raise NotImplementedError("control() not implemented")
    
    def save(self, d: dict) -> None:
        """
        Save the state of the pong controller.
        """
        pass

    def restore(self, d: dict) -> None:
        """
        Restore the state of the pong controller.
        """
        pass

class SimplePongControllerWidget(QWidget):
    """
    Base widget to provide an UI for the SimplePongController.
    """
    def __init__(self, controller: SimplePongController) -> None:
        QWidget.__init__(self)
        self._controller = controller

        self.formLayout = QFormLayout(self)
        self.setLayout(self.formLayout)

        self.speedDeltaSlider = LabeledQSlider(self, orientation=Qt.Horizontal)
        self.speedDeltaSlider.valueChanged.connect(
            lambda val: self._controller.setSpeedDelta(val / 10))
        self.speedDeltaSlider.setRange(1, 20)
        self.speedDeltaSlider.setValue(2)
        self.formLayout.addRow("Speed Delta", self.speedDeltaSlider)

        self.lowerCutoffSlider = LabeledQSlider(self, orientation=Qt.Horizontal)
        self.lowerCutoffSlider.valueChanged.connect(
            lambda val: self._controller.setLowerCutoff(val / 100))
        self.lowerCutoffSlider.setRange(0, 100)
        self.lowerCutoffSlider.setValue(70)
        self.formLayout.addRow("Lower Cutoff", self.lowerCutoffSlider)

        self.higherCutoffSlider = LabeledQSlider(self, orientation=Qt.Horizontal)
        self.higherCutoffSlider.valueChanged.connect(
            lambda val: self._controller.setLowerCutoff(val / 100))
        self.higherCutoffSlider.setRange(0, 100)
        self.higherCutoffSlider.setValue(80)
        self.formLayout.addRow("Higher Cutoff", self.higherCutoffSlider)

    def save(self, d: dict) -> None:
        """
        Save the state of the pong controller.
        """
        d["speed_delta"] = self.speedDeltaSlider.value() / 10
        d["lower_cutoff"] = self.lowerCutoffSlider.value() / 100
        d["higher_cutoff"] = self.higherCutoffSlider.value() / 100

    def restore(self, d: dict) -> None:
        """
        Restore the state of the pong controller.
        """
        if "speed_delta" in d:
            self.speedDeltaSlider.setValue(d["speed_delta"] * 10)
        if "lower_cutoff" in d:
            self.lowerCutoffSlider.setValue(d["lower_cutoff"] * 100)
        if "higher_cutoff" in d:
            self.higherCutoffSlider.setValue(d["higher_cutoff"] * 100)

class WindowedPongControllerWidget(SimplePongControllerWidget):
    """
    Adds the window length slider to the SimplePongControllerWidget.
    """
    def __init__(self, controller: WindowedPongController) -> None:
        SimplePongControllerWidget.__init__(self, controller)

        self.windowLengthSlider = LabeledQSlider(self, orientation=Qt.Horizontal)
        self.windowLengthSlider.valueChanged.connect(self._controller.setWindowLength)
        self.windowLengthSlider.setRange(1, 10)
        self.formLayout.addRow("Window Length", self.windowLengthSlider)

    def save(self, d: dict) -> None:
        """
        Save the state of the pong controller.
        """
        SimplePongControllerWidget.save(self, d)
        d["window_length"] = self.windowLengthSlider.value() / 100

    def restore(self, d: dict) -> None:
        """
        Restore the state of the pong controller.
        """
        SimplePongControllerWidget.restore(self, d)
        if "window_length" in d:
            self.windowLengthSlider.setValue(d["window_length"] * 100)
    
class SimplePongController(PongController):
    """
    A pong controller that increases the speed of the ball when the accuracy
    is above a set percentage and decreases the speed if the accuracy is below
    a certain percentage.
    """
    def __init__(self) -> None:
        PongController.__init__(self)
        self._lowerCutoff = 0.4
        self._higherCutoff = 0.6
        self._speedDelta = 0.2
        self._widget = None

    def widget(self) -> SimplePongControllerWidget:
        if self._widget is None:
            self._widget = SimplePongControllerWidget(self)

        return self._widget
    
    def setLowerCutoff(self, lowerCutoff: float) -> None:
        """
        Set the lower cutoff for the accuracy.
        """
        self._lowerCutoff = lowerCutoff

    def setHigherCutoff(self, higherCutoff: float) -> None:
        """
        Set the higher cutoff for the accuracy.
        """
        self._higherCutoff = higherCutoff

    def setSpeedDelta(self, speedDelta: float) -> None:
        """
        Set the speed delta.
        """
        self._speedDelta = speedDelta

    def higherCutoff(self) -> float:
        """
        Return the higher cutoff for the accuracy.
        """
        return self._higherCutoff
    
    def lowerCutoff(self) -> float:
        """
        Return the lower cutoff for the accuracy.
        """
        return self._lowerCutoff
    
    def speedDelta(self) -> float:
        """
        Return the speed delta.
        """
        return self._speedDelta
    
    def control(self, pongData: dict[str, object]):
        """
        Control the game based on the pong data.
        """
        if "client" not in pongData or pongData["client"] is None:
            return
        
        client: Client = pongData["client"]

        if "selfHits" in pongData \
            and "selfMisses" in pongData \
                and pongData['selfHits'] + pongData['selfMisses'] > 0 \
                    and "ballSpeed" in pongData:
            accuracy = pongData["selfHits"] / \
                (pongData["selfHits"] + pongData["selfMisses"])
            
            if accuracy > self.higherCutoff():
                newSpeed = pongData["ballSpeed"] + self.speedDelta()
                client.send(Event("setBallSpeed", [newSpeed]))
                module_logger.debug(f"Increased pong speed to {newSpeed}")
            elif accuracy < self.lowerCutoff():
                newSpeed = pongData["ballSpeed"] - self.speedDelta()
                client.send(Event("setBallSpeed", [newSpeed]))
                module_logger.debug(f"Decreased pong speed to {newSpeed}")

    
    def save(self, d: dict) -> None:
        """
        Save the state of the pong controller.
        """
        self.widget().save(d)

    
    def restore(self, d: dict) -> None:
        """
        Restore the state of the pong controller.
        """
        self.widget().restore(d)

class WindowedPongController(SimplePongController):
    """
    A pong controller that acts like the SimplePonController, except that
    it uses a window of the last n hits and misses to calculate the accuracy.
    """
    def __init__(self) -> None:
        SimplePongController.__init__(self)
        self._windowLength = 5
        self._lastMiss = 0
        self._lastHit = 0
        self.history = []

    def widget(self) -> WindowedPongControllerWidget:
        if self._widget is None:
            self._widget = WindowedPongControllerWidget(self)

        return self._widget
    
    def setWindowLength(self, windowLength: float) -> None:
        """
        Set the window length for the accuracy.
        """
        if windowLength < 1:
            windowLength = 1
        self._windowLength = windowLength
    
    def windowLength(self) -> float:
        """
        Return the window.
        """
        return self._windowLength
    
    def control(self, pongData: dict[str, object]):
        """
        Control the game based on the pong data.
        """
        if "client" not in pongData or pongData["client"] is None:
            return
        client: Client = pongData["client"]

        if "events" not in pongData:
            return
        events: list[Event] = pongData["events"]
        ballInteraction = False
        
        for e in events:
            if e.payload[0] == pongData["orientation"]:
                ballInteraction = True
                if e.name == "hit":
                    self.history.append(1)
                    module_logger.debug("Registered hit for pong controller")
                elif e.name == "miss":
                    module_logger.debug("Registered miss for pong controller")
                    self.history.append(0)

        if ballInteraction:
            while len(self.history) > self._windowLength:
                self.history.pop(0)
            
            if len(self.history) == 0: return

            accuracy = sum(self.history) / len(self.history)

            if len(self.history) == self._windowLength:
                if accuracy > self.higherCutoff():
                    newSpeed = pongData["ballSpeed"] + self.speedDelta()
                    client.send(Event("setBallSpeed", [newSpeed]))
                    module_logger.debug(f"Increased pong speed to {newSpeed}")
                    self.history = []
                elif accuracy < self.lowerCutoff():
                    newSpeed = pongData["ballSpeed"] - self.speedDelta()
                    client.send(Event("setBallSpeed", [newSpeed]))
                    module_logger.debug(f"Decreased pong speed to {newSpeed}")
                    self.history = []


#REGISTRY.register(SimplePongController, "pong_controllers.SimplePongController")
REGISTRY.register(WindowedPongController, "pong_controllers.WindowedPongController")
