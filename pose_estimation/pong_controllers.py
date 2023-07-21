import logging

from events import Event, Client
from pose_estimation.registry import PONG_CONTROLLER_REGISTRY

module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.DEBUG)

class PongController:
    def __init__(self) -> None:
        self._key = ""

    def key(self) -> str:
        return self._key
    
    def setKey(self, key: str) -> None:
        self._key = key

    def control(self, pongData: dict[str, object]) -> None:
        raise NotImplementedError("control() not implemented")
    
class SimplePongController(PongController):
    def __init__(self) -> None:
        PongController.__init__(self)
    
    def control(self, pongData: dict[str, object]):
        if "client" not in pongData or pongData["client"] is None:
            return
        
        client: Client = pongData["client"]

        if "accuracy" in pongData and "ballSpeed" in pongData:
            if pongData["accuracy"] > 0.6:
                client.send(Event("setBallSpeed", [pongData["ballSpeed"] + 0.02]))
                module_logger.debug(f"Increased pong speed to {pongData['ballSpeed'] + 0.02}")
            elif pongData["accuracy"] < 0.4:
                client.send(Event("setBallSpeed", [pongData["ballSpeed"] - 0.02]))
                module_logger.debug(f"Decreased pong speed to {pongData['ballSpeed'] - 0.02}")


PONG_CONTROLLER_REGISTRY.register(SimplePongController, "SimplePongController")
