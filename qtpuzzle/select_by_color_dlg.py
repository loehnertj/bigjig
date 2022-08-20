from math import sin, cos, pi
from qtpy.QtCore import Qt, QPointF
from qtpy.QtGui import QColor, QBrush, QPen
from qtpy.QtWidgets import QDialog, QGraphicsScene, QGraphicsView, QVBoxLayout, QGraphicsWidget
from qtpy.QtOpenGL import QGLWidget

def select_by_color_dlg(color, pieceItems):
    d = SelectByColorDlg(color, pieceItems)
    d.setWindowFlags(Qt.Dialog | Qt.Tool)
    accepted = d.exec()
    if accepted:
        print('select %d items' % len(d.selected_item_ids))
        return d.selected_item_ids
    else:
        return []

class _RootItem(QGraphicsWidget):
    def __init__(self, color):
        super().__init__()
        self._color = QColor(*color)
        self.sel_size = 1

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        self._paint_circle(painter)

    def _paint_circle(self, painter):
        painter.setPen(QPen(self._color, 3))
        painter.setBrush(Qt.NoBrush)
        radius = self.sel_size
        painter.drawEllipse(QPointF(0, 0), radius, radius)

class _MyView(QGraphicsView):
    def wheelEvent(self, ev):
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        delta = 2 ** (ev.angleDelta().y() / 240.)
        self.scale(delta, delta)

    def showEvent(self, event):
        #self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        self.centerOn(0., 0.)
    
    def mouseMoveEvent(self, event):
        pos = event.pos()
        spos = self.mapToScene(pos)
        x = spos.x()
        y = spos.y()
        r = (x*x + y*y) ** 0.5
        self.parent().set_hover_radius(r)

    def mouseReleaseEvent(self, event):
        self.parent().confirm_result()

class SelectByColorDlg(QDialog):
    def __init__(self, color, pieceItems):
        super().__init__()
        self._color = color
        self.resize(800, 800)

        self.scene = QGraphicsScene()
        layout = QVBoxLayout(self)
        self.view = _MyView(self)
        layout.addWidget(self.view)
        self.view.setScene(self.scene)
        self._view_widget = QGLWidget()
        self.view.setViewport(self._view_widget)
        self.view.setMouseTracking(True)

        gry = sum(color) / 3.0
        if (gry < 168):
            bg = [224,]*3
        else:
            bg = [128,]*3
        self.scene.setBackgroundBrush(QBrush(QColor(*bg)))

        self.setup_scene(self.scene, pieceItems)
        d = self.piece_diag
        self.view.scale(60./d, 60./d)

        self._hover_radius = 1.0
        self.selected_item_ids = []

    def setup_scene(self, scene, pieceItems):
        root = self._rootitem = _RootItem(self._color)
        scene.addItem(root)
        # order piece items by color distance of the most similar color
        pairs = [(self._distance(item), item) for item in pieceItems]
        pairs.sort(key = lambda pair: pair[0])

        phi_increment = 0.61803398874 * 2 * pi
        phi = 0.0

        gamma = 1.0
        # scale distance relative to average piece size
        if pairs:
            rect = pairs[0][1].boundingRect()
            diag = (rect.width()**2 + rect.height()**2) ** 0.5
            # take the median piece
            idx = len(pairs) // 2
            meddist = pairs[idx][0]
            meddist = max(meddist, .1)
            scale = 6*diag/(meddist) ** gamma
            self.piece_diag = diag
        else:
            scale = 1.0
            self.piece_diag = 1.0

        self.dist_and_id = []
        for distance, orig_item in pairs:
            item = orig_item.copy_to(root, rotate=False)
            rr = item.boundingRect()
            item.setTransformOriginPoint(rr.center())
            item.setRotation(item.angle_deg)


            item.setPos(
                scale * distance**gamma * cos(phi)-rr.width()*0.5,
                scale * distance**gamma * sin(phi)-rr.height()*0.5
            )
            self.dist_and_id.append((scale*distance**gamma, item.id))
            phi += phi_increment
        self.updateSceneRect()

    def set_hover_radius(self, r):
        self._hover_radius = r
        self.selected_item_ids = [pair[1] for pair in self.dist_and_id if pair[0] < r]
        self._rootitem.sel_size = r
        self._rootitem.update()

    def confirm_result(self):
        self.accept()

    def _distance(self, pieceItem):
        color = self._color
        def dst(c1, c2):
            c1 = rgb2Lab(c1)
            c2 = rgb2Lab(c2)
            return sum((c1i-c2i)**2 for c1i, c2i in zip(c1, c2)) ** 0.5
        if not pieceItem.dominant_colors:
            return 255.0
        return min(dst(color, piececolor) for piececolor in pieceItem.dominant_colors[:4])

    def updateSceneRect(self):
        r = self.scene.itemsBoundingRect()
        w, h = r.width(), r.height()
        a = .05
        r = r.adjusted(-w*a, -h*a, w*a, h*a)
        self.scene.setSceneRect(r)


def rgb2Lab(rgb):
    # sRGB to XYZ
    rgb = [t/255.0 for t in rgb]

    # Degamma
    def func1(u):
        if u < 0.04045:
            return u / 12.92
        else:
            return ((u + 0.055) / 1.055) ** 2.4

    rgb = [func1(t) for t in rgb]

    # transform to XYZ
    matrix = [[0.41239080, 0.35758434, 0.18048079],
            [0.21263901, 0.71516868, 0.07219232],
            [0.019933082, 0.11919478, 0.95053215]]
    xyz = [
        sum(item*component for item, component in zip(matrixrow, rgb))
        for matrixrow in matrix
    ]

    # apply D65 reference white point
    xyz[0] /= 0.950456
    xyz[2] /= 1.088754 

    def func2(u):
        if (u > 0.008856):
            return u**(1/3.)
        else:
            return 7.787 * u + 16 / 116.0

    fx, fy, fz = [func2(u) for u in xyz]

    # Calculate L, a, b from XYZ
    L = 116.0 * fy - 16.0
    a = 500*(fx - fy)
    b = 200*(fy - fz)

    return L, a, b
