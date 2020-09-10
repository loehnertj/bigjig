# -*- coding: utf-8 -*-
"""a QGraphicScene"""

import os
import logging
from time import time
from random import shuffle

from PyQt4.QtCore import Qt, QPointF, QSizeF, QSize, QRectF
from PyQt4.QtGui import QBrush, QColor, QPen, QPixmap
from PyQt4.QtGui import QGraphicsScene, QGraphicsRectItem
from PyQt4.QtGui import QMenu, QAction


from .input_tracker import InputTracker
from .cluster_widget import ClusterWidget
from .select_by_color_dlg import select_by_color_dlg
#from puzzleboard.puzzle_board import PuzzleBoard


L = lambda: logging.getLogger(__name__)

KEYS = {
    # non-drag actions
    'grab': [Qt.LeftButton, Qt.Key_Space],
    'sel_clear': [Qt.Key_W, Qt.MiddleButton],
    'ctxmenu': [Qt.Key_E],
    'rotate_CW': [Qt.RightButton, Qt.Key_D],
    'rotate_CCW': [Qt.Key_A],
    'zoom': [Qt.Key_Q],

    # drag actions
    'pan': [Qt.LeftButton, Qt.Key_Space],
    'deselect': [Qt.Key_W, Qt.MiddleButton],

    # both
    'select': [Qt.RightButton, Qt.Key_S],
    
    'fullscreen': [Qt.Key_Escape],
}

# in seconds
MOVE_SEND_INTERVAL = 0.2

