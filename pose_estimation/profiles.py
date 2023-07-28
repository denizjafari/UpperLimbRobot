from typing import Optional
import os
import logging

from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QVBoxLayout, \
    QPushButton, QLabel
from PySide6.QtCore import Signal

from pose_estimation.ui_utils import FileSelector


module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)


class UserProfile:
    """
    The user profile class which holds, saves and restores user profile data.
    """
    userId: int
    name: str
    workingDir: str

    def __init__(self, userId: int = -1) -> None:
        """
        Initializes a new user profile with the given userId.
        """
        self.workingDir = os.getcwd()
        self.name = "New User"
        self.userId = userId
        self.additionalNotes = ""

    def restore(self, d: dict) -> None:
        """
        Restore a user profike from a dictionary.
        """
        self.userId = d["userId"]
        self.name = d["name"]
        self.workingDir = d["workingDir"]
        self.additionalNotes = d["additionalNotes"]

    def save(self, d: dict) -> None:
        """
        Save a user profile to a dictionary
        """
        d["userId"] = self.userId
        d["name"] = self.name
        d["workingDir"] = self.workingDir
        d["additionalNotes"] = self.additionalNotes


class UserProfileWidget(QWidget):
    """
    A widget which displays a user profile.
    """
    selected = Signal()
    editRequested = Signal()

    userProfile: UserProfile
    formLayout: QFormLayout

    def __init__(self,
                 userProfile: UserProfile,
                 parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        self.userProfile = userProfile

        self.formLayout = QFormLayout()
        self.setLayout(self.formLayout)

        self.formLayout.addRow("Name",
                               QLabel(self.userProfile.name))
        self.formLayout.addRow("Working Directory",
                               QLabel(self.userProfile.workingDir))
        self.formLayout.addRow("Additional Notes",
                               QLabel(self.userProfile.additionalNotes))
        
        self.editButton = QPushButton("Edit")
        self.editButton.clicked.connect(self.editRequested)
        self.formLayout.addRow("", self.editButton)

        self.selectButton = QPushButton("Select")
        self.selectButton.clicked.connect(self.selected)
        self.formLayout.addRow("", self.selectButton)


class UserProfileEditor(QWidget):
    """
    An editor widget for a user profile.
    """
    saveRequested = Signal()

    vLayout: QVBoxLayout
    formLayout: QFormLayout
    nameField: QLineEdit
    directorySelector: FileSelector
    additionalNotes: QLineEdit
    saveButton: QPushButton
    exitButton: QPushButton
    
    def __init__(self,
                 userProfile: UserProfile,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the widget with the given user profile.
        """
        QWidget.__init__(self, parent)

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)
        
        self.formLayout = QFormLayout()
        self.vLayout.addLayout(self.formLayout)

        self.nameField = QLineEdit()
        self.nameField.setText(userProfile.name)
        self.formLayout.addRow("Name", self.nameField)

        self.directorySelector = FileSelector(mode=FileSelector.MODE_DIRECTORY)
        self.directorySelector.setPath(userProfile.workingDir)
        self.formLayout.addRow("Working Directory", self.directorySelector)

        self.additionalNotes = QLineEdit()
        self.additionalNotes.setText(userProfile.additionalNotes)
        self.formLayout.addRow("Additional Notes", self.additionalNotes)

        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.save)
        self.vLayout.addWidget(self.saveButton)

        self.userProfile = userProfile


    def save(self) -> None:
        """
        Save the user profile.
        """
        self.userProfile.name = self.nameField.text()
        self.userProfile.workingDir = self.directorySelector.selectedFile()
        self.userProfile.additionalNotes = self.additionalNotes.text()
        self.saveRequested.emit()


class UserProfileSelector(QWidget):
    """
    A widget to select which user profile to use, edit or create as new.
    """
    saveRequested = Signal()
    userSelected = Signal(UserProfile)
    
    def __init__(self,
                 parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

        self.vUserLayout = QVBoxLayout()
        self.vLayout.addLayout(self.vUserLayout)

        self.vLayout.addStretch()

        self.newUserButton = QPushButton("New User")
        self.newUserButton.clicked.connect(self.addUser)
        self.vLayout.addWidget(self.newUserButton)

        self.users: list[UserProfile] = []
        self.highestIdGiven = -1
        self.userIdToWidget: dict[int, QWidget] = {}
        self.userCreator = None

    def setUsers(self, users: list[UserProfile]) -> None:
        """
        Set the profiles from which the user can select.
        """
        for user in self.users:
            self.userIdToWidget[user.userId].deleteLater()
        self.users = users
        for user in self.users:
            self.addUserToLayout(user)

    def addUserToLayout(self, user: UserProfile) -> None:
        """
        Add a user to the layout.
        """
        widget = UserProfileWidget(user)
        widget.selected.connect(lambda: self.userSelected.emit(user))
        widget.editRequested.connect(lambda: self.editUser(user))
        self.vUserLayout.addWidget(widget)
        self.userIdToWidget[user.userId] = widget

    def addUser(self) -> None:
        """
        Add a user to the list of users and to the layout.
        """
        self.editUser(UserProfile(self.highestIdGiven + 1))

    def editUser(self, user: UserProfile) -> None:
        """
        Open the edit dialog for a user.
        """
        self.userCreator = UserProfileEditor(user)
        self.userCreator.saveRequested.connect(lambda: self.saveUser(user))
        self.userCreator.show()

    def saveUser(self, user: UserProfile) -> None:
        """
        Save changes to a user. Can be a completely new user or an existing
        one.
        """
        userIsNew = True
        for u in self.users:
            if u.userId == user.userId:
                widget = UserProfileWidget(user)
                widget.selected.connect(lambda: self.userSelected.emit(user))
                widget.editRequested.connect(lambda: self.editUser(user))
                self.vUserLayout.replaceWidget(
                    self.userIdToWidget[u.userId], widget)
                self.userIdToWidget[u.userId].deleteLater()
                self.userIdToWidget[u.userId] = widget
                userIsNew = False

        if userIsNew:
            self.users.append(user)
            self.addUserToLayout(user)
            self.highestIdGiven += 1

        module_logger.debug("Saved user changes in app")
        self.saveRequested.emit()

    
    def restore(self, d: dict) -> None:
        """
        Restore the list of users from a dictionary.
        """
        if "users" in d:
            users = [UserProfile() for _ in d["users"]]
            for i, user in enumerate(users):
                user.restore(d["users"][i])
            self.setUsers(users)
            if "highestIdGiven" in d:
                self.highestIdGiven = -1
            else:
                raise ValueError("Missing highestIdGiven in user profiles dict")
    
    def save(self, d: dict) -> None:
        """
        Save the list of users to a dictionary.
        """
        d["users"] = []
        for user in self.users:
            newD = {}
            user.save(newD)
            d["users"].append(newD)
        d["highestIdGiven"] = self.highestIdGiven