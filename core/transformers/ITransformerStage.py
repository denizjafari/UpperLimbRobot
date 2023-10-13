from typing import Optional

from PySide6.QtCore import QMutex
from .ITransformer import ITransformer


class ITransformerStage(ITransformer):
    """
    One stage in a pipeline that can only be entered by one thread at a time.
    """
    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initilialize the stage.
        """
        ITransformer.__init__(self, isActive, previous)

        self._mutex = QMutex()

    def flowLock(self) -> None:
        """
        Lock the stage. Now, no other thread can enter this stage.
        """
        self._mutex.lock()

    def flowUnlock(self) -> None:
        """
        Unlock the stage. Allow other threads to enter this stage.
        """
        self._mutex.unlock()

    def recursiveLock(self) -> None:
        """
        Lock the stage. Now, no other thread can enter this stage.
        """
        self.flowLock()

    def recursiveUnlock(self) -> None:
        """
        Unlock the stage. Allow other threads to enter this stage.
        """
        self.flowUnlock()