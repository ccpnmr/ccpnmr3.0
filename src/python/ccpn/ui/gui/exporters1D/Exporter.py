from PyQt5 import QtGui, QtWidgets, QtCore
import os, re
import pyqtgraph as pg
from pyqtgraph.widgets.FileDialog import FileDialog
LastExportDirectory = None


class Exporter(object):
    """
    From PyQtGraph
    Abstract class used for exporting graphics to file / printer / whatever.
    """    
    allowCopy = False  # subclasses set this to True if they can use the copy buffer
    Exporters = []
    
    @classmethod
    def register(cls):
        """
        Used to register Exporter classes to appear in the export dialog.
        """
        Exporter.Exporters.append(cls)
    
    def __init__(self, item):
        """
        Initialize with the item to be exported.
        Can be an individual graphics item or a scene.
        """
        object.__init__(self)
        self.item = item
        
    def parameters(self):
        """Return the parameters used to configure this exporter."""
        raise Exception("Abstract method must be overridden in subclass.")
        
    def export(self, fileName=None, toBytes=False, copy=False):
        """
        If *filename* is None, pop-up a file dialog.
        If *toBytes* is True, return a bytes object rather than writing to file.
        If *copy* is True, export to the copy buffer rather than writing to file.
        """
        raise Exception("Abstract method must be overridden in subclass.")

    def fileSaveDialog(self, filter=None, opts=None):
        ## Show a file dialog, call self.export(filename) when finished.
        if opts is None:
            opts = {}
        self.fileDialog = FileDialog()
        self.fileDialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        self.fileDialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        if filter is not None:
            if isinstance(filter, str):
                self.fileDialog.setNameFilter(filter)
            elif isinstance(filter, list):
                self.fileDialog.setNameFilters(filter)
        global LastExportDirectory
        exportDir = LastExportDirectory
        if exportDir is not None:
            self.fileDialog.setDirectory(exportDir)
        self.fileDialog.show()
        self.fileDialog.opts = opts
        self.fileDialog.fileSelected.connect(self.fileSaveFinished)
        return
        
    def fileSaveFinished(self, filename):
        filename = pg.python2_3.asUnicode(filename)
        global LastExportDirectory
        LastExportDirectory = os.path.split(filename)[0]
        
        ## If file name does not match selected extension, append it now
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        selectedExt = re.search(r'\*\.(\w+)\b', pg.python2_3.asUnicode(self.fileDialog.selectedNameFilter()))
        if selectedExt is not None:
            selectedExt = selectedExt.groups()[0].lower()
            if ext != selectedExt:
                filename = filename + '.' + selectedExt.lstrip('.')
        
        self.export(fileName=filename, **self.fileDialog.opts)
        
    def getScene(self):
        if isinstance(self.item, pg.GraphicsScene):
            return self.item
        else:
            return self.item.scene()
        
    def getSourceRect(self):
        if isinstance(self.item, pg.GraphicsScene):
            w = self.item.getViewWidget()
            return w.viewportTransform().inverted()[0].mapRect(w.rect())
        else:
            return self.item.sceneBoundingRect()
        
    def getTargetRect(self):        
        if isinstance(self.item, pg.GraphicsScene):
            return self.item.getViewWidget().rect()
        else:
            return self.item.mapRectToDevice(self.item.boundingRect())
        
    def setExportMode(self, export, opts=None):
        """
        Call setExportMode(export, opts) on all items that will 
        be painted during the export. This informs the item
        that it is about to be painted for export, allowing it to 
        alter its appearance temporarily
        
        
        *export*  - bool; must be True before exporting and False afterward
        *opts*    - dict; common parameters are 'antialias' and 'background'
        """
        if opts is None:
            opts = {}
        for item in self.getPaintItems():
            if hasattr(item, 'setExportMode'):
                item.setExportMode(export, opts)
    
    def getPaintItems(self, root=None):
        """Return a list of all items that should be painted in the correct order."""
        if root is None:
            root = self.item
        preItems = []
        postItems = []
        if isinstance(root, QtWidgets.QGraphicsScene):
            childs = [i for i in root.items() if i.parentItem() is None]
            rootItem = []
        else:
            childs = root.childItems()
            rootItem = [root]
        childs.sort(key=lambda a: a.zValue())
        while len(childs) > 0:
            ch = childs.pop(0)
            tree = self.getPaintItems(ch)
            if int(ch.flags() & ch.ItemStacksBehindParent) > 0 or (ch.zValue() < 0 and int(ch.flags() & ch.ItemNegativeZStacksBehindParent) > 0):
                preItems.extend(tree)
            else:
                postItems.extend(tree)
                
        return preItems + rootItem + postItems

    def render(self, painter, targetRect, sourceRect, item=None):
        self.getScene().render(painter, QtCore.QRectF(targetRect), QtCore.QRectF(sourceRect))
