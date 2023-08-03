"""
Entry point for the modular pose processor application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import logging
import sys
import os
import json
import importlib
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool

from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget
from pose_estimation.profiles import UserProfile, UserProfileSelector
from pose_estimation.registry import GLOBAL_PROPS


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

    state["global_props"] = {}
    GLOBAL_PROPS.save(state["global_props"])

    path = os.path.join(userProfile.workingDir, "state.json")

    with open(path, "w") as file:
        json.dump(state, file, indent=2)
        module_logger.debug("Saved state of modular_pose_processor_widget")

def restore(window: ModularPoseProcessorWidget):
    """
    Restore the window from the state.json data file.
    """
    state = {}
    path = os.path.join(userProfile.workingDir, "state.json")
    try:
        with open(path) as file:
            state = json.load(file)
    except FileNotFoundError:
        state = {}

    if "modular_pose_processor_widget" in state:
        window.restore(state["modular_pose_processor_widget"])
        module_logger.debug("Restored state of modular_pose_processor_widget")
    
    if "global_props" in state:
        GLOBAL_PROPS.restore(state["global_props"])


def saveUsers(userProfileSelector: UserProfileSelector) -> None:
    """
    Save the user profiles to the users.json data file.
    """
    state = {}
    state["user_profiles"] = {}
    userProfileSelector.save(state["user_profiles"])

    path = os.path.join(os.getcwd(), "users.json")

    with open(path, "w") as file:
        json.dump(state, file, indent=2)
        module_logger.debug("Saved state of user_profiles")

def restoreUsers(userProfileSelector: UserProfileSelector) -> None:
    """
    Restore the user profiles from the users.json data file.
    """
    state = {}
    path = os.path.join(os.getcwd(), "users.json")
    try:
        with open(path) as file:
            state = json.load(file)
    except FileNotFoundError:
        state = {}

    if "user_profiles" in state:
        userProfileSelector.restore(state["user_profiles"])
        module_logger.debug("Restored state of user_profiles")


def onUserSelected(userProfile_: UserProfile) -> None:
    """
    Callback for when a user profile is selected.
    """
    global userProfile

    module_logger.debug(f"User {userProfile_.name} selected")
    
    modularPoseProcessor.show()
    userProfileSelector.close()
    
    userProfile = userProfile_
    GLOBAL_PROPS["WORKING_DIR"] = userProfile.workingDir

    restore(modularPoseProcessor)


if __name__ == "__main__":
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(loggingHandler)

    importFrom("widgets")
    importFrom("models")

    app = QApplication(sys.argv)

    userProfile = None
    userProfileSelector = UserProfileSelector()
    restoreUsers(userProfileSelector)
    userProfileSelector.saveRequested.connect(lambda:
                                              saveUsers(userProfileSelector))
    userProfileSelector.userSelected.connect(onUserSelected)
    userProfileSelector.show()

    modularPoseProcessor = ModularPoseProcessorWidget()
    module_logger.info("Ready")

    code = app.exec()
    if userProfile is not None:
        save(modularPoseProcessor)

    module_logger.debug("Waiting for all threads to finish")
    start = time.time()
    QThreadPool.globalInstance().waitForDone()
    elapsed = time.time() - start
    module_logger.debug(f"Threads all finished ({int(1000 * elapsed)}ms)")

    sys.exit(code)
    