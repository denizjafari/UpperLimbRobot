# UpperLimbRobot

## Project Overview

This framework integrates various pose tracking models into one application.
It comes with an easy-to-use user interface allowing detailed configuration.
In the future, interactive games for rehabilitation will be built using it.


## Technological Overview

The framework is programmed in Python, since most important pose analysis models
offer bindings for Python. The Qt framework is used with the PySide 6 bindings
for Python is used to build the user interface.


## Framework details

### Models
The integration and testing of multiple pose tracking models lies at the core
of the framework. There is an interface for models in Models.py which allows
more pose tracking models to be added in the future. The interface includes
the main detection step along with definitions which landmarks should be
connected to draw skeletons.

### Transformers and the Pipeline
To allow seamless integration of models an visualization steps, so-called
transformers are used (not the ML concept of transformers). Each transformer
should perform one transformation step taking an image, detected keypoints
and metadata from an original state to a transformed state. There are
transformers which flip (mirror) the image, rescale it, draw keypoints as
landmarks, or draw the skeleton on the image. More special transformers wrap
models to detect keypoints on the fly, provide a video feed from a camera or
file, or record the output to a file. For each transformer, a related
transformer widget should exist, which allows to add and modify a transformer
through the user interface.

Transformers can be arranged in a pipeline, so that they can be run on streams
of frames from a video.
