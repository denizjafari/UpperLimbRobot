import sys
import asyncio
import functools
import qasync

from PySide6.QtWidgets import QApplication,QWidget, QVBoxLayout
from qasync import asyncSlot, asyncClose, QApplication


class MainWindow(QWidget):
    """Main window."""

    def __init__(self):
        super().__init__()

        self.vLayout = QVBoxLayout()
        self.setLayout(self.vLayout)
       

    @asyncClose
    async def closeEvent(self, event):
        await self.session.close()

    @asyncSlot()
    async def on_btnFetch_clicked(self):
        self.btnFetch.setEnabled(False)
        self.lblStatus.setText("Fetching...")

        try:
            async with self.session.get(self.editUrl.text()) as r:
                self.editResponse.setText(await r.text())
        except Exception as exc:
            self.lblStatus.setText("Error: {}".format(exc))
        else:
            self.lblStatus.setText("Finished!")
        finally:
            self.btnFetch.setEnabled(True)


async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    mainWindow = MainWindow()
    mainWindow.show()

    await future
    return True

if __name__ == "__main__":
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)
