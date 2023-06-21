"""
Machine Learning models used for pose estimation. Includes full support for the
MediaPipe BlazePose model and partial support for MoveNet. A model inteface is
provided alongside an interface for keypoint sets.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe.python.solutions.pose as mp_pose

from PySide6.QtCore import QRunnable, QObject, Signal, Slot
from pose_estimation.Models import KeypointSet, PoseModel, SimpleKeypointSet

from pose_estimation.registry import MODEL_REGISTRY    

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
                    [output[i].y, output[i].x, output[i].z, output[i].visibility]
                    for i in range(33)
                    ]

        def getKeypoints(self) -> list[list[float]]:
            return self.keypoints
        
        def getSkeletonLinesBody(self) -> list[list[int]]:
            return [
                [21, 15, 17, 19, 15, 13, 11, 23, 25, 27, 31, 29, 27],
                [22, 16, 18, 20, 16, 14, 12, 24, 26, 28, 32, 30],
                [11, 12],
                [23, 24],
            ]
        
        def getSkeletonLinesFace(self) -> list[list[int]]:
            return [[8, 6, 5, 4, 0, 1, 2, 3, 7], [9, 10]]
        
        def getLeftShoulder(self) -> list[float]:
            return self.getKeypoints()[11]
        
        def getRightShoulder(self) -> list[float]:
            return self.getKeypoints()[12]
        
        def getLeftElbow(self) -> list[float]:
            return self.getKeypoints()[13]
        
        def getRightElbow(self) -> list[float]:
            return self.getKeypoints()[14]
        
        def getNose(self) -> list[float]:
            return self.getKeypoints()[0]
    
class FeedThroughModel(PoseModel):
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Do nothing and return the input as the result
        """
        return SimpleKeypointSet([], [])
    
    def __str__(self) -> str:
        return "None"


MODEL_REGISTRY.register(FeedThroughModel, "None")
MODEL_REGISTRY.register(BlazePose, "BlazePose")