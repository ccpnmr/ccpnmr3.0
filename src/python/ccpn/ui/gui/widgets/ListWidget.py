"""
List widget

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (http://www.ccpn.ac.uk) 2014 - 2019"
__credits__ = ("Ed Brooksbank, Luca Mureddu, Timothy J Ragan & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: CCPN $"
__dateModified__ = "$dateModified: 2017-07-07 16:32:54 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-18 15:19:30 +0100 (Tue, April 18, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.util.Constants import ccpnmrJsonData

# GST is this really a WrapperObject ListWidget because there appear to be some
# methods and features that are possibly quite coupled to them or some defined
# object e.g objects with text() methods and which have items associated with them
# maybe needs a refactoring or a rename (or both)... or of course I maybe reading this wrong...
class ListWidget(QtWidgets.QListWidget, Base):
    # # To be done more rigeriously later
    # _styleSheet = """
    # QListWidget {background-color: #f7ffff;
    #              color: #122043;
    #              font-weight: normal;
    #              margin: 0px 0px 0px 0px;
    #              padding: 2px 2px 2px 2px;
    #              border: 1px solid #182548;
    #              }
    # """

    dropped = pyqtSignal(list)
    cleared = pyqtSignal()

    def __init__(self, parent=None, objects=None, callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=False,
                 sortOnDrop=False,
                 allowDuplicates=False,
                 copyDrop=True,
                 infinitleyTallVertically= False,
                 minRowsVisible = 4,
                 **kwds):

        super().__init__(parent)
        Base._init(self, acceptDrops=acceptDrops, **kwds)

        self.setDragDropMode(self.DragDrop)

        self.setAcceptDrops(acceptDrops)
        self.contextMenu = contextMenu
        self.callback = callback
        # GST why dow we keep our own list of items and objects when we could add them as user data
        # to the ListWidgetItem... this st seems like a way for things to get out of sync
        self.objects = {id(obj): obj for obj in objects} if objects else {}  # list(objects) or [])
        self._items = list(objects or [])
        self.multiSelect = multiSelect
        self.dropSource = None

        # GST this only works for sorting on drops... it doesn't allow for sorting on moving items
        # with double clicks or menus
        self.sortOnDrop = sortOnDrop
        self.copyDrop = copyDrop
        self.allowDuplicates = allowDuplicates
        if not self.copyDrop:
            self.setDefaultDropAction(QtCore.Qt.MoveAction)

        self.rightMouseCallback = rightMouseCallback
        if callback is not None:
            self.itemClicked.connect(callback)

        if self.multiSelect:
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        else:
            self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.contextMenuItem = 'Remove'
        self.currentContextMenu = self.getContextMenu

        self.infinitleyTallVerically = infinitleyTallVertically
        self.minRowsVisible = minRowsVisible

        # self.setStyleSheet(self._styleSheet)

    def minimumSizeHint(self) -> QtCore.QSize:
        result =  super().minimumSizeHint()
        if self.count()  > 0:
            result.setHeight(self.sizeHintForRow(0)* self.minRowsVisible)
        else:
            result.setHeight(self.fontMetrics().height()* self.minRowsVisible)
        return result

    def sizeHint(self):
        result = super().sizeHint()

        if self.infinitleyTallVerically:
            result.setHeight(QtWidgets.QWIDGETSIZE_MAX)
        return result

    def contextCallback(self, remove=True):

        if remove:
            self.removeItem()
        self.rightMouseCallback()

    def setTexts(self, texts, clear=True):
        if clear:
            self.clear()
            self.cleared.emit()

            # GST why don't we clear self._items and self.objects
            # GST why don't we add to self.objects
            # self.items = []
        for text in texts:
            item = QtWidgets.QListWidgetItem(str(text))
            self.addItem(item)

    def setObjects(self, objects, name='pid'):
        self.clear()
        self.cleared.emit()

        self.objects = {id(obj): obj for obj in objects}  # list(objects)
        for obj in objects:
            if hasattr(obj, name):
                item = QtWidgets.QListWidgetItem(getattr(obj, name), self)
                item.setData(QtCore.Qt.UserRole, id(obj))
                obj.item = item
                self.addItem(item)
                #GST why do we store items when a list widget stores them as well...
                self._items.append(item)

            else:
                item = QtWidgets.QListWidgetItem(str(obj))
                item.setData(QtCore.Qt.UserRole, id(obj))
                self.addItem(item)

    def getObjects(self):
        return list(self.objects.values())

    def addItem(self, item):
        if self.allowDuplicates:
            super(ListWidget, self).addItem(item)
        else:
            if isinstance(item, str):
                if not item in self.getTexts():
                    super(ListWidget, self).addItem(item)
            else:
                if not item.text() in self.getTexts():
                    super(ListWidget, self).addItem(item)

    def hideAllItems(self):
        for i in range(self.count()):
            item = self.item(i)
            item.setHidden(True)

    def showAllItems(self):
        for i in range(self.count()):
            item = self.item(i)
            item.setHidden(False)

    def showItems(self, items, select=False):
        """ Shows specific items and hides the rest"""

        for i in range(self.count()):
            item = self.item(i)
            if item.text() in items:
                item.setHidden(False)
                if select:
                    item.setSelected(True)
            else:
                item.setHidden(True)
                item.setSelected(False)

    def _getDroppedObjects(self, project):
        '''This will return obj if the items text is a ccpn pid. This is used when the objects inside a listWidget are being dragged and dropped across widgets'''
        items = []
        objs = []

        for index in range(self.count()):
            items.append(self.item(index))
        for item in items:
            obj = project.getByPid(item.text())
            objs.append(obj)
        return objs

    def getSelectedObjects(self):
        indexes = self.selectedIndexes()
        objects = []
        for item in indexes:
            objId = item.data(QtCore.Qt.UserRole)
            if objId in self.objects:
                obj = self.objects[objId]
                if obj is not None:
                    objects.append(obj)
        return objects

    def selectItems(self, names):
        for index in range(self.count()):
            item = self.item(index)
            if item.text() in names:
                item.setSelected(True)

    def select(self, name):
        for index in range(self.count()):
            item = self.item(index)
            if item.text() == name:
                self.setCurrentItem(item)

    def clearSelection(self):
        for i in range(self.count()):
            item = self.item(i)
            # self.setItemSelected(item, False)
            item.setSelected(False)

    def getItems(self):
        items = []
        for index in range(self.count()):
            items.append(self.item(index))
        return items

    def getTexts(self):
        items = []
        for index in range(self.count()):
            items.append(self.item(index))
        return [i.text() for i in items]

    def getSelectedTexts(self):
        return [i.text() for i in self.selectedItems()]

    def selectObject(self, obj):
        try:
            obj.item.setSelected(True)
        except Exception as e:
            # Error wrapped C/C++ object of type QListWidgetItem has been deleted
            pass

    def selectObjects(self, objs):
        self.clearSelection()
        for obj in objs:
            self.selectObject(obj)

    def removeItem(self):
        for selectedItem in self.selectedItems():
            self.takeItem(self.row(selectedItem))
            # self.takeItem(self.currentRow())

    def mousePressEvent(self, event):
        self._mouse_button = event.button()
        if event.button() == QtCore.Qt.RightButton:
            if self.contextMenu:
                self.raiseContextMenu(event)
        elif event.button() == QtCore.Qt.LeftButton:
            if self.itemAt(event.pos()) is None:
                self.clearSelection()
            else:
                super(ListWidget, self).mousePressEvent(event)

    def raiseContextMenu(self, event):
        """
        Raise the context menu
        """
        menu = self.currentContextMenu()
        if menu:
            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
            menu.exec()

    def getContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        if self.rightMouseCallback is None:
            contextMenu.addItem("Remove", callback=self.removeItem)
            contextMenu.addItem("Remove All", callback=self._deleteAll)
        else:
            contextMenu.addItem("Remove", callback=self.contextCallback)
        return contextMenu

    def setContextMenu(self, menu):
        self.currentContextMenu = menu
        return menu

    # TODO:ED these are not very generic yet
    def setSelectContextMenu(self):
        self.currentContextMenu = self._getSelectContextMenu

    def _getSelectContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem("Select All", callback=self._selectAll)
        contextMenu.addItem("Clear Selection", callback=self._selectNone)
        return contextMenu

    def setSelectDeleteContextMenu(self):
        self.currentContextMenu = self._getSelectDeleteContextMenu

    def _getSelectDeleteContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem("Select All", callback=self._selectAll)
        contextMenu.addItem("Clear Selection", callback=self._selectNone)
        contextMenu.addItem("Remove", callback=self.removeItem)
        return contextMenu

    def _selectAll(self):
        """
        Select all items in the list
        """
        for i in range(self.count()):
            item = self.item(i)
            item.setSelected(True)

    def _selectNone(self):
        """
        Clear item selection
        """
        self.clearSelection()

    def _deleteAll(self):
        self.clear()
        self.cleared.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(ListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            super(ListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            # self.emit(QtCore.SIGNAL("dropped"), links)
            self.dropped.emit(links)
            if self.sortOnDrop is True:
                self.sortItems()
        else:
            data = [self.parseEvent(event)]
            if event.source() != self:  # otherwise duplicates
                if self.dropSource is None:  # allow event drops from anywhere
                    if self.copyDrop:
                        event.setDropAction(QtCore.Qt.CopyAction)
                    else:
                        event.setDropAction(QtCore.Qt.MoveAction)

                    super(ListWidget, self).dropEvent(event)
                    self.dropped.emit(data)
                    if not self.allowDuplicates:
                        self._removeDuplicate()
                    if self.sortOnDrop is True:
                        self.sortItems()
                else:

                    if event.source() is self.dropSource:  # check that the drop comes
                        event.setDropAction(QtCore.Qt.MoveAction)  # from only the permitted widget
                        # self.emit(QtCore.SIGNAL("dropped"), items)
                        super(ListWidget, self).dropEvent(event)
                        self.dropped.emit(data)
                        if self.sortOnDrop is True:
                            self.sortItems()
                    else:
                        event.accept()

            # ejb - tried to fix transfer of CopyAction, but intermittent
            # encodedData = event.mimeData().data(ccpnmrJsonData)
            # stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.ReadOnly)
            # eventData = stream.readQVariantHash()
            #
            # items = []
            # if event.source() != self: #otherwise duplicates
            #   actionType = QtCore.Qt.CopyAction
            #   if 'dragAction' in eventData.keys():        # put these strings somewhere else
            #     if eventData['dragAction'] == 'copy':
            #       actionType = QtCore.Qt.CopyAction             # ejb - changed from Move
            #     elif eventData['dragAction'] == 'move':
            #       actionType = QtCore.Qt.MoveAction             # ejb - changed from Move
            #
            #   event.setDropAction(actionType)
            #   # self.emit(QtCore.SIGNAL("dropped"), items)
            #   self.dropped.emit(items)
            #   super(ListWidget, self).dropEvent(event)
            # else:
            #   event.ignore()

    def _removeDuplicate(self):
        """ Removes duplicates from listwidget on dropping. Could be implemented to don't add in first place but difficult
        to know where the items are added from, eg from different drop event sources (sidebar, other List or outside urls etc).
        which didn't work well when duplicates  were dropped as a group and also qt as different signatures for each item on same function!.
        Don't use the ccpn parse data for pids as this is not a widget where you use always pids!
        """

        seen = set()
        uniq = [i for i in self.getItems() if i.text() not in seen and not seen.add(i.text())]
        removeDuplicates = [self.model().removeRow(self.row(i)) for i in self.getItems() if i not in uniq]


from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Spacer import Spacer


class ListWidgetPair(Frame):
    """
    Define a pair of listWidgets such that information can be cpoied from one side
    to the other and vise-versa
    """

    def __init__(self, parent=None, objects=None, callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=False,
                 showMoveArrows=True,
                 showMoveText=False,
                 title='Copy Items', **kwds):
        """
        Initialise the pair of listWidgets
        :param parent:
        :param objects:
        :param callback:
        :param rightMouseCallback:
        :param contextMenu:
        :param multiSelect:
        :param acceptDrops:
        :param pairName:
        :param kwds:
        """
        Frame.__init__(self, parent, **kwds)

        self.title = Label(self, text=title, setLayout=True, grid=(0, 0), gridSpan=(1, 7), hAlign='l')
        self.leftList = ListWidget(self, setLayout=True, grid=(1, 1), gridSpan=(5, 1), acceptDrops=True,
                                   sortOnDrop=True)
        self.rightList = ListWidget(self, setLayout=True, grid=(1, 5), gridSpan=(5, 1), acceptDrops=True,
                                    sortOnDrop=True)

        # set the drop source
        self.leftList.dropSource = self.rightList
        self.rightList.dropSource = self.leftList

        self.leftList.setSelectContextMenu()
        self.rightList.setSelectContextMenu()
        # self.rightList.setSelectDeleteContextMenu()

        self.leftList.itemDoubleClicked.connect(self._moveRight)
        self.rightList.itemDoubleClicked.connect(self._moveLeft)

        self.leftIcon = Icon('icons/yellow-arrow-left')
        self.rightIcon = Icon('icons/yellow-arrow-right')

        if showMoveArrows:
            moveText = ['', '']
            if showMoveText:
                moveText = ['move left', 'move right']

            self.buttons = ButtonList(self, texts=moveText,
                                      icons=[self.leftIcon, self.rightIcon],
                                      callbacks=[self._moveLeft, self._moveRight],
                                      direction='v',
                                      grid=(3, 3), hAlign='c')
            self.buttons.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            transparentStyle = "background-color: transparent; border: 0px solid transparent"
            self.buttons.setStyleSheet(transparentStyle)

        # self.button = Button(self, text='',
        #                           icon=self.rightIcon,
        #                           callback=self._copyRight,
        #                           grid=(3,3))
        # self.button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.spacer1 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(0, 2), gridSpan=(1, 1))
        self.spacer2 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(2, 2), gridSpan=(1, 1))
        self.spacer3 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(4, 4), gridSpan=(1, 1))
        self.spacer4 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(6, 4), gridSpan=(1, 1))

        for i, cs in enumerate([2, 8, 1, 1, 1, 8, 2]):
            self.getLayout().setColumnStretch(i, cs)

        # self.showBorder=True
        # self.leftList.setContentsMargins(15,15,15,15)
        # self.rightList.setContentsMargins(15,15,15,15)

    def setListObjects(self, left):
        # self.leftObjects = left
        # self._populate(self.leftList, self.objects)

        self.objects = left
        self._populate(self.rightList, self.objects)

    def _populate(self, list, objs):
        """
        List the Pids of the objects in the listWidget
        :param list: target listWidget
        :param objs: list of objects with Pids
        """
        list.clear()
        if objs:
            for item in objs:
                item = QtWidgets.QListWidgetItem(str(item.pid))
                list.addItem(item)
        list.sortItems()

    def _moveLeft(self):  # not needed now
        """
        Move contents of the right window to the left window
        """
        for item in self.rightList.selectedItems():
            leftItem = QtWidgets.QListWidgetItem(item)
            self.leftList.addItem(leftItem)
            self.rightList.takeItem(self.rightList.row(item))
        self.leftList.sortItems()

    def _moveRight(self):  # not needed now
        """
        Move contents of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
            self.leftList.takeItem(self.leftList.row(item))
        self.rightList.sortItems()

    def _moveItemLeft(self):
        """
        Move contents of the right window to the left window
        """
        rightItem = QtWidgets.QListWidgetItem(self.rightList.selectedItems())
        self.leftList.addItem(rightItem)
        self.rightList.takeItem(self.rightList.row(rightItem))
        self.leftList.sortItems()

    def _moveItemRight(self):
        """
        Move contents of the left window to the right window
        """
        leftItem = QtWidgets.QListWidgetItem(self.leftList.selectedItem)
        self.rightList.addItem(leftItem)
        self.leftList.takeItem(self.leftList.row(leftItem))
        self.rightList.sortItems()

    def _copyRight(self):
        """
        Copy selection of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
        self.rightList.sortItems()

    def getLeftList(self):
        return self.leftList.getTexts()

    def getRightList(self):
        return self.rightList.getTexts()

        # RESIDUE                     ABBREVIATION                SYNONYM
        # -----------------------------------------------------------------------------
        # Alanine                     ALA                         A
        # Arginine                    ARG                         R
        # Asparagine                  ASN                         N
        # Aspartic acid               ASP                         D
        # ASP/ASN ambiguous           ASX                         B
        # Cysteine                    CYS                         C
        # Glutamine                   GLN                         Q
        # Glutamic acid               GLU                         E
        # GLU/GLN ambiguous           GLX                         Z
        # Glycine                     GLY                         G
        # Histidine                   HIS                         H
        # Isoleucine                  ILE                         I
        # Leucine                     LEU                         L
        # Lysine                      LYS                         K
        # Methionine                  MET                         M
        # Phenylalanine               PHE                         F
        # Proline                     PRO                         P
        # Serine                      SER                         S
        # Threonine                   THR                         T
        # Tryptophan                  TRP                         W
        # Tyrosine                    TYR                         Y
        # Unknown                     UNK
        # Valine                      VAL                         V


