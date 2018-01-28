# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qtpuzzle/shortcut_help.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_ShortcutHelp(object):
    def setupUi(self, ShortcutHelp):
        ShortcutHelp.setObjectName(_fromUtf8("ShortcutHelp"))
        ShortcutHelp.resize(1045, 495)
        self.verticalLayout = QtGui.QVBoxLayout(ShortcutHelp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(ShortcutHelp)
        self.label.setText(_fromUtf8(""))
        self.label.setPixmap(QtGui.QPixmap(_fromUtf8("Keybindings.png")))
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.buttonBox = QtGui.QDialogButtonBox(ShortcutHelp)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ShortcutHelp)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ShortcutHelp.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ShortcutHelp.reject)
        QtCore.QMetaObject.connectSlotsByName(ShortcutHelp)

    def retranslateUi(self, ShortcutHelp):
        ShortcutHelp.setWindowTitle(_translate("ShortcutHelp", "Keyboard Shortcuts", None))

