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
    QApplication, QPushButton

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
        d["text"] = self.textEdit.toPlainText()
    

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
    feedbackForm.show()

    sys.exit(app.exec())
