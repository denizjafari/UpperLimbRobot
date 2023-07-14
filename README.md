# UpperLimbRobot

## Project Overview

This framework integrates various pose tracking models into one application.
It comes with an easy-to-use user interface allowing detailed configuration.
In the future, interactive games for rehabilitation will be built using it.


## Technological Overview

The framework is programmed in Python, since most important pose analysis models
offer bindings for Python. The Qt framework with the PySide 6 bindings
for Python is used to build the user interface.


## Setup
### Prerequisites
- Conda
- Python 3.9

### Installation
1. Clone the repository to your local machine.
2. Create a new conda environment with Python 3.9.
3. Activate the environment.
4. Install the requirements with `pip install -r requirements.txt`.


## Games
The framework comes with a few games that can be played using the pose tracking
models. The games are implemented in the game_hosts directory. The game_host.py
is a separate application and serves as the entry point into the games. Interaction
between the pose tracking software and the game is done through a TCP connection.
This allows people to join from a different device altogether.


### Pong Example
To play pong, the following Transformers need to be selected:
CameraSource > Model > Min/Max Selector > Pong Game

Select the camera source and the model. Then press "Start" to start the
tracking. Update the metrics in the Min/Max Selector. Then select the left hand
elevtion. Raise your hand as high as you can and press to select the max.
Then reach to the bottom and press min. Then you can press "Connect" in the
Pong Game Widget to connect to the paddle in the pong application.

In the pong application, you can "Toggle" to start the game. The right paddle
is controlled by the up and down keys, the left paddle is controlled by your left
arm (or alternatively with the W and S keys). After losing a game, you can "Reset"
the game to start again.


## Framework details

### Directory Structure
The entrypoint into the application is main.py. Core components are in the
pose_estimation directory. This includes interfaces that can be used for
extensions. Extensions can be found in the models and widgets directories.
You can add your own extensions by creating new files in these two directories.
This includes widgets making use of custom transformers and models. Just register
them with the registries exported by registry.py.

### Models
The integration and testing of multiple pose tracking models lies at the core
of the framework. There is an interface for models in Models.py which allows
more pose tracking models to be added in the future. The interface includes
the main detection step along with definitions which landmarks should be
connected to draw skeletons. A keypoint is a four-tuple (y, x, z, confidence).
Commonly used keypoints can be accessed through the interface, for a seamless
transition between all the models.

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
of frames from a video. Pipelines itself can also be part of a bigger pipeline,
allowing endless ways to compose transformers.

Core transformers are provided in transforms.py. They are usable in the application
in conjunction with their respective widgets from tranformer_widgets.py.
