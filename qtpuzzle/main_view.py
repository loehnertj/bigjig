import logging as L

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QGraphicsView
from qtpy.QtOpenGL import QGLWidget

from .input_tracker import InputTracker

class MainView(QGraphicsView):
    def __init__(self, *args):
        QGraphicsView.__init__(self, *args)
        #self._input_tracker = InputTracker(self, accepts=[Qt.Key_Space])
        # geht nich -- Fehler & weisses Fenster -- Bug in Ubuntu
        self.gl_widget = QGLWidget()
        self.setViewport(self.gl_widget)
        #self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.HighQualityAntialiasing)
        self._is_view_all = False
        self.setMouseTracking(True)
        self.pan_active = False
        self._prev_mouse_pos = None
        self._last_zoom_level = 1.0
        
    def resizeEvent(self, ev):
        pass
        
    def wheelEvent(self, ev):
        self.lastMouseMoveScenePoint = self.mapToScene(ev.pos())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        delta = 2 ** (ev.angleDelta().y() / 240.)
        self.scale(delta, delta)
        self._is_view_all = False
        
    def viewAll(self):
        self._last_zoom_level = self.transform().m11()
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        self._is_view_all = True
        
    def zoomOnMouse(self):
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.resetTransform()
        self.scale(self._last_zoom_level, self._last_zoom_level)
        self._is_view_all=False
        
    def isViewAll(self):
        return self._is_view_all
    
    def toggleZoom(self):
        if self.isViewAll():
            self.zoomOnMouse()
        else:
            self.viewAll()
            
    def togglePan(self, pan):
        if self.pan_active==pan:
            return
        self.pan_active = pan
        
    def mouseMoveEvent(self, ev):
        QGraphicsView.mouseMoveEvent(self, ev)
        if self.pan_active and self._prev_mouse_pos:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            delta = ev.pos() - self._prev_mouse_pos
            delta /= self.transform().m11()
            self.translate(delta.x(), delta.y())
            self._is_view_all = False
        self._prev_mouse_pos = ev.pos()
