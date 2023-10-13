"""
Unitility classes for the UI. Selector Buttons, loads of Selector Buttons. 

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional

import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QRadioButton, QHBoxLayout, \
    QPushButton, QFileDialog, QLineEdit, QLabel, QGroupBox, QSlider, \
    QAbstractSlider, QStyleOptionSlider, QStyle, QToolTip, QComboBox
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaDevices
from PySide6.QtCore import Signal, Slot, QPoint
from core.protocols.events import Client

from core.models.IModel import IModel
from core.resource_management.registry import REGISTRY


# The frame dimensions and rate for which a suitable format is selected.
TARGET_FRAME_WIDTH = 296
TARGET_FRAME_HEIGHT = 296
TARGET_FRAME_RATE = 25

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class CameraSelectorButton(QRadioButton):
    """
    A Radio button that allows selection of one camera.
    """
    cameraDevice: QCameraDevice
    selected = Signal(QCamera)

    def __init__(self, device: QCameraDevice, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the selector for a given camera device.
        """
        QRadioButton.__init__(self, device.description(), parent)
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
                module_logger.warn("No suitable video format exists")
            else:
                format = usable_formats[0]
                module_logger.info(f"Recording in {format.resolution().width()}x{format.resolution().height()}@{format.maxFrameRate()}")
                camera.setCameraFormat(format)

            self.selected.emit(camera)


class CameraSelector(QGroupBox):
    """
    A group of radio buttons to select a camera from the inputs.
    """
    selected = Signal(QCamera)
    refreshButton: QPushButton
    cameraButtons: list[CameraSelectorButton]
    qMediaDevices: QMediaDevices
    vLayout: QVBoxLayout

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Intitialize the selector and update the list of cameras.
        """
        QGroupBox.__init__(self, "Camera", parent)
        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.qMediaDevices = QMediaDevices()
        self.qMediaDevices.videoInputsChanged.connect(self.updateCameraDevices)

        self.cameraButtons = []

        self.updateCameraDevices()

    @Slot()
    def updateCameraDevices(self) -> None:
        """
        Update the list of available cameras and add radio buttons.
        """
        while len(self.cameraButtons) > 0:
            button = self.cameraButtons.pop()
            self.vLayout.removeWidget(button)
            button.deleteLater()

        cameraDevices = QMediaDevices.videoInputs()
        for camera in cameraDevices:
            button = CameraSelectorButton(camera, self)
            button.selected.connect(self.selected)

            self.vLayout.addWidget(button)
            self.cameraButtons.append(button)

    def selectedCamera(self) -> str:
        """
        Get the currently selected camera.
        """
        for button in self.cameraButtons:
            if button.isChecked():
                return button.cameraDevice.description()

        return ""
    
    def setSelectedCamera(self, camera: str) -> None:
        """
        Set the currently selected camera.
        """
        for button in self.cameraButtons:
            if button.cameraDevice.description() == camera:
                button.setChecked(True)
                break

class ModelSelectorButton(QRadioButton):
    """
    A Radio button that allows selection of one model.
    """
    model: IModel
    selected = Signal(IModel)

    def __init__(self, modelName: str) -> None:
        """
        Initialize the selector for a given pose model.
        """
        QRadioButton.__init__(self, modelName)

        self.model = REGISTRY.createItem(modelName)
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
    modelSelected = Signal(IModel)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the selector
        """
        QGroupBox.__init__(self, "Model", parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        REGISTRY.itemsChanged.connect(self.addAllModels)
        self.addAllModels("models")

    def addAllModels(self, category: str) -> None:
        """
        Add all available models to the selector.
        """
        if category != "models":
            return

        for item in self.layout().children():
            item.deleteLater()

        for model in REGISTRY.items("models"):
            self.addModel(model)

    @Slot(IModel)
    def addModel(self, modelName: str) -> None:
        button = ModelSelectorButton(modelName)
        button.selected.connect(self.modelSelected)
        self.layout().addWidget(button)

    def selectedModel(self) -> str:
        """
        Get the name of the currently selected model.
        """
        for item in self.children():
            if isinstance(item, ModelSelectorButton):
                if item.isChecked():
                    return item.text()
                
        return ""
    
    def setSelectedModel(self, modelName: str) -> None:
        for item in self.children():
            if isinstance(item, ModelSelectorButton):
                if item.text() == modelName:
                    item.setChecked(True)
                    return

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
    MODE_DIRECTORY = 2

    fileSelectButton: QPushButton
    textInput: QLineEdit
    label: QLabel

    removeButton: QPushButton

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 mode: int = MODE_LOAD,
                 title: Optional[str] = None,
                 removable: bool = False,
                 defaultPath: str = "") -> None:
        """
        Initialize the file selector widget.
        """
        QWidget.__init__(self, parent)

        self.setLayout(QHBoxLayout())

        if title is not None:
            self.label = QLabel(title, self)
            self.layout().addWidget(self.label)

        self.textInput = QLineEdit(self)
        self.textInput.setText(defaultPath)
        self.textInput.textChanged.connect(self.fileSelected)
        self.layout().addWidget(self.textInput)

        self.fileSelectButton = QPushButton("Select file", self)
        self.fileSelectButton.clicked.connect(self.selectFile)
        self.layout().addWidget(self.fileSelectButton)

        if removable:
            self.removeButton = QPushButton("Remove", self)
            self.layout().addWidget(self.removeButton)
        else:
            self.removeButton = None
        
        self.option = mode

    @Slot()
    def selectFile(self) -> None:
        """
        Open the default file dialog to determine the file to be loaded.
        """
        if self.option == self.MODE_LOAD:
            path, _ = QFileDialog.getOpenFileName(self, "Select Input")
        elif self.option == self.MODE_SAVE:
            path, _ = QFileDialog.getSaveFileName(self, "Select Output")
        elif self.option == self.MODE_DIRECTORY:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.textInput.setText(path)

    def setPath(self, path: str) -> None:
        """
        Set the current path to the file.
        """
        self.textInput.setText(path)

    def selectedFile(self) -> str:
        """
        Get the selected filename.
        """
        return self.textInput.text()
    

