from random import random

from PyQt4.QtCore import Qt, QPointF, QLineF
from PyQt4.QtGui import QImage, QPainter, QPen, QPainterPath

from .util import nonuniform_rand, dsin, dcos

class GBEngineSettings(object):
    def __init__(o):
        o.piece_count = 30
        o.flip_threshold=.1     # 0 to .5 linear
        o.alternate_flip = False
        o.edge_curviness = -.5  # -1  to 1 linear
        o.plug_size = 1.        # .50 to 1.5 linear
        o.sigma_curviness = .25 # .25 to 1 squared
        o.sigma_basepos = .1225 # .20 to 1 squared
        o.sigma_plugs = .25     # .25 to 1 squared

class GBClassicPlugParams(object):
    def __init__(o, unit_x, length_base, is_straight=False, settings=None):
        '''unit_x: a QLineF connecting start and end.'''
        o.settings = settings or GBEngineSettings()
        o.size_correction = 1.0
        o.length_base = length_base
        o.flipped = (random() < settings.flip_threshold)
        o.is_straight = is_straight
        o._is_plugless = False
        o.unit_x = unit_x
        if is_straight:
            o.startangle = 0.
            o.endangle = 0.
            o.basepos = .5
            o.basewidth = .1
            o.knobsize = .2
            o.knobangle = 25
            o.knobtilt = 0
            o.path_is_rendered = False
        else:
            o.rerandomize_edge(keep_endangles=False, settings=settings, )
            
    @property
    def path(o):
        if not o.path_is_rendered:
            o._path = o.render()
            o.path_is_rendered = True
        return o._path
    
    @property
    def is_plugless(o):
        return o._is_plugless
    
    @is_plugless.setter
    def is_plugless(o, val):
        o._is_plugless = val
        o.size_correction = 1.0
        o.path_is_rendered = False
            
    def rerandomize_edge(o, keep_endangles=False, settings=None):
        settings = settings or o.settings
        if not keep_endangles:
            skew = settings.edge_curviness * 1.5
            # start, end-angle: angle of ctl point at first and last node
            o.startangle = nonuniform_rand(2, -35, settings.sigma_curviness, skew)
            o.endangle = nonuniform_rand(2, -35, settings.sigma_curviness, skew)
            # base roundness: how "curvy" the baseline is. 0..1.
            o.baseroundness = -dsin(min(o.startangle, o.endangle))
            o.baseroundness = max(o.baseroundness, 0.0)
            
        # basepos, basewidth: x-center and distance of base points
        o.basepos = nonuniform_rand(0.2, 0.8, settings.sigma_basepos, 0)
        o.basewidth = nonuniform_rand(0.1, 0.17, settings.sigma_plugs, 0)
        # knobsize: distance of knob ctl points from base points
        o.knobsize = nonuniform_rand(.17, .23, settings.sigma_plugs, 0)
        # knobangle, knobtilt: hard to describe.. they determine width
        # and asymetry of the knob.
        o.knobangle = nonuniform_rand(10., 30., settings.sigma_plugs, 0)
        o.knobtilt = nonuniform_rand(-20., 20., settings.sigma_plugs, 0)
        
        o.path_is_rendered = False
        
    def smooth_join_to(border1, border2):
        found = False
        u1, u2 = border1.unit_x, border2.unit_x
        b1end = (u1.p2() == u2.p1() or u1.p2() == u2.p2())
        b2end = (u2.p2() == u1.p1() or u2.p2() == u1.p2())
        if (u1.p2() if b1end else u1.p1()) != (u2.p2() if b2end else u2.p1()):
            L.warn("GBClassicPlugParams.smooth_join: was asked to smooth between non-adjacent borders.")
            return
        b1end ^= border1.flipped
        b2end ^= border2.flipped

        a1 = border1.endangle if b1end else border1.startangle
        a2 = border2.endangle if b2end else border2.startangle

        if b1end != b2end:
            a1 = 0.5*(a1-a2)
            a2 = -a1
        else:
            a1 = 0.5*(a1+a2)
            a2 = a1

        if b1end: 
            border1.endangle = a1 
        else:
            border1.startangle = a1
        if b2end:
            border2.endangle = a2
        else:
            border2.startangle = a2

        border1.path_is_rendered = False
        border2.path_is_rendered = False

    def intersects(o, other, offenders=None):
        '''check and returns if the plug intersects other.
        if True and offenders is given, appends other to offenders.
        '''
        result = o.path.intersects(other.path)
        if result and offenders is not None:
            offenders.append(other)
        return result
    
    def render(o):
        path = QPainterPath()
        
        # unit_x gives offset and direction of the x base vector. Start and end should be the grid points.

        # move the endpoints inwards an unnoticable bit, so that the intersection detector
        # won't trip on the common endpoint.
        u_x = QLineF(o.unit_x.pointAt(0.0001), o.unit_x.pointAt(0.9999))

        path.moveTo(u_x.p1())

        if o.is_straight:
            path.lineTo(u_x.p2())
            return path
        
        if o.flipped:
            u_x = QLineF(u_x.p2(), u_x.p1())

        u_y = u_x.normalVector()
        # move y unit to start at (0,0).
        u_y.translate(-u_y.p1())

        scaling = o.length_base / u_x.length() * o.size_correction
        if o.basewidth * scaling > 0.8:
            # Plug is too large for the edge length. Make it smaller.
            scaling = 0.8 / o.basewidth

        # some magic numbers here... carefully fine-tuned, better leave them as they are.
        ends_ctldist = 0.4
        #base_lcdist = 0.1 * scaling
        base_ucdist = 0.05 * scaling
        knob_lcdist = 0.6 * o.knobsize * scaling
        knob_ucdist = 0.8 * o.knobsize * scaling

        # set up piece -- here is where the really interesting stuff happens.
        # We will work from the ends inwards, so that symmetry counterparts are adjacent.
        # The QLine.pointAt function is used to transform everything into the coordinate
        # space defined by the us.
        # -- end points

        r1y = ends_ctldist * o.basepos * dsin(o.startangle)
        q6y = ends_ctldist * (1.-o.basepos) * dsin(o.endangle)
        p1 = u_x.p1()
        p6 = u_x.p2()
        r1 = u_x.pointAt(ends_ctldist * o.basepos * dcos(o.startangle)) + u_y.pointAt(r1y)
        q6 = u_x.pointAt(1. - ends_ctldist * (1.-o.basepos) * dcos(o.endangle)) + u_y.pointAt(q6y)

        # -- base points
        p2x = o.basepos - 0.5 * o.basewidth * scaling
        p5x = o.basepos + 0.5 * o.basewidth * scaling

        if p2x < 0.1 or p5x > 0.9:
            # knob to large. center knob on the edge. (o.basewidth * scaling < 0.8 -- see above)
            p2x = 0.5 - 0.5 * o.basewidth * scaling
            p5x = 0.5 + 0.5 * o.basewidth * scaling

        #base_y = r1y > q6y ? r1y : q6y
        #base_y = 0.5*(r1y + q6y)
        base_y = -o.baseroundness * ends_ctldist * min(p2x, 1.-p5x)
        if base_y > 0:
            base_y = 0

        base_lcy = base_y * 2.0

        base_y += base_ucdist/2
        base_lcy -= base_ucdist/2
        #base_lcy = r1y
        #if (q6y < r1y): base_lcy = q6y

        # at least -base_ucdist from base_y
        #if (base_lcy > base_y - base_ucdist): base_lcy = base_y-base_ucdist

        q2 = u_x.pointAt(p2x) + u_y.pointAt(base_lcy)
        r5 = u_x.pointAt(p5x) + u_y.pointAt(base_lcy)
        p2 = u_x.pointAt(p2x) + u_y.pointAt(base_y)
        p5 = u_x.pointAt(p5x) + u_y.pointAt(base_y)
        r2 = u_x.pointAt(p2x) + u_y.pointAt(base_y + base_ucdist)
        q5 = u_x.pointAt(p5x) + u_y.pointAt(base_y + base_ucdist)

        if o._is_plugless:
            if not o.flipped:
                path.cubicTo(r1, q2, p2)
                path.cubicTo(r2, q5, p5)
                path.cubicTo(r5, q6, p6)
            else:
                path.cubicTo(q6, r5, p5)
                path.cubicTo(q5, r2, p2)
                path.cubicTo(q2, r1, p1)
            return path

        # -- knob points
        p3x = p2x - o.knobsize * scaling * dsin(o.knobangle - o.knobtilt)
        p4x = p5x + o.knobsize * scaling * dsin(o.knobangle + o.knobtilt)
        # for the y coordinate, knobtilt sign was swapped. Knobs look better this way...
        # like x offset from base points y, but that is 0.
        p3y = o.knobsize * scaling * dcos(o.knobangle + o.knobtilt) + base_y
        p4y = o.knobsize * scaling * dcos(o.knobangle - o.knobtilt) + base_y

        q3 = u_x.pointAt(p3x) + u_y.pointAt(p3y - knob_lcdist)
        r4 = u_x.pointAt(p4x) + u_y.pointAt(p4y - knob_lcdist)
        p3 = u_x.pointAt(p3x) + u_y.pointAt(p3y)
        p4 = u_x.pointAt(p4x) + u_y.pointAt(p4y)
        r3 = u_x.pointAt(p3x) + u_y.pointAt(p3y + knob_ucdist)
        q4 = u_x.pointAt(p4x) + u_y.pointAt(p4y + knob_ucdist)

        # done setting up. construct path.
        # if flipped, add points in reverse.
        if not o.flipped:
            path.cubicTo(r1, q2, p2)
            path.cubicTo(r2, q3, p3)
            path.cubicTo(r3, q4, p4)
            path.cubicTo(r4, q5, p5)
            path.cubicTo(r5, q6, p6)
        else:
            path.cubicTo(q6, r5, p5)
            path.cubicTo(q5, r4, p4)
            path.cubicTo(q4, r3, p3)
            path.cubicTo(q3, r2, p2)
            path.cubicTo(q2, r1, p1)
        return path



