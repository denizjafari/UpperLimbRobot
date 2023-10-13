
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QThreadPool
from .ITransformer import ITransformer
from .TransformerRunner import TransformerRunner


class TransformerHead:
    """
    The Transformer head managing the creation of new runners for the
    transformer.
    """
    _isRunning: bool
    _transformer: ITransformer
    _threadingModel: MultiThreading

    class MultiThreading(Enum):
        """
        How the transformers use multiple threads.
        PER_FRAME - one thread processes the frame from beginning to end
        before another thread is spawned.
        PER_STAGE - one thread is spawned every time there is an empty stage.
        """
        PER_FRAME = 0
        PER_STAGE = 1

    def __init__(self,
                 transformer: ITransformer,
                 threadingModel: MultiThreading = MultiThreading.PER_FRAME,
                 qThreadPool: QThreadPool = QThreadPool.globalInstance()) -> None:
        """
        Initialize the TransformerHead.
        """
        self._transformer = transformer
        self._isRunning = False
        self._qThreadPool = qThreadPool
        self._threadingModel = threadingModel

    def start(self) -> None:
        """
        Start execution of the transformer
        """
        self._isRunning = True
        self.startNext()
    
    def stop(self) -> None:
        """
        Stop execution of the transformer. This stops the creation of new
        runners. Existing runners will continue to run until completion, however.
        """
        self._isRunning = False

    def isRunning(self) -> bool:
        """
        Return whether this transformer head is running or in a pause.
        """
        return self._isRunning
    
    def threadingModel(self) -> MultiThreading:
        """
        Return the threading model that is used.
        """
        return self._threadingModel
    
    def setThreadingModel(self, threadingModel: MultiThreading) -> MultiThreading:
        """
        Set the threshold model
        """
        self._threadingModel = threadingModel

    def onStageCleared(self) -> None:
        """
        Called when the first stage in the transformer is cleared.
        The next transformer will be run if the threading model is per stage
        and the execution has not been stopped.
        """
        if self._isRunning \
            and self.threadingModel() \
                == TransformerHead.MultiThreading.PER_STAGE:
            self.startNext()

    def onTransformCompleted(self) -> None:
        """
        Called when the transformer is completed.
        The next transformer will be run if the threading model is per frame
        and the execution has not been stopped.
        """
        if self._isRunning \
            and self.threadingModel() \
                == TransformerHead.MultiThreading.PER_FRAME:
            self.startNext()

    def startNext(self) -> None:
        """
        Start the next TransformerRunner and connect to its signals.
        """
        runner = TransformerRunner(self._transformer)
        runner.transformerStarted.connect(self.onStageCleared)
        runner.transformerCompleted.connect(self.onTransformCompleted)
        self._qThreadPool.start(runner)