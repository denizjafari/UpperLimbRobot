"""
The feedback module allowing feedback questions to be loaded from a
json file and the answers saved back to a file. Every feedback
question/matrix is a QWidget that can be added to a layout.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""
from typing import Optional

import logging
import json
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, \
    QApplication, QPushButton, QGridLayout, QRadioButton, QButtonGroup, \
    QScrollArea

from PySide6.QtCore import Qt

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class FeedbackItem(QWidget):
    """
    Abstract class for all feedback items.
    """

    def __init__(self,
                 d: dict,
                 parent: Optional[QWidget] = None) -> None:
        """
        Initialize the QWidget.
        """
        QWidget.__init__(self, parent)

    def save(self, d: dict) -> None:
        """
        Save the results from this feedback item.
        """
        raise NotImplementedError("save() not implemented")
    

class FreeTextFeedback(FeedbackItem):
    """
    Feedback Item that poses a question and then allows the user
    to input free text.
    """
    def __init__(self,
                 d: dict,
                 parent: Optional[QWidget] = None) -> None:
        FeedbackItem.__init__(self, d, parent)

        self.vLayout = QVBoxLayout(self)
        self.setLayout(self.vLayout)

        self.vLayout.addWidget(QLabel(d["question"], self))

        self._d = d

        self.textEdit = QTextEdit(self)
        self.vLayout.addWidget(self.textEdit)

    def save(self, d: dict) -> None:
        """
        Save the results from this feedback item.
        """
        d["type"] = "free-text"
        d["question"] = self._d["question"]
        d["response"] = self.textEdit.toPlainText()

    
class FeedbackMatrixRow:
    """
    A row in the feedback matrix that holds a question and manages the answers.
    """
    def __init__(self, question: str, selections: list[str]) -> None:
        self.question = question
        self.selections = selections
        self.buttons: list[QRadioButton] = []
        self.question = QLabel(question)
        self.buttonGroup = QButtonGroup()
        self._value = ""

        for _ in selections:
            button = QRadioButton()
            self.buttons.append(button)
            self.buttonGroup.addButton(button)

    def value(self) -> str:
        """
        Get the currently selected response.
        """
        for index, button in enumerate(self.buttons):
            if button.isChecked():
                return self.selections[index]
    
    def save(self, d: dict) -> None:
        """
        Save the results from this feedback item.
        """
        d["question"] = self.question.text()
        d["response"] = self.value()

class FeedbackMatrix(FeedbackItem):
    """
    Feedback Item that poses multiple question and ask
    for answers on a scale.
    """
    def __init__(self,
                 d: dict,
                 parent: Optional[QWidget] = None) -> None:
        FeedbackItem.__init__(self, d, parent)

        self.gridLayout = QGridLayout(self)
        self.setLayout(self.gridLayout)

        self.rows: list[FeedbackMatrixRow] = []

        if "selections" not in d or not isinstance(d["selections"], list):
            raise ValueError("Feedback matrix must have a list of possible \
                             selections")

        if "questions" not in d or not isinstance(d["questions"], list):
            raise ValueError("Feedback matrix must have a list of questions")
        
        for selection in d["selections"]:
            if not isinstance(selection, str):
                raise ValueError("Selections must be strings")
        
        for index, selection in enumerate(d["selections"]):
            self.gridLayout.addWidget(QLabel(selection), 0, index + 1, Qt.AlignCenter)

        for index, question in enumerate(d["questions"]):
            if not isinstance(question, str):
                raise ValueError("Questions must be strings")
            matrixRow = FeedbackMatrixRow(question, d["selections"])
            self.gridLayout.addWidget(matrixRow.question, index + 1, 0)
            for i, button in enumerate(matrixRow.buttons):
                self.gridLayout.addWidget(button, index + 1, i + 1, Qt.AlignCenter)

            self.rows.append(matrixRow)
            
        self._d = d

    def save(self, d: dict) -> None:
        """
        Save the results from this feedback item.
        """
        d["type"] = "matrix"
        d["questions"] = self._d["questions"]
        d["selections"] = self._d["selections"]
        d["responses"] = []

        for row in self.rows:
            newD = {}
            row.save(newD)
            d["responses"].append(newD)
    

class FeedbackForm(QWidget):
    """
    The form that aggregates all the different types of feedback.
    """
    def __init__(self,
                 file: str,
                 parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)
        self.vLayout = QVBoxLayout(self)
        self.setLayout(self.vLayout)
        self._items = []

        with open(file) as f:
            items = json.load(f)
        
        if not isinstance(items, list):
            raise ValueError("Feedback file must contain a list of items")
        
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Items must be dicts")
            
            if "type" not in item:
                raise ValueError("Item must have a type")
            
            if item["type"] == 'free-text':
                feedbackItem = FreeTextFeedback(item, self)
                self._items.append(feedbackItem)
                self.vLayout.addWidget(feedbackItem)
            elif item["type"] == 'matrix':
                feedbackItem = FeedbackMatrix(item, self)
                self._items.append(feedbackItem)
                self.vLayout.addWidget(feedbackItem)
            else:
                module_logger.info(f"Unknown feedback item type: {item['type']}")

        self.saveButton = QPushButton("Submit", self)
        self.saveButton.clicked.connect(self.export)
        self.vLayout.addWidget(self.saveButton)


    def export(self) -> None:
        """
        Export the feedback to a file.
        """
        d = {}
        self.save(d)
        with open("feedback_output.json", "w") as f:
            json.dump(d, f, indent=2)


    def save(self, d: dict) -> None:
        """
        Save the results from this feedback form.
        """
        d["feedback-form"] = []
        for item in self._items:
            newD = {}
            item.save(newD)
            d["feedback-form"].append(newD)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Please provide a feedback file")
    
    app = QApplication()

    feedbackForm = FeedbackForm(sys.argv[1])

    scrollArea = QScrollArea()
    scrollArea.setWidget(feedbackForm)
    scrollArea.setWidgetResizable(True)
    scrollArea.show()
    scrollArea.setWindowTitle("Feedback Form")

    sys.exit(app.exec())
