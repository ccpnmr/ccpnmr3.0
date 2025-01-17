#TODO:GEERTEN: Move to other places, like SpectrumDisplay or Strip

from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.Peak import Peak
from ccpn.core.Project import Project
from typing import List
from ccpn.ui.gui.lib.GuiSpectrumDisplay import GuiSpectrumDisplay
from ccpn.ui.gui.lib.Strip import navigateToPositionInStrip, navigateToNmrAtomsInStrip
from ccpn.core.lib.ContextManagers import undoBlock
from ccpn.util.Logging import getLogger


def navigateToCurrentPeakPosition(application):
    """

    Takes the current peak position and navigates (centres) to that position all strips and spectrum displays of the project.
    Called by shortcut. For a more generic usage refer to:  "navigateToPositionInStrip"
    instead
    """

    project = application.project
    displays = project.spectrumDisplays
    peak = application.current.peak

    if len(application.current.peaks) > 1:
        getLogger().warning('More than one peak selected. Select only one for the "navigateToCurrentPeakPosition" command.')
        return

    if len(displays) < 1:
        getLogger().warning('No Displays where to navigate.')
        return

    if peak is None:
        getLogger().warning('No peak selected.')
        return

    for display in displays:
        for strip in display.strips:
            if strip:
                navigateToPositionInStrip(strip, peak.position, peak.axisCodes)


def navigateToCurrentNmrResiduePosition(application):
    """

    Takes the current nmrResidue and navigates (centres) to that position all strips and spectrum displays of the project.
    Called by shortcut. For a more generic usage refer to:  "navigateToPositionInStrip"
    instead
    """

    project = application.project
    displays = project.spectrumDisplays
    nmrResidue = application.current.nmrResidue

    if len(application.current.nmrResidues) > 1:
        getLogger().warning('More than one nmrResidue selected. Select only one for the "navigateToCurrentNmrResiduePosition" command.')
        return

    if len(displays) < 1:
        getLogger().warning('No Displays where to navigate.')
        return

    if nmrResidue is None:
        getLogger().warning('No nmrResidue selected.')
        return

    for display in displays:
        for strip in display.strips:
            if strip:
                navigateToNmrResidueInStrip(display, strip, nmrResidue=nmrResidue)


def makeStripPlot(spectrumDisplay: GuiSpectrumDisplay, nmrAtomPairs: List[List[NmrAtom]], autoWidth=True, widths=None):
    if not nmrAtomPairs:
        return

    with undoBlock():
        numberOfStrips = len(spectrumDisplay.strips)

        # Make sure there are enough strips to display nmrAtomPairs
        if numberOfStrips < len(nmrAtomPairs):
            for ii in range(numberOfStrips, len(nmrAtomPairs)):
                # spectrumDisplay.strips[-1].clone()
                spectrumDisplay.addStrip()
        else:  # numberOfStrips >= len(nmrAtomPairs):  # too many strips if >
            for ii in range(len(nmrAtomPairs), numberOfStrips):
                spectrumDisplay.deleteStrip(spectrumDisplay.strips[-1])
                # spectrumDisplay.removeLastStrip()

        # loop through strips and navigate to appropriate position in strip
        for ii, strip in enumerate(spectrumDisplay.strips):
            if autoWidth:
                widths = ['default'] * len(strip.axisCodes)
            elif not widths:
                widths = None
            navigateToNmrAtomsInStrip(strip, nmrAtomPairs[ii], widths=widths)


def makeStripPlotFromSingles(spectrumDisplay: GuiSpectrumDisplay, nmrAtoms: List[NmrAtom], autoWidth=True):
    numberOfStrips = len(spectrumDisplay.strips)

    # Make sure there are enough strips to display nmrAtomPairs
    if numberOfStrips < len(nmrAtoms):
        for ii in range(numberOfStrips, len(nmrAtoms)):
            # spectrumDisplay.strips[-1].clone()
            spectrumDisplay.addStrip()

    # print(spectrumDisplay, nmrAtomPairs, len(nmrAtomPairs), len(spectrumDisplay.strips))
    # loop through strips and navigate to appropriate position in strip
    for ii, strip in enumerate(spectrumDisplay.strips):
        if autoWidth:
            widths = ['default'] * len(strip.axisCodes)
        else:
            widths = None
        navigateToNmrAtomsInStrip(strip, [nmrAtoms[ii]], widths=widths)


def navigateToPeakInStrip(spectrumDisplay: GuiSpectrumDisplay, strip, peak, widths=None):

    from ccpn.util.Common import getAxisCodeMatchIndices

    spCodes = spectrumDisplay.axisCodes
    pos = [None] * len(spCodes)
    newWidths = ['full'] * len(spCodes)
    index = 'YXT'.index(spectrumDisplay.stripArrangement)

    if widths == None and index < 2:
        # set the width in case of nD (n>2)
        _widths = {'H': 0.3, 'C': 1.0, 'N': 1.0}
        # _ac = strip.axisCodes[0]
        _ac = spCodes[index]                                # primary axisCode based in stripArrangement
        _w = _widths.setdefault(_ac[0], 1.0)
        newWidths[index] = _w
        # newWidths = [_w, 'full']
    else:
        newWidths = widths

    indices = getAxisCodeMatchIndices(spCodes, peak.axisCodes)

    for ii, ind in enumerate(indices):
        if ind is not None and ind < len(peak.position):
            pos[ii] = peak.position[ind]
            # mappedNewWidths[ii] = newWidths[ind]

    navigateToPositionInStrip(strip, pos, spCodes, widths=newWidths)
    strip.header.reset()
    strip.header.setLabelText(position='c', text=peak.pid)
    # strip.header.headerVisible = True


def navigateToNmrResidueInStrip(spectrumDisplay: GuiSpectrumDisplay, strip, nmrResidue, widths=None, markPositions=False):

    spCodes = spectrumDisplay.axisCodes
    newWidths = ['full'] * len(spCodes)
    index = 'YXT'.index(spectrumDisplay.stripArrangement)

    if widths == None and index < 2:
        # set the width in case of nD (n>2)
        _widths = {'H': 0.3, 'C': 1.0, 'N': 1.0}
        _ac = spCodes[index]                                # primary axisCode based in stripArrangement
        _w = _widths.setdefault(_ac[0], 1.0)
        newWidths[index] = _w
        # newWidths = [_w, 'full']
    else:
        newWidths = widths

    navigateToNmrAtomsInStrip(strip, nmrResidue.nmrAtoms,
                              widths=newWidths, markPositions=markPositions, setNmrResidueLabel=False)

    strip.header.reset()
    strip.header.setLabelText(position='c', text=nmrResidue.pid)
    # strip.header.headerVisible = True


