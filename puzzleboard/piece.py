import json

class Piece(object):
    def __init__(o, id=0, image='', x0=0, y0=0, w=0, h=0, cluster=None, **kwargs):
        o.id = id
        o.image = image
        o.x0 = x0
        o.y0 = y0
        o.w = w
        o.h = h
        o.cluster = cluster
        
    @classmethod
    def from_jsonstruct(cls, struct):
        return cls(**struct)
    
    def as_jsonstruct(o):
        return {
            'id': o.id,
            'image': o.image,
            'x0': o.x0, 
            'y0': o.y0,
            'w': o.w,
            'h': o.h,
        }