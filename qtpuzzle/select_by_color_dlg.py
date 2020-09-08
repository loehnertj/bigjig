from math import sin, cos, pi
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QGraphicsScene, QGraphicsView, QVBoxLayout
from PyQt4.QtGui import QGraphicsWidget
from PyQt4.QtGui import QColor, QBrush, QPen
from PyQt4.QtCore import Qt, QPointF
from PyQt4.QtOpenGL import QGLWidget

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
        delta = 2 ** (ev.delta() / 240.)
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
    def func(t):
        if (t > 0.008856):
            return t**(1/3.)
        else:
            return 7.787 * t + 16 / 116.0

    #Conversion Matrix
    matrix = [[0.412453, 0.357580, 0.180423],
            [0.212671, 0.715160, 0.072169],
            [0.019334, 0.119193, 0.950227]]

    # Convert to XYZ
    cie = [
        sum(item*component/255.0 for item, component in zip(matrixrow, rgb))
        for matrixrow in matrix
    ]

    cie[0] = cie[0] /0.950456
    cie[2] = cie[2] /1.088754 

    # Calculate L, a, b from XYZ
    L = 116 * cie[1] ** (1/3.0) - 16.0 if cie[1] > 0.008856 else 903.3 * cie[1]
    a = 500*(func(cie[0]) - func(cie[1]))
    b = 200*(func(cie[1]) - func(cie[2]))
    return L, a, b
