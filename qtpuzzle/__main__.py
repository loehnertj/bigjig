# -*- coding: utf-8 -*-

import logging
import os,sys

# Import Qt modules
from qtpy.QtWidgets import QApplication

from .mainwindow import MainWindow

def main():
    logging.basicConfig(level="INFO")
    logging.getLogger('neatocom').setLevel('INFO')
    # Again, this is boilerplate, it's going to be the same on
    # almost every app you write
    QApplication.setOrganizationName("Aurisoft")
    QApplication.setApplicationName("Jigsoid")
    app = QApplication(sys.argv)
    windows=[MainWindow()]
    windows[0].container = windows
    windows[0].show()
    # It's exec_ because exec is a reserved word in Python
    return app.exec_()
    


if __name__ == "__main__":
    main()

