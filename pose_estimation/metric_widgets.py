import pandas as pd
import matplotlib

matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget
import pyqtgraph as pg


class MetricWidget():    
    def update(self) -> None:
        raise NotImplementedError

class MPLMetricWidget(MetricWidget, FigureCanvasQTAgg):
    def __init__(self) -> None:
        MetricWidget.__init__(self)
        FigureCanvasQTAgg.__init__(self, Figure(figsize=(5, 3)))

        self.axes = self.figure.add_subplot(111)
        self.axes.plot(self.values)
    
    def update(self, values: list[float]) -> None:
        if self.axes is None:
            return
        
        self.axes.plot(values)
        self.draw()


class PyQtMetricWidget(MetricWidget, pg.PlotWidget):
    def __init__(self, name: str) -> None:
        MetricWidget.__init__(self)
        pg.PlotWidget.__init__(self, background="white", title=name)
        self.line = None
    
    def update(self, values: list[float]) -> None:
        if self.line is None:
            self.line = self.plot(values)
        else:
            self.line.setData(values)
