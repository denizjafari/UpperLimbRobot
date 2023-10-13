"""
Implementation of the sound interface using Qt's QMediaPlayer.

Author: Henrik S. Zimmermann <henrik.zimmermann@utoronto.ca>
"""

from .ISound import ISound
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl


class QSound(ISound):
    """
    An implementation of the souond class using Qt's QMediaPlayer.
    """
    def __init__(self, filename: str):
        """
        Create a QSound object from a file.
        """
        self.player = QMediaPlayer()
        self.audioOutput = QAudioOutput()
        
        self.player.setAudioOutput(self.audioOutput)
        self.player.setSource(QUrl.fromLocalFile(filename))

        self.audioOutput.setVolume(50)

    def play(self, interrupt=False) -> None:
        """
        Play the sound. By default, if the sound is already playing, it will not
        play again. If interrupt is True, the sound currently active will be
        stopped, reset, and then played again.
        """
        if self.player.isPlaying():
            if interrupt:
                self.player.stop()
            else:
                return
        self.player.play()

    def pause(self) -> None:
        """
        Pause the sound.
        """
        self.player.pause()

    def reset(self) -> None:
        """
        Reset the sound to the beginning.
        """
        self.player.stop()
