import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QThreadPool
from pose_estimation.Models import BlazePose, FeedThroughModel, ModelManager
from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget


if __name__ == "__main__":
    app = QApplication(sys.argv)

    threadpool = QThreadPool.globalInstance()
    modelManager = ModelManager([FeedThroughModel, BlazePose], threadpool)
    window = ModularPoseProcessorWidget(modelManager)

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
