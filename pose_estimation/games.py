"""
Games transformers that are used to start and manage games, passing information
from the frame data objects to the games and/or adapting the games parameters
based on collected metrics.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from queue import Queue
from typing import Optional
import logging

import cv2

from PySide6.QtCore import QObject, Signal
from pose_estimation.audio import QSound
from pose_estimation.pong_controllers import PongController
from pose_estimation.registry import REGISTRY

from game_hosts.snake import SnakeGame
from pose_estimation.transforms import FrameData, Transformer, TransformerStage
from events import Client, Event

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class GestureDetector:
    """
    Interface for all GestureDetectors.
    """
    def detect(self, metrics: dict[str, float]) -> None:
        raise NotImplementedError

class ChickenWingDetector(GestureDetector):
    """
    Abstract class for chicken wing detection. Detects whether a chicken wing
    is performed.
    """
    def __init__(self) -> None:
        """
        Initialize the detector.
        """
        self.has_recovered = False

    def elbowHeight(self, metrics: dict) -> float:
        """
        Return the elbow height from the metrics. Needs to be implemented by
        the subclass to return the left or right elbow height.
        """
        raise NotImplementedError
    
    def shoulderHeight(self, metrics: dict) -> float:
        """
        Return the shoulder height from the metrics.
        """
        return metrics["shoulder_height"]

    def detect(self, metrics: dict) -> bool:
        """
        Detect whether a chicken wing is performed.
        """
        over_threshold = self.elbowHeight(metrics) > self.shoulderHeight(metrics)
        if over_threshold and self.has_recovered:
            module_logger.info("Chicken wing detected")
            self.has_recovered = False
            return True
        elif not self.has_recovered and \
                self.elbowHeight(metrics) < self.shoulderHeight(metrics) - 0.1:
            module_logger.info("Chicken wing recovered")
            self.has_recovered = True
            return False
        else:
            return False
        
class LeftChickenWingDetector(ChickenWingDetector):
    def elbowHeight(self, metrics: dict):
        return metrics["left_elbow_height"]
    
class RightChickenWingDetector(ChickenWingDetector):
    def elbowHeight(self, metrics: dict):
        return metrics["right_elbow_height"]


class GestureMapper:
    """
    A class that tracks one metric and its min/max attributes to map it to a
    range from 0.0 to 1.0
    """
    def __init__(self) -> None:
        self.metric = ""

    def setMetric(self, metric: str) -> None:
        """
        Set the metric to track.
        """
        self.metric = metric

    def mapFrom(self, frameData: FrameData) -> float:
        """
        Map the metric to a value between 0.0 and 1.0. Returns a negative value
        if needed values are not present in the frameData.
        """
        try:
            metrics = frameData["metrics"]
            metricsMax = frameData["metrics_max"]
            metricsMin = frameData["metrics_min"]

            return (metrics[self.metric] - metricsMin[self.metric]) \
                / (metricsMax[self.metric] - metricsMin[self.metric])

        except KeyError:
            return -1.0
        
class MetricsListProvider(QObject):
    """
    A class that provides a list of metrics.
    """
    availableMetricsUpdated = Signal(object)

    def __init__(self) -> None:
        """
        Initialize the class.
        """
        QObject.__init__(self)
        self._availableMetrics = []

    def availableMetrics(self) -> list[str]:
        """
        Return the list of available metrics.
        """
        return self._availableMetrics

    def updateFrom(self, frameData: FrameData) -> None:
        """
        Set the list of metrics.
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

class PoseFeedbackTransformer(TransformerStage):
    """
    Adds feedback on compensation to the image. Measures the angle between a
    straight line connecting the two shoulder joints and the horizontal axis.
    If the angle is within the defined angleLimit, a green border is added to
    the image, otherwise a red border is drawn.

    keypointSetIndex - the index into the keypointSet list from which the
    shoulder joint coordinates should be taken.
    angleLimit - the maximum angle (in degrees) that is accepted.
    """
    keypointSetIndex: int
    elevAngleLimit: int
    leanForwardLimit: int
    shoulderBaseDistance: float
    lastShoulderDistance: float

    def __init__(self,
                 keypointSetIndex: int = 0,
                 previous: Optional[Transformer] = None) -> None:
        """
        Initialize it.
        """
        TransformerStage.__init__(self, True, previous)

        self.keypointSetIndex = keypointSetIndex
        self.elevAngleLimit = 10
        self.leanForwardLimit = 1
        self.shoulderBaseDistance = 1

        self.wasLeaningTooFar = False
        self.shouldersWereNotLevel = False
        self.feedbackSound = REGISTRY.createItem("sounds.feedback")

    def setAngleLimit(self, angleLimit: int) -> None:
        """
        Set the angleLimit to this angle (in degrees).
        """
        self.elevAngleLimit = angleLimit

    def setLeanForwardLimit(self, lfLimit: int) -> None:
        """
        Set the lf limit to (1 + lfLimit / 10).
        """
        self.leanForwardLimit = 1 + (lfLimit / 10)

    def transform(self, frameData: FrameData) -> None:
        """
        Determine the angle between the straight line connecting the two
        shoulder joints and the horizontal line. Then draw the border in
        the correct color.
        """
        if self.active() and not frameData.dryRun \
                and "metrics_max" in frameData \
                    and "metrics" in frameData:

            metrics = frameData["metrics"]
            metricsMax = frameData["metrics_max"]

            correct = True

            if correct and metrics["shoulder_distance"] > metricsMax["shoulder_distance"]:
                if not self.wasLeaningTooFar:
                    module_logger.info("User is leaning too far forward")
                    self.feedbackSound.play()
                    self.wasLeaningTooFar = True
                correct = False
            elif self.wasLeaningTooFar:
                module_logger.info("User corrected leaning too far forward")
                self.wasLeaningTooFar = False

            if correct and metrics["shoulder_elevation_angle"] > metricsMax["shoulder_elevation_angle"]:
                if not self.shouldersWereNotLevel:
                    module_logger.info("User is not keeping their shoulders level enough")
                    self.feedbackSound.play()
                    self.shouldersWereNotLevel = True
                correct = False
            elif self.shouldersWereNotLevel:
                module_logger.info("User corrected not keeping their shoulder level enough")
                self.shouldersWereNotLevel = False
            
            cv2.rectangle(frameData.image,
                            (0,0),
                            (frameData.width(), frameData.height()),
                            (0, 255, 0) if correct else (0, 0, 255),
                            thickness=10)

        self.next(frameData)

    def __str__(self) -> str:
        return "Feedback"


