"""Module Documentation here

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
__dateModified__ = "$dateModified: 2017-07-07 16:32:56 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: rhfogh $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from functools import partial
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject


class SpectrumGroupToolBar(ToolBar):
    def __init__(self, parent=None, spectrumDisplay=None, **kwds):
        super().__init__(parent=parent, **kwds)
        self.spectrumDisplay = spectrumDisplay
        self._project = self.spectrumDisplay.project

        # self._spectrumGroups = []

    # def _getSpectrumGroups(self):
    #     from ccpn.ui.gui.lib.GuiSpectrumDisplay import SPECTRUMGROUPS, SPECTRUMGROUPLIST
    #
    #     _spectrumGroups = AbstractWrapperObject.getParameter(self.spectrumDisplay,
    #                                                          SPECTRUMGROUPS, SPECTRUMGROUPLIST)
    #     if _spectrumGroups is not None:
    #         return _spectrumGroups
    #
    #     AbstractWrapperObject.setParameter(self.spectrumDisplay,
    #                                        SPECTRUMGROUPS, SPECTRUMGROUPLIST, ())
    #     return ()
    #
    # def _setSpectrumGroups(self, groups):
    #     from ccpn.ui.gui.lib.GuiSpectrumDisplay import SPECTRUMGROUPS, SPECTRUMGROUPLIST
    #
    #     AbstractWrapperObject.setParameter(self.spectrumDisplay,
    #                                        SPECTRUMGROUPS, SPECTRUMGROUPLIST, groups)

    def _addAction(self, spectrumGroup):

        _spectrumGroups = self.spectrumDisplay._getSpectrumGroups()

        if spectrumGroup.pid not in _spectrumGroups:
            # _spectrumGroups.append(spectrumGroup)
            _spectrumGroups += (spectrumGroup.pid,)

            action = self.addAction(spectrumGroup.pid, partial(self._toggleSpectrumGroup, spectrumGroup))
            action.setCheckable(True)
            action.setChecked(True)
            action.setToolTip(spectrumGroup.name)
            action.setObjectName(spectrumGroup.pid)
            self._setupButton(action, spectrumGroup)

            self.spectrumDisplay._setSpectrumGroups(_spectrumGroups)

    def _forceAddAction(self, spectrumGroup):

        action = self.addAction(spectrumGroup.pid, partial(self._toggleSpectrumGroup, spectrumGroup))
        action.setCheckable(True)
        action.setChecked(True)
        action.setToolTip(spectrumGroup.name)
        action.setObjectName(spectrumGroup.pid)
        self._setupButton(action, spectrumGroup)

    def _setupButton(self, action, spectrumGroup):
        widget = self.widgetForAction(action)
        widget.setIconSize(QtCore.QSize(120, 10))
        widget.setFixedSize(75, 30)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """
        Re-implementation of the Toolbar mouse event so a right mouse context menu can be raised.
        """
        if event.button() == QtCore.Qt.RightButton:
            button = self.childAt(event.pos())
            if button:
                sg = self._project.getByPid(button.text())
                if sg is not None:
                    if len(button.actions()) > 0:
                        menu = self._setupContextMenu(button.actions()[0], sg)
                        if menu:
                            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
                            menu.exec()

    def _setupContextMenu(self, action, spectrumGroup):

        popMenu = Menu('', self)
        removeAction = popMenu.addAction('Remove', partial(self._deleteSpectrumGroup, action, spectrumGroup))
        peakListAction = popMenu.addAction('PeakLists')
        peakListAction.setCheckable(True)
        peakListAction.toggled.connect(partial(self._showHidePeakListView, spectrumGroup))
        return popMenu

    def _getStrip(self):
        strips = self.spectrumDisplay.strips
        if len(strips) > 0:
            return strips[0]

    def _toggleSpectrumGroup(self, spectrumGroup):
        spectrumGroupPeakLists = [spectrum.peakLists[0] for spectrum in spectrumGroup.spectra]
        peakListViews = [peakListView for peakListView in self.spectrumDisplay.peakListViews]

        strip = self._getStrip()
        if strip is not None:
            spectrumViews = [spectrumView for spectrumView in strip.spectrumViews
                             if spectrumView.spectrum in spectrumGroup.spectra]

            widget = self.widgetForAction(self.sender())
            if widget.isChecked():
                for spectrumView in spectrumViews:
                    spectrumView.setVisible(True)
                    if hasattr(spectrumView, 'plot'):
                        spectrumView.plot.show()
                    self._showPeakList(spectrumGroupPeakLists, peakListViews)
            else:
                for spectrumView in spectrumViews:
                    spectrumView.setVisible(False)
                    if hasattr(spectrumView, 'plot'):
                        spectrumView.plot.hide()
                self._hidePeakLists(spectrumGroupPeakLists, peakListViews)

    def _deleteSpectrumGroup(self, action, spectrumGroup):
        strip = self._getStrip()
        if strip is not None:
            self.removeAction(action)
            for spectrumView in strip.spectrumViews:
                if spectrumView.spectrum in spectrumGroup.spectra:
                    spectrumView.delete()
        if spectrumGroup in self._spectrumGroups:
            self._spectrumGroups.remove(spectrumGroup)
        if len(strip.spectra) == 0:
            self.spectrumDisplay._closeModule()

    # LM: Fixme the code for peakList views below needs refactoring

    def _showHidePeakListView(self, spectrumGroup):
        for plv in self._getPeakListViews(spectrumGroup):
            if plv is not None:
                if plv.isVisible():
                    plv.setVisible(False)
                else:
                    plv.setVisible(True)

    def _hidePeakLists(self, spectrumGroupPeakLists, peakListViews):
        for peakList in spectrumGroupPeakLists:
            if self.spectrumDisplay is not None:
                for peakListView in peakListViews:
                    if peakList == peakListView.peakList:
                        peakListView.setVisible(False)

    def _showPeakList(self, spectrumGroupPeakLists, peakListViews):
        for peakList in spectrumGroupPeakLists:
            if self.spectrumDisplay is not None:
                for peakListView in peakListViews:
                    if peakList == peakListView.peakList:
                        peakListView.setVisible(True)

    def _getPeakListViews(self, spectrumGroup):
        spectrumGroupPeakLists = [peakList for spectrum in spectrumGroup.spectra for peakList in spectrum.peakLists]
        return [plv for peakList in spectrumGroupPeakLists for plv in peakList.peakListViews]
