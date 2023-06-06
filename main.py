import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QThreadPool
from pose_estimation.Models import BlazePose, FeedThroughModel, ModelManager
from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget
from pose_estimation.transform_widgets import BackgroundRemoverWidget, \
    LandmarkDrawerWidget, ModelRunnerWidget, PoseFeedbackWidget, \
        QCameraSourceWidget, RecorderTransformerWidget, ScalerWidget, \
            SkeletonDrawerWidget, TransformerWidgetsRegistry, VideoSourceWidget
from pose_estimation.transforms import ImageMirror


if __name__ == "__main__":
    app = QApplication(sys.argv)

    threadpool = QThreadPool.globalInstance()
    modelManager = ModelManager([FeedThroughModel, BlazePose], threadpool)
    widgetRegistry = TransformerWidgetsRegistry()
    
    widgetRegistry.addTransformerWidget(lambda parent: VideoSourceWidget(parent), "Video Source")
    widgetRegistry.addTransformerWidget(lambda parent: QCameraSourceWidget(parent), "Camera Source")
    widgetRegistry.addTransformerWidget(lambda parent: ImageMirror(parent), "Mirror")
    widgetRegistry.addTransformerWidget(lambda parent: ScalerWidget(parent), "Scaler")
    widgetRegistry.addTransformerWidget(lambda parent: ModelRunnerWidget(modelManager, parent), "Camera Source")
    widgetRegistry.addTransformerWidget(lambda parent: LandmarkDrawerWidget(parent), "Landmarks")
    widgetRegistry.addTransformerWidget(lambda parent: SkeletonDrawerWidget(parent), "Skeleton")
    widgetRegistry.addTransformerWidget(lambda parent: RecorderTransformerWidget(parent), "Recorder")
    widgetRegistry.addTransformerWidget(lambda parent: PoseFeedbackWidget(parent), "Feedback")
    widgetRegistry.addTransformerWidget(lambda parent: BackgroundRemoverWidget(parent), "Background Remover")

    window = ModularPoseProcessorWidget(widgetRegistry)

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()
    sys.exit(app.exec())
