# -*- coding: utf-8 -*-
import logging as L 
import os
from math import sin, cos, pi

from qtpy.QtCore import Qt, QPointF
from qtpy.QtGui import QImage, QPixmap, QColor, QPen, QIcon, QPixmap
from qtpy.QtWidgets import QGraphicsItem, QGraphicsWidget, QGraphicsPixmapItem

from .render_outline import outline

_zvalue = 0.0

class PieceItem(QGraphicsPixmapItem):
    def __init__(o, parent, pieceid, w, h, dominant_colors):
        QGraphicsPixmapItem.__init__(o, parent=parent)
        o.id = pieceid
        o.dominant_colors = dominant_colors
        o.angle_deg = 0
        o.img = None
        o._got_image = False
        # create dummy pixmap, transparent
        pxm = QPixmap(w, h)
        pxm.fill(QColor(0,0,0,0))
        o.setPixmap(pxm)
        o.setTransformationMode(Qt.SmoothTransformation)
        
    def setPieceImage(o, rawdata):
        o.img = QImage.fromData(rawdata)
        o._got_image = True
        
    def updateRotation(o, angle_deg):
        o.angle_deg = angle_deg
        if not o._got_image:
            return
        img = o.img.copy(o.img.rect())
        outline(img, illum_angle=-angle_deg-30)
        o.setPixmap(QPixmap.fromImage(img))
        
    def copy_to(o, parent, rotate=True):
        '''copies this item to the ClusterWidget parent.'''
        p = PieceItem(parent, o.id, o.img.width(), o.img.height(), o.dominant_colors)
        p.angle_deg = o.angle_deg
        p.img = o.img.copy(o.img.rect())
        p._got_image = True
        p.setPos(o.pos())
        if rotate:
            p.updateRotation(parent.rotation())
        else:
            p.setPixmap(o.pixmap())
        return p

    def get_menu_items(o, menu, puzzle_scene, ievent):
        # Offer at most 4 colors
        for color in o.dominant_colors[:4]:
            q_color = QColor(*color)
            colortxt = get_color_name(q_color)
            pixmap = QPixmap(32,32)
            pixmap.fill(QColor(*color))
            icon = QIcon(pixmap)
            def cb(*args, color=color):
                puzzle_scene.select_by_color(color, pos=ievent.lastScenePos)
            a = menu.addAction(icon, "Find %s pieces" % colortxt, cb)
        
