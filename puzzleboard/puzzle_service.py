import logging
L = lambda: logging.getLogger(__name__)

from .puzzle_api import PuzzleAPI
from .puzzle_board import PuzzleBoard


class PuzzleService(object):
    def __init__(self, codec, transport, quit_handler):
        self.transport = transport
        self.api = PuzzleAPI(codec=codec, transport=transport)
        self.quit_handler = quit_handler
        
        self.board = PuzzleBoard()
        self.players = {}
        
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
                
    def on_quit(self, sender):
        if sender!='stdio':
            L().warning('quit command only allowed from stdio')
            return
        self.quit_handler()
                
    def on_connect(self, sender, name):
        # TODO: check that the name does not contain evil stuff.
        self.players[sender] = name
        
    def on_disconnect(self, sender):
        # TODO: drop pieces of sender
        del self.players[sender]
        
    def on_load_puzzle(self, sender, path):
        if sender!='stdio':
            L().warning('load_puzzle command only allowed from stdio.')
            return
        board = PuzzleBoard.from_folder(path)
        # FIXME: error check
        if board:
            self.board = board
            L().info('New puzzle was loaded: %s'%path)
            # send new puzzle to all players
            self.send_puzzle(None)
            
    def on_save_puzzle(self, sender, path):
        if sender!='stdio':
            L().warning('save_puzzle command only allowed from stdio.')
            return
        try:
            self.board.save_state()
        except ValueError as e:
            L().error(e)
            
    def on_restart_puzzle(self, sender):
        if sender!='stdio':
            L().warning('reset_puzzle command only allowed from stdio.')
            return
        self.board.reset_puzzle()
        self.send_clusters(None)
    
    def send_puzzle(self, receivers):
        # FIXME
        pass
    
    def send_clusters(self, receivers):
        pass