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
__dateModified__ = "$dateModified: 2017-07-07 16:32:33 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import copy
import os
# from ccpn.framework import Framework
from ccpn.core.testing.WrapperTesting import WrapperTesting
from ccpn.core.lib import CcpnNefIo


def test_nef_maps():
    # Validity check
    # Check that elements in nef2CcpnMap match saveFrameOrder
    # and that all contents are present and reached from saveframes in saveFrameOrder
    copyMap = copy.deepcopy(CcpnNefIo.nef2CcpnMap)
    for category in CcpnNefIo.saveFrameWritingOrder:
        map1 = copyMap.pop(category)
        for tag, val in map1.items():
            if val == CcpnNefIo._isALoop:
                copyMap.pop(tag)
    if copyMap:
        raise TypeError("Coding Error - Data in nef2CcpnMap not reached from saveFrameOrder:\n%s"
                        % list(copyMap.keys()))


class NefIoTest(WrapperTesting):
    # Path of project to load (None for new project
    projectPath = 'CcpnCourse2b'

    def test_nef_write_read(self):
        nefPath = self.project.path + '.out.nef'
        if os.path.exists(nefPath):
            os.remove(nefPath)
        CcpnNefIo.saveNefProject(self.project, nefPath)
        application = self.project._appBase
        application.loadProject(nefPath)
