"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (http://www.ccpn.ac.uk) 2014 - 2020"
__credits__ = ("Ed Brooksbank, Luca Mureddu, Timothy J Ragan & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2020-03-10 01:57:05 +0000 (Tue, March 10, 2020) $"
__version__ = "$Revision: 3.0.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import importlib, os

from PyQt5 import QtWidgets, QtCore, QtGui
from functools import partial

from ccpn.core.Project import Project
from ccpn.core.Peak import Peak
from ccpn.core.PeakList import PeakList
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Sample import Sample

from ccpn.ui.gui.widgets.ToolBar import ToolBar
from typing import Tuple

from ccpn.ui.gui.widgets.Widget import WidgetCorner
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.PhasingFrame import PhasingFrame
from ccpn.ui.gui.widgets.SpectrumToolBar import SpectrumToolBar
from ccpn.ui.gui.widgets.SpectrumGroupToolBar import SpectrumGroupToolBar
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea, SpectrumDisplayScrollArea
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.AssignmentLib import _assignNmrAtomsToPeaks, _assignNmrResiduesToPeaks
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import PEAKSELECT, MULTIPLETSELECT
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import CcpnGLWidget
from ccpn.ui.gui.widgets.GLWidgets import Gui1dWidgetAxis, GuiNdWidgetAxis
from ccpn.util.Logging import getLogger
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrChain import NmrChain
from ccpn.ui.gui.lib.Strip import GuiStrip
from ccpn.ui._implementation.PeakListView import PeakListView
from ccpn.ui._implementation.IntegralListView import IntegralListView
from ccpn.ui._implementation.MultipletListView import MultipletListView
from ccpn.ui.gui.widgets.SettingsWidgets import SpectrumDisplaySettings
from ccpn.ui._implementation.SpectrumView import SpectrumView
from ccpn.core.lib.ContextManagers import undoStackBlocking, notificationBlanking, \
    BlankedPartial, undoBlock, notificationEchoBlocking
from ccpn.util.decorators import logCommand
from ccpn.util.Common import makeIterableList
from ccpn.core.lib import Undo
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.ui.gui.guiSettings import getColours, CCPNGLWIDGET_HEXBACKGROUND, CCPNGLWIDGET_BACKGROUND


STRIP_SPACING = 5
STRIP_MINIMUMWIDTH = 100
STRIP_MINIMUMHEIGHT = STRIP_MINIMUMWIDTH
AXIS_WIDTH = 30
AXISUNITS = ['ppm', 'Hz', 'points']
SPECTRUMGROUPS = 'spectrumGroups'
SPECTRUMISGROUPED = 'spectrumIsGrouped'
SPECTRUMGROUPLIST = 'spectrumGroupList'
STRIPDIRECTIONS = ['Y', 'X', 'T']
SPECTRUMDISPLAY = 'spectrumDisplay'
STRIPARRANGEMENT = 'stripArrangement'

MAXITEMLOGGING = 4
MAXTILEBOUND = 65536
INCLUDE_AXIS_WIDGET = True


# GST All this complication is added because the scroll frame appears to have a lower margin added by some part of Qt
#     that we can't control in PyQt. Specifically even if you overide setContentsMargins on ScrollArea it is never
#     called but at the same time ScrollArea gets a lower contents margin of 1 pixel that we didn't ask for... ;-(
def styleSheetPredicate(target):
    children = [child for child in target.children() if isinstance(child, QtGui.QWidget)]

    return len(children) < 2


def styleSheetMutator(styleSheetTemplate, predicate, clazz):
    if predicate:
        styleSheet = styleSheetTemplate % (clazz.__class__.__name__, '')
    else:
        styleSheet = styleSheetTemplate % (clazz.__class__.__name__, 'background-color: #191919;')

    return styleSheet


class ScrollAreaWithPredicateStylesheet(ScrollArea):

    def __init__(self, styleSheetTemplate, predicate, mutator, *args, **kwds):
        self.styleSheetTemplate = styleSheetTemplate
        self.predicate = predicate
        self.mutator = mutator
        super().__init__(*args, **kwds)

    def checkPredicate(self):
        return self.predicate(self)

    def modifyStyleSheet(self, predicate):
        self.setStyleSheet(self.mutator(self.styleSheetTemplate, predicate, self))

    def resizeEvent(self, e):
        self.modifyStyleSheet(self.checkPredicate())
        return super().resizeEvent(e)


class GuiSpectrumDisplay(CcpnModule):
    """
    Main spectrum display Module object.

    This module inherits the following attributes from the SpectrumDisplay wrapper class:

    title             Name of spectrumDisplay;
                        :return <str>
    stripDirection    Strip axis direction
                        :return <str>:('X', 'Y', None) - None only for non-strip plots
    stripCount        Number of strips
                        :return <str>.
    comment           Free-form text comment
                        comment = <str>
                        :return <str>
    axisCodes         Fixed string Axis codes in original display order
                        :return <tuple>:(X, Y, Z1, Z2, ...)
    axisOrder         String Axis codes in display order, determine axis display order
                        axisOrder = <sequence>:(X, Y, Z1, Z2, ...)
                        :return <tuple>:(X, Y, Z1, Z2, ...)
    is1D              True if this is a 1D display
                        :return <bool>
    window            Gui window showing SpectrumDisplay
                        window = <Window>
                        :return <Window>
    nmrResidue        NmrResidue attached to SpectrumDisplay
                        nmrResidue = <NmrResidue>
                        :return <NmrResidue>
    positions         Axis centre positions, in display order
                        positions = <Tuple>
                        :return <Tuple>
    widths            Axis display widths, in display order
                        widths = <Tuple>
                        :return <Tuple>
    units             Axis units, in display order
                        :return <Tuple>

    parameters        Keyword-value dictionary of parameters.
                        NB the value is a copy - modifying it will not modify the actual data.
                        Values can be anything that can be exported to JSON,
                        including OrderedDict, numpy.ndarray, ccpn.util.Tensor,
                        or pandas DataFrame, Series, or Panel
                        :return <dict>
    setParameter      Add name:value to parameters, overwriting existing entries
                        setParameter(name:str, value)
                          :param name:<str> name of parameter
                          :param value: value to set
    deleteParameter   Delete parameter
                        deleteParameter(name:str)
                          :param name:<str> name of parameter to delete
    clearParameters   Delete all parameters
    updateParameters  Update list of parameters
                        updateParameters(value:dict)
                          :param value:<dict> parameter list

    resetAxisOrder    Reset display to original axis order
    findAxis          Find axis
                        findAxis(axisCode)
                          :param axisCode:
                          :return axis
    """

    # overide in specific module implementations
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'
    settingsMinimumSizes = (250, 50)

    def __init__(self, mainWindow, name, useScrollArea=False):
        """
        Initialise the Gui spectrum display object

        :param mainWindow: MainWindow instance
        :param name: Title-bar name for the Module
        :param useScrollArea: Having a scrolled widget containing OpenGL and PyQtGraph widgets does not seem to work.
                              The leftmost strip is full of random garbage if it's not completely visible.
                              So for now add option below to have it turned off (False) or on (True).
        """

        getLogger().debug('GuiSpectrumDisplay>> mainWindow, name: %s %s' % (mainWindow, name))
        super(GuiSpectrumDisplay, self).__init__(mainWindow=mainWindow, name=name,
                                                 size=(1100, 1300), autoOrientation=False
                                                 )
        self.setMinimumWidth(150)

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        # derive current from application
        self.current = mainWindow.application.current
        # cannot set self.project because self is a wrapper object
        # self.project = mainWindow.application.project

        # self.mainWidget will be the parent of all the subsequent widgets
        self.qtParent = self.mainWidget

        # create settings widget
        if not self.is1D:
            self._spectrumDisplaySettings = SpectrumDisplaySettings(parent=self.settingsWidget,
                                                                    mainWindow=self.mainWindow, spectrumDisplay=self,
                                                                    grid=(0, 0),
                                                                    xTexts=AXISUNITS, yTexts=AXISUNITS,
                                                                    _baseAspectRatioAxisCode=self.application.preferences.general._baseAspectRatioAxisCode,
                                                                    _aspectRatios=self.application.preferences.general.aspectRatios.copy(),
                                                                    _useLockedAspectRatio=self.application.preferences.general.useLockedAspectRatio,
                                                                    _useDefaultAspectRatio=self.application.preferences.general.useDefaultAspectRatio)
        else:
            self._spectrumDisplaySettings = SpectrumDisplaySettings(parent=self.settingsWidget,
                                                                    mainWindow=self.mainWindow, spectrumDisplay=self,
                                                                    grid=(0, 0),
                                                                    xTexts=AXISUNITS, yTexts=[''],
                                                                    showYAxis=False,
                                                                    _baseAspectRatioAxisCode=self.application.preferences.general._baseAspectRatioAxisCode,
                                                                    _aspectRatios=self.application.preferences.general.aspectRatios.copy(),
                                                                    _useLockedAspectRatio=self.application.preferences.general.useLockedAspectRatio,
                                                                    _useDefaultAspectRatio=self.application.preferences.general.useDefaultAspectRatio)

        self._spectrumDisplaySettings.settingsChanged.connect(self._settingsChanged)
        self.settingsWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        # respond to values changed in the containing spectrumDisplay settings widget
        self._spectrumDisplaySettings.stripArrangementChanged.connect(self._stripDirectionChangedInSettings)

        # GWV: Not sure what the widget argument is for
        # LM: is the spectrumDisplay, used in the widget to set actions/callbacks to the buttons
        spectrumRow = 1
        toolBarRow = 0
        stripRow = 2
        axisRow = 3
        phasingRow = 4

        # self._widgetScrollArea = ScrollArea(parent=self.qtParent, scrollBarPolicies=('asNeeded', 'never'),
        #                                     grid=(spectrumRow, 0), gridSpan=(1,7))
        # self._widgetScrollArea.setWidgetResizable(True)
        #
        # self._spectrumFrame = Frame(parent=self.qtParent, setLayout=True,
        #                             grid=(spectrumRow, 0), gridSpan=(1, 7))
        # self.spectrumToolBar = SpectrumToolBar(parent=self._spectrumFrame, widget=self, grid=(0,0))
        #
        # self._widgetScrollArea.setWidget(self._spectrumFrame)
        # self._widgetScrollArea.setFixedHeight(30)
        # self._spectrumFrame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Ignored)
        # # self.spectrumToolBar.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        # self.spectrumToolBar.setFixedSize(self.spectrumToolBar.sizeHint())

        # self._spectrumFrame = Frame(parent=self.qtParent, setLayout=True,
        #                             grid=(spectrumRow, 0), gridSpan=(1, 7))
        #
        # self._leftButton = Button(parent=self._spectrumFrame, vAlign='c', hAlign='l', grid=(0, 0),
        #                          icon='icons/yellow-arrow-left')
        #
        # self.spectrumToolBar = SpectrumToolBar(parent=self._spectrumFrame, widget=self,
        #                                        grid=(0, 1))
        # self.spectrumToolBar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        #
        # self._spacer = Spacer(self._spectrumFrame, 2, 2,
        #                       QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed, grid=(0, 2))
        #
        # self._rightButton = Button(parent=self._spectrumFrame, grid=(0, 3),
        #                          icon='icons/yellow-arrow-right')
        #
        #

        self.toolBarFrame = Frame(parent=self.qtParent, grid=(spectrumRow, 0), gridSpan=(1, 7), setLayout=True,
                                  hPolicy='minimal', hAlign='left')
        self.toolBarFrame.setContentsMargins(4, 4, 4, 4)

        TOOLBAR_HEIGHT = 30

        # Utilities Toolbar; filled in Nd/1d classes
        self.spectrumUtilToolBar = ToolBar(parent=self.toolBarFrame, iconSizes=(24, 24),
                                           grid=(0, 0), hPolicy='minimal', hAlign='left')
        self.spectrumUtilToolBar.setFixedHeight(TOOLBAR_HEIGHT)

        self.spectrumToolBar = SpectrumToolBar(parent=self.toolBarFrame, widget=self,
                                               grid=(1, 0), hPolicy='minimal', hAlign='left')
        self.spectrumToolBar.setFixedHeight(TOOLBAR_HEIGHT)

        # spectrumGroupsToolBar
        self.spectrumGroupToolBar = SpectrumGroupToolBar(parent=self.toolBarFrame, spectrumDisplay=self,
                                                         grid=(2, 0), hPolicy='minimal', hAlign='left')

        self.spectrumGroupToolBar.setFixedHeight(TOOLBAR_HEIGHT)
        self.spectrumGroupToolBar.hide()

        if self.application.preferences.general.showToolbar:
            self.spectrumUtilToolBar.show()
        else:
            self.spectrumUtilToolBar.hide()

        self.stripFrame = Frame(setLayout=True, showBorder=False, spacing=(5, 0), stretch=(1, 1), margins=(0, 0, 0, 0),
                                acceptDrops=True)
        # self.stripFrame.layout().setContentsMargins(0, 0, 0, 0)

        # frameStyleSheetTemplate = ''' .%s { border-left: 1px solid #a9a9a9;
        #                               border-right: 1px solid #a9a9a9;
        #                               border-bottom: 1px solid #a9a9a9;
        #                               border-bottom-right-radius: 2px;
        #                               border-bottom-left-radius: 2px;
        #                               %s
        #                               }'''

        if useScrollArea:
            # scroll area for strips
            # This took a lot of sorting-out; better leave as is or test thoroughly
            # self._stripFrameScrollArea = ScrollAreaWithPredicateStylesheet(parent=self.qtParent,
            self._stripFrameScrollArea = SpectrumDisplayScrollArea(parent=self.qtParent,
                                                                   # styleSheetTemplate = frameStyleSheetTemplate,
                                                                   # predicate=styleSheetPredicate, mutator=styleSheetMutator,
                                                                   setLayout=True, acceptDrops=False,
                                                                   scrollBarPolicies=('asNeeded', 'never'))
            self._stripFrameScrollArea.setWidget(self.stripFrame)
            self._stripFrameScrollArea.setWidgetResizable(True)
            self.qtParent.getLayout().addWidget(self._stripFrameScrollArea, stripRow, 0, 1, 7)
            self._stripFrameScrollArea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                     QtWidgets.QSizePolicy.Expanding)
            self.stripFrame.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                          QtWidgets.QSizePolicy.Expanding)

        else:
            self._stripFrameScrollArea = None
            self.qtParent.getLayout().addWidget(self.stripFrame, stripRow, 0, 1, 7)
            # self.stripFrame.setStyleSheet(frameStyleSheetTemplate % ('Frame', ''))

        if INCLUDE_AXIS_WIDGET:
            # NOTE:ED - testing new axis widget - required actually adding tiling
            if self.is1D:
                # self._rightGLAxis = Gui1dWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow)
                pass

            else:
                self._rightGLAxis = GuiNdWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow)

                self._rightGLAxis.tilePosition = (0, -1)
                self._rightGLAxis.setAxisType(1)
                self._rightGLAxis.show()

            # NOTE:ED - testing new axis widget - required actually adding tiling
            if self.is1D:
                # self._bottomGLAxis = Gui1dWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow)
                pass

            else:
                self._bottomGLAxis = GuiNdWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow)

                self._bottomGLAxis.tilePosition = (-1, 0)
                self._bottomGLAxis.setAxisType(0)
                self._bottomGLAxis.hide()

            # add a small widget to fill the corner between the widgets
            self._cornerAxis = WidgetCorner(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow)

        self.qtParent.getLayout().setContentsMargins(0, 0, 0, 0)
        self.qtParent.getLayout().setSpacing(0)
        self.lastAxisOnly = mainWindow.application.preferences.general.lastAxisOnly

        if not self.is1D:
            self.setVisibleAxes()

        includeDirection = not self.is1D
        self.phasingFrame = PhasingFrame(parent=self.qtParent,
                                         showBorder=False,
                                         includeDirection=includeDirection,
                                         callback=self._updatePhasing,
                                         returnCallback=self._updatePivot,
                                         directionCallback=self._changedPhasingDirection,
                                         applyCallback=self._applyPhasing,
                                         grid=(phasingRow, 0), gridSpan=(1, 7), hAlign='top',
                                         margins=(0, 0, 0, 0), spacing=(0, 0))
        self.phasingFrame.setVisible(False)

        # self.stripFrame.setAcceptDrops(True)

        # notifier to respond to items being dropped onto the stripFrame
        self.droppedNotifier = self.setGuiNotifier(self.stripFrame,
                                                   [GuiNotifier.DROPEVENT], [DropBase.URLS, DropBase.PIDS],
                                                   self._processDroppedItems)

        # GWV: This assures that a 'hoverbar' is visible over the strip when dragging
        # the module to another location
        self.hoverEvent = self._hoverEvent
        self._phasingTraceScale = 1.0e-7
        self.stripScaleFactor = 1.0

        self._spectrumRenameNotifier = self.setNotifier(self.project,
                                                        [Notifier.RENAME],
                                                        'Spectrum',
                                                        self._spectrumRenameChanged)

        # FIXME _toolbarNotifier is a nasty notifier.
        self._toolbarNotifier = self.setNotifier(self.project,
                                                 [Notifier.CHANGE],
                                                 'SpectrumDisplay',
                                                 self._toolbarChange)

        self._spectrumViewNotifier = self.setNotifier(self.project,
                                                      [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],
                                                      SpectrumView.className,
                                                      self._spectrumViewChanged,
                                                      onceOnly=True)

        self._peakListViewNotifier = self.setNotifier(self.project,
                                                      [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],
                                                      PeakListView.className,
                                                      self._listViewChanged,
                                                      onceOnly=True)

        self._integralListViewNotifier = self.setNotifier(self.project,
                                                          [Notifier.CREATE, Notifier.DELETE],
                                                          IntegralListView.className,
                                                          self._listViewChanged,
                                                          onceOnly=True)

        self._multipletListViewNotifier = self.setNotifier(self.project,
                                                           [Notifier.CREATE, Notifier.DELETE],
                                                           MultipletListView.className,
                                                           self._listViewChanged,
                                                           onceOnly=True)

    # GWV 20181124:
    # def _unRegisterNotifiers(self):
    #     """Unregister notifiers
    #     """
    #     if self._spectrumViewNotifier:
    #         self._spectrumViewNotifier.unRegister()

    def showAllStripHeaders(self, handle=None):
        """Convenience to show headers of all strips
        """
        for strip in self.strips:
            strip.header.headerVisible = True
            if handle:
                strip.header.handle = handle

    def hideAllStripHeaders(self, handle=None):
        """Convenience to hide headers of all strips
        """
        for strip in self.strips:
            # only hide the strips that match the handle or hide all if None
            if handle is None:
                strip.header.headerVisible = False
            elif strip.header.handle == handle:
                strip.header.headerVisible = False

    def _spectrumRenameChanged(self, data):
        """Respond to a change on the name of a spectrum
        """
        self.spectrumToolBar._spectrumRename(data)

    def _spectrumViewChanged(self, data):
        """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
        """
        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibilty()

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict={})

    def _spectrumViewVisibleChanged(self):
        """Respond to a visibleChanged in one of the spectrumViews.
        """
        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibilty()

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict={})

    def _settingsChanged(self, dataDict):
        """Handle changes that occur in the settings widget
        dataDict is a dictionary of settingsWidget contents:
            {
            xUnits: range(0-number of options)
            yUnits: range(0-number of options)
            lockAspectRatio: True/False
            }
        """
        # spawn a redraw of the GL windows
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict=dataDict)

    def _stripDirectionChangedInSettings(self, value):
        """Handle changing the stripDirection from the settings widget
        """
        if value not in range(len(STRIPDIRECTIONS)):
            raise ValueError('stripDirection not in ', STRIPDIRECTIONS)

        newDirection = STRIPDIRECTIONS[value]

        # set the new stripDirection, and redraw
        self.stripArrangement = newDirection
        self._redrawLayout(self)

    def _listViewChanged(self, data):
        """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
        """
        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibilty()

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals.emitPaintEvent()

    @property
    def isGrouped(self):
        """Return whether the spectrumDisplay contains grouped spectra
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        grouped = AbstractWrapperObject.getParameter(self, SPECTRUMGROUPS, SPECTRUMISGROUPED)
        if grouped is not None:
            return grouped

        # set default to False
        AbstractWrapperObject.setParameter(self, SPECTRUMGROUPS, SPECTRUMISGROUPED, False)
        return False

    @isGrouped.setter
    def isGrouped(self, grouped):
        """Set whether the spectrumDisplay contains grouped spectra
        """
        AbstractWrapperObject.setParameter(self, SPECTRUMGROUPS, SPECTRUMISGROUPED, grouped)

    @property
    def stripArrangement(self):
        """Strip axis direction ('X', 'Y', 'T', None) - None only for non-strip plots
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        arrangement = AbstractWrapperObject.getParameter(self, SPECTRUMDISPLAY, STRIPARRANGEMENT)
        if arrangement is not None:
            return arrangement

        # set default values in the ccpnInternal store
        arrangement = self._wrappedData.stripDirection  # SHOULD always be 'Y', if it makes a difference
        AbstractWrapperObject.setParameter(self, SPECTRUMDISPLAY, STRIPARRANGEMENT, arrangement)
        return arrangement

    @stripArrangement.setter
    def stripArrangement(self, value):
        """Set the new strip direction ('X', 'Y', 'T', None) - None only for non-strip plots
        """
        if not isinstance(value, str):
            raise TypeError('stripArrangement must be a string')
        elif value not in ['X', 'Y', 'T']:
            raise ValueError("stripArrangement must be either 'X', 'Y' or 'T'")

        AbstractWrapperObject.setParameter(self, SPECTRUMDISPLAY, STRIPARRANGEMENT, value)
        # leave the _wrappedData as it's initialised value

        self.setVisibleAxes()

    def _updateAxesVisibilty(self):
        if not self.is1D:
            self._rightGLAxis.updateVisibleSpectrumViews()
            self._bottomGLAxis.updateVisibleSpectrumViews()

    def setVisibleAxes(self):
        """Set which of the axis widgets are visible based on the strip tilePositions and stripArrangement
        """
        # NOTE:ED - currently only one row or column
        #           Should no-shared-axis mean don't show either axis?
        #           Need to think about tiles later
        # leave a gap for overlaying the axis widgets

        if not self.lastAxisOnly or len(self.strips) < 2:
            # remove the margins and hide the axes
            self._stripFrameScrollArea.setViewportMargins(0, 0, 0, 0)
            self._rightGLAxis.hide()
            self._bottomGLAxis.hide()
        else:

            # show the required axis
            if self.stripArrangement == 'Y':
                self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), 0)
                # self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), self._bottomGLAxis.height())
                self._rightGLAxis.show()
                self._bottomGLAxis.hide()
                self._rightGLAxis._updateAxes = True
            else:
                self._stripFrameScrollArea.setViewportMargins(0, 0, 0, self._bottomGLAxis.height())
                # self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), self._bottomGLAxis.height())
                self._rightGLAxis.hide()
                self._bottomGLAxis.show()
                self._bottomGLAxis._updateAxes = True

        # update the background colour
        self.colours = getColours()
        self._cornerAxis.setBackground(self.colours[CCPNGLWIDGET_BACKGROUND])

        self.stripFrame.update()
        self._stripFrameScrollArea._updateAxisWidgets()

    def _stripRange(self):
        """Return the bounds for the tilePositions of the strips
        as tuple of tuples ((minRow, minColumn), (maxRow, maxColumn))
        """
        maxTilePos = (0, 0)
        minTilePos = (MAXTILEBOUND, MAXTILEBOUND)
        for strip in self.strips:
            tilePos = strip.tilePosition or (0, strip.stripIndex)
            minTilePos = tuple(min(ii, jj) for ii, jj in zip(minTilePos, tilePos))
            maxTilePos = tuple(max(ii, jj) for ii, jj in zip(maxTilePos, tilePos))

        if minTilePos != (0, 0):
            raise ValueError('Illegal tilePosition in strips')

        return (minTilePos, maxTilePos)

    @property
    def rowCount(self):
        """Strip row count.
        This is independent of the stripArrangement and always returns the same value.
        If stripArrangement is 'Y', strips are in a row and 'row' will return the visible row count
        If stripArrangement is 'X', strips are in a column and 'row' will return the visible column count
        """
        _, maxTilePos = self._stripRange()
        return maxTilePos[0] + 1

    @property
    def columnCount(self):
        """Strip column count.
        This is independent of the stripArrangement and always returns the same value.
        If stripArrangement is 'Y', strips are in a row and 'column' will return the visible column count
        If stripArrangement is 'X', strips are in a column and 'column' will return the visible row count
        """
        _, maxTilePos = self._stripRange()
        return maxTilePos[1] + 1

    def stripAtTilePosition(self, tilePosition: Tuple[int, int]) -> 'Strip':
        """Return the strip at a given tilePosition
        """
        if not isinstance(tilePosition, tuple):
            raise ValueError('Expected a tuple for tilePosition')
        if len(tilePosition) != 2:
            raise ValueError('Tuple must be (x, y)')
        if any(type(vv) != int for vv in tilePosition):
            raise ValueError('Tuple must be of type int')

        for strip in self.strips:
            stripTilePos = strip.tilePosition or (0, strip.stripIndex)
            if tilePosition == stripTilePos:
                return strip

    def _stripList(self, dim, value):
        foundStrips = []
        for strip in self.strips:
            stripTilePos = strip.tilePosition or (0, strip.stripIndex)
            if stripTilePos[dim] == value:
                # append the strip with its row
                foundStrips.append((strip, stripTilePos[1 - dim]))

        # sort by required dimension
        sortedStrips = sorted(foundStrips, key=lambda k: k[dim])
        return tuple(strip for strip, dim in sortedStrips)

    def stripRow(self, row: int) -> ['Strip']:
        """Return the ordered stripRow at a given row
        tilePositions are independent of stripArrangement
        """
        if not isinstance(row, int):
            raise ValueError('Expected an int')

        return self._stripList(0, row)

    def stripColumn(self, column: int) -> ['Strip']:
        """Return the ordered stripColumn at a given column
        tilePositions are independent of stripArrangement
        """
        if not isinstance(column, int):
            raise ValueError('Expected an int')

        return self._stripList(1, column)

    def _getSpectrumGroups(self):
        """Return the groups contained in the spectrumDisplay
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        _spectrumGroups = AbstractWrapperObject.getParameter(self, SPECTRUMGROUPS, SPECTRUMGROUPLIST)
        if _spectrumGroups is not None:
            return _spectrumGroups

        AbstractWrapperObject.setParameter(self, SPECTRUMGROUPS, SPECTRUMGROUPLIST, ())
        return ()

    def _setSpectrumGroups(self, groups):
        """Set the groups in the spectrumDisplay
        """
        AbstractWrapperObject.setParameter(self, SPECTRUMGROUPS, SPECTRUMGROUPLIST, groups)

    def getSettings(self):
        """get the settings dict from the settingsWidget
        """
        return self._spectrumDisplaySettings.getValues()

    def resizeEvent(self, ev):
        if self.isDeleted:
            return

        # resize the contents of the stripFrame
        self.setColumnStretches(stretchValue=True, widths=False)
        super().resizeEvent(ev)

    def _toolbarAddSpectrum(self, data):
        """Respond to a new spectrum being added to the spectrumDisplay; add new toolbar Icon
        """
        # print('>>>_toolbarAddSpectrum')

        trigger = data[Notifier.TRIGGER]
        spectrum = data[Notifier.OBJECT]
        # self.spectrumToolBar._addSpectrumViewToolButtons(spectrum.spectrumViews[0])

    def _toolbarChange(self, data):
        """Respond to a change in the spectrum Icon toolbar denoting that clicked or spectrum created/deleted
        """
        # FIXME this is called 1000s when dropping more spectra then usual
        trigger = data[Notifier.TRIGGER]
        if trigger == Notifier.CHANGE:
            # self.spectrumToolBar._toolbarChange(self.strips[0].orderedSpectrumViews())

            if data[Notifier.OBJECT] == self:
                strips = data[Notifier.OBJECT].strips
                if len(strips) > 0:
                    specViews = strips[0].spectrumViews
                    self.spectrumToolBar._toolbarChange(self.orderedSpectrumViews(specViews))

                    # flag that the listViews need to be updated
                    for strip in self.strips:
                        strip._updateVisibility()
                    self._updateAxesVisibilty()

                    # spawn a redraw of the GL windows
                    from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

                    GLSignals = GLNotifier(parent=None)
                    GLSignals.emitPaintEvent()

    def _hoverEvent(self, event):
        event.accept()

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events

        CCPN INTERNAL: Also called from GuiStrip
        """
        theObject = data.get('theObject')

        if DropBase.URLS in data:
            # process dropped items but don't open any spectra
            self.mainWindow._processDroppedItems(data)

        # handle Pids, many more items than mainWindow._processPids
        pids = data.get(DropBase.PIDS, [])
        if pids and len(pids) > 0:
            with undoBlock():
                getLogger().info('Handling pids...')
                if len(pids) > MAXITEMLOGGING:
                    with notificationEchoBlocking():
                        self._handlePids(pids, theObject)
                else:
                    self._handlePids(pids, theObject)

    def _handlePids(self, pids, strip=None):
        "handle a; return True in case it is a Spectrum or a SpectrumGroup"
        success = False
        objs = []
        nmrChains = []
        nmrResidues = []
        nmrAtoms = []

        for pid in pids:
            obj = self.project.getByPid(pid)
            if obj:
                objs.append(obj)

        for obj in objs:
            if obj is not None and isinstance(obj, Spectrum):
                if self.isGrouped:
                    showWarning('Forbidden drop', 'A Single spectrum cannot be dropped onto grouped displays.')
                    return success

                with undoBlock():
                    self.displaySpectrum(obj)

                if strip in self.strips:
                    self.current.strip = strip
                elif self.current.strip not in self.strips:
                    self.current.strip = self.strips[0]

                # spawn a redraw of the GL windows
                from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

                GLSignals = GLNotifier(parent=None)
                GLSignals.emitPaintEvent()

                success = True
            elif obj is not None and isinstance(obj, PeakList):
                with undoBlock():
                    self._handlePeakList(obj)
                success = True
            elif obj is not None and isinstance(obj, SpectrumGroup):
                with undoBlock():
                    self._handleSpectrumGroup(obj)
                success = True
            elif obj is not None and isinstance(obj, Sample):
                with undoBlock():
                    self._handleSample(obj)
                success = True
            elif obj is not None and isinstance(obj, NmrAtom):
                nmrAtoms.append(obj)

            elif obj is not None and isinstance(obj, NmrResidue):
                nmrResidues.append(obj)

            elif obj is not None and isinstance(obj, NmrChain):
                nmrChains.append(obj)

            elif obj is not None and isinstance(obj, GuiStrip):
                self._handleStrip(obj, strip)

            elif obj is not None and isinstance(obj, Peak):
                self._handlePeak(obj, strip)

            else:
                showWarning('Dropped item "%s"' % obj.pid, 'Wrong kind; drop Spectrum, SpectrumGroup, PeakList,'
                                                           ' NmrChain, NmrResidue, NmrAtom or Strip')
        if nmrChains:
            with undoBlock():
                self._handleNmrChains(nmrChains)
        if nmrResidues:
            with undoBlock():
                self._handleNmrResidues(nmrResidues)
        if nmrAtoms:
            with undoBlock():
                self._handleNmrAtoms(nmrAtoms)

        return success

    def _handlePeak(self, peak, strip, widths=None):
        """Navigate to the peak position in the strip
        """
        from ccpn.ui.gui.lib.SpectrumDisplay import navigateToPeakInStrip

        # use the library method
        navigateToPeakInStrip(self, strip, peak, widths=None)

    def _handleStrip(self, moveStrip, dropStrip):
        """Move a strip within a spectrumDisplay by dragging the strip label to another strip
        """
        if moveStrip.spectrumDisplay == self:
            strips = self.orderedStrips
            stripInd = strips.index(dropStrip)

            if stripInd != strips.index(moveStrip):
                moveStrip.moveTo(stripInd)

    def _handlePeakList(self, peakList):
        """See if peaklist can be copied
        """
        spectrum = peakList.spectrum

        if spectrum.dimensionCount != self.strips[0].spectra[0].dimensionCount or \
                not True:  # peakList.spectrum.axisCodes match
            showWarning('Dropped PeakList "%s"' % peakList.pid, 'Cannot copy: Axes do not match')
            return
        else:
            from ccpn.ui.gui.popups.CopyPeakListPopup import CopyPeakListPopup

            popup = CopyPeakListPopup(parent=self.mainWindow, mainWindow=self.mainWindow, spectrumDisplay=self)
            popup.sourcePeakListPullDown.select(peakList.pid)
            popup.exec_()
        # showInfo(title='Copy PeakList "%s"' % peakList.pid, message='Copy to selected spectra')

    def _handleSpectrumGroup(self, spectrumGroup):
        """
        Add spectrumGroup on the display and its button on the toolBar
        """
        self.spectrumGroupToolBar._addAction(spectrumGroup)
        for spectrum in spectrumGroup.spectra:
            self.displaySpectrum(spectrum)
        if self.current.strip not in self.strips:
            self.current.strip = self.strips[0]

    def _handleSample(self, sample):
        """
        Add spectra linked to sample and sampleComponent. Used for screening
        """
        for spectrum in sample.spectra:
            self.displaySpectrum(spectrum)
        for sampleComponent in sample.sampleComponents:
            if sampleComponent.substance is not None:
                for spectrum in sampleComponent.substance.referenceSpectra:
                    self.displaySpectrum(spectrum)
        if self.current.strip not in self.strips:
            self.current.strip = self.strips[0]

    def _handleNmrChains(self, nmrChains):
        nmrResidues = []
        for chain in nmrChains:
            nmrResidues += chain.nmrResidues

        # mark all nmrChains.nmrResidues.nmrAtoms to the window
        self._handleNmrResidues(nmrResidues, showDialog=False)

    def _handleNmrResidues(self, nmrResidues, showDialog=True):

        # get the widget that is under the cursor, SHOULD be guiWidget
        point = QtGui.QCursor.pos()
        destStrip = QtWidgets.QApplication.widgetAt(point)

        if destStrip and isinstance(destStrip, CcpnGLWidget):
            objectsClicked = destStrip.getObjectsUnderMouse()

            if objectsClicked is None:
                return

            if PEAKSELECT in objectsClicked or MULTIPLETSELECT in objectsClicked:
                # dropped onto a peak or multiplet
                # dropping onto a multiplet will apply to all attached peaks

                # dialogResult = showMulti('nmrResidue', 'What do you want to do with the nmrResidues?',
                #                          texts=['Mark and Assign', 'Assign NmrResidues to selected peaks/multiplets'])

                # Assign nmrResidues atoms to peaks
                peaks = set(self.current.peaks)
                for mult in self.current.multiplets:
                    peaks = peaks | set(mult.peaks)
                _assignNmrResiduesToPeaks(peaks=list(peaks), nmrResidues=nmrResidues)

                # # mark all nmrResidues.nmrAtoms to the window
                # if 'Mark' in dialogResult:
                #     for nmrResidue in nmrResidues:
                #         self._createNmrResidueMarks(nmrResidue)

            elif not objectsClicked:
                # mark all nmrResidues.nmrAtoms to the window
                for nmrResidue in nmrResidues:
                    self._createNmrResidueMarks(nmrResidue)

    def _handleNmrAtoms(self, nmrAtoms):

        # get the widget that is under the cursor, SHOULD be guiWidget
        point = QtGui.QCursor.pos()
        destStrip = QtWidgets.QApplication.widgetAt(point)

        if destStrip and isinstance(destStrip, CcpnGLWidget):
            objectsClicked = destStrip.getObjectsUnderMouse()

            if objectsClicked is None:
                return

            if PEAKSELECT in objectsClicked or MULTIPLETSELECT in objectsClicked:
                # dropped onto a peak or multiplet
                # dropping onto a multiplet will apply to all attached peaks

                # dialogResult = showMulti('nmrAtoms', 'What do you want to do with the nmrAtoms?',
                #                          texts=['Mark and Assign', 'Assign NmrAtoms to selected peaks/multiplets'])

                # Assign nmrAtoms to peaks
                peaks = set(self.current.peaks)
                for mult in self.current.multiplets:
                    peaks = peaks | set(mult.peaks)
                _assignNmrAtomsToPeaks(nmrAtoms=nmrAtoms, peaks=list(peaks))

                # # mark all nmrAtoms to the window
                # if 'Mark' in dialogResult:
                #     for nmrAtom in nmrAtoms:
                #         self._markNmrAtom(nmrAtom)

            elif not objectsClicked:
                # mark all nmrResidues.nmrAtoms to the window
                for nmrAtom in nmrAtoms:
                    self._markNmrAtom(nmrAtom)

    def _createNmrResidueMarks(self, nmrResidue):
        """
        Mark a list of nmrAtoms in the spectrum displays
        """
        # showInfo(title='Mark nmrResidue "%s"' % nmrResidue.pid, message='mark nmrResidue in strips')

        from ccpn.AnalysisAssign.modules.BackboneAssignmentModule import nmrAtomsFromResidue, nmrAtomsFromOffsets, markNmrAtoms

        nmrAtoms = nmrAtomsFromOffsets(nmrResidue)
        if nmrAtoms:
            markNmrAtoms(self.mainWindow, nmrAtoms)

    def _markNmrAtom(self, nmrAtom):
        """
        Mark an nmrAtom in the spectrum displays with horizontal/vertical bars
        """
        # showInfo(title='Mark nmrAtom "%s"' % nmrAtom.pid, message='mark nmrAtom in strips')

        from ccpn.AnalysisAssign.modules.BackboneAssignmentModule import markNmrAtoms

        markNmrAtoms(self.mainWindow, [nmrAtom])

    def setScrollbarPolicies(self, horizontal='asNeeded', vertical='asNeeded'):
        "Set the scrolbar policies; convenience to expose to the user"
        from ccpn.ui.gui.widgets.ScrollArea import SCROLLBAR_POLICY_DICT

        if horizontal not in SCROLLBAR_POLICY_DICT or \
                vertical not in SCROLLBAR_POLICY_DICT:
            getLogger().warning('Invalid scrollbar policy (%s, %s)' % (horizontal, vertical))
        self.stripFrame.setScrollBarPolicies((horizontal, vertical))

    def _updatePivot(self):
        """Updates pivot in all strips contained in the spectrum display."""
        for strip in self.strips:
            strip._updatePivot()

    def _updatePhasing(self):
        """Updates phasing in all strips contained in the spectrum display."""
        for strip in self.strips:
            strip._updatePhasing()

    def _changedPhasingDirection(self):
        """Changes direction of phasing from horizontal to vertical or vice versa."""
        for strip in self.strips:
            strip._changedPhasingDirection()

    def updateSpectrumTraces(self):
        """Add traces to all strips"""
        for strip in self.strips:
            strip._updateTraces()

    def _applyPhasing(self, phasingValues):
        """apply the phasing values here
        phasingValues is a dict:

        { 'direction': 'horizontal' or 'vertical' - the last direction selected
          'horizontal': {'ph0': float,
                         'ph1': float,
                         'pivot': float},
          'vertical':   {'ph0': float,
                         'ph1': float,
                         'pivot': float}
        }
        """
        pass

    def toggleHTrace(self):
        if not self.is1D and self.current.strip:
            trace = not self.current.strip.hTraceAction.isChecked()
            self.setHorizontalTraces(trace)
        else:
            getLogger().warning('no strip selected')

    def toggleVTrace(self):
        if not self.is1D and self.current.strip:
            trace = not self.current.strip.vTraceAction.isChecked()
            self.setVerticalTraces(trace)
        else:
            getLogger().warning('no strip selected')

    def setHorizontalTraces(self, trace):
        for strip in self.strips:
            strip._setHorizontalTrace(trace)

    def setVerticalTraces(self, trace):
        for strip in self.strips:
            strip._setVerticalTrace(trace)

    def removePhasingTraces(self):
        """
        Removes all phasing traces from all strips.
        """
        for strip in self.strips:
            strip.removePhasingTraces()

    def togglePhaseConsole(self):
        """Toggles whether phasing console is displayed.
        """
        isVisible = not self.phasingFrame.isVisible()
        self.phasingFrame.setVisible(isVisible)

        if self.is1D:
            self.hTraceAction = True
            self.vTraceAction = False

            if not self.phasingFrame.pivotsSet:
                inRange, point, xDataDim, xMinFrequency, xMaxFrequency, xNumPoints \
                    = self.spectrumViews[0]._getTraceParams((0.0, 0.0))

                self.phasingFrame.setInitialPivots((xDataDim.primaryDataDimRef.pointToValue((xMinFrequency + xMaxFrequency) / 2.0), 0.0))

        else:
            self.hTraceAction = self.current.strip.hTraceAction.isChecked()
            self.vTraceAction = self.current.strip.vTraceAction.isChecked()

            if not self.phasingFrame.pivotsSet:
                inRange, point, xDataDim, xMinFrequency, xMaxFrequency, xNumPoints, yDataDim, yMinFrequency, yMaxFrequency, yNumPoints \
                    = self.spectrumViews[0]._getTraceParams((0.0, 0.0))

                self.phasingFrame.setInitialPivots((xDataDim.primaryDataDimRef.pointToValue((xMinFrequency + xMaxFrequency) / 2.0),
                                                    yDataDim.primaryDataDimRef.pointToValue((yMinFrequency + yMaxFrequency) / 2.0)))

        for strip in self.strips:
            if isVisible:
                strip.turnOnPhasing()
            else:
                strip.turnOffPhasing()
        self._updatePhasing()

    def showToolbar(self):
        """show the toolbar"""
        # showing the toolbar, but we need to update the checkboxes of all strips as well.
        self.spectrumUtilToolBar.show()
        for strip in self.strips:
            strip.toolbarAction.setChecked(True)

    def hideToolbar(self):
        """hide the toolbar"""
        # hiding the toolbar, but we need to update the checkboxes of all strips as well.
        self.spectrumUtilToolBar.hide()
        for strip in self.strips:
            strip.toolbarAction.setChecked(False)

    def toggleToolbar(self):
        """Toggle the toolbar """
        if not self.spectrumUtilToolBar.isVisible():
            self.showToolbar()
        else:
            self.hideToolbar()

    def showSpectrumToolbar(self):
        """show the spectrum toolbar"""
        # showing the spectrum toolbar, but we need to update the checkboxes of all strips as well.
        if self.isGrouped:
            self.spectrumGroupToolBar.show()
        else:
            self.spectrumToolBar.show()

        for strip in self.strips:
            strip.spectrumToolbarAction.setChecked(True)

    def hideSpectrumToolbar(self):
        """hide the spectrum toolbar"""
        # hiding the spectrum toolbar, but we need to update the checkboxes of all strips as well.
        if self.isGrouped:
            self.spectrumGroupToolBar.hide()
        else:
            self.spectrumToolBar.hide()

        for strip in self.strips:
            strip.spectrumToolbarAction.setChecked(False)

    def toggleSpectrumToolbar(self):
        """Toggle the spectrum toolbar """
        if self.isGrouped:
            if not self.spectrumGroupToolBar.isVisible():
                self.showSpectrumToolbar()
            else:
                self.hideSpectrumToolbar()
        else:
            if not self.spectrumToolBar.isVisible():
                self.showSpectrumToolbar()
            else:
                self.hideSpectrumToolbar()

    def close(self):
        """
        Close the module from the commandline
        """
        self._closeModule()

    def _closeModule(self):
        """
        CCPN-INTERNAL: used to close the module
        Closes spectrum display and deletes it from the project.
        """
        self.mainWindow._deleteSpectrumDisplay(self)

    def _removeIndexStrip(self, value):
        self.deleteStrip(self.strips[value])

    def _redrawLayout(self, spectrumDisplay):
        """Redraw the stripFrame with the new stripDirection
        """
        layout = spectrumDisplay.stripFrame.getLayout()

        if layout and layout.count() > 0:
            spectrumDisplay.stripFrame.blockSignals(True)
            spectrumDisplay.stripFrame.setUpdatesEnabled(False)

            # clear the layout and rebuild
            _widgets = []

            # need to be removed if not using QObjectCleanupHandler before creating new layout
            while layout.count():
                _widgets.append(layout.takeAt(0).widget())

            # remember necessary layout info and create a new layout - ensures clean for new widgets
            margins = layout.getContentsMargins()
            space = layout.spacing()
            QtWidgets.QWidget().setLayout(layout)
            layout = QtWidgets.QGridLayout()
            spectrumDisplay.stripFrame.setLayout(layout)
            layout.setContentsMargins(*margins)
            layout.setSpacing(space)

            # reinsert strips in new order - reset minimum widths
            if spectrumDisplay.stripArrangement == 'Y':

                # horizontal strip layout
                for m, widgStrip in enumerate(_widgets):
                    # layout.addWidget(widgStrip, 0, m)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, 0, m)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[0], tilePosition[1])

            elif spectrumDisplay.stripArrangement == 'X':

                # vertical strip layout
                for m, widgStrip in enumerate(_widgets):
                    # layout.addWidget(widgStrip, m, 0)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, m, 0)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[1], tilePosition[0])

            elif spectrumDisplay.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            else:
                getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            spectrumDisplay.stripFrame.setUpdatesEnabled(True)
            spectrumDisplay.stripFrame.blockSignals(False)

            self.showAxes()
            self.setColumnStretches(stretchValue=True)

    def _removeStripFromLayout(self, spectrumDisplay, strip):
        """Remove the current strip from the layout
        CCPN Internal
        """
        layout = spectrumDisplay.stripFrame.getLayout()

        if layout and layout.count() > 1:
            spectrumDisplay.stripFrame.blockSignals(True)
            spectrumDisplay.stripFrame.setUpdatesEnabled(False)

            # clear the layout and rebuild
            _widgets = []

            # need to be removed if not using QObjectCleanupHandler before creating new layout
            while layout.count():
                _widgets.append(layout.takeAt(0).widget())
            _widgets.remove(strip)
            strip.hide()
            strip.setParent(None)  # set widget parent to None to hide,
            # was previously handled by addWidget to tempStore

            # remember necessary layout info and create a new layout - ensures clean for new widgets
            margins = layout.getContentsMargins()
            space = layout.spacing()
            QtWidgets.QWidget().setLayout(layout)
            layout = QtWidgets.QGridLayout()
            spectrumDisplay.stripFrame.setLayout(layout)
            layout.setContentsMargins(*margins)
            layout.setSpacing(space)

            # reinsert strips in new order - reset minimum widths
            if spectrumDisplay.stripArrangement == 'Y':

                # horizontal strip layout
                for m, widgStrip in enumerate(_widgets):
                    #     layout.addWidget(widgStrip, 0, m)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, 0, m)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[0], tilePosition[1])

            elif spectrumDisplay.stripArrangement == 'X':

                # vertical strip layout
                for m, widgStrip in enumerate(_widgets):
                    #     layout.addWidget(widgStrip, m, 0)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, m, 0)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[1], tilePosition[0])

            elif spectrumDisplay.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            else:
                getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            spectrumDisplay.stripFrame.setUpdatesEnabled(True)
            spectrumDisplay.stripFrame.blockSignals(False)
        else:
            raise RuntimeError('Error, stripFrame layout in invalid state')

    def _restoreStripToLayout(self, spectrumDisplay, strip, currentIndex):
        """Restore the current strip to the layout
        CCPN Internal
        """
        layout = spectrumDisplay.stripFrame.layout()
        # print(spectrumDisplay, strip, currentIndex)

        if layout:
            spectrumDisplay.stripFrame.setUpdatesEnabled(False)
            spectrumDisplay.stripFrame.blockSignals(True)

            # clear the layout and rebuild
            # need to be removed if not using QObjectCleanupHandler before creating new layout
            _widgets = []
            while layout.count():
                _widgets.append(layout.takeAt(0).widget())
            _widgets.insert(currentIndex, strip)
            strip.show()

            # remember necessary layout info and create a new layout - ensures clean for new widgets
            margins = layout.getContentsMargins()
            space = layout.spacing()
            QtWidgets.QWidget().setLayout(layout)
            layout = QtWidgets.QGridLayout()
            spectrumDisplay.stripFrame.setLayout(layout)
            layout.setContentsMargins(*margins)
            layout.setSpacing(space)

            # reinsert strips in new order - reset minimum widths
            if spectrumDisplay.stripArrangement == 'Y':

                # horizontal strip layout
                for m, widgStrip in enumerate(_widgets):
                    # layout.addWidget(widgStrip, 0, m)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, 0, m)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[0], tilePosition[1])

            elif spectrumDisplay.stripArrangement == 'X':

                # vertical strip layout
                for m, widgStrip in enumerate(_widgets):
                    # layout.addWidget(widgStrip, m, 0)

                    tilePosition = widgStrip.tilePosition
                    if True:            #tilePosition is None:
                        layout.addWidget(widgStrip, m, 0)
                        widgStrip.tilePosition = (0, m)
                    else:
                        layout.addWidget(widgStrip, tilePosition[1], tilePosition[0])

            elif spectrumDisplay.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            else:
                getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(spectrumDisplay.pid))

            # put ccpnStrip back into strips using the api
            # if self not in ccpnStrip.spectrumDisplay.strips:
            if self not in spectrumDisplay.strips:
                for order, cStrip in enumerate(_widgets):
                    cStrip._setStripIndex(order)

            spectrumDisplay.stripFrame.blockSignals(False)
            spectrumDisplay.stripFrame.setUpdatesEnabled(True)
        else:
            raise RuntimeError('Error, stripFrame layout in invalid state')

    @logCommand(get='self')
    def deleteStrip(self, strip):
        """Delete a strip from the spectrumDisplay

        :param strip: strip to delete as object or pid
        """
        strip = self.getByPid(strip) if isinstance(strip, str) else strip

        if strip is None:
            showWarning('Delete strip', 'Invalid strip')
            return

        if strip not in self.strips:
            showWarning('Delete strip', 'Selected strip "%s" is not part of SpectrumDisplay "%s"' \
                        % (strip.pid, self.pid))
            return

        if self.stripCount == 1:
            showWarning('Delete strip', 'Last strip of SpectrumDisplay "%s" cannot be removed' \
                        % (self.pid,))
            return

        with undoBlock():
            with undoStackBlocking() as addUndoItem:
                # retrieve list of created items from the api
                # strangely, this modifies _wrappedData.orderedStrips, and 'removes' the boundStrip by changing the indexing
                # if it is at the end of apiBoundStrips then it confuses the indexing
                indexing = [st.stripIndex() for st in self.strips]

                apiObjectsCreated = strip._getApiObjectTree()

                # reset indexing again SHOULD now be okay; i.e. nothing has been 'removed' from apiBoundStrips yet
                for ii, ind in enumerate(indexing):
                    self.strips[ii]._setStripIndex(ind)

                index = strip.stripIndex()

                # add layout handling to the undo stack
                addUndoItem(undo=partial(self._redrawAxes, index))
                addUndoItem(undo=partial(self._restoreStripToLayout, self, strip, index),
                            redo=partial(self._removeStripFromLayout, self, strip))
                # add notifier handling for the strip
                addUndoItem(undo=partial(strip.setBlankingAllNotifiers, False),
                            redo=partial(strip.setBlankingAllNotifiers, True))

                self._removeStripFromLayout(self, strip)
                strip.setBlankingAllNotifiers(True)

                #EJB 20181213: old style delete notifiers
                # # add object delete/undelete to the undo stack
                # addUndoItem(undo=partial(strip._wrappedData.root._unDelete,
                #                          apiObjectsCreated, (strip._wrappedData.topObject,)),
                #             redo=partial(strip._delete)
                #             )
                # # delete the strip
                # strip._delete()

                # add object delete/undelete to the undo stack
                addUndoItem(undo=BlankedPartial(strip._wrappedData.root._unDelete,
                                                topObjectsToCheck=(strip._wrappedData.topObject,),
                                                obj=strip, trigger='create', preExecution=False,
                                                objsToBeUnDeleted=apiObjectsCreated),
                            redo=BlankedPartial(strip._delete,
                                                obj=strip, trigger='delete', preExecution=True)
                            )

                # delete the strip
                strip._finaliseAction('delete')
                with notificationBlanking():
                    strip._delete()

                addUndoItem(redo=partial(self._redrawAxes, deletingStrip=True))

            # do axis redrawing
            self._redrawAxes(deletingStrip=True)

    def _redrawAxes(self, index=-1, deletingStrip=False):
        """Redraw the axes for the stripFrame, and set the new current strip,
        will default to the last strip if not selected.
        """
        self.showAxes(stretchValue=True, deletingStrip=deletingStrip)
        if self.strips:
            self.current.strip = self.strips[index]

    def removeCurrentStrip(self):
        """Remove current.strip if it belongs to self.
        """
        if self.current.strip is None:
            showWarning('Remove current strip', 'Select first in SpectrumDisplay by clicking')
            return

        self.deleteStrip(self.current.strip)

    # def duplicateStrip(self):
    #   """
    #   Creates a new strip identical to the last one created and adds it to right of the display.
    #   """
    #   newStrip = self.strips[-1].clone()

    # def addStrip(self, stripIndex=-1) -> 'GuiStripNd':

    def setLastAxisOnly(self, lastAxisOnly: bool = True):
        self.lastAxisOnly = lastAxisOnly

    def showAxes(self, strips=None, stretchValue=False, widths=True, minimumWidth=STRIP_MINIMUMWIDTH, deletingStrip=False):
        # use the strips as they are ordered in the model
        currentStrips = self.orderedStrips

        if currentStrips:

            if self.stripArrangement == 'Y':

                # strips are arranged in a row
                if self.lastAxisOnly and len(currentStrips) > 1:
                    # for ss in currentStrips[:-1]:
                    #     ss.setAxesVisible(rightAxisVisible=False, bottomAxisVisible=True)
                    #
                    # currentStrips[-1].setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=False, bottomAxisVisible=True)

                    # show _rightGLAxis
                else:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

            elif self.stripArrangement == 'X':

                # strips are arranged in a column
                if self.lastAxisOnly and len(currentStrips) > 1:
                    # for ss in currentStrips[:-1]:
                    #     ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=False)
                    #
                    # currentStrips[-1].setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=False)

                    # show _bottomGLAxis

                else:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

            elif self.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

            else:
                getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

            self.setColumnStretches(stretchValue=stretchValue, widths=widths, minimumWidth=minimumWidth, deletingStrip=deletingStrip)

            # show the required _rightGLAxis/_bottomGLAxis
            self.setVisibleAxes()

    def increaseTraceScale(self):
        # self.mainWindow.traceScaleUp(self.mainWindow)
        if not self.is1D:
            for strip in self.strips:
                for spectrumView in strip.spectrumViews:
                    spectrumView.traceScale *= 1.4

                # spawn a redraw of the strip
                strip._updatePivot()

    def decreaseTraceScale(self):
        # self.mainWindow.traceScaleDown(self.mainWindow)
        if not self.is1D:
            for strip in self.strips:
                for spectrumView in strip.spectrumViews:
                    spectrumView.traceScale /= 1.4

                # spawn a redraw of the strip
                strip._updatePivot()

    def increaseStripSize(self):
        """Increase the width/height of the strips depending on the orientation
        """
        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._increaseStripWidth()

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._increaseStripHeight()

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def decreaseStripSize(self):
        """Decrease the width/height of the strips depending on the orientation
        """
        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._decreaseStripWidth()

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._decreaseStripHeight()

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def _increaseStripWidth(self):
        """Increase the widths of the strips
        """
        factor = (100.0 + self.application.preferences.general.stripWidthZoomPercent) / 100.0
        self._setStripWidths(factor)

    def _decreaseStripWidth(self):
        """decrease the widths of the strips
        """
        factor = 100.0 / (100.0 + self.application.preferences.general.stripWidthZoomPercent)
        self._setStripWidths(factor)

    def _setStripWidths(self, factor=1.0):
        """set the widths for the strips
        """
        self.stripFrame.hide()

        strips = self.orderedStrips
        newWidth = max(strips[0].width() * factor, STRIP_MINIMUMWIDTH)  # + (0 if self.lastAxisOnly else strips[0].getRightAxisWidth()))
        axisWidth = 0               #strips[0].getRightAxisWidth() if self.lastAxisOnly else 0

        # NOTE:ED - always uniform width with new axis

        if len(strips) > 1:
            for strip in strips[:-1]:
                strip.setMinimumWidth(newWidth)
            strips[-1].setMinimumWidth(newWidth + axisWidth)
            self.stripFrame.setMinimumWidth((newWidth + STRIP_SPACING) * len(strips) + axisWidth - STRIP_SPACING)
        else:
            strips[0].setMinimumWidth(newWidth)
            self.stripFrame.setMinimumWidth(newWidth)

        self.stripFrame.show()

    def _increaseStripHeight(self):
        """Increase the heights of the strips
        """
        factor = (100.0 + self.application.preferences.general.stripWidthZoomPercent) / 100.0
        self._setStripHeights(factor)

    def _decreaseStripHeight(self):
        """decrease the heights of the strips
        """
        factor = 100.0 / (100.0 + self.application.preferences.general.stripWidthZoomPercent)
        self._setStripHeights(factor)

    def _setStripHeights(self, factor=1.0):
        """set the heights for the strips
        """
        self.stripFrame.hide()

        strips = self.orderedStrips
        newHeight = max(strips[0].height() * factor, STRIP_MINIMUMHEIGHT)  # + (0 if self.lastAxisOnly else strips[0].getRightAxisWidth()))
        axisHeight = 0                  #strips[0].getBottomAxisHeight() if self.lastAxisOnly else 0

        # NOTE:ED - always uniform height with new axis

        if len(strips) > 1:
            for strip in strips[:-1]:
                strip.setMinimumHeight(newHeight)
            strips[-1].setMinimumHeight(newHeight + axisHeight)
            self.stripFrame.setMinimumHeight((newHeight + STRIP_SPACING) * len(strips) + axisHeight - STRIP_SPACING)
        else:
            strips[0].setMinimumHeight(newHeight)
            self.stripFrame.setMinimumHeight(newHeight)

        self.stripFrame.show()

    def _copyPreviousStripValues(self, fromStrip, toStrip):
        """Copy the trace settings to another strip in the spectrumDisplay.
        """
        traceScale = fromStrip.spectrumViews[0].traceScale
        toStrip.setTraceScale(traceScale)

        if self.phasingFrame.isVisible():
            toStrip.turnOnPhasing()

    @logCommand(get='self')
    def addStrip(self, strip=None) -> 'GuiStripNd':
        """Creates a new strip by cloning strip with index (default the last) in the display.
        """
        strip = self.getByPid(strip) if isinstance(strip, str) else strip
        index = strip.stripIndex() if strip else -1
        tilePosition = strip.tilePosition if strip else None
        if tilePosition is None:
            tilePosition = (0, 0)

        if self.phasingFrame.isVisible():
            showWarning(str(self.windowTitle()), 'Please disable Phasing Console before adding strips')
            return

        with undoBlock():
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._redrawAxes)

                #EJB 20181213: old style delete notifiers
                # result = self.strips[index]._clone()
                # if not isinstance(result, GuiStrip):
                #     raise RuntimeError('Expected an object of class %s, obtained %s' % (GuiStrip, result.__class__))
                # apiObjectsCreated = result._getApiObjectTree()
                # # add object delete/undelete to the undo stack
                # addUndoItem(undo=partial(Undo._deleteAllApiObjects, apiObjectsCreated),
                #             redo=partial(result._wrappedData.root._unDelete,
                #                          apiObjectsCreated, (result._wrappedData.topObject,))
                #             )

                with notificationBlanking():
                    # get the visibility of strip to be copied
                    copyVisible = self.strips[index].header.headerVisible

                    # inserts the strip into the stripFrame here
                    result = self.strips[index]._clone()
                    if not isinstance(result, GuiStrip):
                        raise RuntimeError('Expected an object of class %s, obtained %s' % (GuiStrip, result.__class__))
                result._finaliseAction('create')

                # copy the strip Header if needed
                # result.header.headerVisible = copyVisible if copyVisible is not None else False
                # result.header.setLabelVisible(visible=copyVisible if copyVisible is not None else False)

                # retrieve list of created items from the api
                # strangely, this modifies _wrappedData.orderedStrips
                apiObjectsCreated = result._getApiObjectTree()
                addUndoItem(undo=BlankedPartial(Undo._deleteAllApiObjects,
                                                obj=result, trigger='delete', preExecution=True,
                                                objsToBeDeleted=apiObjectsCreated),
                            redo=BlankedPartial(result._wrappedData.root._unDelete,
                                                topObjectsToCheck=(result._wrappedData.topObject,),
                                                obj=result, trigger='create', preExecution=False,
                                                objsToBeUnDeleted=apiObjectsCreated)
                            )

                index = result.stripIndex()

                # add notifier handling to the stack
                addUndoItem(undo=partial(result.setBlankingAllNotifiers, True),
                            redo=partial(result.setBlankingAllNotifiers, False))

                # add layout handling to the undo stack
                addUndoItem(undo=partial(self._removeStripFromLayout, self, result),
                            redo=partial(self._restoreStripToLayout, self, result, index))
                addUndoItem(redo=partial(self._redrawAxes, index))

            # do axis redrawing
            self._redrawAxes(index)  # this might be getting confused with the ordering

        return result

    def setColumnStretches(self, stretchValue=False, scaleFactor=1.0, widths=True, minimumWidth=None, deletingStrip=False):
        """Set the column widths of the strips so that the last strip accommodates the axis bar
                if necessary."""

        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._setColumnStretches(stretchValue=stretchValue, scaleFactor=scaleFactor, widths=widths, minimumWidth=minimumWidth, deletingStrip=deletingStrip)

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._setRowStretches(stretchValue=stretchValue, scaleFactor=scaleFactor, heights=widths, minimumHeight=minimumWidth, deletingStrip=deletingStrip)

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def _setColumnStretches(self, stretchValue=False, scaleFactor=1.0, widths=True, minimumWidth=STRIP_MINIMUMWIDTH, deletingStrip=False):
        """Set the column widths of the strips so that the last strip accommodates the axis bar
        if necessary."""
        widgets = self.stripFrame.children()

        # set the strip spacing and the visibility of the scroll bars
        layout = self.stripFrame.getLayout()
        layout.setHorizontalSpacing(STRIP_SPACING)
        layout.setVerticalSpacing(0)
        if self._stripFrameScrollArea:
            # scroll area for strips
            self._stripFrameScrollArea.setScrollBarPolicies(scrollBarPolicies=('asNeeded', 'never'))

        if widgets:

            AXIS_WIDTH = 1
            AXIS_PADDING = STRIP_SPACING

            thisLayout = self.stripFrame.layout()
            thisLayoutWidth = self.stripFrame.width() - (2 * STRIP_SPACING)

            if deletingStrip:
                thisLayoutWidth *= (self.stripCount / (self.stripCount + 1))

            if not thisLayout.itemAt(0):
                return

            self.stripFrame.hide()

            if self.strips:
                AXIS_WIDTH = self.orderedStrips[0].getRightAxisWidth()
                firstStripWidth = (thisLayoutWidth - AXIS_WIDTH) / self.stripCount
            else:
                firstStripWidth = thisLayoutWidth

            if minimumWidth:
                firstStripWidth = max(firstStripWidth, minimumWidth)

            if True:                    # not self.lastAxisOnly:
                maxCol = 0
                for wid in self.orderedStrips:
                    index = thisLayout.indexOf(wid)
                    if index >= 0:
                        row, column, cols, rows = thisLayout.getItemPosition(index)
                        maxCol = max(maxCol, column)

                for col in range(0, maxCol + 1):
                    if widths and thisLayout.itemAt(col):
                        thisLayout.itemAt(col).widget().setMinimumWidth(firstStripWidth)
                    thisLayout.setColumnStretch(col, 1 if stretchValue else 1)

                if minimumWidth:
                    self.stripFrame.setMinimumWidth((firstStripWidth + STRIP_SPACING) * len(self.orderedStrips) - STRIP_SPACING)
                else:
                    self.stripFrame.setMinimumWidth(self.stripFrame.minimumSizeHint().width())
                self.stripFrame.setMinimumHeight(50)

            else:

                # set the correct widths for the strips
                maxCol = thisLayout.count() - 1
                firstWidth = scaleFactor * (thisLayoutWidth - AXIS_WIDTH - (maxCol * AXIS_PADDING)) / (maxCol + 1)

                if minimumWidth:
                    firstWidth = max(firstWidth, minimumWidth)

                endWidth = firstWidth + AXIS_WIDTH

                # set the minimum widths and stretch values for the strips
                for column in range(thisLayout.count()):
                    thisLayout.setColumnStretch(column, firstWidth if stretchValue else 1)
                    if widths:
                        wid = thisLayout.itemAt(column).widget()
                        wid.setMinimumWidth(firstWidth)

                thisLayout.setColumnStretch(maxCol, endWidth if stretchValue else 1)
                if widths:
                    wid = thisLayout.itemAt(maxCol).widget()
                    wid.setMinimumWidth(endWidth)

                # fix the width of the stripFrame
                if minimumWidth:

                    # this depends on the spacing in stripFrame
                    self.stripFrame.setMinimumWidth((firstWidth + STRIP_SPACING) * len(self.orderedStrips) + AXIS_WIDTH)
                else:
                    self.stripFrame.setMinimumWidth(self.stripFrame.minimumSizeHint().width())
                self.stripFrame.setMinimumHeight(50)

            self.stripFrame.show()

    def _setRowStretches(self, stretchValue=False, scaleFactor=1.0, heights=True, minimumHeight=None, deletingStrip=False):
        """Set the row heights of the strips so that the last strip accommodates the axis bar
        if necessary."""
        widgets = self.stripFrame.children()

        # set the strip spacing and the visibility of the scroll bars
        layout = self.stripFrame.getLayout()
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(STRIP_SPACING)
        if self._stripFrameScrollArea:
            # scroll area for strips
            self._stripFrameScrollArea.setScrollBarPolicies(scrollBarPolicies=('never', 'asNeeded'))

        if widgets:

            AXIS_HEIGHT = 1
            AXIS_PADDING = STRIP_SPACING

            thisLayout = self.stripFrame.layout()
            # thisLayoutHeight = self._stripFrameScrollArea.height()
            thisLayoutHeight = self.stripFrame.height() - (2 * STRIP_SPACING)

            if deletingStrip:
                thisLayoutHeight *= (self.stripCount / (self.stripCount + 1))

            if not thisLayout.itemAt(0):
                return

            self.stripFrame.hide()

            if self.strips:
                firstStripHeight = thisLayoutHeight / self.stripCount
                AXIS_HEIGHT = self.orderedStrips[0].getBottomAxisHeight()
            else:
                firstStripHeight = thisLayoutHeight

            if minimumHeight:
                firstStripHeight = max(firstStripHeight, minimumHeight)

            if True:                        #not self.lastAxisOnly:
                maxRow = 0
                for wid in self.orderedStrips:
                    index = thisLayout.indexOf(wid)
                    if index >= 0:
                        row, column, cols, rows = thisLayout.getItemPosition(index)
                        maxRow = max(maxRow, row)

                for rr in range(0, maxRow + 1):
                    if heights and thisLayout.itemAt(rr):
                        thisLayout.itemAt(rr).widget().setMinimumHeight(firstStripHeight)
                    thisLayout.setRowStretch(rr, 1 if stretchValue else 1)

                if minimumHeight:
                    self.stripFrame.setMinimumHeight((firstStripHeight + STRIP_SPACING) * len(self.orderedStrips) - STRIP_SPACING)
                else:
                    self.stripFrame.setMinimumHeight(self.stripFrame.minimumSizeHint().height())
                self.stripFrame.setMinimumWidth(50)

            else:

                # set the correct heights for the strips
                maxRow = thisLayout.count() - 1
                firstHeight = scaleFactor * (thisLayoutHeight - AXIS_HEIGHT - (maxRow * AXIS_PADDING)) / (maxRow + 1)

                if minimumHeight:
                    firstHeight = max(firstHeight, minimumHeight)

                endHeight = firstHeight + AXIS_HEIGHT

                # set the minimum heights and stretch values for the strips
                for rr in range(thisLayout.count()):
                    thisLayout.setRowStretch(rr, firstHeight if stretchValue else 1)
                    if heights:
                        wid = thisLayout.itemAt(rr).widget()
                        wid.setMinimumHeight(firstHeight)

                thisLayout.setRowStretch(maxRow, endHeight if stretchValue else 1)
                if heights:
                    wid = thisLayout.itemAt(maxRow).widget()
                    wid.setMinimumHeight(endHeight)

                # fix the height of the stripFrame
                if minimumHeight:
                    # this depends on the spacing in stripFrame
                    self.stripFrame.setMinimumHeight((firstHeight + STRIP_SPACING) * len(self.orderedStrips) + AXIS_HEIGHT)
                else:
                    self.stripFrame.setMinimumHeight(self.stripFrame.minimumSizeHint().height())
                self.stripFrame.setMinimumWidth(50)

            self.stripFrame.show()

    def autoRange(self):
        """Zooms Y axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip.autoRange()

    def _resetYZooms(self):
        """Zooms Y axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetYZoom()

    def _resetXZooms(self):
        """Zooms X axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetXZoom()

    def _resetAllZooms(self):
        """Zooms X/Y axes of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetAllZoom()

    def _restoreZoom(self):
        """Restores last saved zoom of current strip.
        """
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._restoreZoom()

    def _storeZoom(self):
        """Saves zoomed region of current strip."""
        if not self.strips:
            showWarning('Store Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._storeZoom()

    def _previousZoom(self):
        """Changes to the previous zoom of current strip."""
        if not self.strips:
            showWarning('Undo Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._previousZoom()

    def _nextZoom(self):
        """Changes to the next zoom of current strip."""
        if not self.strips:
            showWarning('Redo Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._nextZoom()

    def _zoomIn(self):
        """zoom in to the current strip."""
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._zoomIn()

    def _zoomOut(self):
        """zoom out of current strip."""
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._zoomOut()

    def toggleGrid(self):
        """Toggles whether grid is displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip.toggleGrid()

    def toggleSideBands(self):
        """Toggles whether sideBands are displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip.toggleSideBands()

    def toggleCrosshair(self):
        """Toggles whether cross hair is displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip._toggleCrosshair()

    def toggleDoubleCrosshair(self):
        """Toggles whether double cross hairs are displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip._toggleDoubleCrosshair()

    def _cycleSymbolLabelling(self):
        """Toggles peak labelling of current strip.
        """
        try:
            if not self.current.strip:
                showWarning('Cycle Peak Labelling', 'No strip selected')
                return

            for strip in self.strips:
                strip.cycleSymbolLabelling()

        except:
            getLogger().warning('Error cycling peak labelling')

    def _cyclePeakSymbols(self):
        """toggles peak labelling of current strip.
        """
        try:
            if not self.current.strip:
                showWarning('Cycle Peak Symbols', 'No strip selected')
                return

            for strip in self.strips:
                strip.cyclePeakSymbols()
        except:
            getLogger().warning('Error cycling peak symbols')

    # def _deletedPeak(self, peak):
    #     apiPeak = peak._wrappedData
    #     # NBNB TBD FIXME rewrite this to not use API peaks
    #     # ALSO move this machinery from subclasses to this class.
    #     for peakListView in self.activePeakItemDict:
    #         peakItemDict = self.activePeakItemDict[peakListView]
    #         peakItem = peakItemDict.get(apiPeak)
    #         if peakItem:
    #             # peakListView.spectrumView.strip.plotWidget.scene().removeItem(peakItem)
    #             del peakItemDict[apiPeak]
    #             inactivePeakItems = self.inactivePeakItemDict.get(peakListView)
    #             if inactivePeakItems:
    #                 inactivePeakItems.add(peakItem)
    from ccpn.util.decorators import profile

    @logCommand(get='self')
    def displaySpectrum(self, spectrum, axisOrder: (str,) = ()):
        """Display additional spectrum, with spectrum axes ordered according ton axisOrder
        """
        spectrum = self.getByPid(spectrum) if isinstance(spectrum, str) else spectrum
        if not isinstance(spectrum, Spectrum):
            raise TypeError('spectrum is not of type Spectrum')

        with undoBlock():
            oldIndex = self.getOrderedSpectrumViewsIndex()

            # need set ordering here on undo
            # with undoStackBlocking() as addUndoItem:
            #     addUndoItem(undo=partial(self._listViewChanged, {}))
            #     addUndoItem(undo=partial(self.setOrderedSpectrumViewsIndex, tuple(oldIndex)))

            newSpectrum = self.strips[0].displaySpectrum(spectrum, axisOrder=axisOrder)
            if newSpectrum:
                # index = self.getOrderedSpectrumViewsIndex()
                # self.setOrderedSpectrumViewsIndex(tuple(index))

                # original old code seems to be okay?
                newInd = self.spectrumViews.index(newSpectrum)
                index = self.getOrderedSpectrumViewsIndex()
                index = tuple((ii + 1) if (ii >= newInd) else ii for ii in index)
                index += (newInd,)
                self.setOrderedSpectrumViewsIndex(tuple(index))

    def _removeSpectrum(self, spectrum):
        try:
            # self._orderedSpectra.remove(spectrum)
            self._orderedSpectrumViews.removeSpectrumView(spectrum)
        except:
            getLogger().warning('Error, %s does not exist' % spectrum)

    @logCommand(get='self')
    def makeStripPlot(self, peaks=None, nmrResidues=None,
                      autoClearMarks=True,
                      sequentialStrips=True,
                      markPositions=True,
                      widths=None):
        """Make a list of strips in the current spectrumDisplay based on the list of peaks or
        the list of nmrResidues passing in
        Can only choose either peaks or nmrResidues, peaks chosen will override any selected nmrResidues
        """
        pkList = makeIterableList(peaks)
        pks = []
        for peak in pkList:
            pks.append(self.project.getByPid(peak) if isinstance(peak, str) else peak)

        resList = makeIterableList(nmrResidues)
        nmrs = []
        for nmrRes in resList:
            nmrs.append(self.project.getByPid(nmrRes) if isinstance(nmrRes, str) else nmrRes)

        # need to clean up the use of GLNotifier - possibly into AbstractWrapperObject
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier
        # from functools import partial
        # from ccpn.ui.gui.lib.Strip import navigateToPositionInStrip, navigateToNmrAtomsInStrip
        from ccpn.ui.gui.lib.SpectrumDisplay import navigateToPeakInStrip, navigateToNmrResidueInStrip

        def _updateGl(self, spectrumList):
            GLSignals = GLNotifier(parent=self)
            GLSignals.emitPaintEvent()

        if pks or nmrs:

            GLSignals = GLNotifier(parent=self)
            _undo = self.project._undo

            project = self.project
            # with logCommandBlock(get='self') as log:
            #     peakStr = '[' + ','.join(["'%s'" % peak.pid for peak in pks]) + ']'
            #     nmrResidueStr = '[' + ','.join(["'%s'" % nmrRes.pid for nmrRes in nmrs]) + ']'
            #     log('addPeaks', peaks=peakStr, nmrResidues=nmrResidueStr)

            with undoBlock():
                # _undo._newItem(undoPartial=partial(_updateGl, self, []))

                if autoClearMarks:
                    self.mainWindow.clearMarks()

                # Make sure there are enough strips to display nmrAtomPairs
                stripCount = len(pks) if pks else len(nmrs)
                while len(self.strips) < stripCount:
                    self.addStrip()
                for strip in self.strips[stripCount:]:
                    self.deleteStrip(strip)

                # build the strips
                if pks:
                    for ii, pk in enumerate(pks):
                        strip = self.strips[ii]
                        navigateToPeakInStrip(self, strip, pk)

                elif nmrs:
                    for ii, nmr in enumerate(nmrs):
                        strip = self.strips[ii]
                        navigateToNmrResidueInStrip(self, strip, nmr, widths, markPositions)

                # _undo._newItem(redoPartial=partial(_updateGl, self, []))

                # repaint - not sure whether needed here
                GLSignals.emitPaintEvent()

    #===========================================================================================
    # new'Object' and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    # @logCommand('project.')
    # def newSpectrumView(self, spectrumName: str = None,
    #                     stripSerial: int = None, dataSource=None,
    #                     dimensionOrdering=None,
    #                     **kwds):
    #     """Create new SpectrumView
    #
    #     See the SpectrumView class for details.
    #
    #     Optional keyword arguments can be passed in; see SpectrumView._newSpectrumView for details.
    #
    #     :return: a new SpectrumView instance.
    #     """
    #     from ccpn.ui._implementation.SpectrumView import _newSpectrumView
    #
    #     return _newSpectrumView(self, spectrumName=spectrumName,
    #                                  stripSerial=stripSerial, dataSource=dataSource,
    #                                  dimensionOrdering=dimensionOrdering, **kwds)


#=========================================================================================

# def _deletedPeak(peak: Peak):
#     """Function for notifiers.
#     #CCPNINTERNAL
#     """
#
#     for spectrumView in peak.peakList.spectrum.spectrumViews:
#         spectrumView.strip.spectrumDisplay._deletedPeak(peak)


def _spectrumHasChanged(data):
    spectrum = data[Notifier.OBJECT]

    project = spectrum.project
    apiDataSource = spectrum._wrappedData
    for spectrumDisplay in project.spectrumDisplays:
        action = spectrumDisplay.spectrumActionDict.get(apiDataSource)
        if action:  # spectrum might not be in all displays
            # update toolbar button name
            action.setText(spectrum.name)

        # check the visibleAliasing here and update planeToolbar
        for strip in spectrumDisplay.strips:
            strip._checkAliasingRange(spectrum)
            strip._checkVisibleAliasingRange(spectrum)

    # force redraw of the spectra
    for specView in spectrum.spectrumViews:
        specView.buildContours = True

    from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

    # fire refresh event to repaint the screen
    GLSignals = GLNotifier(parent=spectrum)
    targets = [objList for objList in spectrum.peakLists] + [objList for objList in spectrum.multipletLists]
    GLSignals.emitEvent(targets=targets, triggers=[GLNotifier.GLPEAKLISTS,
                                                   GLNotifier.GLPEAKLISTLABELS,
                                                   GLNotifier.GLMULTIPLETLISTS,
                                                   GLNotifier.GLMULTIPLETLISTLABELS
                                                   ])


def _deletedSpectrumView(project: Project, apiSpectrumView):
    """tear down SpectrumDisplay when new SpectrumView is deleted - for notifiers"""
    spectrumDisplay = project._data2Obj[apiSpectrumView.spectrumDisplay]
    apiDataSource = apiSpectrumView.dataSource

    # remove toolbar action (button)
    # NBNB TBD FIXME get rid of API object from code
    action = spectrumDisplay.spectrumActionDict.get(apiDataSource)  # should always be not None
    if action:
        spectrumDisplay.spectrumToolBar.removeAction(action)
        del spectrumDisplay.spectrumActionDict[apiDataSource]

    if not spectrumDisplay.is1D:
        for strip in spectrumDisplay.strips:
            strip._setZWidgets(ignoreSpectrumView=apiSpectrumView)


GuiSpectrumDisplay.processSpectrum = GuiSpectrumDisplay.displaySpectrum  # ejb - from SpectrumDisplay
