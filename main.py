import sys
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import Qt
from pose_estimation.Models import BlazePose, FeedThroughModel, MoveNetLightning, MoveNetThunder
from pose_estimation.pose_tracking import PoseTrackerWidget, PoseTracker
from pose_estimation.video import CVVideoSource, QVideoSource


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QTabWidget()
    poseWindow = PoseTrackerWidget()
    poseTracker = PoseTracker()
    videoSource = QVideoSource()

    poseWindow.setQVideoSource(videoSource)
    poseTracker.setVideoSource(videoSource)
    poseWindow.setPoseTracker(poseTracker)
    window.addTab(poseWindow, "Pose Estimation")

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
