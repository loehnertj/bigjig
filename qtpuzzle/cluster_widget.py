# -*- coding: utf-8 -*-
import logging as L 
import os
from math import sin, cos, pi

from PyQt4.QtCore import Qt, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QImage, QPixmap, QColor, QStaticText, QStyle
from PyQt4.QtGui import QGraphicsItem, QGraphicsWidget, QGraphicsPixmapItem

from .render_outline import outline

class PieceItem(QGraphicsPixmapItem):
    def __init__(o, parent, pieceid, w, h):
        QGraphicsPixmapItem.__init__(o, parent=parent)
        o.id = pieceid
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
        if not o._got_image:
            return
        img = o.img.copy(o.img.rect())
        outline(img, illum_angle=-angle_deg-30)
        o.setPixmap(QPixmap.fromImage(img))
        
    def copy_to(o, parent):
        '''copies this item to the ClusterWidget parent.'''
        p = PieceItem(parent, o.id, o.img.width(), o.img.height())
        p.img = o.img.copy(o.img.rect())
        p._got_image = True
        p.setPos(o.pos())
        p.updateRotation(parent.rotation())
        return p
        
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
        item = PieceItem(o, piece.id, piece.w, piece.h)
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
            # TODO nicer selection marker
            painter.fillRect(o.boundingRect().adjusted(-5, -5, 5, 5), QColor("lightGray"))
            
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
        if o._grabbed_by is None or o._grabbed_by == client.playerid:
            if not o._grabbed_locally:
                o._last_server_pos = o.pos()
                o._last_server_rotation = o.clusterRotation()
                o._grab_local_ofs = o.pos() - mousePos
                o._grabbed_locally = True
            # piece is now grabbed locally
            return True
        # somebody else is holding the piece, refuse local grab
        return False
    
    def onClusterGrabbed(o, playerid, on_loss):
        '''If playerid is myself, just note the grab. (Local grab not required)
        If playerid is somebody else, call on_loss if l-grabbed, and reset onscreen position.
        '''
        if playerid == o.client.playerid:
            o._grabbed_by = playerid
        else:
            if o._grabbed_locally:
                on_loss(o)
                o._grabbed_locally=False
                pos = o._last_server_pos
                o.setClusterPosition(pos.x(), pos.y(), o._last_server_rotation)
            # TODO: mark the clusters as foreign-grabbed on the screen
    
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