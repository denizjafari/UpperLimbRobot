import sys
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import Qt, QThreadPool
from pose_estimation.Models import BlazePose, FeedThroughModel, ModelManager
from pose_estimation.pose_reprocessing import PoseReprocessingWidget
from pose_estimation.pose_tracking import PoseTrackerWidget, PoseTracker
from pose_estimation.video import QVideoSource


if __name__ == "__main__":
    app = QApplication(sys.argv)

    threadpool = QThreadPool()
    modelManager = ModelManager([FeedThroughModel, BlazePose], threadpool)

    window = QTabWidget()
    poseWindow = PoseTrackerWidget(modelManager)
    poseTracker = PoseTracker(threadpool)
    videoSource = QVideoSource()

    poseWindow.setQVideoSource(videoSource)
    poseTracker.setVideoSource(videoSource)
    poseWindow.setPoseTracker(poseTracker)
    window.addTab(poseWindow, "Pose Tracking")

    reprocessWindow = PoseReprocessingWidget(modelManager, threadpool)
    window.addTab(reprocessWindow, "Pose Reprocessing")

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
