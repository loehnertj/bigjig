from neatocom.concepts import RemoteAPI, incoming, outgoing

class PuzzleAPI(RemoteAPI):
    @incoming
    def quit(self, sender):
        '''stop the server'''
        pass
    
    # ---- player management ----
    
    @incoming
    def connect(self, sender, name):
        '''registers the given name as alias for the sender.'''
        pass
        
    @outgoing
    def connected(self, receivers, playerid, name):
        '''tells other clients that someone connected.'''
        pass
    
    @incoming
    def disconnect(self, sender):
        '''drops everything that is grabbed by the sender and
        tells the others that he disconnected.
        If sender is connected over TCP, server closes connection afterwards.
        '''
        pass
        
    @outgoing
    def disconnected(self, receivers, playerid):
        '''tells other clients that someone disconnected.'''
        pass
        
        
    # ---- puzzle administration ----
    
    @incoming
    def load_puzzle(self, sender, path):
        '''loads the given puzzle. sender must be stdio.'''
        pass
    
    @incoming
    def save_puzzle(self, sender):
        '''saves the puzzle (i.e. clusters.json). Sender must be stdio.'''
        pass
    
    @incoming
    def restart_puzzle(self, sender):
        '''restarts the puzzle (i.e. rerandomizes clusters.json).'''
        pass
    
    
    
    # ---- bulk data requests ----
    
    @incoming
    def get_puzzle(self, sender):
        '''request to have puzzle.json returned to the sender.'''
        pass
    
    @outgoing
    def puzzle(self, receivers, puzzle_data, cluster_data):
        '''send current puzzle data. Schema:
        puzzle_data : {
            name: str,
            rotations: int,
            pieces: [{id: int, image:str, x0, y0, w, h: int}],
            links: [{id1, id2, x, y: int}]
        }
        cluster_data : {
            clusters: [{x, y, rotation:int, pieces:[int,]}]
        }
        '''
        pass
        
    @outgoing
    def clusters(self, receivers, cluster_data):
        '''send current cluster data (schema see puzzle())
        Broadcast when big changes occur e.g. puzzle reset.
        '''
        pass
        
    @incoming
    def get_pieces(self, sender, pieces=None):
        '''request for the puzzle piece images.
        List of piece ids can be given to request only those pieces.'''
        pass
        
    @outgoing
    def piece_pixmaps(self, receivers, pixmaps):
        '''send puzzle piece images.
        pixmaps is a dict {pieceid: data}, where data are the
        raw bytes of the image file.
        
        !! Note !! The keys are strings.
        '''
        pass
    
    # ---- piece movement ---
    
    @incoming
    def grab(self, sender, clusters):
        '''grabs the given clusters i.e. locks them for the sender. 
        No other player can grab or move those clusters.
        '''
        pass
        
    @outgoing
    def grabbed(self, receivers, clusters, playerid):
        '''Tells other players that clusters were grabbed'''
        pass
        
    @incoming
    def drop(self, sender, clusters):
        '''inverse of grab. Causes join check.'''
        pass
        
    @outgoing
    def dropped(self, receivers, clusters):
        '''Tells other players that the clusters were released.'''
        pass

    @incoming
    def move(self, sender, cluster_positions):
        '''move clusters to new positions.
        cluster_positions is a nested dict:
        {clusterid: {x:, y:, rotation:}}
        '''
        pass
    
    @incoming
    def rearrange(self, sender, clusters, x=None, y=None):
        '''special kind of move, rearranges clusters as grid.'''
        pass
    
    @outgoing
    def moved(self, receivers, cluster_positions):
        '''see move'''
        pass
    
    @outgoing
    def joined(self, receivers, cluster, joined_clusters, position):
        '''on join: joined_clusters (list) are merged into cluster.
        position = {x:, y:, rotation:} gives the new position.'''
        pass
        
    @outgoing
    def solved(self, receivers):
        '''when puzzle is solved.'''
        pass