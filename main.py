import sys
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import Qt, QThreadPool
from pose_estimation.Models import BlazePose, FeedThroughModel, ModelManager
from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget
from pose_estimation.pose_reprocessing import PoseReprocessingWidget
from pose_estimation.video import QVideoSource


if __name__ == "__main__":
    app = QApplication(sys.argv)

    threadpool = QThreadPool.globalInstance()
    modelManager = ModelManager([FeedThroughModel, BlazePose], threadpool)

    window = QTabWidget()

    modularWindow = ModularPoseProcessorWidget(modelManager, window)
    window.addTab(modularWindow, "Modular Pose Processing")

    reprocessWindow = PoseReprocessingWidget(modelManager, threadpool)
    window.addTab(reprocessWindow, "Pose Reprocessing")

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
