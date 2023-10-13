import numpy as np

import app.keypoint_sets.IKeyPointSet as IKeypointSet

class IModel:
    """
    Abstract class to allow models to be exchanged easily.
    """
    def detect(self, image: np.ndarray) -> IKeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        raise NotImplementedError

    def key(self) -> str:
        return self._key
    
    def setKey(self, key: str) -> None:
        self._key = key

    def __str__(self) -> None:
        return self._key