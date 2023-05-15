from PySide6.QtWidgets import QWidget, QVBoxLayout, QRadioButton, QHBoxLayout, \
    QPushButton, QFileDialog, QLineEdit, QLabel, QGroupBox
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaDevices
from PySide6.QtCore import Signal, Slot
from typing import Optional

from pose_estimation.Models import FeedThroughModel, ModelManager, PoseModel


# The frame dimensions and rate for which a suitable format is selected.
TARGET_FRAME_WIDTH = 296
TARGET_FRAME_HEIGHT = 296
TARGET_FRAME_RATE = 25

# The number of frames that should be allowed to processed at each point in time.
# Higher numbers allow for a smoother display, while additional lag is induced.
MAX_FRAMES_IN_PROCESSING = 1


class CameraSelectorButton(QRadioButton):
    """
    A Radio button that allows selection of one camera.
    """
    cameraDevice: QCameraDevice
    selected = Signal(QCamera)

    def __init__(self, device: QCameraDevice) -> None:
        """
        Initialize the selector for a given camera device.
        """
        QRadioButton.__init__(self, device.description())
        self.cameraDevice = device

        self.toggled.connect(self.slotSelected)
        
    @Slot(bool)
    def slotSelected(self, isChecked) -> None:
        """
        Pepare the camera for recording by selecting an appropriate
        format and issue a 'selected' signal.
        """
        if isChecked:
            camera = QCamera(self.cameraDevice)
            formats = self.cameraDevice.videoFormats()
            formats.sort(key=lambda f: f.resolution().height())
            formats.sort(key=lambda f: f.resolution().width())
            formats.sort(key=lambda f: f.maxFrameRate())

            usable_formats = [f for f in formats
                              if f.resolution().width() >= TARGET_FRAME_WIDTH
                              and f.resolution().height() >= TARGET_FRAME_HEIGHT
                              and f.maxFrameRate() >= TARGET_FRAME_RATE]
            if len(usable_formats) == 0:
                print("No suitable video format exists")
            else:
                format = usable_formats[0]
                print(f"Recording in {format.resolution().width()}x{format.resolution().height()}@{format.maxFrameRate()}")
                camera.setCameraFormat(format)

            self.selected.emit(camera)


class CameraSelector(QGroupBox):
    """
    A group of radio buttons to select a camera from the inputs.
    """
    selected = Signal(QCamera)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Intitialize the selector and update the list of cameras.
        """
        QGroupBox.__init__(self, "Camera", parent)
        self.updateCameraDevices()


    def updateCameraDevices(self) -> None:
        """
        Update the list of available cameras and add radio buttons.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        cameraDevices = QMediaDevices.videoInputs()
        for camera in cameraDevices:
            button = CameraSelectorButton(camera)
            button.selected.connect(self.selected)
            layout.addWidget(button)

class ModelSelectorButton(QRadioButton):
    """
    A Radio button that allows selection of one model.
    """
    model: PoseModel
    selected = Signal(PoseModel)

    def __init__(self, model: PoseModel) -> None:
        """
        Initialize the selector for a given pose model.
        """
        QRadioButton.__init__(self, str(model))

        self.model = model
        self.toggled.connect(self.slotSelected)

    @Slot()
    def slotSelected(self) -> None:
        """
        Propagate the signal if the model has been selected.
        """
        if self.isChecked():
            self.selected.emit(self.model)

class ModelSelector(QGroupBox):
    """
    A selector that can select all available models.
    """
    modelSelected = Signal(PoseModel)

    def __init__(self, modelManager: ModelManager, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the selector
        """
        QGroupBox.__init__(self, "Model", parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        modelManager.modelAdded.connect(self.addModel)
        for model in modelManager.models:
            self.addModel(model)

    @Slot(PoseModel)
    def addModel(self, model: PoseModel) -> None:
        button = ModelSelectorButton(model)
        if isinstance(model, FeedThroughModel):
            button.setChecked(True)
        button.selected.connect(self.modelSelected)
        self.layout().addWidget(button)


class FileSelector(QWidget):
    """
    A widget to select a file. The file path can be manually entered in an
    input box. A click of a button opens a file dialog to visually select
    a file.

    fileSelected - the path to the file that has been selected.
    """
    fileSelected = Signal(str)
    MODE_LOAD = 0
    MODE_SAVE = 1

    fileSelectButton: QPushButton
    textInput: QLineEdit
    label: QLabel

    def __init__(self, parent: Optional[QWidget] = None, mode=MODE_LOAD, title="File") -> None:
        """
        Initialize the file selector widget.
        """
        QWidget.__init__(self, parent)

        self.setLayout(QVBoxLayout())

        self.label = QLabel(title, self)
        self.layout().addWidget(self.label)

        hContainer = QWidget(self)
        hContainer.setLayout(QHBoxLayout())
        self.layout().addWidget(hContainer)

        self.textInput = QLineEdit(hContainer)
        self.textInput.textChanged.connect(self.fileSelected)
        hContainer.layout().addWidget(self.textInput)

        self.fileSelectButton = QPushButton("Select file", hContainer)
        self.fileSelectButton.clicked.connect(self.selectFile)
        hContainer.layout().addWidget(self.fileSelectButton)
        
        self.option = mode

    @Slot()
    def selectFile(self) -> None:
        """
        Open the default file dialog to determine the file to be loaded.
        """
        if self.option == self.MODE_LOAD:
            path, _ = QFileDialog.getOpenFileName(self, "Select Input")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Select Output")
        self.textInput.setText(path)

    def selectedFile(self) -> str:
        """
        Get the selected filename.
        """
        return self.textInput.text()