class PuzzleScene(QGraphicsScene):
    @property
    def grab_active(o):
        return bool(o.grabbed_widgets)
    
    def __init__(o, parent, puzzle_client, mainwindow, *args):
        QGraphicsScene.__init__(o, parent, *args)
        o._input_tracker = InputTracker(o, accepts=sum(KEYS.values(), []))

        o.setBackgroundBrush(QBrush(QColor("darkGray")))
        o.client = puzzle_client
        o.mainwindow = mainwindow
        o.cluster_map = {}
        
        # connect my events
        o.client.puzzle.connect(o._display_puzzle)
        o.client.piece_pixmaps.connect(o._set_piece_pixmaps)
        o.client.clusters.connect(o.OnClustersChanged)
        o.client.grabbed.connect(o.onClustersGrabbed)
        o.client.moved.connect(o.onClustersMoved)
        o.client.dropped.connect(o.onClustersDropped)
        o.client.joined.connect(o.onClustersJoined)
        # request puzzle data from server
        o.client.get_puzzle()

        # init piece movement
        o.rotations = 1 # number of rotations that the puzzle allows
        # List of cluster (widgets) that have been grabbed locally. dict clusterid -> ClusterWidget
        o.grabbed_widgets = {}
        # number of rotations (relative to initial rotation) having been applied to the grabbed widgets.
        o._move_rotation = 0
        # time of last position update (for rate limit)
        o._last_move_send_time = 0

        # init selection
        o._drag_start = None
        o._rubberband = QGraphicsRectItem(QRectF(0., 0., 100., 100.))
        p = QPen(QColor(255,255,255))
        o._rubberband.setPen(p)
        o._rubberband.hide()
        o.addItem(o._rubberband)

    def _display_puzzle(o, sender, puzzle_data, cluster_data):
        L().debug('display new puzzle')
        items = list(o.cluster_map.items())
        for key, cw in items:
            del o.cluster_map[key]
            o.removeItem(cw)
        o.grabbed_widgets = {}
        o.rotations = puzzle_data.rotations
        pieces = {piece.id: piece for piece in puzzle_data.pieces}
        # "Task list" for piece image retrieval.
        # Shuffle so that the loading order does not reveal
        # piece positions.
        o._pieces_to_get = list(pieces.keys())
        shuffle(o._pieces_to_get)
        o._create_clusters(cluster_data, piece_defs=pieces)
        o.updateSceneRect()
        o.parent().viewAll()
        # request piece images from the api
        o._get_next_pieces()
        
    def OnClustersChanged(o, sender, cluster_data):
        L().debug('clusters changed')
        pieces = {}
        for cw in o.cluster_map.values():
            for piece in cw.pieceItems():
                pieces[piece.id] = piece
        o.grabbed_widgets = {}
        old_clusters = list(o.cluster_map.values())
        o.cluster_map = {}
        o._create_clusters(cluster_data, piece_items=pieces)
        for cw in old_clusters:
            o.removeItem(cw)
        o.updateSceneRect()
        
    def _create_clusters(o, cluster_data, piece_defs=None, piece_items=None):
        pieces = []
        for cluster in cluster_data.clusters:
            if piece_defs:
                pieces = [piece_defs[pid] for pid in cluster.pieces]
            cw = ClusterWidget(
                clusterid=cluster.id,
                pieces=pieces,
                rotations=o.rotations,
                client=o.client
            )
            if piece_items:
                for pid in cluster.pieces:
                    piece_items[pid].copy_to(cw)
            o.addItem(cw)
            o.cluster_map[cluster.id] = cw
            cw.setClusterPosition(cluster.x, cluster.y, cluster.rotation)
        
    def _get_next_pieces(o):
        if o._pieces_to_get:
            p = o._pieces_to_get[:10]
            del o._pieces_to_get[:10]
            o.client.get_pieces(pieces=p)
        
    def _set_piece_pixmaps(o, sender, pixmaps):
        for cw in o.cluster_map.values():
            cw.setPieceImages(pixmaps)
        o._get_next_pieces()

    def get_menu_items(o, menu, iev):
        if o.selectedItems():
            a = menu.addAction(
                'Rearrange selection',
                lambda *args: o.selectionRearrange(pos=iev.lastScenePos)
            )

    def select_by_color(o, color):
        # If a selection exists, restrict to selected pieces.
        clusters = o.selectedItems()
        if not clusters:
            clusters = list(o.cluster_map.values())

        # Only select among unconnected pieces.
        pieceItems = [
            items[0]
            for cw in clusters
            for items in [list(cw.pieceItems())]
            if len(items) == 1
        ]
        piece_ids = select_by_color_dlg(color, pieceItems)
        piece_ids = set(piece_ids)
        for cw in o.cluster_map.values():
            pieces = list(cw.pieceItems())
            cw.setSelected(
                len(pieces) == 1 and pieces[0].id in piece_ids
            )


    # Piece movement #######################################
    def toggle_grab_mode(o, scene_pos, grab_active=None):
        if grab_active is None:
            grab_active = not o.grab_active
        if o.grabbed_widgets:
            if grab_active: return
            o.dropGrabbedWidgets()
        else:
            if not grab_active: return
            o.tryGrabWidgets(scene_pos)

    def tryGrabWidgets(o, scene_pos):
        item = o.itemAt(scene_pos)
        if item:
            widget = item.parentWidget()
            if widget.isSelected():
                # lift all selected clusters
                widgets = o.selectedItems()
            else:
                widgets = [widget]
            o.grabbed_widgets = {}
            for widget in widgets:
                if widget.grabLocally(scene_pos):
                    o.grabbed_widgets[widget.clusterid] = widget
            o._move_rotation = 0
            o._last_move_send_time = time()
            if o.grabbed_widgets:
                # send grab to the server
                ids = list(o.grabbed_widgets.keys())
                o.client.grab(clusters=ids)
        L().debug("lift: " + o.grabbed_widgets.__repr__())

    def dropGrabbedWidgets(o):
        # Send last position unconditionally
        o.sendPositions()
        o.client.drop(clusters=list(o.grabbed_widgets.keys()))
        o.grabbed_widgets = {}
        L().debug('dropped')
        o.updateSceneRect()

    def repositionGrabbedPieces(o, scene_pos, rotate=0):
        '''update position on screen (e.g. on mouse move).
        rotate = number of rotation steps to take (once)
        Send position update if timer allows.
        '''
        for widget in o.grabbed_widgets.values():
            widget.repositionGrabbedPiece(scene_pos, rotate)
        t = time()
        if t-o._last_move_send_time > MOVE_SEND_INTERVAL:
            o.sendPositions()
            o._last_move_send_time = t
        # disabled - leads to endless recursion due to triggering mouse move event
        #o.updateSceneRect()
            
    def sendPositions(o):
        positions = {}
        for widget in o.grabbed_widgets.values():
            new_pos = widget.pos()
            rotation = widget.clusterRotation() % widget.rotations
            if rotation<0:
                rotation += widget.rotations
            positions[str(widget.clusterid)] = {'x': new_pos.x(), 'y': new_pos.y(), 'rotation': rotation}
        o.client.move(cluster_positions=positions)
        
    def selectionRearrange(o, pos=None):
        items = o.selectedItems()
        clusters = [i.clusterid for i in items]
        # FIXME: get center of mass from clusters
        x, y = (pos.x(), pos.y()) if pos else (0., 0.)
        # fixme: order by position
        o.client.grab(clusters=clusters)
        # Clusters are not notified of being grabbed. The moved() message triggered by rearrange() will move them on-screen.
        o.client.rearrange(clusters=clusters, x=x, y=y)
        o.client.drop(clusters=clusters)
        o.updateSceneRect()
        
    def updateSceneRect(o):
        r = o.itemsBoundingRect()
        w, h = r.width(), r.height()
        a = .1
        r = r.adjusted(-w*a, -h*a, w*a, h*a)
        o.setSceneRect(r)
    
    # Server messages #############################
    def onClustersGrabbed(o, sender, clusters, playerid):
        '''Server notifies that somebody (maybe me) has grabbed clusters.'''
        def on_loss(widget):
            '''called if the cluster was lost i.e. grabbed by somebody else.'''
            try:
                del o.grabbed_widgets[widget.clusterid]
            except KeyError:
                L().debug('lost cluster %d which was not grabbed in the first place!?'%widget.clusterid)
        for clusterid in clusters:
            o.cluster_map[clusterid].onClusterGrabbed(playerid=playerid, on_loss=on_loss)
    
    def onClustersMoved(o, sender, cluster_positions):
        '''Server notifies that somebody (maybe me) has moved clusters.'''
        for clusterid, position in cluster_positions.items():
            o.cluster_map[int(clusterid)].onClusterMoved(
                x=position.x,
                y=position.y,
                rotation=position.rotation
            )
    
    def onClustersDropped(o, sender, clusters):
        for clusterid in clusters:
            o.cluster_map[clusterid].onClusterDropped()
    
    def onClustersJoined(o, sender, cluster, joined_clusters, position):
        dst = o.cluster_map[cluster]
        for clusterid in joined_clusters:
            cw = o.cluster_map[clusterid]
            # reparent piece images
            for item in cw.pieceItems():
                item.copy_to(dst)
            # delete item
            if cw in o.grabbed_widgets:
                del o.grabbed_widgets[cw.clusterid]
            del o.cluster_map[cw.clusterid]
            o.removeItem(cw)
        # update position from puzzleboard
        dst.setClusterPosition(x=position.x, y=position.y, rotation=position.rotation)
            
    # events ################################
    def mouseMoveEvent(o, ev):
        QGraphicsScene.mouseMoveEvent(o, ev)
        o._input_tracker.mouseMoveEvent(ev)
        if o.grab_active:
            o.repositionGrabbedPieces(ev.scenePos())
            
    # disable default behaviour
    def mouseDoubleClickEvent(o, ev):
        pass
            
    def onInputDown(o, iev):
        if iev.key in KEYS['rotate_CW']+KEYS['rotate_CCW']:
            # if no pieces are grabbed, try to get some
            if not o.grab_active and iev.key!=Qt.RightButton:
                o.toggle_grab_mode(iev.startScenePos)
            if o.grab_active:
                o.repositionGrabbedPieces(
                    iev.startScenePos, 
                    -1 if (iev.key in KEYS['rotate_CW']) else 1
                )
        elif iev.key in KEYS['zoom']:
            o.parent().toggleZoom()
            
        elif iev.key in KEYS['fullscreen']:
            L().info(iev.key)
            o.mainwindow.toggle_fullscreen('toggle')
    
    def onInputMove(o, iev):
        if iev.isDrag:
            if iev.key in KEYS['select']+KEYS['deselect']:
                if not o.grab_active:
                    # continuously update drag
                    o._drag_start = iev.startScenePos
                    o._rubberband.setRect(QRectF(o._drag_start, iev.lastScenePos).normalized())
                    o._rubberband.show()
            if iev.key in KEYS['pan']:
                o.parent().togglePan(True)
    
    def onInputUp(o, iev):
        if iev.isDrag:
            if iev.key in KEYS['select']+KEYS['deselect']:
                frame = QRectF(o._drag_start, iev.lastScenePos).normalized()
                items = o.items(frame, Qt.ContainsItemBoundingRect, Qt.AscendingOrder)
                # deselect on Shift+Select or Deselect key.
                select = True
                if iev.key in KEYS['deselect'] or (iev.modifiers & Qt.ShiftModifier):
                    select=False
                for item in items:
                    if not isinstance(item, ClusterWidget): continue
                    item.setSelected(select)
                o._drag_start = None
                o._rubberband.hide()
            if iev.key in KEYS['pan']:
                o.parent().togglePan(False)
        else:
            if iev.key in KEYS['select']:
                if not o.grab_active:
                    item = o.itemAt(iev.startScenePos)
                    if not item: return
                    widget = item.parentWidget()
                    widget.setSelected(not widget.isSelected())
            elif iev.key in KEYS['sel_clear']:
                o.clearSelection()
            elif iev.key in KEYS['grab']:
                o.toggle_grab_mode(iev.startScenePos)
            elif iev.key in KEYS['ctxmenu']:
                pos = iev.startScenePos
                piece_item = o.itemAt(iev.startScenePos)
                menu = QMenu()
                o.get_menu_items(menu, iev)
                if piece_item:
                    piece_item.get_menu_items(menu, o)
                menu.popup(iev.startScreenPos)
                # store the variable, so it doesn't get GC'ed
                o.__menu = menu
