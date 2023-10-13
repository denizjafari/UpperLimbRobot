
from typing import Optional

import logging

from PySide6.QtCore import QObject

from app.transformers.ITransformerStage import ITransformerStage
from app.transformers.ITransformer import ITransformer
from app.transformers.utils import FrameData
from app.gestures.detectors import LeftChickenWingDetector, RightChickenWingDetector
from app.protocols.events import Event, Client

module_logger = logging.getLogger(__name__)


class SnakeClient(ITransformerStage, QObject):
    """
    The snake game. The snake is controlled by the user's body. A right chicken
    wing turns the snake to the right, a left chicken wing turns the snake to
    left.
    """

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        ITransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

        self.leftChickenWingDetector = LeftChickenWingDetector()
        self.rightChickenWingDetector = RightChickenWingDetector()

        self.client = None

    def setClient(self, client: Client) -> None:
        """
        Set the client to send the data to. This transformer will not take
        ownsership of the client.
        """
        self.client = client

    def transform(self, frameData: FrameData) -> None:
        """
        Check wether the user has performed a chicken wing. If so, emit the
        corresponding signal. The signal is emitted when the elbow is above the
        shoulder. Before the signal is emitted, the elbow must be below the shoulder
        plus some margin.
        """
        if self.active() and not frameData.dryRun and "metrics" in frameData \
            and self.client is not None:
            if self.leftChickenWingDetector.detect(frameData["metrics"]):
                self.client.send(Event("leftTurn"))
            if self.rightChickenWingDetector.detect(frameData["metrics"]):
                self.client.send(Event("rightTurn"))

        self.next(frameData)