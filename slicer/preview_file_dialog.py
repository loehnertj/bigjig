import sys
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QFileDialog, QLabel, QVBoxLayout


class PreviewFileDialog(QFileDialog):
    def __init__(self, caption, directory, filter):
        QFileDialog.__init__(self, None, caption, directory, filter)
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setObjectName('PreviewFileDialog')
        box = QVBoxLayout()
        self.preview = QLabel("Preview", self)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setObjectName("labelPreview")
        box.addWidget(self.preview)
        # inject into own layout
        layout = self.layout()
        layout.addLayout(box, 1, 3, 3, 1)
        self.preview.setFixedWidth(400)
        self.currentChanged.connect(self.onCurrentChanged)
        
    def onCurrentChanged(self, path):
        print("current changed")
        pixmap = QPixmap(path)
        if not pixmap:
            self.preview.setText("Not an image")
        else:
            self.preview.setPixmap(pixmap.scaled(self.preview.width(), self.preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            #self.preview.adjustSize()
        
        

    
def run_standalone():
    from qtpy.QtWidgets import QApplication
    app = QApplication(sys.argv)
    pfd=PreviewFileDialog("Pick an image", "", "Image Files (*.jpg)")
    pfd.setMinimumSize(1200,600)
    pfd.show()
    app.exec_()

if __name__=='__main__':
    run_standalone()