class LabeledQSlider(QSlider):
    """
    Slider that also shows the value as a tooltip when it is changed.
    """
    def sliderChange(self, change: QAbstractSlider.SliderChange) -> None:
        """
        Do the default action, but also display the currently selected value
        as a tooltip.
        """
        super().sliderChange(change)

        if change == QAbstractSlider.SliderChange.SliderValueChange:
            sliderStyle = QStyleOptionSlider()
            self.initStyleOption(sliderStyle)

            sr = self.style().subControlRect(QStyle.ComplexControl.CC_Slider,
                                             sliderStyle,
                                             QStyle.SubControl.SC_SliderHandle,
                                             self)
            
            bottomRight = sr.bottomRight()

            QToolTip.showText(
                self.mapToGlobal(QPoint(bottomRight.x(), bottomRight.y())),
                str(self.value()))
            

class ConnectionWidget(QWidget):
    """
    A widget to setup and connect to a server.
    """
    clientConnected = Signal(Client)

    def __init__(self) -> None:
        """
        Initialize the connection widget.
        """
        QWidget.__init__(self)
        
        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.hostField = QLineEdit("localhost")
        self.vLayout.addWidget(self.hostField)

        self.portField = QLineEdit("9876")
        self.vLayout.addWidget(self.portField)
        
        self.connectButton = QPushButton("Connect")
        self.vLayout.addWidget(self.connectButton)

        self.connectButton.clicked.connect(self.connectClient)


    def connectClient(self) -> None:
        """
        Create a client object and attempt to connect to the server with the
        host and port specified in the text fields.
        """
        address = (self.hostField.text(), int(self.portField.text()))
        self.client = Client(address)
        self.client.start()
        module_logger.info("Connecting to server")
        self.clientConnected.emit(self.client)


class MetricSelector(QWidget):
    metricSelected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.metricDropdown = QComboBox()
        self.vLayout.addWidget(self.metricDropdown)

    def updateMetricsList(self, metricsList: list) -> None:
        """
        Update the metrics list.
        """
        newMetricDropdown = QComboBox(self)
        for metric in metricsList:
            newMetricDropdown.addItem(metric)
            if metric == self.metricDropdown.currentText():
                newMetricDropdown.setCurrentText(metric)

        newMetricDropdown.currentTextChanged.connect(self.metricSelected)
        
        self.vLayout.replaceWidget(self.metricDropdown, newMetricDropdown)
        self.metricDropdown.deleteLater()
        self.metricDropdown = newMetricDropdown

    def save(self, d: dict[str, object]) -> None:
        """
        Save the current state of the widget.
        """
        d["availableMetrics"] = [self.metricDropdown.itemText(i) \
                                 for i in range(self.metricDropdown.count())]
        d["selectedMetric"] = self.metricDropdown.currentText()

    def restore(self, d: dict[str, object]) -> None:
        """
        Restore the state of the widget.
        """
        if "availableMetrics" in d and "selectedMetric" in d:
            self.updateMetricsList(d["availableMetrics"])
            self.metricDropdown.setCurrentText(d["selectedMetric"])
