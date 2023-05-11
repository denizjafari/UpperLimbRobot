import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe.python.solutions.pose as mp_pose
from PySide6.QtGui import QImage

# The default radius used to draw a marker
MARKER_RADIUS = 3
# The level of confidence above which a marker is drawn
MARKER_CONFIDENCE_THRESHOLD = 0.3

class DisplayOptions:
    """
    Store and exchange the options according to which the pose is analyzed.

    mirror - whether to mirror the image. Useful for front cameras.
    showSkeleton - whether to draw the markers on the frame.
    markerRadius - the radius of the markers that are drawn to the frame.
    confidenceThreshold - the level of confidence above which a marker
                          should be drawn.
    """
    mirror: bool
    showSkeleton: bool
    markerRadius: int
    confidenceThreshold: float

    def __init__(self, mirror=False,
                 showSkeleton=False,
                 confidenceThreshold=MARKER_CONFIDENCE_THRESHOLD,
                 markerRadius=MARKER_RADIUS) -> None:
        """
        Intialize the display options.
        """
        self.mirror = mirror
        self.showSkeleton = showSkeleton
        self.markerRadius = markerRadius
        self.confidenceThreshold = confidenceThreshold


class DetectionResult:
    """
    The result that contains all relevant detection data and can synthesize
    frames for display.

    input_image - the original input in its full resolution.
    image_arr - the image in array form as it was prepared for the model.
    keypoints - a 2D array of the landmarks detected by the model.
                Each entry has the format (y, x, confidence)
                TODO: Change to (x, y, ...)
    """
    image: np.ndarray
    keypoints: np.ndarray

    def __init__(self,
                 image: np.ndarray,
                 keypoints: np.ndarray) -> None:
        """
        Intialize the detection result by creating shallow copies of all
        outputs.
        """
        self.image = image
        self.keypoints = keypoints
    
    def draw_keypoints(self,
                       arr: np.ndarray,
                       markerRadius=MARKER_RADIUS,
                       confidenceThreshold=MARKER_CONFIDENCE_THRESHOLD) -> None:
        """
        Draw the keypoints (landmarks) onto the frame given by arr.
        
        arr - the array containing the frame.
        markerRadius - the radius of the marker.
        confidenceThreshold - the threshold above which the marker should be
                              drawn.
        """
        width = arr.shape[0]
        height = arr.shape[1]

        for keypoint in self.keypoints:
            if keypoint[2] < confidenceThreshold:
                continue # Don't draw markers with low confidence values
            x = round(keypoint[0] * width)
            y = round(keypoint[1] * height)
            for xdiff in range(-markerRadius, markerRadius):
                for ydiff in range(-markerRadius, markerRadius):
                    if 0 <= x+xdiff < width and 0 <= y+ydiff < height:
                        arr[x+xdiff, y+ydiff, 0] = 255
                        arr[x+xdiff, y+ydiff, 1] = 255
                        arr[x+xdiff, y+ydiff, 2] = 255


    def toImage(self, displayOptions=DisplayOptions()) -> np.ndarray:
        """
        Transform the internal representation image_arr into a QImage sucb that
        both dimenstions are as big as the bigger one of the original image.
        """
        image_size = 640
        image = tf.image.resize(self.image, tf.constant([image_size, image_size]))
        padding = [[0, 0], [0, 0], [0, 1]]
        image = tf.pad(image, padding, constant_values=255).numpy()

        if displayOptions.showSkeleton:
            self.draw_keypoints(image,
                                markerRadius=displayOptions.markerRadius,
                                confidenceThreshold=displayOptions.confidenceThreshold)
        return image


class PoseModel:
    """
    Abstract class to allow models to be exchanged easily.
    """
    def detect(self, image: QImage) -> DetectionResult:
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
            

    def detect(self, image: np.ndarray) -> DetectionResult:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize_with_pad(image, self.inputSize, self.inputSize)
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0][0]

        image = tf.squeeze(image).numpy()

        return DetectionResult(image, output)
    

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
            

    def detect(self, image: np.ndarray) -> None:
        """
        Detect the pose in the given image. The image has to have dimensions
        (height, width, channels).

        image - the image to analyze.
        """
        image = tf.expand_dims(image, axis=0)
        image = tf.image.resize_with_pad(image, self.inputSize, self.inputSize)
        image = tf.cast(image, dtype=np.int32)

        output = self.movenet(image)["output_0"].numpy()[0][0]

        image = tf.squeeze(image).numpy()

        return DetectionResult(image, output)
    

class BlazePose(PoseModel):
    """
    The BlazePose Model from MediaPipe in Full flavor.
    """

    def __init__(self) -> None:
        self.blazePose = mp_pose.Pose(min_detection_confidence=0.5,
                     min_tracking_confidence=0.5,
                     static_image_mode=False)
        self.inputSize = 256
    
    def detect(self, image: np.ndarray) -> DetectionResult:
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
            result = [(output[i].y, output[i].x, output[i].visibility) for i in range(33)]
        else:
            result = []

        return DetectionResult(image, result)
