from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, \
    QPushButton, QCheckBox, QSlider
from PySide6.QtCore import Slot, Signal, Qt
from pose_estimation.Models import ModelManager

from pose_estimation.transforms import ImageMirror, LandmarkDrawer, ModelRunner, Scaler, SkeletonDrawer, Transformer
from pose_estimation.ui_utils import ModelSelector


class TransformerWidget(QWidget):
    """
    The base transformer widget including the title label and remove logic.
    """
    removed = Signal()

    titleLabel: QLabel
    vLayout: QVBoxLayout
    transformer: Transformer

    def __init__(self, title: str="Transformer", parent: Optional[QWidget] = None) -> None:
        """
        Initialize the TransformerWidget.
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.titleLabel = QLabel(title, self)
        self.vLayout.addWidget(self.titleLabel)

        self.activeCheckBox = QCheckBox("Active")
        self.activeCheckBox.clicked.connect(self.onActiveToggle)
        self.vLayout.addWidget(self.activeCheckBox)

        self.removeButton = QPushButton("Remove", self)
        self.removeButton.clicked.connect(self.removed)
        self.vLayout.addWidget(self.removeButton)


    def onActiveToggle(self) -> None:
        self.transformer.isActive = self.activeCheckBox.isChecked()


class ScalerWidget(TransformerWidget):
    """
    Widget wrapper around the Scaler transformer exposing the target size
    property in the ui.
    """
    transformer: Scaler

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ScalerWidget.
        """
        TransformerWidget.__init__(self, "Scaler", parent)

        self.transformer = Scaler(640, 640)

        self.heightSelector = QLineEdit(self)
        self.heightSelector.setText(str(640))
        self.vLayout.addWidget(self.heightSelector)

        self.applyButton = QPushButton("Apply", self)
        self.applyButton.clicked.connect(self.onApplyClicked)
        self.vLayout.addWidget(self.applyButton)

    @Slot()
    def onApplyClicked(self) -> None:
        """
        Apply the entered target size.
        """
        self.transformer.setTargetSize(int(self.heightSelector.text()))


class ImageMirrorWidget(TransformerWidget):
    """
    Widget wrapper around the ImageMirror transformer exposing the target size
    property in the ui.
    """
    transformer: ImageMirror

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ImageMirrorWidget.
        """
        TransformerWidget.__init__(self, "Mirror", parent)

        self.transformer = ImageMirror()


class ModelRunnerWidget(TransformerWidget):
    """
    """
    transformer: ModelRunner

    def __init__(self, modelManager: ModelManager, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ModelRunnerWidget.
        """
        TransformerWidget.__init__(self, "Model", parent)

        self.transformer = ModelRunner()

        self.modelSelector = ModelSelector(modelManager, self)
        self.modelSelector.modelSelected.connect(self.transformer.setModel)
        self.vLayout.addWidget(self.modelSelector)


class LandmarkDrawerWidget(TransformerWidget):
    """
    """
    transformer: LandmarkDrawer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the LandmarkDrawerWidget.
        """
        TransformerWidget.__init__(self, "Landmark Drawer", parent)

        self.transformer = LandmarkDrawer()

        self.markerRadiusSlider = QSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.markerRadiusSlider.setMinimum(1)
        self.markerRadiusSlider.setMaximum(10)
        self.markerRadiusSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.markerRadiusSlider.setTickInterval(1)
        self.markerRadiusSlider.valueChanged.connect(self.transformer.setMarkerRadius)
        self.vLayout.addWidget(self.markerRadiusSlider)


class SkeletonDrawerWidget(TransformerWidget):
    """
    """
    transformer: SkeletonDrawer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the SkeletonDrawerWidget.
        """
        TransformerWidget.__init__(self, "Skeleton Drawer", parent)

        self.transformer = SkeletonDrawer()

        self.lineThicknessSlider = QSlider(self,
                                          orientation=Qt.Orientation.Horizontal)
        self.lineThicknessSlider.setMinimum(1)
        self.lineThicknessSlider.setMaximum(10)
        self.lineThicknessSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lineThicknessSlider.setTickInterval(1)
        self.lineThicknessSlider.valueChanged.connect(self.transformer.setLineThickness)
        self.vLayout.addWidget(self.lineThicknessSlider)
