class IDetector:
    """
    Interface for all GestureDetectors.
    """
    def detect(self, metrics: dict[str, float]) -> None:
        raise NotImplementedError