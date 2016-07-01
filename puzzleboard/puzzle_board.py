import os
import logging as L
import json

from random import shuffle, randint
from .piece import Piece
from .cluster import Cluster
from .link import Link

SNAP_DISTANCE = 40

def as_jsonstring(o):
    def obj2json(obj):
        try:
            return obj.as_jsonstruct()
        except AttributeError:
            raise TypeError("object is missing the as_jsonstruct method: %r"%obj)
    return json.dumps(o, default=obj2json, indent=2)

class PuzzleBoard(object):
    def __init__(o, name='', rotations=1, pieces=None, links=None, **kwargs):
        o.name = name
        o.rotations = rotations
        o.pieces = list(pieces or [])
        o.pieces_by_id = {p.id:p for p in o.pieces}
        o.links = links or []
        o.init_clusters()
        o.basefolder = ''
        o.imagefolder = ''
        o.on_changed = (lambda:None)
    
    @classmethod
    def from_folder(cls, foldername):
        L.debug('PuzzleBoard.from_folder: FIXME: Error handling')
        with open(os.path.join(foldername, 'puzzle.json'), 'r') as f:
            puzzle = cls.from_jsonstring(f.read())
            puzzle.basefolder = foldername
            puzzle.imagefolder = os.path.join(foldername, 'pieces')
        clustersfile = os.path.join(foldername, 'clusters.json')
        if os.path.exists(clustersfile):
            try:
                with open(clustersfile, 'r') as f:
                    puzzle.clusters_from_jsonstring(f.read())
            except ValueError:
                L.error('PuzzleBoard.from_folder: clusters file is corrupt.')
        return puzzle
        
    @classmethod
    def from_jsonstring(cls, jsonstring):
        return cls.from_jsonstruct(json.loads(jsonstring))
    
    @classmethod
    def from_jsonstruct(cls, struct):
        pieces = list(map(Piece.from_jsonstruct, struct['pieces']))
        links = list(map(Link.from_jsonstruct, struct['links']))
        #links = links + [l.reversed() for l in links]
        result = cls(name=struct['name'], rotations=struct['rotations'], pieces=pieces, links=links)
        return result
    
    def clusters_from_jsonstring(o, jsonstring):
        o.clusters_from_jsonstruct(json.loads(jsonstring))
        
    def clusters_from_jsonstruct(o, jsonstruct):
        o.clusters = [
            Cluster.from_jsonstruct(js, pieces_by_id=o.pieces_by_id, rotations=o.rotations)
            for js in jsonstruct['clusters']
        ]
        o._clusters_changed()
    
    def init_clusters(o):
        o.clusters = [
            Cluster(x=0, y=0, pieces=[piece], rotation=0, rotations=o.rotations)
            for piece in o.pieces
        ]
        o._clusters_changed()
    
    def _clusters_changed(o):
        for cluster in o.clusters:
            for piece in cluster:
                piece.cluster = cluster
        
    def save_state(o):
        if not o.basefolder:
            raise ValueError('State cannot be saved without base folder')
        clusterfile = os.path.join(o.basefolder, 'clusters.json')
        with open(clusterfile, 'w') as f:
            f.write(as_jsonstring(o.clusters_as_jsonstruct()))
            
    def clusters_as_jsonstruct(o):
        return {
            'clusters': [cluster.as_jsonstruct() for cluster in o.clusters],
        }
    
    def puzzle_as_jsonstruct(o):
        return {
            'name': o.name,
            'rotations': o.rotations,
            'pieces': [piece.as_jsonstruct() for piece in o.pieces],
            'links': [link.as_jsonstruct() for link in o.links],
        }
    
    def save_puzzle(o):
        if not o.basefolder:
            raise ValueError('Puzzle has no basefolder set.')
        puzzlefile = os.path.join(o.basefolder, 'puzzle.json')
        with open(puzzlefile, 'w') as f:
            f.write(as_jsonstring(o.puzzle_as_jsonstruct()))
            
    
    def move_cluster(o, cluster, x, y, rotation):
        cluster.x = x
        cluster.y = y
        cluster.rotation = rotation
        L.info('moved cluster %s to %r, %r * %r'%([p.id for p in cluster.pieces], x, y, rotation))
        o.on_changed()
        
    def joinable_clusters(o, cluster):
        pids = {piece.id for piece in cluster}
        links = {l for l in o.links if l.id1 in pids or l.id2 in pids}
        linked_clusters = {o.pieces_by_id[link.id1].cluster for link in links}
        linked_clusters |= {o.pieces_by_id[link.id2].cluster for link in links}
        result = []
        for linked_cluster in linked_clusters:
            if linked_cluster is cluster: continue
            if (
                abs(cluster.x-linked_cluster.x) < SNAP_DISTANCE 
                and abs(cluster.y-linked_cluster.y) < SNAP_DISTANCE
                and cluster.rotation == linked_cluster.rotation
            ):
                result.append(linked_cluster)
        return result
    
    def join(o, clusters, to_cluster):
        '''joins pieces from all clusters in clusters to to_cluster.
        clusters in clusters become invalid.
        position of to_cluster changes to the cluster with the most pieces position.
        '''
        anchor = max(clusters+[to_cluster], key=lambda c: len(c.pieces))
        to_cluster.x, to_cluster.y, to_cluster.rotation = anchor.x, anchor.y, anchor.rotation
        for cluster in clusters:
            to_cluster.pieces.extend(cluster.pieces)
            o.clusters.remove(cluster)
        for piece in to_cluster.pieces:
            piece.cluster = to_cluster
        L.debug('clusters after join: %r'%[c.as_jsonstruct() for c in o.clusters])
        o.on_changed()
        
    def reset_puzzle(o):
        o.init_clusters()
        clusters = o.clusters[:]
        shuffle(clusters)
        for cluster in clusters:
            cluster.rotation = randint(0, o.rotations-1)
        o._rearrange(clusters)
        o.on_changed()
        
    def rearrange(o, clusters, pos=None):
        o._rearrange(clusters, pos)
        o.on_changed()
        
    def _rearrange(o, clusters, pos=None):
        clusters = [c for c in clusters if len(c.pieces) == 1]
        pieces = [c.pieces[0] for c in clusters]
        # calculate maximum piece diagonal (squared)
        maxdgsq = max((p.w*p.w + p.h*p.h for p in pieces))
        # no matter how you rotate a piece, it will never be higher or wider
        # than its diagonal. so choose this value as pitch.
        pitch = maxdgsq ** 0.5
        # try to achieve roughly square aspect.
        pieces_per_row = max(int(len(clusters)**0.5), 1)
        if not pos:
            # try to keep center of mass
            x = sum((cluster.x for cluster in clusters)) / len(clusters)
            y = sum((cluster.y for cluster in clusters)) / len(clusters)
        else:
            x, y = pos
        x -= pitch * (pieces_per_row -0.5) * 0.5
        y -= pitch * (pieces_per_row - 0.5) * 0.5
        x0 = x
        n_in_row = 0
        for cluster in clusters:
            p = cluster.pieces[0]
            xc, yc  = cluster.rotate(-p.x0 - 0.5*p.w, -p.y0 - 0.5*p.h)
            cluster.x = x + xc
            cluster.y = y + yc
            x += pitch
            n_in_row += 1
            if n_in_row >= pieces_per_row:
                x = x0
                y += pitch
                n_in_row = 0