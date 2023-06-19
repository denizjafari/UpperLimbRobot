"""
Entry point for the modular pose processor application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

import logging
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    app = QApplication(sys.argv)
    window = ModularPoseProcessorWidget()
    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.setWindowTitle("Modular Pose Processor")
    window.show()

    module_logger.info("Ready")

    sys.exit(app.exec())