from __future__ import annotations
from typing import Optional

import time

from .utils import FrameData

class ITransformer:
    """
    Interface that is implemented by all transformers. A transformer makes
    modifications to images, the landmarks, and/or metadata in the pipeline.
    These transformers can be layered like neural networks, by wrapping
    previous layers in later layers.
    """
    _isActive: bool
    _next: Optional[ITransformer]

    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[ITransformer] = None) -> None:
        """
        Initialize this transformer by setting whether it is active and
        optionally setting the next transformer in the chain.
        """
        self._isActive = isActive
        self._next = None if previous is None else previous._next

    def active(self) -> bool:
        """
        Return whether this transformer is active or not.
        """
        return self._isActive
    
    def setActive(self, isActive: bool) -> None:
        """
        Set whether this transformer is active or not.
        """
        self._isActive = isActive

    def next(self, frameData: FrameData) -> None:
        """
        Run the next stage in the pipeline. First acquire the lock of the next
        stage before unlocking this stage.
        """
        if "timings" not in frameData:
            frameData["timings"] = []

        frameData["timings"].append((str(self), time.time()))
        if self._next is not None:
            self._next.flowLock()
        self.flowUnlock()
        if self._next is not None:
            self._next.transform(frameData)

    def flowLock(self) -> None:
        """
        Lock this stage (or only the first part of it) to multithreading.
        """
        raise NotImplementedError

    def flowUnlock(self) -> None:
        """
        Unlock this stage (or only the first part of it) to multithreading.
        """
        raise NotImplementedError
    
    def recursiveLock(self) -> None:
        """
        Recursively lock all lower stages.
        """
        raise NotImplementedError
    
    def recursiveUnlock(self) -> None:
        """
        Recursively unlock all lower stages.
        """
        raise NotImplementedError

    def transform(self, frameData: FrameData) -> None:
        """
        Transform the input image. This occurs in place.
        """
        self.next(frameData)
    
    def setNextTransformer(self,
                           nextTransformer: Optional[ITransformer]) -> None:
        """
        Changes the next transformer in the pipeline.

        nextTransformer - the next transformer, can be None to make the
        pipeline end with this transformer
        """
        self._next = nextTransformer
    
    def getNextTransformer(self) -> None:
        """
        Get the transformer that comes after this one in the pipeline.
        """
        return self._next