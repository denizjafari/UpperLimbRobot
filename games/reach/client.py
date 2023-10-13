

from typing import Optional

import logging

from PySide6.QtCore import QObject, Signal

from core.transformers.ITransformerStage import ITransformerStage
from core.transformers.utils import FrameData
from core.protocols.events import Event, Client

module_logger = logging.getLogger(__name__)


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

class ReachClient(ITransformerStage, QObject):
    availableMetricsUpdated = Signal(object)
    client: Optional[Client]

    def __init__(self) -> None:
        """
        Initialize the client.
        """
        ITransformerStage.__init__(self, True)
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