"""
Interface for audio playback. The main component is a Sound class, which
allows to load and playback sounds.

Author: Henrik S. Zimmermann <henrik.zimmermann@utoronto.ca>
"""

class ISound:
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
