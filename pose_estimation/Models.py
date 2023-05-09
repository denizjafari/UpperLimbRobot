import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import mediapipe.python.solutions.pose as mp_pose
from PySide6.QtGui import QImage

MARKER_RADIUS = 3

MARKER_CONFIDENCE_THRESHOLD = 0.3

class DisplayOptions:
    mirror: bool
    showSkeleton: bool
    markerRadius: int
    confidenceThreshold: float

    def __init__(self, mirror=False,
                 showSkeleton=False,
                 confidenceThreshold=MARKER_CONFIDENCE_THRESHOLD,
                 markerRadius=MARKER_RADIUS) -> None:
        self.mirror = mirror
        self.showSkeleton = showSkeleton
        self.markerRadius = markerRadius
        self.confidenceThreshold = confidenceThreshold


class DetectionResult:
    input_image: QImage
    image_arr: np.ndarray
    keypoints: np.ndarray

    def __init__(self, image: QImage, image_arr: np.ndarray, keypoints: np.ndarray) -> None:
        self.input_image = image
        self.image_arr = image_arr
        self.keypoints = keypoints
    
    def draw_keypoints(self, arr: np.ndarray,
                        markerRadius=MARKER_RADIUS,
                        confidenceThreshold=MARKER_CONFIDENCE_THRESHOLD) -> None:
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


    def toImage(self, displayOptions=DisplayOptions()) -> QImage:
        image_size = max(self.input_image.width(), self.input_image.height())
        image = tf.image.resize(self.image_arr, tf.constant([image_size, image_size]))
        image = tf.squeeze(image)
        padding = [[0, 0], [0, 0], [0, 1]]
        image = tf.pad(image, padding, constant_values=255)
        arr = image.numpy()

        if displayOptions.showSkeleton:
            self.draw_keypoints(arr,
                                markerRadius=displayOptions.markerRadius,
                                confidenceThreshold=displayOptions.confidenceThreshold)

        buffer = arr.astype(np.uint8).tobytes()

        image = QImage(buffer, 640, 640, QImage.Format.Format_RGB32)

        return image


class PoseModel:
    def detect(self, image: QImage) -> DetectionResult:
        raise NotImplementedError


class MoveNetLightning(PoseModel):
    def __init__(self) -> None:
        module = hub.load("https://tfhub.dev/google/movenet/singlepose/lightning/4")
        self.inputSize = 192
        self.movenet = module.signatures['serving_default']
            

    def detect(self, image: QImage) -> DetectionResult:
        image_arr = np.array(image.bits()).reshape(1, image.height(), image.width(), 4)
        image_arr = np.delete(image_arr, np.s_[-1:], axis=3)
        image_arr = tf.image.resize_with_pad(image_arr, self.inputSize, self.inputSize)
        image_arr = tf.cast(image_arr, dtype=np.int32)

        output = self.movenet(image_arr)["output_0"].numpy()[0][0]

        return DetectionResult(image, image_arr.numpy())
    

class MoveNetThunder(PoseModel):
    def __init__(self) -> None:
        module = hub.load("https://tfhub.dev/google/movenet/singlepose/thunder/4")
        self.inputSize = 256
        self.movenet = module.signatures['serving_default']
            

    def detect(self, image: QImage) -> None:
        image_arr = np.array(image.bits()).reshape(1, image.height(), image.width(), 4)
        image_arr = np.delete(image_arr, np.s_[-1:], axis=3)
        image_arr = tf.image.resize_with_pad(image_arr, self.inputSize, self.inputSize)
        image_arr = tf.cast(image_arr, dtype=np.int32)

        output = self.movenet(image_arr)["output_0"].numpy()[0][0]

        return DetectionResult(image, image_arr.numpy(), output)
    

class BlazePose(PoseModel):
    def __init__(self) -> None:
        self.blazePose = mp_pose.Pose(min_detection_confidence=0.5,
                     min_tracking_confidence=0.5,
                     static_image_mode=False)
        self.inputSize = 256
    
    def detect(self, image: QImage) -> DetectionResult:
        image_arr = np.array(image.bits()).reshape(1, image.height(), image.width(), 4)
        image_arr = np.delete(image_arr, np.s_[-1:], axis=3)
        image_arr = tf.image.resize_with_pad(image_arr, self.inputSize, self.inputSize)
        image_arr = tf.squeeze(image_arr)
        image_arr = tf.cast(image_arr, dtype=np.uint8).numpy()

        output = self.blazePose.process(image_arr).pose_landmarks

        if output is not None:
            output = output.landmark
            result = [(output[i].y, output[i].x, output[i].visibility) for i in range(33)]
        else:
            result = []

        return DetectionResult(image, image_arr, result)
