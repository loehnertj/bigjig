import logging
import inspect
L = lambda: logging.getLogger(__name__)

from puzzleboard.puzzle_api import PuzzleAPI

class PuzzleClient(PuzzleAPI):
    def __init__(self, codec, transport):
        PuzzleAPI.__init__(self, codec=codec, transport=transport)
        self.invert()