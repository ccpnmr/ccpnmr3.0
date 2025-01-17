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
__dateModified__ = "$dateModified: 2017-07-07 16:32:48 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.popups.AttributeEditorPopupABC import AttributeEditorPopupABC
from ccpnmodel.ccpncore.lib.assignment.ChemicalShift import PROTEIN_ATOM_NAMES
from ccpn.util.Common import isotopeCode2Nucleus
from ccpn.core.NmrAtom import NmrAtom
from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget, PulldownListCompoundWidget, CheckBoxCompoundWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrResiduePulldown


class NmrAtomPopup(AttributeEditorPopupABC):
    """
    NmrAtom attributes editor popup
    """

    def _getNmrAtomTypes(self, nmrAtom):
        """Populate the nmrAtom pulldown
        """
        isotopeCode = self.obj.isotopeCode
        nucleus = isotopeCode2Nucleus(isotopeCode)
        if nucleus:
            atomNames = sorted(set([x for y in PROTEIN_ATOM_NAMES.values() for x in y if x.startswith(nucleus)]))
        else:
            atomNames = sorted(set([x for y in PROTEIN_ATOM_NAMES.values() for x in y]))

        if self.obj.name not in atomNames:
            atomNames.insert(0, self.obj.name)

        self.nmrAtomname.modifyTexts(atomNames)
        if self.obj.name:
            self.nmrAtomname.select(self.obj.name)

    def _getNmrResidueTypes(self, nmrResidue):
        """Populate the nmrResidue pulldown
        """
        self.nmrResidue.modifyTexts([x.id for x in self.obj.project.nmrResidues])
        self.nmrResidue.select(self.obj.nmrResidue.id)

    klass = NmrAtom
    attributes = [('pid', EntryCompoundWidget, getattr, None, None, None, {}),
                  ('nmrAtom name', PulldownListCompoundWidget, getattr, None, _getNmrAtomTypes, None, {}),
                  ('nmrResidue', PulldownListCompoundWidget, getattr, setattr, _getNmrResidueTypes, None, {}),
                  ('Merge to Existing', CheckBoxCompoundWidget, None, None, None, None, {}),
                  ('comment', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <'}),
                  ]
    hWidth = 130

    def _applyAllChanges(self, changes):
        """Apply all changes - update nmrAtom name
        """
        atomName = self.nmrAtomname.getText()
        nmrResidue = self.nmrResidue.getText()

        if self.obj.name != atomName:
            self.obj.rename(atomName)

        if self.obj.nmrResidue.id != nmrResidue:
            nmrResidue = self.project.getByPid('NR:%s' % nmrResidue)
            merge = self.MergetoExisting.isChecked()

            if not merge and self.project.getByPid('NA:%s.%s' % (nmrResidue.id, atomName)):
                showWarning('Merge must be selected', 'Cannot re-assign NmrAtom to an existing '
                                                      'NmrAtom of another NmrResidue without merging')

            else:
                self.obj.assignTo(chainCode=nmrResidue.nmrChain.shortName,
                                  sequenceCode=nmrResidue.sequenceCode,
                                  residueType=nmrResidue.residueType,
                                  mergeToExisting=merge)

            self.pid.setText(self.obj.pid)

    def _setValue(self, attr, setFunction, value):
        """Not needed here - subclass so does no operation
        """
        pass