class ListWidgetSelector(Frame):
    """
    Define a pair of listWidgets such that information can be cpoied from one side
    to the other and vise-versa
    """
    residueTypes = [('Alanine', 'ALA', 'A'),
                    ('Arginine', 'ARG', 'R'),
                    ('Asparagine', 'ASN', 'N'),
                    ('Aspartic acid', 'ASP', 'D'),
                    ('ASP/ASN ambiguous', 'ASX', 'B'),
                    ('Cysteine', 'CYS', 'C'),
                    ('Glutamine', 'GLN', 'Q'),
                    ('Glutamic acid', 'GLU', 'E'),
                    ('GLU/GLN ambiguous', 'GLX', 'Z'),
                    ('Glycine', 'GLY', 'G'),
                    ('Histidine', 'HIS', 'H'),
                    ('Isoleucine', 'ILE', 'I'),
                    ('Leucine', 'LEU', 'L'),
                    ('Lysine', 'LYS', 'K'),
                    ('Methionine', 'MET', 'M'),
                    ('Phenylalanine', 'PHE', 'F'),
                    ('Proline', 'PRO', 'P'),
                    ('Serine', 'SER', 'S'),
                    ('Threonine', 'THR', 'T'),
                    ('Tryptophan', 'TRP', 'W'),
                    ('Tyrosine', 'TYR', 'Y'),
                    ('Unknown', 'UNK', ''),
                    ('Valine', 'VAL', 'V')]

    def __init__(self, parent=None, objects=None, callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=False,
                 title='Copy Items', **kwds):
        """
        Initialise the pair of listWidgets
        :param parent:
        :param objects:
        :param callback:
        :param rightMouseCallback:
        :param contextMenu:
        :param multiSelect:
        :param acceptDrops:
        :param pairName:
        :param kwds:
        """
        Frame.__init__(self, parent, **kwds)

        self.title = Label(self, text=title, setLayout=True, grid=(0, 0), gridSpan=(1, 7), hAlign='l')
        self.leftList = ListWidget(self, setLayout=True, grid=(1, 1), gridSpan=(5, 1), acceptDrops=True,
                                   sortOnDrop=True)
        self.rightList = ListWidget(self, setLayout=True, grid=(1, 5), gridSpan=(5, 1), acceptDrops=True,
                                    sortOnDrop=True)

        # set the drop source
        self.leftList.dropSource = self.rightList
        self.rightList.dropSource = self.leftList

        self.leftList.setSelectContextMenu()
        self.rightList.setSelectContextMenu()
        # self.rightList.setSelectDeleteContextMenu()

        self.leftList.itemDoubleClicked.connect(self._moveRight)
        self.rightList.itemDoubleClicked.connect(self._moveLeft)

        # self.leftIcon = Icon('icons/yellow-arrow-left')
        # self.rightIcon = Icon('icons/yellow-arrow-right')
        #
        # self.buttons = ButtonList(self, texts=['move left', 'move right'],
        #                          icons=[self.leftIcon, self.rightIcon],
        #                          callbacks=[self._moveLeft, self._moveRight],
        #                          direction='v',
        #                          grid=(3,3), hAlign='c')
        # self.buttons.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # transparentStyle = "background-color: transparent; border: 0px solid transparent"
        # self.buttons.setStyleSheet(transparentStyle)

        # self.button = Button(self, text='',
        #                          icon=self.rightIcon,
        #                          callback=self._copyRight,
        #                          grid=(3,3)),
        # self.button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.spacer1 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(0, 2), gridSpan=(1, 1))
        self.spacer2 = Spacer(self, 10, 10,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(2, 2), gridSpan=(1, 1))
        self.spacer3 = Spacer(self, 10, 10,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(4, 4), gridSpan=(1, 1))
        self.spacer4 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(6, 4), gridSpan=(1, 1))

        for i, cs in enumerate([2, 6, 1, 1, 1, 6, 2]):
            self.getLayout().setColumnStretch(i, cs)

        # self.showBorder=True
        # self.leftList.setContentsMargins(15,15,15,15)
        # self.rightList.setContentsMargins(15,15,15,15)

    def setListObjects(self, left):
        # self.leftObjects = left
        # self._populate(self.leftList, self.objects)

        self.objects = left
        self._populate(self.rightList, self.objects)

    def _populate(self, list, objs):
        """
        List the Pids of the objects in the listWidget
        :param list: target listWidget
        :param objs: list of objects with Pids
        """
        list.clear()
        if objs:
            for item in objs:
                item = QtWidgets.QListWidgetItem(str(item.pid))
                list.addItem(item)
        list.sortItems()

    def _moveLeft(self):  # not needed now
        """
        Move contents of the right window to the left window
        """
        for item in self.rightList.selectedItems():
            leftItem = QtWidgets.QListWidgetItem(item)
            self.leftList.addItem(leftItem)
            self.rightList.takeItem(self.rightList.row(item))
        self.leftList.sortItems()

    def _moveRight(self):  # not needed now
        """
        Move contents of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
            self.leftList.takeItem(self.leftList.row(item))
        self.rightList.sortItems()

    def _moveItemLeft(self):
        """
        Move contents of the right window to the left window
        """
        rightItem = QtWidgets.QListWidgetItem(self.rightList.selectedItems())
        self.leftList.addItem(rightItem)
        self.rightList.takeItem(self.rightList.row(rightItem))
        self.leftList.sortItems()

    def _moveItemRight(self):
        """
        Move contents of the left window to the right window
        """
        leftItem = QtWidgets.QListWidgetItem(self.leftList.selectedItem)
        self.rightList.addItem(leftItem)
        self.leftList.takeItem(self.leftList.row(leftItem))
        self.rightList.sortItems()

    def _copyRight(self):
        """
        Copy selection of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
        self.rightList.sortItems()

    def getLeftList(self):
        return self.leftList.getTexts()

    def getRightList(self):
        return self.rightList.getTexts()


#===================================================================================================
# __main__
#===================================================================================================

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog
    from ccpn.ui.gui.widgets.Widget import Widget


    def droppedCallback(*r):
        print(r)


    app = TestApplication()

    texts = ['Int', 'Float', 'String', '']
    objects = [int, float, str, 'Green']

    popup = CcpnDialog(windowTitle='Test widget', setLayout=True)
    widget = ListWidget(parent=popup, allowDuplicates=True, acceptDrops=True, grid=(0, 0))
    widget2 = ListWidget(parent=popup, allowDuplicates=False, acceptDrops=True, grid=(0, 1))
    widget2.dropped.connect(droppedCallback)

    for i in ['a', 'a', 'c']:
        widget.addItem(i)
    popup.show()
    popup.raise_()
    app.start()
