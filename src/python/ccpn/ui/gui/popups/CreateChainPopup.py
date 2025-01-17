"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2017-07-07 16:32:43 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-07-04 15:21:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import string
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.popups.Dialog import CcpnDialog, handleDialogApply


def _nextChainCode(project):
    """This gives a "next" available chain code.
       First does A-Z, then A1-Z1, then A2-Z2, etc.
    """

    possibleChainCodes = list(string.ascii_uppercase)
    existingChainCodes = set([chain.shortName for chain in project.chains])

    n = 0
    code = possibleChainCodes[n]
    while code in existingChainCodes and n < len(possibleChainCodes) - 1:
        n += 1
        code = possibleChainCodes[n]

    r = 0
    while code in existingChainCodes:
        r += 1
        n = 0
        code = '%s%d' % (possibleChainCodes[n], r)
        while code in existingChainCodes and n < len(possibleChainCodes) - 1:
            n += 1
            code = '%s%d' % (possibleChainCodes[n], r)

    return code


class CreateChainPopup(CcpnDialog):
    def __init__(self, parent=None, mainWindow=None, project=None, **kwds):
        """
        Initialise the widget
        """
        CcpnDialog.__init__(self, parent, setLayout=True, windowTitle='Create Chain', **kwds)

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = project if project is not None else mainWindow.application.project
        self.current = mainWindow.application.current

        label2a = Label(self, text="Molecule Name", grid=(2, 0))
        moleculeName = LineEdit(self, text="", grid=(2, 1), gridSpan=(1, 1))
        label2b = Label(self, text="Molecule Type", grid=(2, 2))
        self.molTypePulldown = PulldownList(self, grid=(2, 3))
        molTypes = ['protein', 'DNA', 'RNA']
        self.molTypePulldown.setData(molTypes)
        label3a = Label(self, text="sequence", grid=(3, 0))
        tipText = """Sequence may be entered a set of one letter codes without
                 spaces or a set of three letter codes with spaces inbetween"""
        self.sequenceEditor = TextEditor(self, grid=(3, 1), gridSpan=(1, 3), tipText=tipText)
        label4a = Label(self, 'Sequence Start', grid=(4, 0))
        lineEdit1a = Spinbox(self, grid=(4, 1), value=1, min=-1000000, max=1000000)
        label5a = Label(self, 'Chain code', grid=(4, 2))
        code = _nextChainCode(self.project)
        lineEdit2a = LineEdit(self, grid=(4, 3), text=code)

        # self.residueList = ListWidgetSelector(self, setLayout=True, grid=(5,0), gridSpan=(1,4), title='Residue Types')

        buttonBox = ButtonList(self, grid=(6, 3), texts=['Cancel', 'Ok'],
                               callbacks=[self.reject, self._okButton])
        self.sequenceStart = 1
        self.chainCode = code
        self.sequence = self.sequenceEditor.toPlainText()
        self.moleculeName = None
        moleculeName.textChanged.connect(self._setMoleculeName)
        lineEdit1a.valueChanged.connect(self._setSequenceStart)
        lineEdit2a.textChanged.connect(self._setChainCode)
        self.sequenceEditor.textChanged.connect(self._setSequence)

    def _createSequence(self):
        """Creates a sequence using the values specified in the text widget.
        Single-letter codes must be entered with no spacing
        Three-letter codes can be entered as space or <return> separated
        """
        # check the sequence for consistency, sequence widget does most of the work
        seq = self.sequence

        # split and remove white spaces
        if isinstance(seq, str):
            seq = seq.split()

        # # trap rogue spaces and lower case residues entered by 3-letter code
        # if seq and len(seq) == 1 and not isinstance(seq, str):
        #     seq = seq[0]
        # elif not isinstance(seq, str) and isinstance(seq, Iterable):
        #     newSeq = []
        #     for s in seq:
        #         newSeq.append(s.upper())
        #     seq = tuple(newSeq)
        # else:
        #     seq.strip('\n')

        self.project.createChain(sequence=seq, compoundName=self.moleculeName,
                                 startNumber=self.sequenceStart, shortName=self.chainCode,
                                 molType=self.molTypePulldown.currentText())

    def _setSequenceStart(self, value: int):
        """
        Sets sequence start for sequence being created
        """
        self.sequenceStart = int(value)

    def _setChainCode(self, value: str):
        """
        Sets chain code for sequence being created.
        """
        self.chainCode = value

    def _setSequence(self):

        sequence = self.sequenceEditor.toPlainText()
        if not ' ' in sequence:
            self.sequence = self.sequenceEditor.toPlainText()
        else:
            self.sequence = tuple(sequence.split())

    def _setMoleculeName(self, value: str):
        """
        Sets name of molecule being created.
        """
        self.moleculeName = value

    def _repopulate(self):
        #TODO:ED make sure that this popup is repopulated correctly
        pass

    def _applyChanges(self):
        """
        The apply button has been clicked
        Define an undo block for setting the properties of the object
        If there is an error setting any values then generate an error message
          If anything has been added to the undo queue then remove it with application.undo()
          repopulate the popup widgets
        """
        with handleDialogApply(self) as error:
            self._createSequence()

        if error.errorValue:
            # repopulate popup
            self._repopulate()
            return False

        return True

    def _okButton(self):
        if self._applyChanges() is True:
            self.accept()
