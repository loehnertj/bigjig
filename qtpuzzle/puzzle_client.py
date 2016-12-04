import logging
import inspect
L = lambda: logging.getLogger(__name__)

from puzzleboard.puzzle_api import PuzzleAPI

class PuzzleClient(PuzzleAPI):
    def __init__(self, codec, transport, nickname):
        PuzzleAPI.__init__(self, codec=codec, transport=transport)
        self.invert()
        self.players = {}
        self.nickname = nickname 
        self.playerid = None
        self.connected.connect(self._add_player)
        self.disconnected.connect(self._remove_player)
        
    def _add_player(self, sender, playerid, name):
        self.players[playerid] = name
        # FIXME: get own playerid by other means
        if name == self.nickname:
            self.playerid = playerid
        
    def _remove_player(self, sender, playerid):
        del self.players[playerid]