import os,sys
import logging as L

# Import Qt modules
from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt, QPoint, QRect # , pyqtSignature
from PyQt4.QtGui import QDialog, QImage, QPainter

from puzzleboard.puzzle_board import PuzzleBoard
from puzzleboard.piece import Piece
from puzzleboard.link import Link

from .goldberg_engine import GoldbergEngine, GBEngineSettings
from .slicerUI import Ui_Slicer
from .preview_file_dialog import PreviewFileDialog
from . import grid_rect

class SlicerMain(QDialog):
    def __init__(o):
        QDialog.__init__(o)
        o.ui = Ui_Slicer()
        o.ui.setupUi(o)
        o.ui.btnOpenImageFile.clicked.connect(o.pick_source_image);
        
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
            
        dst_path = '/home/jo/proggis/puzzle2/puzzles/outtest'
        o.ui.buttonBox.setEnabled(False)
        o.run(image_path, piece_count, dst_path)
        o.close()
        
    def run(o, image_path, piece_count, dst_path):
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
        
        puzzlename = os.path.splitext(os.path.basename(image_path))[0]
        o.board = PuzzleBoard(
            name=puzzlename,
            rotations=grid_rect.rotations, # FIXME
        )
        o.board.basefolder=dst_path
        o.board.imagefolder=os.path.join(dst_path, 'pieces')
        settings = GBEngineSettings()
        engine = GoldbergEngine(o.add_piece_func, o.add_relation_func, settings)
        engine(grid_rect.generate_grid, piece_count, o.source_image.width(), o.source_image.height())
        o.board.reset_puzzle()
        o.board.save_puzzle()
        o.board.save_state()
        L.info('puzzle was saved to %s.'%dst_path)
        
    def pick_source_image(o):
        pfd = PreviewFileDialog("Choose source image", "/home/jo/Daten/Bilder/bgpics", "Image files (*.jpg *.jpeg *.png *.gif *.bmp *.tiff)")
        def action(path):
            o.ui.txtImageFile.setText(path)
        pfd.fileSelected.connect(action)
        # FIXME: should be screen resolution dependent
        pfd.setMinimumSize(1200, 600)
        print("show now")
        sys.stdout.flush()
        pfd.exec_()
    
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
        # add piece to puzzleboard
        o.board.pieces.append(Piece(
            id=piece_id,
            image=imgfile,
            x0=offset.x(),
            y0=offset.y(),
            w=pieceImage.width(),
            h=pieceImage.height(),
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
