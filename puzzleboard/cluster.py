from math import sin, cos, pi
import json

class Cluster(object):
    @property
    def id(o):
        return min(piece.id for piece in o.pieces)
    
    @property
    def position(o):
        return {
            'x': o.x,
            'y': o.y,
            'rotation': o.rotation,
        }
            
    def __init__(o, x=0, y=0, rotation=0, rotations=0, pieces=None, **kwargs):
        o.x = x
        o.y = y
        o.rotation = rotation
        o.rotations = rotations
        o.pieces = pieces or []
        
    @classmethod
    def from_jsonstruct(cls, struct, pieces_by_id, rotations):
        struct = struct.copy()
        struct['pieces'] = [pieces_by_id[id] for id in struct['pieces']]
        return cls(rotations=rotations, **struct)
    
    def as_jsonstruct(o):
        return {
            'x': o.x, 
            'y': o.y,
            'rotation': o.rotation,
            'pieces': [piece.id for piece in o.pieces],
        }
    
    def __iter__(o):
        return o.pieces.__iter__()
    
    def rotate(o, x, y, rotation=None):
        if rotation is None:
            rotation = o.rotation
        sinval, cosval = sin(2.*pi*rotation/o.rotations), cos(2.*pi*rotation/o.rotations)
        xr = x * cosval + y * sinval
        yr = -x * sinval + y * cosval
        return xr, yr
    
    def __str__(o):
        return '%s'%o.as_jsonstruct()