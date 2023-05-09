import sys
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import Qt
from pose_estimation.Models import BlazePose, MoveNetLightning
from pose_estimation.PoseWindow import PoseTrackerWidget, PoseTracker


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QTabWidget()
    poseWindow = PoseTrackerWidget()
    poseTracker = PoseTracker()
    model = BlazePose()
    poseTracker.setModel(model)
    poseWindow.setPoseTracker(poseTracker)
    window.addTab(poseWindow, "Pose Estimation")

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
