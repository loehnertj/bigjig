import logging
L = lambda: logging.getLogger(__name__)

from puzzleboard.puzzle_api import PuzzleAPI

class PuzzleClient(object):
    def __init__(self, codec, transport):
        self.transport = transport
        self.api = PuzzleAPI(codec=codec, transport=transport)
        self.api.invert()
        self._init_handlers()
        
    def _init_handlers(self):
        '''connect all methods of myself named "on_something"
        to the respective incoming method "something" of the PuzzleAPI.
        '''
        for name in dir(self):
            if name.startswith('on_'):
                try:
                    getattr(self.api, name[3:]).connect(getattr(self, name))
                except AttributeError:
                    raise AttributeError("There is a handler defined for a nonexistent message '%s'"%name[3:])
                
    def quit(self):
        self.api.quit(None)
        
    def connect(self, name):
        self.api.connect(None, name=name)
                
    def on_connected(self, sender, playerid, name):
        L().info("Player connected: {} {}".format(playerid, name))