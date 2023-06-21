"""
Entry point for the modular pose processor application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import logging
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

def import_from(dir):
    for module in os.listdir(os.path.dirname(__file__) + "/" + dir):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        __import__(dir + "." + module[:-3], locals(), globals())

if __name__ == "__main__":
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(loggingHandler)

    import_from("widgets")
    import_from("models")

    app = QApplication(sys.argv)
    window = ModularPoseProcessorWidget()
    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.setWindowTitle("Modular Pose Processor")
    window.show()

    module_logger.info("Ready")

    sys.exit(app.exec())
    