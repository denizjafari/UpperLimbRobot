"""
Machine Learning models used for pose estimation. Includes full support for the
MediaPipe BlazePose model and partial support for MoveNet. A model inteface is
provided alongside an interface for keypoint sets.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe as mp
import mediapipe.python.solutions.pose as mp_pose
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

VisionRunningMode = mp.tasks.vision.RunningMode

from pose_estimation.Models import KeypointSet, PoseModel, SimpleKeypointSet

from app.resource_management.registry import REGISTRY    

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
            if isinstance(output[0], list):
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
        
        def getRightWrist(self) -> list[float]:
            return self.getKeypoints()[16]
        
        def getLeftWrist(self) -> list[float]:
            return self.getKeypoints()[15]
        
class BlazePoseHeavy(PoseModel):
    """
    New (?) version of the BlazePose Model from MediaPipe in Heavy flavour.
    """
    def __init__(self) -> None:
        file = open("pose_landmarker_heavy.task", "rb")
        base_options = python.BaseOptions(model_asset_buffer=file.read())
        file.close()
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=True)
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.inputSize = 224

    def detect(self, image: np.ndarray) -> KeypointSet:
        image = tf.image.resize(image, (self.inputSize, self.inputSize))
        image = tf.cast(image, dtype=np.uint8).numpy()
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)

        output = self.detector.detect(image).pose_landmarks

        if len(output) > 0:
            result = BlazePose.KeypointSet(output[0])
        else:
            result = SimpleKeypointSet([], [])

        return result
    
class BlazePoseLite(PoseModel):
    """
    New (?) version of the BlazePose Model from MediaPipe in Lite flavour.
    """
    def __init__(self) -> None:
        file = open("pose_landmarker_lite.task", "rb")
        base_options = python.BaseOptions(model_asset_buffer=file.read())
        file.close()
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=VisionRunningMode.VIDEO)
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.inputSize = 224
        self.timeline = 0

    def detect(self, image: np.ndarray) -> KeypointSet:
        image = tf.image.resize(image, (self.inputSize, self.inputSize))
        image = tf.cast(image, dtype=np.uint8).numpy()
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)

        output = self.detector.detect_for_video(image, self.timeline).pose_landmarks
        self.timeline += 50

        if len(output) > 0:
            result = BlazePose.KeypointSet(output[0])
        else:
            result = SimpleKeypointSet([], [])

        return result
        
    
class FeedThroughModel(PoseModel):
    def detect(self, image: np.ndarray) -> KeypointSet:
        """
        Do nothing and return the input as the result
        """
        return SimpleKeypointSet([], [])
    
    def __str__(self) -> str:
        return "None"


REGISTRY.register(FeedThroughModel, "models.None")
REGISTRY.register(BlazePose, "models.BlazePose")
#REGISTRY.register(BlazePoseHeavy, "models.BlazePose (Heavy)")
#REGISTRY.register(BlazePoseLite, "models.BlazePose (Lite)")
#REGISTRY.register(MoveNetLightning, "models.MoveNet (Lightning)")
