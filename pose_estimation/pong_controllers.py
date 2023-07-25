"""
Controllers for the pong game. The controllers change the difficulty of the
pong game based on game data.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QWidget, QFormLayout
from PySide6.QtCore import Qt

from events import Event, Client
from pose_estimation.registry import PONG_CONTROLLER_REGISTRY
from pose_estimation.ui_utils import LabeledQSlider

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
    
class SimplePongControllerWidget(QWidget):
    def __init__(self, controller: SimplePongController) -> None:
        QWidget.__init__(self)
        self._controller = controller

        self.formLayout = QFormLayout(self)
        self.setLayout(self.formLayout)

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
    
class SimplePongController(PongController):
    """
    A pong controller that increases the speed of the ball when the accuracy
    is above 60% and decreases the speed if the accuracy is less than 40%.
    """
    def __init__(self) -> None:
        PongController.__init__(self)
        self._lowerCutoff = 0.4
        self._higherCutoff = 0.6

    def widget(self) -> None:
        return SimplePongControllerWidget(self)
    
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
    
    def control(self, pongData: dict[str, object]):
        """
        Control the game based on the pong data.
        """
        if "client" not in pongData or pongData["client"] is None:
            return
        
        client: Client = pongData["client"]

        if "accuracy" in pongData and "ballSpeed" in pongData:
            if pongData["accuracy"] > 0.8:
                client.send(Event("setBallSpeed", [pongData["ballSpeed"] + 0.02]))
                module_logger.debug(f"Increased pong speed to {pongData['ballSpeed'] + 0.02}")
            elif pongData["accuracy"] < 0.7:
                client.send(Event("setBallSpeed", [pongData["ballSpeed"] - 0.02]))
                module_logger.debug(f"Decreased pong speed to {pongData['ballSpeed'] - 0.02}")


PONG_CONTROLLER_REGISTRY.register(SimplePongController, "SimplePongController")
