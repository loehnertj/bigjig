import json

class Link(object):
    def __init__(o, id1, id2, x=0, y=0, **kwargs):
        o.id1 = id1
        o.id2 = id2
        o.x = x
        o.y = y
        
    @classmethod
    def from_jsonstruct(cls, struct):
        return cls(**struct)
    
    def reversed(o):
        return Link(id1=o.id2, id2=o.id1, x=0, y=0)
    
    def as_jsonstruct(o):
        return {
            'id1': o.id1,
            'id2': o.id2,
            'x': o.x, 
            'y': o.y,
        }