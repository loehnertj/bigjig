import os,sys
import logging as L

# Import Qt modules
from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt, QPoint, QRect # , pyqtSignature
from PyQt4.QtGui import QDialog, QImage, QPainter, QFileDialog, QColor, QPixmap

from puzzleboard.puzzle_board import PuzzleBoard
from puzzleboard.piece import Piece
from puzzleboard.link import Link

from .goldberg_engine import GoldbergEngine, GBEngineSettings
from .slicerUI import Ui_Slicer
from .preview_file_dialog import PreviewFileDialog
from .dominant_colors import find_colors
from . import grid_rect
from . import grid_hex
from . import grid_cairo
from . import grid_rotrex

# TODO:
# add_piece_func: find main colors of each piece
# algorithm idea:
# - convert image to HSL
# - make histogram in HSx space (Nh x Ns x Nl bins)
# - sort all nontransparent pixels into the bins
#    in parallel, compute centroid in each bin
# - use only bins with > 10?% of total (visible) pixel piece_count
# - repeat:
#   - find the two closest centroids
#   - if they are < 1? bin distances from each other, merge them.

class SlicerMain(QDialog):
    def __init__(o):
        QDialog.__init__(o)
        o.ui = Ui_Slicer()
        o.ui.setupUi(o)
        o.ui.btnOpenImageFile.clicked.connect(o.pick_source_image);
        o.ui.btnSaveTo.clicked.connect(o.pick_dst)
        o.grid_types = [
            ('Rectangular grid', grid_rect),
            ('Hexagonal grid', grid_hex),
            ('Cairo grid', grid_cairo),
            ('Rhombitrihexagonal', grid_rotrex),
        ]
        
        for name, grid_type in o.grid_types:
            o.ui.cboGridType.addItem(name)
        o.ui.cboGridType.setCurrentIndex(0)
        o.onFinish = None
        o.settings = GBEngineSettings()
        o.ui.cboGridType.currentIndexChanged.connect(lambda *args: o.generate_preview())
        o.ui.flipSlider.sliderMoved.connect(o.onFlipSlider)
        o.ui.curvinessSlider.sliderMoved.connect(o.onCurvinessSlider)
        o.ui.plugSizeSlider.sliderMoved.connect(o.onPlugSizeSlider)
        o.ui.curvinessVarSlider.sliderMoved.connect(o.onCurvinessVarSlider)
        o.ui.plugPosVarSlider.sliderMoved.connect(o.onPlugPosVarSlider)
        o.ui.plugShapeVarSlider.sliderMoved.connect(o.onPlugShapeVarSlider)
        o.generate_preview()
        
    def onFlipSlider(o, value):
        o.settings.flip_threshold = .01*value if value<50 else 1-.01*value
        o.settings.alternate_flip = (value>=50)
        o.generate_preview()
    
    def onCurvinessSlider(o, value):
        o.settings.edge_curviness = .01*value
        o.generate_preview()
        
    def onPlugSizeSlider(o, value):
        o.settings.plug_size = 1. + .01*value
        o.generate_preview()
        
    def onCurvinessVarSlider(o, value):
        o.settings.sigma_curviness = .01*value
        o.generate_preview()
        
    def onPlugPosVarSlider(o, value):
        o.settings.sigma_basepos = .01*value
        o.generate_preview()
        
    def onPlugShapeVarSlider(o, value):
        o.settings.sigma_plugs = .01*value
        o.generate_preview()
        
    def accept(o):
        image_path = o.ui.txtImageFile.text()
        if image_path=="":
            o.ui.txtImageFile.setFocus()
            return
        piece_count = 20
        if o.ui.pc_custom.isChecked():
            piece_count = o.ui.pc_box.value()
        else:
            for pc in [20, 50, 100, 200, 500]:
                if getattr(o.ui, "pc_%d"%pc).isChecked():
                    piece_count = pc
        dst_path = o.ui.txtSaveTo.text()
        o.ui.buttonBox.setEnabled(False)
        o.run(image_path, dst_path, piece_count)
        o.ui.buttonBox.setEnabled(True)
        o.close()
        
    def _cur_grid_generator(o):
        gt = dict(o.grid_types)
        return gt[o.ui.cboGridType.currentText()]
        
    def run(o, image_path, dst_path, piece_count):
        L.debug('run')
        if not image_path: return
        if not dst_path: return
    
        import shutil
        try:
            shutil.rmtree(dst_path)
        except FileNotFoundError:
            pass
        
        o.source_image = QImage(image_path)
        try:
            os.makedirs(dst_path)
        except os.error:
            L.info('dst_path exists, cancel')
        os.makedirs(os.path.join(dst_path, 'pieces'))
        
        grid_generator = o._cur_grid_generator()
        
        puzzlename = os.path.splitext(os.path.basename(image_path))[0]
        o.board = PuzzleBoard(
            name=puzzlename,
            rotations=grid_generator.rotations,
        )
        o.board.basefolder=dst_path
        o.board.imagefolder=os.path.join(dst_path, 'pieces')
        engine = GoldbergEngine(o.add_piece_func, o.add_relation_func, o.settings, outline_only=False)
        engine(grid_generator.generate_grid, piece_count, o.source_image.width(), o.source_image.height())
        o.board.reset_puzzle()
        o.board.save_puzzle()
        o.board.save_state()
        L.info('puzzle was saved to %s.'%dst_path)
        if o.onFinish:
            o.onFinish(dst_path)
        
    def pick_source_image(o):
        pfd = PreviewFileDialog("Choose source image", "/home/jo/Daten/Bilder/bgpics", "Image files (*.jpg *.jpeg *.png *.gif *.bmp *.tiff)")
        def action(path):
            o.ui.txtImageFile.setText(path)
        pfd.fileSelected.connect(action)
        # FIXME: should be screen resolution dependent
        pfd.setMinimumSize(1200, 600)
        pfd.exec_()
        
    def pick_dst(o):
        path = QFileDialog.getSaveFileName(o, "Choose folder", "", "Directory (*)")
        if path:
            o.ui.txtSaveTo.setText(path)
            
    def generate_preview(o):
        size = o.ui.previewImage.size()
        img = QImage(size, QImage.Format_ARGB32)
        img.fill(QColor(224,224,224,255))
        painter = QPainter(img)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        def preview_add_piece_func(piece_id, mask_image, offset):
            painter.drawImage(offset, mask_image)
        engine = GoldbergEngine(preview_add_piece_func, lambda id1,id2: None, o.settings, outline_only=True)
        engine(o._cur_grid_generator().generate_grid, 30, size.width(), size.height())
        painter.end()
        
        o.ui.previewImage.setPixmap(QPixmap(img))
    
    def add_piece_func(o, piece_id, mask_image, offset):
        # o.source_image required (QImage)
        L.debug('add_piece_func %d %r'%(piece_id, offset))
        
        pieceImage = QImage(mask_image)
        piecePainter = QPainter(pieceImage)
        piecePainter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        piecePainter.drawImage(QPoint(), _safeQImageCopy(o.source_image, QRect(offset, mask_image.size())))
        piecePainter.end()
        
        # save pieceImage as pieces/piece<id>.png
        imgfile = 'piece%d.png'%piece_id
        pieceImage.save(os.path.join(o.board.imagefolder, imgfile))
        dominant_colors = find_colors(pieceImage)
        # add piece to puzzleboard
        o.board.pieces.append(Piece(
            id=piece_id,
            image=imgfile,
            x0=offset.x(),
            y0=offset.y(),
            w=pieceImage.width(),
            h=pieceImage.height(),
            dominant_colors=dominant_colors,
        ))
        
    def add_relation_func(o, piece_id_1, piece_id_2):
        L.debug('add_relation_func %d %d'%(piece_id_1, piece_id_2))
        o.board.links.append(Link(
            id1=piece_id_1,
            id2=piece_id_2,
            x=0, #FIXME
            y=0, #FIXME
        ))
    
def _safeQImageCopy(source, rect):
    '''A modified version of QImage::copy, which avoids rendering errors even if rect is outside the bounds of the source image.'''
    targetRect = QRect(QPoint(), rect.size())
    # copy image
    target = QImage(rect.size(), source.format())
    p = QPainter(target)
    p.drawImage(targetRect, source, rect)
    p.end()
    return target
    # Strangely, source.copy(rect) does not work. It produces black borders.

def run_standalone():
    from PyQt4.QtGui import QApplication
    app = QApplication(sys.argv)
    windows=[SlicerMain()]
    windows[0].show()
    # It's exec_ because exec is a reserved word in Python
    return app.exec_()
