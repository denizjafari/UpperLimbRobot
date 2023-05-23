from PySide6.QtCore import QRunnable, QObject, Signal, Slot, QThreadPool
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe.python.solutions.pose as mp_pose

class KeypointSet:
    """
    A set to store all keypoint sets recognized from a model / imported.
    """

    def getKeypoints(self) -> list[list[float]]:
        """
        Returns the underlying modifiable list of keypoints
        """
        raise NotImplementedError
    

    def getSkeletonLines(self) -> list[list[int]]:
        """
        Returns a list of skeleton lines. A skeleton line is a sequence
        of indices into the keypoint list that indicates in which order the
        indexed keypoints should be connected.
        """
        raise NotImplementedError
    
    def getLeftShoulder(self) -> list[float]:
        """
        Return the coordinates and confidence for the left shoulder.
        """
        raise NotImplementedError

    def getRightShoulder(self) -> list[float]:
        """
        Return the coordinates and confidence for the right shoulder.
        """
        raise NotImplementedError

class PoseModel:
    """
    Abstract class to allow models to be exchanged easily.
    """
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        raise NotImplementedError  

class SimpleKeypointSet(KeypointSet):
    keypoints: list[list[float]]
    skeletonLines: list[list[int]]

    def __init__(self, keypoints: list[list[float]], skeletonLines: list[list[int]]) -> None:
        self.keypoints = keypoints
        self.skeletonLines = skeletonLines

    def getKeypoints(self) -> list[list[float]]:
        return self.keypoints
    
    def getSkeletonLines(self) -> list[list[int]]:
        return self.skeletonLines
    
    def getLeftShoulder(self) -> list[float]:
        return [0.0, 0.0, 0.0]
    
    def getRightShoulder(self) -> list[float]:
        return [0.0, 0.0, 0.0]
    

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
            

    def detect(self, image: np.ndarray) -> KeypointSet:
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
            

    def detect(self, image: np.ndarray) -> KeypointSet:
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
    

class BlazePose(PoseModel):
    """
    The BlazePose Model from MediaPipe in Full flavor.
    """

    def __init__(self) -> None:
        self.blazePose = mp_pose.Pose(min_detection_confidence=0.5,
                     min_tracking_confidence=0.5,
                     static_image_mode=False)
        self.inputSize = 256
    
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.image.resize(image, (self.inputSize, self.inputSize))
        image = tf.cast(image, dtype=np.uint8).numpy()

        output = self.blazePose.process(image).pose_landmarks

        if output is not None:
            output = output.landmark
            result = BlazePose.KeypointSet(output)
        else:
            result = SimpleKeypointSet([], [])

        return result
    
    def __str__(self) -> str:
        return "BlazePose"
    
    class KeypointSet(KeypointSet):
        keypoints: list[list[float]]

        def __init__(self, output) -> None:
            if isinstance(output, list):
                self.keypoints = output
            else:
                self.keypoints = [
                    [output[i].y, output[i].x, output[i].visibility]
                    for i in range(33)
                    ]

        def getKeypoints(self) -> list[list[float]]:
            return self.keypoints
        
        def getSkeletonLines(self) -> list[list[int]]:
            return [
                [8, 6, 5, 4, 0, 1, 2, 3, 7],
                [9, 10],
                [21, 15, 17, 19, 15, 13, 11, 23, 25, 27, 31, 29, 27],
                [22, 16, 18, 20, 16, 14, 12, 24, 26, 28, 32, 30],
                [11, 12],
                [23, 24],
            ]
        
        def getLeftShoulder(self) -> list[float]:
            return self.getKeypoints()[11]
        
        def getRightShoulder(self) -> list[float]:
            return self.getKeypoints()[12]
    
class FeedThroughModel(PoseModel):
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Do nothing and return the input as the result
        """
        return SimpleKeypointSet([], [])
    
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

class ModelManager(QObject):
    """
    A class to instantiate a predefined set of models.
    """
    modelAdded = Signal(PoseModel)

    models: list[PoseModel]
    threadpool: QThreadPool

    def __init__(self, models: list[type], threadpool=QThreadPool()) -> None:
        QObject.__init__(self)

        self.threadPool = threadpool
        self.models = []

        for modelClass in models:
            loader = ModelLoader(modelClass)
            loader.modelReady.connect(self.modelReadySlot)
            self.threadPool.start(loader)

    @Slot(PoseModel)
    def modelReadySlot(self, model: PoseModel) -> None:
        self.models.append(model)
        self.modelAdded.emit(model)
