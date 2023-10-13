
from typing import Optional

import logging

from .ITransformer import ITransformer
from .utils import FrameData

module_logger = logging.getLogger(__name__)

class Pipeline(ITransformer):
    """
    A pipeline of transformer stages. It can act as a transformer by itself,
    but multiple threads can be in it at the same time. Only the stages the
    pipeline is made of are locked to only one thread.
    """
    transformers: list[ITransformer]

    def __init__(self,
                 isActive: bool = True,
                 previous: Optional[ITransformer] = None) -> None:
        ITransformer.__init__(self, isActive, previous)
        self.transformers = []

    def append(self, transformer: ITransformer) -> None:
        """
        Append a ITransformer to the end of the pipeline.
        """
        self.recursiveLock()

        module_logger.debug(f"Appended transformer {transformer} to the pipeline")
        if len(self.transformers) > 0:
            self.transformers[-1].setNextTransformer(transformer)
        self.transformers.append(transformer)
        transformer.setNextTransformer(self._next)

        self.recursiveUnlock()

    def remove(self, transformer: ITransformer) -> None:
        """
        Remove the given transformer from the pipeline.
        """
        self.recursiveLock()

        module_logger.debug(f"Removed transformer {transformer} from the pipeline")
        index = self.transformers.index(transformer)
        if index > 0:
            self.transformers[index - 1].setNextTransformer(transformer.getNextTransformer())
        if len(self.transformers) == 1:
            # There is no other transformer to work with
            self._next = transformer.getNextTransformer()
        transformer.setNextTransformer(None)
        self.transformers.pop(index)

        self.recursiveUnlock()

    def setNextTransformer(self, nextTransformer: Optional[ITransformer]) -> None:
        """
        Set the transformer that should be run after the pipeline is completed.
        """
        super().setNextTransformer(nextTransformer)
        if len(self.transformers) > 0:
            self.transformers[-1].setNextTransformer(nextTransformer)

    def getNextITransformer(self) -> Optional[ITransformer]:
        """
        Get the transformer that is run after the pipeline is completed.
        """
        return self._next

    def start(self, frameData: FrameData) -> None:
        """
        Stat the pipeline by locking the first stage and beginning
        transformation.
        """
        self.flowLock()
        self.transform(frameData)

    def flowLock(self) -> None:
        """
        Lock the first stage in the pipeline.
        """
        if len(self.transformers) > 0:
            self.transformers[0].flowLock()

    def flowUnlock(self) -> None:
        """
        Do nothing. Unlocking the first stage is done by the first stage itself
        upon completion of its transformation.
        """
        pass

    def recursiveLock(self) -> None:
        """
        Lock all stages in the pipeline.
        """
        for t in self.transformers:
            t.recursiveLock()

    def recursiveUnlock(self) -> None:
        """
        Unlock all stages in the pipeline.
        """
        for t in self.transformers:
            t.recursiveUnlock()

    def next(self, frameData: FrameData) -> None:
        """
        If the next transformer is defined, run it.
        """
        nextTransformer = self.getNextITransformer()
        if nextTransformer is not None:
            nextTransformer.flowLock()
            nextTransformer.transform(frameData)
    
    def transform(self, frameData: FrameData) -> None:
        """
        Start transformation with the frst transformer in the pipeline.
        """
        if self.active() and len(self.transformers) > 0:
            self.transformers[0].transform(frameData)
        else:
            self.next(frameData)