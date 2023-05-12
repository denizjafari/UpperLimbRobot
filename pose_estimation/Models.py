from PySide6.QtCore import QRunnable, QObject, Signal, Slot
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe.python.solutions.pose as mp_pose


class PoseModel:
    """
    Abstract class to allow models to be exchanged easily.
    """
    def detect(self, image: np.ndarray) -> tuple[np.ndarray, list[list[float]]]:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        raise NotImplementedError
    

class MoveNetLightning(PoseModel):
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
            

    def detect(self, image: np.ndarray) -> tuple[np.ndarray, list[list[float]]]:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize_with_pad(image, self.inputSize, self.inputSize)
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0, 0].tolist()

        image = tf.squeeze(image).numpy()

        return image, output
    
    def __str__(self) -> str:
        return "MoveNet (Lightning)"
    

class MoveNetThunder(PoseModel):
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
            

    def detect(self, image: np.ndarray) -> tuple[np.ndarray, list[list[float]]]:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize_with_pad(image, self.inputSize, self.inputSize)
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0, 0].tolist()

        image = tf.squeeze(image).numpy()

        return image, output
    
    def __str__(self) -> str:
        return "MoveNet (Thunder)"
    

class BlazePose(PoseModel):
    """
    The BlazePose Model from MediaPipe in Full flavor.
    """

    def __init__(self) -> None:
        self.blazePose = mp_pose.Pose(min_detection_confidence=0.5,
                     min_tracking_confidence=0.5,
                     static_image_mode=False)
        self.inputSize = 256
    
    def detect(self, image: np.ndarray) -> tuple[np.ndarray, list[list[float]]]:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.image.resize_with_pad(image, self.inputSize, self.inputSize)
        image = tf.cast(image, dtype=np.uint8).numpy()

        output = self.blazePose.process(image).pose_landmarks


        if output is not None:
            output = output.landmark
            result = [[output[i].y, output[i].x, output[i].visibility] for i in range(33)]
        else:
            result = []

        return image, result
    
    def __str__(self) -> str:
        return "BlazePose"
    
class FeedThroughModel(PoseModel):
    def detect(self, image: np.ndarray) -> tuple[np.ndarray, list[list[float]]]:
        """
        Do nothing and return the input as the result
        """
        return image, []
    
    def __str__(self) -> str:
        return "None"
    

class ModelLoader(QRunnable, QObject):
    """
    A class that can instantiate a single model.

    modelReady - signal that is sent when the model is ready
    modelClass - the class of the model that should be instantiated
    """
    modelReady = Signal(PoseModel)
    modelClass: type

    def __init__(self, modelClass: type) -> None:
        """
        Initialize the loader with the model class to load.
        """
        QRunnable.__init__(self)
        QObject.__init__(self)

        self.modelClass = modelClass

    @Slot()
    def run(self) -> None:
        """
        Instantiate the model and emit the result.
        """
        self.modelReady.emit(self.modelClass())
