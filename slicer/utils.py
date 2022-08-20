__all__ = ["loadUi"]

from pkgutil import get_data
from io import BytesIO
from qtpy.uic import loadUi as qt_loadUi

def loadUi(filename, attach_to):
    data = get_data(__package__, filename)
    io = BytesIO(data)
    ui = qt_loadUi(io, attach_to)
    return ui
