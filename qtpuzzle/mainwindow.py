# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os,sys
import logging
L = lambda: logging.getLogger(__name__)


# Import Qt modules
from PyQt4 import QtCore,QtGui
from PyQt4.QtCore import Qt, QSettings # , pyqtSignature
from PyQt4.QtGui import QMainWindow, QFileDialog, QAction, QMessageBox, QGraphicsScene, QInputDialog

# Import the compiled UI module
from .mainwindowUI import Ui_MainWindow

from .i18n import tr

from .puzzle_scene import PuzzleScene
from .puzzle_client import PuzzleClient

from neatocom.QtTransports import QProcessTransport, QTcpTransport, QUdpTransport
from neatocom.codecs import TerseCodec
from neatocom.announcer_api import AnnouncerAPI

from slicer.slicer_main import SlicerMain


# Create a class for our main window
class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.container = []

        # This is always the same
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)
        
        mappings = dict(
            actionSave=self.save,
            actionReset=self.reset_puzzle,
            actionSelRearrange=self.selection_rearrange,
            actionSelClear=self.selection_clear,
            actionNewPuzzle=self.new_puzzle,
            actionOpen=self.open,
            actionNickname=self.change_nickname,
            actionShortcutHelp=self.display_shortcut_help,
            actionFullscreen=self.toggle_fullscreen,
        )
        for key, func in mappings.items():
            getattr(self.ui, key).triggered.connect(func)
        
        self.ui.actionAutosave.toggled.connect(self.toggle_autosave)
        self.ui.menuNetwork.aboutToShow.connect(self.refreshNetworkMenu)
        self.ui.menuNetwork.aboutToHide.connect(self.stopNetworkMenu)

        self._slicer = None
        
        # None, "local" or "tcp"
        self.client_type = None
        self.switchClient(nickname='', client_type=None)
        
        settings = QSettings()
        self.nickname = settings.value("nickname", "Sir Lancelot")
        path = settings.value("LastOpened", "")
        if path:
            # this switches the client_type to 'local'
            self.load_puzzle(path)
        self.ui.actionAutosave.setChecked(settings.value("Autosave", "true")=="true")
        
    def switchClient(self, nickname, client_type='local', address=''):
        self.deinitPuzzleClient()
        self.client_type = client_type
        if self.client_type is not None:
            self.client = self.initPuzzleClient(self.nickname, client_type, address)
            self.client.connect(name=self.nickname)
            self.scene = PuzzleScene(self.ui.mainView, self.client, self)
        else:
            # set dummy scene
            self.scene = QGraphicsScene()
        self.ui.actionSave.setEnabled(client_type=='local')
        self.ui.actionSave_as.setEnabled(client_type=='local')
        self.ui.actionAutosave.setEnabled(client_type=='local')
        self.ui.actionReset.setEnabled(client_type=='local')
        self.ui.mainView.setScene(self.scene)
        
    def deinitPuzzleClient(self):
        L().info('deinit puzzle client')
        if self.client_type == 'local':
            self.do_autosave('')
            self.client.quit()
            self.client.transport.stop()
        elif self.client_type == 'tcp':
            self.client.disconnect()
            # FIXME: explicit stop necessary? server should tcp-disconnect client.
            # QTcpTransport to be written, decide then...
            self.client.transport.stop()
        self.client = None
        self.client_type = None
        
    def initPuzzleClient(self, nickname, client_type='local', address=''):
        L().info('reinit puzzle client as %s'%client_type)
        self.own_servername = ''
        if client_type=='local':
            transport = QProcessTransport('{python} -u -m puzzleboard'.format(python=sys.executable))
        elif client_type=='tcp':
            transport = QTcpTransport(address, 8888)
        else:
            raise ValueError('Unsupported client_type %s!'%client_type)
        codec = TerseCodec()
        client = PuzzleClient(codec, transport, nickname)
        client.connected.connect(self.on_player_connect)
        client.dropped.connect(self.do_autosave)
        client.joined.connect(self.do_autosave)
        client.clusters.connect(self.do_autosave)
        client.solved.connect(self.on_solved)
        transport.start()
        if client_type=='local':
            self.own_servername = nickname+"'s server"
            client.servername(name=self.own_servername)
        return client
    
    def change_nickname(self):
        nickname, ok = QInputDialog.getText(self, "Network Nickname", "What is your name?", text=self.nickname)
        if ok and nickname != '':
            settings = QSettings()
            settings.setValue("nickname", nickname)
            self.nickname = nickname
    
    def refreshNetworkMenu(self):
        menu = self.ui.menuNetwork
        
        try:
            self.ui.actionNickname.setText("You are: " + self.nickname)
        except TypeError:
            self.nickname = "?"
        for action in menu.actions():
            if action.data() == 'dynamic':
                menu.removeAction(action)
                
        self._found_servers = [self.own_servername]
        self._seeker = AnnouncerAPI(TerseCodec(), QUdpTransport(8889))
        self._seeker.invert()
        self._seeker.transport.start()
        
        def on_advertise(sender, description):
            L().info('got advertisement from %r'%sender)
            servername = server = sender
            # seek for a servername within the description
            dparts = description.split(' ')
            for part in dparts:
                if part.startswith('servername:'):
                    _, _, servername = part.partition(':')
                    servername = servername.replace('_', ' ')
            if servername in self._found_servers:
                L().info('Ignoring advertisement, already known: %s'%servername)
                return
            action = QAction(servername, menu)
            action.triggered.connect(lambda: self.switchClient(self.nickname, client_type='tcp', address=server))
            action.setData('dynamic')
            menu.addAction(action)
            self._found_servers.append(servername)
            
        self._seeker.advertise.connect(on_advertise)
        L().info('broadcast seek message')
        self._seeker.seek()
            
    def stopNetworkMenu(self):
        self._seeker.transport.stop()
        del self._seeker
    
    def on_player_connect(self, sender, playerid, name):
        L().info('{} connected as {}'.format(playerid, name))
        
    def closeEvent(self, ev):
        self.ui.mainView.gl_widget.setParent(None)
        del self.ui.mainView.gl_widget
        self.deinitPuzzleClient()
        
    def showEvent(self, ev):
        self.ui.mainView.viewAll()
        
    def save(self):
        if self.client_type != 'local':
            L().warning('MainWindow.save: can only save on local client')
            return
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
        if self.client_type != "local":
            self.switchClient(self.nickname, client_type='local')
        if path.endswith("puzzle.json"):
            path = os.path.dirname(path)
        self.client.load_puzzle(path=path)
        settings = QSettings()
        settings.setValue("LastOpened", path)
    
    def toggle_autosave(self):
        settings = QSettings()
        settings.setValue("Autosave", self.ui.actionAutosave.isChecked())
        
    def toggle_fullscreen(self, fs='auto'):
        if fs=='auto' or fs=='toggle':
            new_state = self.ui.actionFullscreen.isChecked()
        if fs=='toggle':
            new_state = not new_state
        if fs=='on' or fs is True:
            new_state=True
        if fs=='off' or fs is False:
            new_state=False
        L().info('Toggle fullscreen <%s>'%new_state)
        if new_state:
            self.showFullScreen()
            self.ui.menubar.setVisible(False)
        else:
            self.showNormal()
            self.ui.menubar.setVisible(True)
        self.ui.actionFullscreen.setChecked(new_state)
    
    def reset_puzzle(self):
        if self.client_type != 'local':
            L().warning('MainWindow.reset_puzzle: can only reset on local client')
            return
        if QMessageBox.Ok != QMessageBox.warning(self, "Reset puzzle", "Really reset the puzzle?", QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel):
            return
        self.client.restart_puzzle()
        self.ui.mainView.viewAll()
        
    def selection_rearrange(self):
        if self.client_type is None:
            return
        self.scene.selectionRearrange()
        self.ui.mainView.viewAll()
        
    def selection_clear(self):
        if self.client_type is None:
            return
        self.scene.clearSelection()
        
    def do_autosave(self, sender, **kwargs):
        if self.ui.actionAutosave.isChecked():
            L().debug('autosaving')
            self.client.save_puzzle()
        
    def on_solved(self, sender):
        QMessageBox.information(self, "Puzzle solved.", "You did it!", "Yeehaw!!!")
        
    def display_shortcut_help(self, sender):
        from PyQt4.QtGui import QDialog
        from .shortcutHelpUI import Ui_ShortcutHelp
        d = QDialog(self)
        Ui_ShortcutHelp().setupUi(d)
        d.show()
        
