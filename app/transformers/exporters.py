from typing import Optional

import csv
import io
import json

from .ITransformer import ITransformer
from .ITransformerStage import ITransformerStage
from .utils import FrameData

class CsvExporter(ITransformerStage):
    """
    Exports the keypoints frame by frame to a separate file.
    """
    index: int
    csvWriter: Optional[csv.writer]

    def __init__(self,
                 index: int,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.csvWriter = None
        self.index = index

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.csvWriter = csv.writer(file) if file is not None else None

    def transform(self, frameData: FrameData) -> None:
        """
        Export the first set of keypoints from the list of keypoint sets. This
        set is subsequently popped from the list.
        """
        if self.active() \
            and self.csvWriter is not None \
                and not frameData.dryRun:
            for k in frameData.keypointSets[self.index].getKeypoints():
                self.csvWriter.writerow(k)
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Exporter"
    
class PongDataExporter(ITransformerStage):
    """
    Exports key pong data frame by frame.
    """
    pongData: list[dict]
    file: Optional[io.TextIOBase]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.file = None
        self.record = False

    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.file = file

    def startRecording(self) -> None:
        """
        Start recording pong data.
        """
        self.pongData = []
        self.record = True

    def endRecording(self) -> None:
        """
        End recording pong data.
        """
        if self.file is not None:
            json.dump(self.pongData, self.file)
        self.record = False
        self.pongData = []

    def transform(self, frameData: FrameData) -> None:
        """
        Add the current pong data to the export.
        """
        if self.active() \
            and "pong" in frameData \
                and self.record \
                    and not frameData.dryRun:
            pongData: dict = frameData["pong"].copy()
            del pongData["client"]
            del pongData["events"]
            self.pongData.append(pongData.copy())
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Pong Data Exporter"


class MetricsExporter(ITransformerStage):
    """
    Exports metrics data frame by frame.
    """
    metricsData: dict[str, list[float]]
    file: Optional[io.TextIOBase]

    def __init__(self,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize it.
        """
        ITransformerStage.__init__(self, True, previous)

        self.file = None
        self.record = False
    
    def setFile(self, file: io.TextIOBase) -> None:
        """
        Set the file that the csv should be written to.
        The previous file is NOT closed.
        """
        self.file = file

    def startRecording(self) -> None:
        self.record = True
        self.metricsData = {}

    def endRecording(self) -> None:
        self.record = False
        if self.file is not None:
            json.dump(self.metricsData, self.file)
    
    def transform(self, frameData: FrameData) -> None:
        """
        Add all current metrics data to the export.
        """
        if self.active() \
            and "metrics" in frameData \
                and "metrics_max" in frameData \
                    and "metrics_min" in frameData \
                        and self.record \
                            and not frameData.dryRun:
            metrics: dict = frameData["metrics"]
            metricsMin: dict = frameData["metrics_min"]
            metricsMax: dict = frameData["metrics_max"]

            for key in metrics:
                if key not in self.metricsData:
                    self.metricsData[key] = []

                d = {}
                d["value"] = metrics[key]
                if key in metricsMin:
                    d["min"] = metricsMin[key]
                if key in metricsMax:
                    d["max"] = metricsMax[key]
                    
                self.metricsData[key].append(d)
        
        self.next(frameData)

    def __str__(self) -> str:
        return "Metrics Exporter"