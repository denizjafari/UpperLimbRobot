"""
Registry for models and widgets. Keeps all available models and widgets
in one central place. This allows for easy extensibility of the application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Union, Callable

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
    
    def register(self,
                 itemClass: Union[type, Callable[[], object]],
                 name: str) -> None:
        """
        Register an item with a name for app-wide access. This item can be a
        class which will be instantiated on createItem() or a function which
        will be called.
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
        Create an item by name. Either instantiate the class or calls the
        registered function.
        """
        widget = self._items[key]()
        widget.setKey(key)

        return widget


MODEL_REGISTRY = Registry()
WIDGET_REGISTRY = Registry()
