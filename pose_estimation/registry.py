"""
Registry for models and widgets. Keeps all available models and widgets
in one central place. This allows for easy extensibility of the application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

class Registry(QObject):
    """
    One registry for one type of assets.
    """
    itemsChanged = Signal()
    _items: dict[str, type]

    def __init__(self) -> None:
        """
        Initialize the registry.
        """
        QObject.__init__(self)
        self._items = {}
    
    def register(self, itemClass: type, name: str) -> None:
        """
        Register an item class with a name for app-wide access.
        """
        self._items[name] = itemClass
        self.itemsChanged.emit()
        
    def items(self) -> list[str]:
        """
        List all items by name.
        """
        return [str(key) for key in self._items.keys()]
    
    def createItem(self, key: str) -> object:
        """
        Create an item by name.
        """
        return self._items[key]()


MODEL_REGISTRY = Registry()
WIDGET_REGISTRY = Registry()
