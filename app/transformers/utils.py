from typing import Optional

import numpy as np

from app.ui.metric_widgets import MetricWidget
from app.keypoint_sets.IKeyPointSet import IKeypointSet

class FrameData:
    """
    Contains image, keypoints and metadata to pass between transformers.
    This object is passed between transformers in the pipeline. The state
    of one frame data object should never directly affect the state of
    another frame data object. All persistence or tracking of data should
    occur in the transfomers themselves, or in UI Widgets.

    dryRun - whether this run is a dry run. If true, no complex processing
    should take place. Instead, format changes like image resolution
    adjustments should take place.
    _width - the width of the proprosed image if the image is None.
    _height - the height of the proposed image if the image is None.

    streamEnded - whether the stream of frames is ended.
    image - the image/frame that should be processed (if it exists).
    keypointSets - a list of all detected keypointSets.
    """
    dryRun: bool
    _width: int
    _height: int

    streamEnded: bool
    metrics: dict[str, MetricWidget]
    image: Optional[np.ndarray]
    keypointSets: list[IKeypointSet]

    def __init__(self,
                 width: int = -1,
                 height: int = -1,
                 dryRun: bool = False,
                 image: Optional[np.ndarray] = None,
                 streamEnded: bool = False,
                 frameRate: int = -1,
                 keypointSets: Optional[list[IKeypointSet]] = None):
        """
        Initialize the FrameData object.
        """
        self.dryRun = dryRun
        self.image = image
        self._width = width
        self._height = height
        self.frameRate = frameRate
        self.streamEnded = streamEnded
        self.keypointSets = keypointSets if keypointSets is not None else []
        self._additional = {}

    def width(self) -> int:
        """
        Determine the width of the (proposed) image.
        """
        if self.image is not None:
            return self.image.shape[1]
        else:
            return self._width
        
    def height(self) -> int:
        """
        Determine the height of the (proposed) image.
        """
        if self.image is not None:
            return self.image.shape[0]
        else:
            return self._width

    def setWidth(self, width) -> None:
        """
        If the image is None, set the proposed image width.
        """
        self._width = width
    
    def setHeight(self, height) -> None:
        """
        If the image is None, set the proposed image height.
        """
        self._height = height

    def __getitem__(self, key: str) -> object:
        """
        Get the value for a key in the additional dictionary.
        """
        return self._additional[key]

    def __setitem__(self, key: str, val: object) -> None:
        """
        Set the value for a key in the additional dictionary.
        """
        self._additional[key] = val

    def __contains__(self, key: str) -> bool:
        """
        Check if a key is in the additional dictionary.
        """
        return key in self._additional