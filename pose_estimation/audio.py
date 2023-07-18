from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl


class Sound:
    """
    An abstract sound class to load and playback sounds.
    """
    def __init__(self) -> None:
        """
        Initialize the sound.
        """
        self._key = ""

    def play(self, interrupt=False):
        """
        Play a sound. By default, if the sound is already playing, it will not
        play again. If interrupt is True, the sound currently active will be
        stopped, reset, and then played again.
        """
        raise NotImplementedError

    def pause(self) -> None:
        """
        Pause the sound.
        """
        raise NotImplementedError
    
    def reset(self) -> None:
        """
        Reset the sound to the beginning.
        """
        raise NotImplementedError

    def key(self) -> str:
        return self._key
    
    def setKey(self, key: str) -> None:
        self._key = key


class QSound(Sound):
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