class ClusterWidget(QGraphicsWidget):
    def __init__(o, clusterid, pieces, rotations, client):
        super(ClusterWidget, o).__init__()
        o.clusterid = clusterid
        o.rotations = rotations
        o.client = client
        
        # movement bookkeeping
        # whether piece is grabbed locally
        o._grabbed_locally = False
        # playerid who grabs this piece server-side
        o._grabbed_by = None
        
        # position and rotation before local grab (for resetting on grab loss)
        o._last_server_pos = None
        o._last_server_rotation = 0
        o._grab_local_ofs = None
        
        # rotation in steps
        o._clusterRotation = 0
        o.setFlags(QGraphicsItem.ItemIsSelectable)
        for piece in pieces:
            o.add_piece(piece)
            
    def add_piece(o, piece):
        #path = os.path.join(o.puzzle_board.imagefolder, piece.image)
        item = PieceItem(o, piece.id, piece.w, piece.h, piece.dominant_colors)
        item.setPos(piece.x0, piece.y0)
        
    def setPieceImages(o, pixmaps):
        for item in o.childItems():
            pieceid = str(item.id)
            if pieceid in pixmaps:
                item.setPieceImage(pixmaps[pieceid])
                item.updateRotation(o.rotation())
            
    def boundingRect(o):
        return o.childrenBoundingRect()
    
    def paint(o, painter, option, widget):
        QGraphicsWidget.paint(o, painter, option, widget)
        if o.isSelected():
            o.setMarking(painter, QColor(220,220,220,128))
        if o._grabbed_locally:
            o.setMarking(painter, QColor(255,255,255,192))
        elif o._grabbed_by:
            # TODO calculate individual color for each playerid
            o.setMarking(painter, QColor(255,0,0,128))
    
    def setMarking(o, painter, color):
        painter.setPen(QPen(color, 3))
        painter.setBrush(Qt.NoBrush)
        rect = o.boundingRect()
        c = rect.center()
        radius = (rect.width()**2 + rect.height()**2)**0.5 * 0.5
        painter.drawEllipse(c, radius, radius)
            
    def pieceItems(o):
        for item in o.childItems():
            yield item
            
    def setClusterPosition(o, x, y, rotation):
        o.setPos(x, y)
        o.setClusterRotation(rotation)

    def setClusterRotation(o, rotation):
        o._clusterRotation = rotation
        angle_deg = rotation * (-360./o.rotations)
        QGraphicsWidget.setRotation(o, angle_deg)
        for item in o.childItems():
            item.updateRotation(angle_deg)
            
    def clusterRotation(o):
        return o._clusterRotation
    
    def grabLocally(o, mousePos):
        '''Check if the piece can be grabbed, and if yes do it.
        Returns True if piece was grabbed, False if currently blocked.
        '''
        global _zvalue
        if o._grabbed_by is None or o._grabbed_by == client.playerid:
            if not o._grabbed_locally:
                o._last_server_pos = o.pos()
                o._last_server_rotation = o.clusterRotation()
                o._grab_local_ofs = o.pos() - mousePos
                o._grabbed_locally = True
                _zvalue += 1e-4
                o.setZValue(_zvalue)
                o.update()
            # piece is now grabbed locally
            return True
        # somebody else is holding the piece, refuse local grab
        return False
    
    def onClusterGrabbed(o, playerid, on_loss):
        '''If playerid is myself, just note the grab. (Local grab not required)
        If playerid is somebody else, call on_loss if l-grabbed, and reset onscreen position.
        '''
        global _zvalue
        o._grabbed_by = playerid
        if playerid != o.client.playerid:
            _zvalue += 1e-4
            o.setZValue(_zvalue)
            if o._grabbed_locally:
                on_loss(o)
                o._grabbed_locally=False
                pos = o._last_server_pos
                # this will trigger a repaint
                o.setClusterPosition(pos.x(), pos.y(), o._last_server_rotation)
            else:
                o.update()
    
    def onClusterMoved(o, x, y, rotation):
        '''Move the piece to the given position, but only if it is not locally grabbed.
        Also save that pos as server pos.'''
        o._last_server_pos = QPointF(x, y)
        o._last_server_rotation = rotation
        if o._grabbed_locally:
            return
        o.setClusterPosition(x, y, rotation)
    
    def onClusterDropped(o):
        '''reset all grab state'''
        o._grabbed_by = None
        o._grabbed_locally = False
        o.update()
    
    def repositionGrabbedPiece(o, scene_pos, rotate):
        '''position and rotate the piece if grab is valid.
        scene_pos gives the cursor pos (piece should move relative with the cursor).
        rotate gives the number of counterclockwise turns to be made.
        Rotation takes place around the scene_pos.
        '''
        if not o._grabbed_locally:
            return
        
        if rotate:
            ofs = o._grab_local_ofs
            x, y = ofs.x(), ofs.y()
            sinval, cosval = sin(2.*pi*rotate/o.rotations), cos(2.*pi*rotate/o.rotations)
            xr = x * cosval + y * sinval
            yr = -x * sinval + y * cosval
            o._grab_local_ofs = QPointF(xr, yr)
            o.setClusterRotation(o.clusterRotation() + rotate)
        o.setPos(scene_pos + o._grab_local_ofs)

def get_color_name(q_color):
    h = q_color.hsvHue()
    s = q_color.hsvSaturation() / 255.0
    v = q_color.value() / 255.0
    # ...n = ..name
    # saturated hue's name
    if h < 20:
        hn = 'red'
    elif h < 45:
        hn = 'orange' if v > .75 else 'brown'
    elif h < 75:
        hn = 'yellow'
    elif h < 140:
        hn = 'green'
    elif h < 190:
        hn = 'cyan'
    elif h < 260:
        hn = 'blue'
    elif h < 315:
        hn = 'purple'
    elif h < 345:
        hn = 'pink'
    else:
        hn = 'red'
    # Black end
    if v < .1:
        return 'black'
    # Bright end
    if v > .9:
        if s > .75:
            return 'bright %s' % hn
        elif s > .3:
            return 'light %s' % hn
        elif s > .1:
            return '%s-tinted white' % hn
        else:
            return 'bright white'
    # Describe hue-and-saturation
    if s > .75:
        hsn = hn
    elif s > .3:
        hsn = 'pale %s' % hn
    elif s > .1:
        hsn = '%sish gray' % hn
    else:
        hsn = 'gray'
    
    # Describe brightness
    v_shift = v - s / 4.0
    if v_shift > 0.72:
        return 'light %s' % hsn
    elif v_shift > 0.25:
        return hsn
    elif v_shift > 0.0:
        return "dark %s" % hsn
    else:
        return 'very dark %s' % hsn
