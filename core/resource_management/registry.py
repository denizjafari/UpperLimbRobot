"""
Registry for models and widgets. Keeps all available models and widgets
in one central place. This allows for easy extensibility of the application.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from __future__ import annotations
from typing import Union, Callable

import os

from PySide6.QtCore import QObject, Signal

class Registry(QObject):
    """
    One registry for one type of assets.
    """
    itemsChanged = Signal(str)
    _items: dict[str, dict[str, Callable[[], object]]]

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
        category, name = name.split(".")
        if category not in self._items:
            self._items[category] = {}
        self._items[category][name] = itemClass
        self.itemsChanged.emit(category)
        
    def items(self, category: str) -> list[str]:
        """
        List all items by name.
        """
        return [f"{category}.{str(key)}" for key in self._items[category].keys()]
    
    def createItem(self, key: str) -> object:
        """
        Create an item by name. Either instantiate the class or calls the
        registered function.
        """
        category, name = key.split(".")
        widget = self._items[category][name]()
        widget.setKey(key)

        return widget
    

class GlobalProps:
    """
    A class wrapping a dictionary to handle globally needed properties.
    """
    def __init__(self) -> None:
        self._props = {}

    def save(self, d: dict) -> None:
        """
        Save all globals props that have been set.
        """
        for key in self._props:
            d[key] = self._props[key]

    def restore(self, d: dict) -> None:
        """
        Restore all global props from a dictionary.
        """
        for key in d:
            self._props[key] = d[key]

    def __getitem__(self, key) -> object:
        return self._props[key]
    
    def __setitem__(self, key, item) -> None:
        self._props[key] = item

REGISTRY = Registry()
GLOBAL_PROPS = GlobalProps()

GLOBAL_PROPS["WORKING_DIR"] = os.getcwd()
