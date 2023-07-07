"""
Entry point for the modular pose processor application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import logging
import sys
import os
import json

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

def import_from(dir):
    basePath = os.path.dirname(__file__)
    basePath = basePath + "/" if basePath != "" else ""
    path = basePath + dir
    module_logger.info("Importing from " + path)
    for module in os.listdir(path):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        __import__(dir + "." + module[:-3], locals(), globals())

def save():
    state = {}
    state["modular_pose_processor_widget"] = {}
    window.save(state["modular_pose_processor_widget"])
    with open("state.json", "w") as file:
        json.dump(state, file, indent=4)

def restore():
    state = {}
    try:
        with open("state.json") as file:
            state = json.load(file)
    except FileNotFoundError:
        pass
    if "modular_pose_processor_widget" in state:
        window.restore(state["modular_pose_processor_widget"])


if __name__ == "__main__":
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(loggingHandler)

    import_from("widgets")
    import_from("models")

    app = QApplication(sys.argv)
    window = ModularPoseProcessorWidget(save)
    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.setWindowTitle("Modular Pose Processor")
    window.show()

    restore()

    module_logger.info("Ready")

    code = app.exec()
    sys.exit(code)
    