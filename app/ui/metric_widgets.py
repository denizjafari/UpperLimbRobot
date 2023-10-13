"""
Widgets to display metrics. Matplotlib and pqygraph are used to display graphs.
However, matplotlib is very slow and basically unusable for real-time display.
Pyqtpgrapg is much faster.

Author: Henrik Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from collections import defaultdict
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
    def setMinimum(self, value: float) -> None:
        """
        Set the minimum allowed value for the metric. This will display a red bar
        at the specified value.
        """
        raise NotImplementedError
    
    def setMaximum(self, value: float) -> None:
        """
        Set the maximum allowed value for the metric. This will display a red bar
        at the specified value.
        """
        raise NotImplementedError

    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        raise NotImplementedError
    
    def addValueTo(self, key: str, value: float) -> None:
        """
        Add a value to the graph to a specific series. The value corresponds
        to the y value of the next point in the timeline.
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

    def updateMetrics(self,
                      metrics: dict[str, list[float]],
                      minimumMetrics: Optional[dict[str, list[float]]] = None,
                      maximumMetrics: Optional[dict[str, list[float]]] = None,
                      derivativeMetrics: Optional[dict[str, list[float]]] = None) -> None:
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

            if derivativeMetrics is not None and col in derivativeMetrics:
                derivatives = derivativeMetrics[col]
                self._metricViews[col].addValue(derivatives[0])
                if len(derivatives) > 1:
                    self._metricViews[col].addValueTo("speed", derivatives[1])
                if len(derivatives) > 2:
                    self._metricViews[col].addValueTo("acceleration", derivatives[2])
            else:
                self._metricViews[col].addValue(metrics[col])

            if minimumMetrics is not None and col in minimumMetrics:
                self._metricViews[col].setMinimum(minimumMetrics[col])
            if maximumMetrics is not None and col in maximumMetrics:
                self._metricViews[col].setMaximum(maximumMetrics[col])
    

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
    _minimumLine: Optional[pg.InfiniteLine]
    _maximumLine: Optional[pg.InfiniteLine]

    def __init__(self, name: str, max_datapoints=500) -> None:
        """
        Create a new metric widget that displays the metric labelled by name.
        """
        MetricWidget.__init__(self)
        pg.PlotWidget.__init__(self, background="white", title=name)
        self._minimum = 0
        self._maximum = 0
        self._minimumLine = None
        self._maximumLine = None
        self.maxDataPoints = max_datapoints
        self.values = defaultdict(self.newSeries)

    def newSeries(self) -> tuple[list, pg.PlotDataItem]:
        """
        Create a new time series for the plot.
        """
        data = [0] * self.maxDataPoints
        line = self.plot(data)

        return data, line

    def setMinimum(self, value: Optional[float]) -> None:
        """
        Set or remove the minimum line for this graph. If value is None, the
        minimum line is removed. Otherwise, it is set to the given value.
        """
        if value == self._minimum:
            return
        elif value is None and self._minimumLine is not None:
            self.removeItem(self._minimumLine)
        elif self._minimumLine is None:
            self._minimumLine = self.getPlotItem().addLine(y=value, pen=pg.mkPen('r', width=1))
        else:
            self._minimumLine.setPos(value)

    def setMaximum(self, value: Optional[float]) -> None:
        """
        Set or remove the maximum line for this graph. If value is None, the
        maximum line is removed. Otherwise, it is set to the given value.
        """
        if value == self._maximum:
            return
        elif value is None and self._maximumLine is not None:
            self.removeItem(self._maximumLine)
        elif self._maximumLine is None:
            self._maximumLine = self.getPlotItem().addLine(y=value, pen=pg.mkPen('r', width=1))
        else:
            self._maximumLine.setPos(value)
    
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph for the default curve "". This corresponds to
        the y value of the next point in the timeline.
        """
        self.addValueTo("", value)

    def addValueTo(self, key: str, value: float) -> None:
        """
        Add a value to the graph for the named curve <key>. This corresponds to
        the y value of the next point in the timeline.
        """
        series, line = self.values[key]
        series.append(value)
        series.pop(0)
        line.setData(series)
            
