
from __future__ import annotations
from typing import Optional

import logging
import importlib
import time

from PySide6.QtCore import QRunnable, QObject, Signal
from .ITransformer import ITransformer
from .utils import FrameData

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

try:
    pydevd = importlib.import_module("pydevd")
except ModuleNotFoundError:
    pydevd = None
    module_logger.debug("Multi threaded debugging not enabled")

class TransformerRunner(QRunnable, QObject):
    """
    Runs the transformer and emits a signal when the next thread can start
    execution.
    """
    transformerStarted = Signal(FrameData)
    transformerCompleted = Signal(FrameData)
    _transformer: ITransformer

    def __init__(self, transformer: ITransformer, frameData: Optional[FrameData] = None) -> None:
        """
        Initialize the Runner with the transformer it should execute.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)
        if frameData is None:
            frameData = FrameData()
        self._transformer = transformer
        self.frameData = frameData

    def run(self) -> None:
        """
        Acquire the lock of the transformer. As soon as the lock could be acquired,
        the stage cleared signal is emitted and the first transformer stage starts
        executing.
        """
        if pydevd is not None:
            pydevd.settrace(suspend=False)
            self.transform()
        else:
            try:
                self.transform()
            except Exception as e:
                module_logger.exception(e)

    def transform(self) -> None:
        self.frameData["timings"] = [("Start", time.time())]
        self._transformer.flowLock()
        self.transformerStarted.emit(self.frameData)
        self._transformer.transform(self.frameData)
        self.transformerCompleted.emit(self.frameData)