class Snake(TransformerStage, QObject):
    """
    The snake game. The snake is controlled by the user's body. A right chicken
    wing turns the snake to the right, a left chicken wing turns the snake to
    left.
    """
    leftChickenWing = Signal()
    rightChickenWing = Signal()
    timeIntervalChanged = Signal(int)

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        TransformerStage.__init__(self, True, previous)
        QObject.__init__(self)

        self.leftChickenWingDetector = LeftChickenWingDetector()
        self.rightChickenWingDetector = RightChickenWingDetector()

        self.game = SnakeGame()
        self.leftChickenWing.connect(self.game.turnLeft)
        self.rightChickenWing.connect(self.game.turnRight)
        self.game.show()

    def setTimerInterval(self, timerInterval) -> None:
        """
        Set the timer interval between the snake moves.
        """
        self.game.setTimerInterval(timerInterval)

    def transform(self, frameData: FrameData) -> None:
        """
        Check wether the user has performed a chicken wing. If so, emit the
        corresponding signal. The signal is emitted when the elbow is above the
        shoulder. Before the signal is emitted, the elbow must be below the shoulder
        plus some margin.
        """
        if self.active() and not frameData.dryRun and "metrics" in frameData:
            if self.leftChickenWingDetector.detect(frameData["metrics"]):
                self.leftChickenWing.emit()
            if self.rightChickenWingDetector.detect(frameData["metrics"]):
                self.rightChickenWing.emit()

        self.next(frameData)

class SnakeClient(TransformerStage, QObject):
    """
    The snake game. The snake is controlled by the user's body. A right chicken
    wing turns the snake to the right, a left chicken wing turns the snake to
    left.
    """

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        TransformerStage.__init__(self, True, previous)
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


class PongClient(TransformerStage, QObject):
    """
    The pong game.
    The height of the hand will determine the height of the left paddle.
    """
    events: Queue[Event]
    pongData: dict[str, object]
    followMetrics: str
    availableMetricsUpdated = Signal(object)

    def __init__(self, previous: Optional[Transformer] = None) -> None:
        """
        Initialize the pong client.
        """
        TransformerStage.__init__(self, True, previous)
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


class PongControllerWrapper(TransformerStage):
    """
    Wrapper for the pong controller. The pong controller is used to adapt the game
    to the capabilities of the user.
    """
    def __init__(self) -> None:
        """
        Initialize the wrapper.
        """
        TransformerStage.__init__(self, True)
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


class ReachClient(TransformerStage, QObject):
    availableMetricsUpdated = Signal(object)
    client: Optional[Client]

    def __init__(self) -> None:
        """
        Initialize the client.
        """
        TransformerStage.__init__(self, True)
        QObject.__init__(self)

        self.xAxisMapper = GestureMapper()
        self.metricsListProvider = MetricsListProvider()
        self.metricsListProvider.availableMetricsUpdated.connect(self.availableMetricsUpdated)
        self.followMetric = ""
        self.client = None

    def setClient(self, client: Client) -> None:
        """
        Set the client to send the data to. The transformer will not take
        ownership of the client object.
        """
        if client is not None:
            client.eventReceived.connect(self.handleEvent)

        self.client = client

    
    def setFollowMetric(self, followMetric) -> None:
        """
        Set the metric that should be followed for determining the paddle's
        position.
        """
        self.followMetric = followMetric
        self.xAxisMapper.setMetric(self.followMetric)


    def handleEvent(self) -> None:
        """
        Handle events received from the server.
        """
        pass

    def transform(self, frameData: FrameData) -> None:
        """
        Send the data to the client.
        """
        self.metricsListProvider.updateFrom(frameData)

        if self.active():
            target = self.xAxisMapper.mapFrom(frameData)
            if self.client:
                self.client.send(Event("moveToY", [target]))

        self.next(frameData)


REGISTRY.register(lambda: QSound("assets/sounds/feedback.wav"), "sounds.feedback")
