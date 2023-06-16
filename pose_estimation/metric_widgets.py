import matplotlib

matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# Import PySide6 before pyqtgraph to make pyqtgraph choose the
# correct backend
import PySide6
import pyqtgraph as pg


class MetricWidget():
    """
    Interface for metric widgets. Metric widgets display metrics on the screen.
    """
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        raise NotImplementedError

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
        self.values = []
        self.cutoff_length = max_datapoints
    
    def addValue(self, value: float) -> None:
        """
        Add a value to the graph. This corresponds to the y value of the next
        point in the timeline.
        """
        self.values.append(value)
        while len(self.values) > self.cutoff_length:
            self.values.pop(0)
        if self.line is None:
            self.line = self.plot(self.values)
        else:
            self.line.setData(self.values)
