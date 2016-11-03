# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os,sys
import logging
L = lambda: logging.getLogger(__name__)


# Import Qt modules
from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt, QSettings # , pyqtSignature
from PyQt4.QtGui import QMainWindow, QFileDialog, QAction, QMessageBox, QGraphicsScene

# Import the compiled UI module
from .mainwindowUI import Ui_MainWindow

from .i18n import tr

from .puzzle_scene import PuzzleScene
from .puzzle_client import PuzzleClient
from neatocom.qprocess_transport import QProcessTransport
from neatocom.json_codec import JsonCodec

from slicer.slicer_main import SlicerMain


# Create a class for our main window
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.container = []

        # This is always the same
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)
        
        #self.ui.toolBar.addAction(self.ui.dock_boxes.toggleViewAction())
        self.ui.dock_boxes.hide()
        mappings = dict(
            actionSave=self.save,
            actionReset=self.reset_puzzle,
            actionSelRearrange=self.selection_rearrange,
            actionSelClear=self.selection_clear,
            actionNewPuzzle=self.new_puzzle,
            actionOpen=self.open,
        )
        for key,func in mappings.items():
            getattr(self.ui, key).triggered.connect(func)
        
        self.ui.actionAutosave.toggled.connect(self.toggle_autosave)

        self._slicer = None
        
        
        self.client = self.initPuzzleClient('SirLancelot')
        self.client.connect(name="SirLancelot")
        
        self.scene = PuzzleScene(self.ui.mainView, self.client)
        self.ui.mainView.setScene(self.scene)
        
        for msg in self.client.unhandled_calls():
            L().warning('qtpuzzle: no handler connected for API call "%s"'%msg)
        
        settings = QSettings()
        path = settings.value("LastOpened", "")
        if path:
            self.load_puzzle(path)
        self.ui.actionAutosave.setChecked(settings.value("Autosave", "true")=="true")
        
    def initPuzzleClient(self, nickname):
        transport = QProcessTransport('{python} -m puzzleboard'.format(python=sys.executable))
        codec = JsonCodec()
        client = PuzzleClient(codec, transport, nickname)
        client.connected.connect(self.on_player_connect)
        client.moved.connect(self.on_pb_changed)
        client.joined.connect(self.on_pb_changed)
        client.solved.connect(self.on_solved)
        transport.start()
        return client
    
    def on_player_connect(self, sender, playerid, name):
        L().info('{} connected as {}'.format(playerid, name))
        
    def closeEvent(self, ev):
        self.ui.mainView.gl_widget.setParent(None)
        del self.ui.mainView.gl_widget
        
        self.client.quit()
        
    def showEvent(self, ev):
        self.ui.mainView.viewAll()
        
    def save(self):
        self.client.save_puzzle()
        
    def open(self):
        path = QFileDialog.getOpenFileName(self, "Choose Puzzle", "puzzles", "Puzzle files (puzzle.json)")
        if path: self.load_puzzle(path)
        
    def new_puzzle(self):
        if not self._slicer:
            self._slicer=SlicerMain()
            self._slicer.onFinish = self.load_puzzle
        self._slicer.show()

    def load_puzzle(self, path):
        if path.endswith("puzzle.json"):
            path = os.path.dirname(path)
        self.client.load_puzzle(path=path)
        settings = QSettings()
        settings.setValue("LastOpened", path)
    
    def toggle_autosave(self):
        settings = QSettings()
        settings.setValue("Autosave", self.ui.actionAutosave.isChecked())
    
    def reset_puzzle(self):
        if QMessageBox.Ok != QMessageBox.warning(self, "Reset puzzle", "Really reset the puzzle?", QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel):
            return
        self.client.restart_puzzle()
        self.ui.mainView.viewAll()
        
    def selection_rearrange(self):
        self.scene.selectionRearrange()
        self.ui.mainView.viewAll()
        
    def selection_clear(self):
        self.scene.clearSelection()
        
    def on_pb_changed(self, sender, **kwargs):
        if self.ui.actionAutosave.isChecked():
            L().debug('autosaving')
            self.client.save_puzzle()
        
    def on_solved(self, sender):
        QMessageBox.information(self, "Puzzle solved.", "You did it!", "Yeehaw!!!")
        