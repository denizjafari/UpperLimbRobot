import numpy as np
import tensorflow as tf
import tensorflow_hub as hub

from core.models.IModel import IModel
from core.keypoint_sets.IKeyPointSet import IKeypointSet
from core.keypoint_sets.SimpleyKeypointSet import SimpleKeypointSet


class MoveNetLightning(IModel):
    """
    The MoveNet Model in lightning flavor.
    """
    def __init__(self) -> None:
        """
        Initialize the model by loading it from tensorflow hub.
        """
        module = hub.load("https://tfhub.dev/google/movenet/singlepose/lightning/4")
        self.inputSize = 192
        self.movenet = module.signatures['serving_default']
            

    def detect(self, image: np.ndarray) -> IKeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize(image, (self.inputSize, self.inputSize))
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0, 0].tolist()

        return SimpleKeypointSet(output, [])
    
    def __str__(self) -> str:
        return "MoveNet (Lightning)"
    

class MoveNetThunder(IModel):
    """
    The MoveNet Model in thunder flavor.
    """
    def __init__(self) -> None:
        """
        Initialize the model by loading it from tensorflow hub.
        """
        module = hub.load("https://tfhub.dev/google/movenet/singlepose/thunder/4")
        self.inputSize = 256
        self.movenet = module.signatures['serving_default']
            

    def detect(self, image: np.ndarray) -> IKeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize(image, (self.inputSize, self.inputSize))
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0, 0].tolist()

        return SimpleKeypointSet(output, [])
    
    def __str__(self) -> str:
        return "MoveNet (Thunder)"