class GoldbergEngine(object):
    def __init__(o, add_piece_func, add_relation_func, settings=None):
        o.add_piece_func = add_piece_func
        o.add_relation_func = add_relation_func
        o.settings = settings or GBEngineSettings()
        
    def __call__(o, gridfunc, piece_count, image_width, image_height):
        p = QPainterPath(QPointF(0.0, 0.0))
        p.lineTo(QPointF(image_width, 0.0))
        p.lineTo(QPointF(image_width, image_height))
        p.lineTo(QPointF(0.0, image_height))
        p.closeSubpath()
        o._boundary_path = p
        gridfunc(o, piece_count, image_width, image_height)
        
    def init_edge(o, unit_x, length_base, is_straight=False):
        return GBClassicPlugParams(
            unit_x=unit_x,
            length_base=length_base,
            is_straight=is_straight,
            settings=o.settings
        )
    
    def out_of_bounds(o, plug):
        return (not o._boundary_path.contains(plug.path))

    
    def add_relation(o, piece_id_1, piece_id_2):
        o.add_relation_func(piece_id_1, piece_id_2)

    def make_piece_from_path(o, piece_id, qpainter_path):
        # generate the mask, and call back to actually create the piec.
        path = qpainter_path
        path.closeSubpath()
        #determine the required size of the mask
        mask_rect = path.boundingRect().toAlignedRect()
        #create the mask
        mask = QImage(mask_rect.size(), QImage.Format_ARGB32_Premultiplied)
        # fully transparent color
        mask.fill(0x00000000)
        
        painter = QPainter(mask)
        painter.translate(-mask_rect.topLeft())
        #we explicitly use a pen stroke in order to let the pieces overlap a bit (which reduces rendering glitches at the edges where puzzle pieces touch)
        # 1.0 still leaves the slightest trace of a glitch. but making the stroke thicker makes the plugs appear non-matching even when they belong together.
        # 2016-06-18: changed to 0.5 -- bevel looks better
        painter.setPen(QPen(Qt.black, 0.5))
        painter.setBrush(Qt.black)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPath(path)
        painter.end()
        
        o.add_piece_func(
            piece_id=piece_id,
            mask_image=mask, 
            offset=mask_rect.topLeft()
        )
    
    def add_plug_to_path(o, qpainter_path, plug_params, reverse=False):
        if reverse:
            qpainter_path.connectPath(plug_params.path.toReversed())
        else:
            qpainter_path.connectPath(plug_params.path)
            
    def _test__2piece_simple(o, image_width, image_height):
        id1, id2 = 1, 2
        
        from PyQt4.QtCore import QPointF
        from PyQt4.QtGui import QPainterPath
        path1 = QPainterPath()
        path1.moveTo(QPointF(0, 0))
        path1.lineTo(QPointF(image_width*.3, 0))
        path1.lineTo(QPointF(image_width*0.7, image_height))
        path1.lineTo(QPointF(0, image_height))
        path1.lineTo(QPointF(0, 0))
        o.make_piece_from_path(id1, path1)
        
        path2 = QPainterPath()
        path2.moveTo(QPointF(image_width, 0))
        path2.lineTo(QPointF(image_width, image_height))
        path2.lineTo(QPointF(image_width*0.7, image_height))
        path2.lineTo(QPointF(image_width*.3, 0))
        path2.lineTo(QPointF(image_width, 0))
        o.make_piece_from_path(id2, path2)
        
        o.add_relation(id1, id2)
    
    def _test_gridfunc(o, ge, image_width, image_height):
        id1, id2 = 1, 2
        length_base = image_height
        # define raster points
        p1 = QPointF(0., 0.)
        p2 = QPointF(image_width/2., 0.)
        p3 = QPointF(image_width, 0.)
        p4 = QPointF(0., image_height)
        p5 = QPointF(image_width/2., image_height)
        p6 = QPointF(image_width, image_height)
        # generate edges
        middle_edge = ge.init_edge(QLineF(p2, p5), length_base)
        
        # piece1
        p = QPainterPath()
        p.moveTo(p1)
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p1, p2), length_base, is_straight=True))
        ge.add_plug_to_path(p, middle_edge)
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p5, p4), length_base, is_straight=True))
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p4, p1), length_base, is_straight=True))
        ge.make_piece_from_path(id1, p)
        
        # piece2
        p = QPainterPath()
        p.moveTo(p2)
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p2, p3), length_base, is_straight=True))
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p3, p6), length_base, is_straight=True))
        ge.add_plug_to_path(p, ge.init_edge(QLineF(p6, p5), length_base, is_straight=True))
        ge.add_plug_to_path(p, middle_edge, reverse=True)
        ge.make_piece_from_path(id2, p)
        
        ge.add_relation(id1, id2)