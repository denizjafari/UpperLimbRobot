
from typing import Optional

from queue import Queue
import logging

from PySide6.QtCore import QObject, Signal

from core.transformers.ITransformer import ITransformer
from core.transformers.ITransformerStage import ITransformerStage
from core.transformers.utils import FrameData
from core.protocols.events import Event, Client
from core.resource_management.registry import REGISTRY
from core.resource_management.audio.QSound import QSound
from .controllers import PongController

module_logger = logging.getLogger(__name__)

class PongClient(ITransformerStage, QObject):
    """
    The pong game.
    The height of the hand will determine the height of the left paddle.
    """
    events: Queue[Event]
    pongData: dict[str, object]
    followMetrics: str
    availableMetricsUpdated = Signal(object)

    def __init__(self, previous: Optional[ITransformer] = None) -> None:
        """
        Initialize the pong client.
        """
        ITransformerStage.__init__(self, True, previous)
        QObject.__init__(self)
        self.events = Queue()

        self.mode = "absolute"
        self.followMetric = ""
        self._availableMetrics = []
        self.pongData = {
            "client":  None,
            "orientation": "LEFT",
            "ballSpeed": 2.0,
            "paddle": "LEFT"
        }

    def setClient(self, client: Client) -> None:
        """
        Set the client to send the data to. The transformer will not take
        ownership of the client object.
        """        
        self.pongData["client"] = client

        if client is not None:
            client.eventReceived.connect(self.handleEvent)
            self.setOrientation(self.pongData["orientation"])
            self.setPaddle(self.pongData["paddle"])

    def handleEvent(self, event: Event) -> None:
        """
        Handle events received from the server.
        """
        if event.name == "scoreUpdated":
            module_logger.debug("Updated scores for left and right player")
            self.pongData["scoreLeft"] = float(event.payload[0])
            self.pongData["scoreRight"] = float(event.payload[1])
        elif event.name == "ballSpeedUpdated":
            module_logger.debug("Updated ball speed")
            self.pongData["ballSpeed"] = float(event.payload[0])
        elif event.name == "orientationUpdated":
            module_logger.debug("Updated orientation")
            self.pongData["orientation"] = event.payload[0]
        self.events.put(event)


    def setMode(self, mode: str) -> None:
        """
        Set the mode of movement. Can be "absolute", "threshold" or "speed".
        Absolute means the paddle will always be at the exact position of the
        metric.
        Threshold means that the paddle will not move as long as the metric is
        around the central value of 0.5. Only if the metric reaches a threshold
        distance, the paddle moves either up or down depending on the directionn
        of the delta.
        Speed means that the distance of the metric to the central value of 0.5
        determines the speed of the paddle. If the metric is at 0.5, the paddle
        would not move for example. At 1.0, it would move up at full speed up, at
        0.0 it would move down at full speed.
        """
        if "client" in self.pongData and self.pongData["client"] is not None:
            self.pongData["client"].send(Event("clearMovement"))
        self.mode = mode
        module_logger.info(f"Pong movement mode set to {mode}")

    def setOrientation(self, orientation: str) -> None:
        """
        Set the orientation of the pong board. If orientation is "LEFT",
        then the user controlled paddle is on the left. If the orientation
        is "RIGHT", then the paddle is on the right.
        """
        if "client" in self.pongData and self.pongData["client"] is not None:
            self.pongData["client"].send(Event("setOrientation", [orientation]))
        
        self.pongData["orientation"] = orientation
        module_logger.info(f"Pong orientation set to {orientation}")

    def setPaddle(self, paddle: str) -> None:
        """
        Set the paddle that should be steered from this transformer
        """
        if "client" in self.pongData and self.pongData["client"] is not None:
            self.pongData["client"].send(Event("setPaddle", [paddle]))
        
        self.pongData["paddle"] = paddle
        module_logger.info(f"Pong paddle set to {paddle}")

    def availableMetrics(self) -> list[str]:
        """
        Return the list of available metrics.
        """
        return self._availableMetrics
    
    def setFollowMetric(self, metric: str) -> None:
        """
        Set the metric that should be followed for determining the paddle's
        position.
        """
        self.followMetric = metric

    def transform(self, frameData: FrameData) -> None:
        """
        Control the paddle.
        """
        if "metrics" in frameData:
            newAvailableMetrics = set(frameData["metrics"].keys())
            if len(newAvailableMetrics) != len(self._availableMetrics):
                self._availableMetrics = list(newAvailableMetrics)
                self.availableMetricsUpdated.emit(self._availableMetrics)
            else:
                for metric in self._availableMetrics:
                    if metric not in newAvailableMetrics:
                        self._availableMetrics = list(newAvailableMetrics)
                        self.availableMetricsUpdated.emit(self._availableMetrics)
                        break

        client = self.pongData["client"]

        if self.active() and not frameData.dryRun and "metrics" in frameData \
            and isinstance(client, Client) and "metrics_max" in frameData \
                and "metrics_min" in frameData \
                    and self.followMetric in frameData["metrics"] \
                        and self.followMetric in frameData["metrics_max"] \
                            and self.followMetric in frameData["metrics_min"]:

            delta = frameData["metrics_max"][self.followMetric] \
                    - frameData["metrics_min"][self.followMetric]

            target = (frameData["metrics"][self.followMetric] \
                    - frameData["metrics_min"][self.followMetric]) / delta

            frameData["metrics"]["target"] = target

            if self.mode == "absolute":
                event = Event("moveTo", [target])
                client.send(event)
            elif self.mode == "threshold":
                if target > 0.8:
                    client.send(Event("moveUp"))
                elif target < 0.2:
                    client.send(Event("moveDown"))
                else:
                    client.send(Event("neutral"))
            elif self.mode == "speed":
                client.send(Event("setSpeed", [2 * target - 1.0]))

            events = []
            while not self.events.empty():
                events.append(self.events.get())

            frameData["pong"] = self.pongData.copy()
            frameData["pong"]["events"] = events

        self.next(frameData)

class PongControllerWrapper(ITransformerStage):
    """
    Wrapper for the pong controller. The pong controller is used to adapt the game
    to the capabilities of the user.
    """
    def __init__(self) -> None:
        """
        Initialize the wrapper.
        """
        ITransformerStage.__init__(self, True)
        self.controller = None

    def setController(self, controller: PongController) -> None:
        """
        Set the controller that should be used to adapt the game.
        """
        self.controller = controller

    def transform(self, frameData: FrameData) -> None:
        """
        Adapt the games values if the controller is active and pong metadata
        is available in the frame data object.
        """
        if self.active() and self.controller is not None and "pong" in frameData:
            self.controller.control(frameData["pong"])
            frameData["metrics"]["ballSpeed"] = frameData["pong"]["ballSpeed"]

        self.next(frameData)


REGISTRY.register(lambda: QSound("assets/sounds/feedback.wav"), "sounds.feedback")
