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
__dateModified__ = "$dateModified: 2017-07-07 16:32:46 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets

from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.PulldownListsForObjects import NotePulldown
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.Note import Note
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.core.lib.ContextManagers import undoBlock


logger = getLogger()


class NotesEditorModule(CcpnModule):
    """
    This class implements the module for editing the NotesList.
    """
    includeSettingsWidget = False
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'

    className = 'NotesEditorModule'
    attributeName = 'notes'  # self.project.notes

    def __init__(self, mainWindow=None, name='Notes Editor',
                 note=None, selectFirstItem=False):
        """
        Initialise the widgets for the module.
        :param mainWindow: required
        :param name: optional
        :param note: leave as None to let window handle item selection
        """
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None
        self.note = None

        self._widgetScrollArea = ScrollArea(parent=self.mainWidget, grid=(0, 0), scrollBarPolicies=('never', 'never'))
        self._widgetScrollArea.setWidgetResizable(True)
        self._widget = Widget(parent=self._widgetScrollArea, setLayout=True)

        row = 0
        self.spacer = Spacer(self._widget, 5, 5,
                             QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                             grid=(row, 0), gridSpan=(1, 1))

        row += 1
        self.noWidget = NotePulldown(parent=self._widget,
                                     mainWindow=self.mainWindow, default=None,
                                     grid=(row, 0), gridSpan=(1, 1), minimumWidths=(0, 100),
                                     showSelectName=True,
                                     sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                     callback=self._selectionPulldownCallback)

        row += 1
        self.spacer = Spacer(self._widget, 5, 5,
                             QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                             grid=(row, 0), gridSpan=(1, 1))

        #~~~~~~~~~~ define noteWidget box to contain man editing
        row += 1
        self.noteWidget = Widget(self._widget, grid=(row, 0), gridSpan=(4, 5), setLayout=True)
        self.noteWidget.hide()

        self.label1 = Label(self.noteWidget, text='Note name', grid=(1, 0), vAlign='centre', hAlign='right')
        self.label1.setMaximumHeight(30)
        self.lineEdit1 = LineEdit(self.noteWidget, grid=(1, 1), gridSpan=(1, 2), vAlign='top')
        self.lineEdit1.editingFinished.connect(self._applyNote)  # *1
        self.spacer = Spacer(self.noteWidget, 5, 5,
                             QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
                             grid=(2, 3), gridSpan=(1, 1))

        self.textBox = TextEditor(self.noteWidget, grid=(3, 0), gridSpan=(1, 6))
        self.textBox.editingFinished.connect(self._applyNote)  # *1

        # *1 Automatically save the note when it loses the focus.
        # Otherwise is very dangerous of loosing all the carefully written notes if you forget to press the button apply!

        #~~~~~~~~~~ end of noteWidget box

        row += 1
        # this spacer is expanding, will fill the space when the textbox is invisible
        self.spacer = Spacer(self._widget, 5, 5,
                             QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
                             grid=(row, 4), gridSpan=(1, 1))

        self._widget.setContentsMargins(5, 5, 5, 5)

        self._widgetScrollArea.setWidget(self._widget)
        self._widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        self._noteNotifier = None
        self.droppedNotifier = None
        self._setNotifiers()

        if note is not None:
            self.selectNote(note)
        elif selectFirstItem:
            self.noWidget.selectFirstItem()

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events
        """
        pids = data.get('pids', [])
        from ccpn.ui.gui.lib.MenuActions import _openItemObject

        objs = [self.project.getByPid(pid) for pid in pids]

        selectableObjects = [obj for obj in objs if isinstance(obj, Note)]
        others = [obj for obj in objs if not isinstance(obj, Note)]
        if len(selectableObjects) > 0:
            self.selectNote(selectableObjects[0])
            _openItemObject(self.mainWindow, selectableObjects[1:])

        else:
            from ccpn.ui.gui.widgets.MessageDialog import showYesNo

            othersClassNames = list(set([obj.className for obj in others]))
            if len(othersClassNames) > 0:
                if len(othersClassNames) == 1:
                    title, msg = 'Dropped wrong item.', 'Do you want to open the %s in a new module?' % ''.join(othersClassNames)
                else:
                    title, msg = 'Dropped wrong items.', 'Do you want to open items in new modules?'
                openNew = showYesNo(title, msg)
                if openNew:
                    _openItemObject(self.mainWindow, others)

    def selectNote(self, note=None):
        """
        Manually select a Note from the pullDown
        """
        if note is None:
            # logger.warning('select: No Note selected')
            # raise ValueError('select: No Note selected')
            self.noWidget.selectFirstItem()
        else:
            if not isinstance(note, Note):
                logger.warning('select: Object is not of type Note')
                raise TypeError('select: Object is not of type Note')
            else:
                if note.pid in self.noWidget.textList:
                    self.note = note
                    self.noWidget.select(self.note.pid)

    def _setNotifiers(self):
        """
        Set a Notifier to call when a note is created/deleted/renamed/changed
        rename calls on name
        change calls on any other attribute
        """
        self._noteNotifier = self.setNotifier(self.project,
                                              [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME, Notifier.CHANGE],
                                              Note.__name__,
                                              self._updateCallback)
        self.droppedNotifier = self.setGuiNotifier(self.mainWidget,
                                                   [GuiNotifier.DROPEVENT], [DropBase.PIDS],
                                                   self._processDroppedItems)

    # def _clearNotifiers(self):
    #     """
    #     clean up the notifiers
    #     """
    #     if self._noteNotifier is not None:
    #         self._noteNotifier.unRegister()
    #     if self.droppedNotifier is not None:
    #         self.droppedNotifier.unRegister()

    def _applyNote(self):
        """
        Called by clicking the apply button in the module.
        Temporarily disable notifiers, and define commandEchoBlock so all changes
        are treated as a single undo/redo event
        """
        self.setBlankingAllNotifiers(True)  # disable the notifier while updating object other
        if self.note:  # calls _updateCallBack during _applyNote
            name = self.lineEdit1.text()
            text = self.textBox.toPlainText()

            with undoBlock():
                if name != self.note.name:
                    self.note.rename(name)
                self.note.text = text

            self.noWidget.select(self.note.pid)
        self.setBlankingAllNotifiers(False)

    def _reject(self):
        """
        Closes the note editor ignoring all changes.
        """
        self._closeModule()

    def _selectionPulldownCallback(self, item):
        """
        Notifier Callback for selecting Note from the pull down menu
        """
        self.note = self.project.getByPid(item)
        if self.note is not None:
            self._update(self.note)
        else:
            self.noteWidget.hide()

    def _updateCallback(self, data):
        """
        Notifier callback for updating module when a Note is create/delete/rename/change
        """
        thisNoteList = getattr(data[Notifier.THEOBJECT], self.attributeName)  # get the notesList
        modifiedNote = data[Notifier.OBJECT]

        if self.note in thisNoteList:
            self._update(self.note)
        else:
            self.noteWidget.hide()

    def _update(self, note):
        """
        Update the Note widgets
        """
        self.noWidget.select(note.pid)
        self.textBox.setText(note.text)
        self.lineEdit1.setText(note.name)
        self.noteWidget.show()
        self.show()

    def _deleteNote(self):
        """
        Delete the current note with the delete button
        """
        if self.note:
            self.note.delete()

    def _closeModule(self):
        """
        CCPN-INTERNAL: used to close the module
        """
        super()._closeModule()

    def close(self):
        """
        Close the table from the commandline
        """
        self._closeModule()
