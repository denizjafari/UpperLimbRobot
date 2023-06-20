"""
Widgets to display metrics. Matplotlib and pqygraph are used to display graphs.
However, matplotlib is very slow and basically unusable for real-time display.
Pyqtpgrapg is much faster.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from typing import Optional
import logging

import matplotlib
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# Import PySide6 before pyqtgraph to make pyqtgraph choose the
# correct backend
import PySide6
import pyqtgraph as pg

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class MetricWidget:    
    """
    Interface for metric widgets. Metric widgets display metrics on the screen.
    """
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        raise NotImplementedError

class MetricWidgetGroup(QWidget):
    """
    Abstract class for a metric widget group. A metric widget group displays
    multiple metrics widgets.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        QWidget.__init__(self, parent)

    def updateMetrics(self, metrics: dict[str, list[float]]) -> None:
        """
        Update the metric widgets based on the metrics info.
        """
        raise NotImplementedError

class VetricalMetricWidgetGroup(MetricWidgetGroup):
    """
    A metric widget group that displays the metric widgets vertically.
    """
    _metricViews: dict[str, MetricWidget]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the vertical metric widget group.
        """
        MetricWidgetGroup.__init__(self, parent)
        self._metricViews = {}

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)

    def updateMetrics(self, metrics: dict[str, list[float]]) -> None:
       """
       Update the metric views.
       """
       for col in metrics:
            if col not in self._metricViews:
                widget = PyQtMetricWidget(col)
                self._metricViews[col] = widget
                self.vLayout.addWidget(widget)
            else:
                widget = self._metricViews[col]
            self._metricViews[col].addValue(metrics[col])

class GridMetricWidgetGroup(MetricWidgetGroup):
    """
    A metric widget group that displays the metric widgets vertically.
    """
    _metricViews: dict[str, MetricWidget]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the vertical metric widget group.
        """
        MetricWidgetGroup.__init__(self, parent)
        self._metricViews = {}

        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)

    def updateMetrics(self, metrics: dict[str, list[float]]) -> None:
       """
       Update the metric views.
       """
       for col in metrics:
            if col not in self._metricViews:
                widget = PyQtMetricWidget(col)
                length = len(self._metricViews)
                self._metricViews[col] = widget
                row = length % 3
                column = length // 3
                module_logger.debug(f"Adding metric view {col} at row {row} and column {column}")
                self.gridLayout.addWidget(widget, row, column)
            else:
                widget = self._metricViews[col]
            self._metricViews[col].addValue(metrics[col])
    

class MPLMetricWidget(MetricWidget, FigureCanvasQTAgg):
    """
    A metric widget that uses matplotlib to display a graph.
    """
    def __init__(self) -> None:
        """
        Create a new metric widget that displays the metric labelled by name.
        """
        MetricWidget.__init__(self)
        FigureCanvasQTAgg.__init__(self, Figure(figsize=(5, 3)))

        self.axes = self.figure.add_subplot(111)
        self.values = []
        self.axes.plot(self.values)
    
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        if self.axes is None:
            return
        
        self.values.append(value)
        self.axes.plot(self.values)
        self.draw()


class PyQtMetricWidget(MetricWidget, pg.PlotWidget):
    """
    A metric widget that uses pyqtpgraph to display a graph.
    """
    def __init__(self, name: str, max_datapoints=500) -> None:
        """
        Create a new metric widget that displays the metric labelled by name.
        """
        MetricWidget.__init__(self)
        pg.PlotWidget.__init__(self, background="white", title=name)
        self.line = None
        self.values = [0] * max_datapoints
    
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        self.values.append(value)
        self.values.pop(0)
        if self.line is None:
            self.line = self.plot(self.values)
        else:
            self.line.setData(self.values)
