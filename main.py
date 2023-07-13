"""
Entry point for the modular pose processor application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import logging
import sys
import os
import json
import importlib

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

def importFrom(dir):
    """
    Import all modules from a directory relative to the script's location.
    """
    basePath = os.path.dirname(__file__)
    basePath = basePath + "/" if basePath != "" else ""
    path = basePath + dir
    module_logger.info("Importing from " + path)
    for module in os.listdir(path):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        importlib.import_module(dir + "." + module[:-3])

def save(window: ModularPoseProcessorWidget):
    """
    Save the window to the state.json data file.
    """
    state = {}
    state["modular_pose_processor_widget"] = {}
    window.save(state["modular_pose_processor_widget"])
    with open("state.json", "w") as file:
        json.dump(state, file, indent=2)
        module_logger.debug("Saved state of modular_pose_processor_widget")

def restore(window: ModularPoseProcessorWidget):
    """
    Restore the window from the state.json data file.
    """
    state = {}
    try:
        with open("state.json") as file:
            state = json.load(file)
    except FileNotFoundError:
        state = {}

    if "modular_pose_processor_widget" in state:
        window.restore(state["modular_pose_processor_widget"])
        module_logger.debug("Restored state of modular_pose_processor_widget")


if __name__ == "__main__":
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(loggingHandler)

    importFrom("widgets")
    importFrom("models")

    app = QApplication(sys.argv)
    window = ModularPoseProcessorWidget()
    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.setWindowTitle("Modular Pose Processor")
    window.show()

    restore(window)
    module_logger.info("Ready")

    code = app.exec()
    save(window)

    sys.exit(code)
    