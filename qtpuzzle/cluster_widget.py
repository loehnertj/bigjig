# -*- coding: utf-8 -*-
import logging as L 
import os

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
        # create dummy pixmap, plain white for now
        pxm = QPixmap(w, h)
        pxm.fill()
        o.setPixmap(pxm)
        
    def setPieceImage(o, rawdata):
        o.img = QImage.fromData(rawdata)
        o._got_image = True
        
    def updateRotation(o, angle_deg):
        if not o._got_image:
            return
        img = o.img.copy(o.img.rect())
        outline(img, illum_angle=-angle_deg-30)
        o.setPixmap(QPixmap.fromImage(img))

class ClusterWidget(QGraphicsWidget):
    def __init__(o, clusterid, pieces):
        super(ClusterWidget, o).__init__()
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
            painter.fillRect(o.boundingRect().adjusted(-5, -5, 5, 5), QColor("lightGray"))
            
    def updatePos(o, cluster, rotations):
        o.setPos(cluster.x, cluster.y)
        o.setRotation(-360.*cluster.rotation/rotations)

    def setRotation(o, angle_deg):
        QGraphicsWidget.setRotation(o, angle_deg)
        for item in o.childItems():
            item.updateRotation(angle_deg)