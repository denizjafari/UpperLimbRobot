import logging
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pose_estimation.Models import BlazePose, FeedThroughModel, ModelManager
from pose_estimation.games import DefaultMeasurementsTransformer
from pose_estimation.games_widgets import ChickenWingWidget, DefaultMeasurementsWidget, PoseFeedbackWidget
from pose_estimation.modular_pose_processor import ModularPoseProcessorWidget
from pose_estimation.transform_widgets import BackgroundRemoverWidget, ImageMirrorWidget, \
    LandmarkDrawerWidget, ModelRunnerWidget, \
        QCameraSourceWidget, RecorderTransformerWidget, ScalerWidget, \
            SkeletonDrawerWidget, TransformerWidgetsRegistry, VideoSourceWidget


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    modelManager = ModelManager([FeedThroughModel, BlazePose])
    widgetRegistry = TransformerWidgetsRegistry()
    
    widgetRegistry.addTransformerWidget(lambda parent: QCameraSourceWidget(parent), "Camera Source")
    widgetRegistry.addTransformerWidget(lambda parent: VideoSourceWidget(parent), "Video Source")
    widgetRegistry.addTransformerWidget(lambda parent: ImageMirrorWidget(parent), "Mirror")
    widgetRegistry.addTransformerWidget(lambda parent: ScalerWidget(parent), "Scaler")
    widgetRegistry.addTransformerWidget(lambda parent: BackgroundRemoverWidget(parent), "Background Remover")
    widgetRegistry.addTransformerWidget(lambda parent: ModelRunnerWidget(modelManager, parent), "Model")
    widgetRegistry.addTransformerWidget(lambda parent: SkeletonDrawerWidget(parent), "Skeleton")
    widgetRegistry.addTransformerWidget(lambda parent: LandmarkDrawerWidget(parent), "Landmarks")
    widgetRegistry.addTransformerWidget(lambda parent: RecorderTransformerWidget(parent), "Recorder")
    widgetRegistry.addTransformerWidget(lambda parent: DefaultMeasurementsWidget(parent), "Default Measurements")
    widgetRegistry.addTransformerWidget(lambda parent: PoseFeedbackWidget(parent), "Feedback")
    widgetRegistry.addTransformerWidget(lambda parent: ChickenWingWidget(parent), "Chicken Wings")

    window = ModularPoseProcessorWidget(widgetRegistry)

    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    window.setWindowState(Qt.WindowState.WindowMaximized)
    window.show()

    module_logger.info("Ready")
    sys.exit(app.exec())
