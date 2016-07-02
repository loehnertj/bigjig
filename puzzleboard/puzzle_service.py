import logging
L = lambda: logging.getLogger(__name__)

import os

from .puzzle_api import PuzzleAPI
from .puzzle_board import PuzzleBoard


class PuzzleService(object):
    def __init__(self, codec, transport, quit_handler):
        self.transport = transport
        self.api = PuzzleAPI(codec=codec, transport=transport)
        self.quit_handler = quit_handler
        
        self.board = PuzzleBoard()
        self.players = {}
        # player id -> list of grabbed clusters
        self.grabbed_clusters_by_player = {}
        
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
        
    # ---- Player management ----
    
    def on_connect(self, sender, name):
        # TODO: check that the name does not contain evil stuff.
        self.players[sender] = name
        self.grabbed_clusters_by_player[sender] = []
        
    def on_disconnect(self, sender):
        # drop all pieces of sender
        self.on_drop(sender, [cluster.id for cluster in self._get_grabbed(sender)])
        # forget about him
        del self.players[sender]
        del self.grabbed_clusters_by_player[sender]
        
        
    # ---- puzzle load/save/reset ----
    
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
            
    def on_save_puzzle(self, sender):
        if sender!='stdio':
            L().warning('save_puzzle command only allowed from stdio.')
            return
        try:
            self.board.save_state()
        except ValueError as e:
            L().error(e)
        L().info('puzzle state was saved')
            
    def on_restart_puzzle(self, sender):
        if sender!='stdio':
            L().warning('reset_puzzle command only allowed from stdio.')
            return
        self.board.reset_puzzle()
        self.send_clusters(None)
        L().info('puzzle was restarted')
        
    
    # ---- bulk data transmission
    
    def send_puzzle(self, receivers):
        self.api.puzzle(
            receivers,
            puzzle_data = self.board.puzzle_as_jsonstruct(),
            cluster_data = self.board.clusters_as_jsonstruct()
        )
    
    def send_clusters(self, receivers):
        self.api.clusters(
            receivers,
            cluster_data = self.board.clusters_as_jsonstruct()
        )
        
    def on_get_puzzle(self, sender):
        self.send_puzzle(sender)
        
    def on_get_pieces(self, sender, pieces=None):
        if not pieces:
            pieces = [p.id for p in self.board.pieces]
        pixmaps = {}
        for pieceid in pieces:
            try:
                piece = self.board.pieces_by_id[pieceid]
            except KeyError:
                L().warning('%s requested pixmap for nonexisting piece id %d'%(sender, pieceid))
                continue
            path = os.path.join(self.board.imagefolder, piece.image)
            with open(path, "rb") as f:
                pixmaps[piece.id] = f.read()
        self.api.piece_pixmaps(sender, pixmaps=pixmaps)
        
    
    # ---- piece movement ----
    
    def _get_clusters(self, cluster_ids):
        cc = []
        # existing clusters only
        for cluster in self.board.clusters:
            if cluster.id in cluster_ids:
                cc.append(cluster)
        return cc
    
    def _get_grabbed(self, sender):
        if sender not in self.grabbed_clusters_by_player:
            self.grabbed_clusters_by_player[sender] = []
        return self.grabbed_clusters_by_player[sender]
    
    def on_grab(self, sender, clusters):
        clusters = self._get_clusters(clusters)
        # remove all clusters that are grabbed by any player (including sender)
        all_grabbed_clusters = sum(self.grabbed_clusters_by_player.values(), [])
        for cluster in clusters:
            if cluster in all_grabbed_clusters: 
                clusters.remove(cluster)
        
        grabbed_clusters = self._get_grabbed(sender)
        grabbed_clusters += clusters
        
        clusterids = [cluster.id for cluster in clusters]
        L().debug('%s grabbed clusters %s'%(sender, clusterids))
        self.api.grabbed(None, playerid=sender, clusters = clusterids)
        
        
    def on_drop(self, sender, clusters):
        clusters = self._get_clusters(clusters)
        grabbed_clusters = self._get_grabbed(sender)
        clusters = [cluster for cluster in clusters if cluster in grabbed_clusters]
        
        for cluster in clusters:
            grabbed_clusters.remove(cluster)
        
        clusterids = [cluster.id for cluster in clusters]
        L().debug('%s dropped clusters %s'%(sender, clusterids))
        self.api.dropped(None, clusters = clusterids)
        
        # check joins
        for cluster in clusters:
            joinable_clusters = self.board.joinable_clusters(cluster)
            if not joinable_clusters: continue
        
            # drop all joinable clusters and remove from clusters list
            for jc in joinable_clusters:
                for gc in self.grabbed_clusters_by_player.values():
                    if jc in gc:
                        gc.remove(jc)
                        self.api.dropped(None, clusters=[jc.id])
                if jc in clusters:
                    clusters.remove(jc)
                    
            # execute join
            # The new cluster will have the lowest id of all joined clusters.
            clusterid = min([cluster.id for cluster in joinable_clusters+[cluster]])
            jcids = [jc.id for jc in joinable_clusters+[cluster]]
            jcids.remove(clusterid)
            
            self.board.join(joinable_clusters, to_cluster=cluster)
            self.api.joined(None, cluster=clusterid, joined_clusters=jcids, position=cluster.position)
            
    def on_move(self, sender, cluster_positions):
        clusters = self._get_clusters([int(key) for key in cluster_positions.keys()])
        grabbed_clusters = self._get_grabbed(sender)
        clusters = [cluster for cluster in clusters if cluster in grabbed_clusters]
        
        new_positions = {}
        for cluster in clusters:
            pos = cluster_positions[str(cluster.id)]
            self.board.move_cluster(cluster, pos['x'], pos['y'], pos['rotation'])
            new_positions[str(cluster.id)] = cluster.position
        self.api.moved(None, cluster_positions=new_positions)
        
    def on_rearrange(self, sender, clusters, x=None, y=None):
        clusters = self._get_clusters(clusters)
        grabbed_clusters = self._get_grabbed(sender)
        clusters = [cluster for cluster in clusters if cluster in grabbed_clusters]
        
        pos = None
        if x is not None and y is not None:
            pos = (x, y)
        
        self.board.rearrange(clusters, pos)
        new_positions = {
            str(cluster.id): cluster.position
            for cluster in clusters
        }
        self.api.moved(None, cluster_positions=new_positions)