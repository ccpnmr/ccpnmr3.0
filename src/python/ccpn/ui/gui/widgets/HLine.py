#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (http://www.ccpn.ac.uk) 2014 - 2017"
__credits__ = ("Wayne Boucher, Ed Brooksbank, Rasmus H Fogh, Luca Mureddu, Timothy J Ragan & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               "or ccpnmodel.ccpncore.memops.Credits.CcpnLicense for licence text")
__reference__ = ("For publications, please use reference from http://www.ccpn.ac.uk/v3-software/downloads/license",
               "or ccpnmodel.ccpncore.memops.Credits.CcpNmrReference")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2017-07-07 16:32:46 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.b2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================



import sys
from PyQt4 import QtGui, QtCore
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Widget import Widget

class HLine(Widget, Base):
  def __init__(self, parent=None, style='SolidLine', **kwds):
    '''

    :param style: Options: 
                          'SolidLine';
                           'DashLine'; 
                           'DashDotLine';
                           'DashDotDotLine'
    '''

    QtGui.QWidget.__init__(self, parent)
    Base.__init__(self, **kwds)
    self.parent = parent
    self.style = style

    self.styles = {
      'SolidLine':          QtCore.Qt.SolidLine,
      'DashLine':           QtCore.Qt.DashLine,
      'DashDotLine':        QtCore.Qt.DashDotLine,
      'DashDotDotLine':    QtCore.Qt.DashDotDotLine,
    }

    self.setMaximumHeight(10)


  def paintEvent(self, e):
    qp = QtGui.QPainter()
    qp.begin(self)
    self.drawLine(qp, self.style)
    qp.end()

  def drawLine(self, qp, style=None, colour=None ,):

    if style in self.styles:
      style = self.styles[style]
      pen = QtGui.QPen(QtCore.Qt.black, 2, style)
      qp.setPen(pen)
      qp.drawLine(0, 10, self.geometry().right(), 10)





def main():
  app = QtGui.QApplication(sys.argv)
  ex = HLine()
  sys.exit(app.exec_())


if __name__ == '__main__':
  from ccpn.ui.gui.widgets.Application import TestApplication
  from ccpn.ui.gui.popups.Dialog import CcpnDialog
  from ccpn.ui.gui.widgets.Slider import SliderSpinBox

  app = TestApplication()
  popup = CcpnDialog(windowTitle='Test slider', setLayout=True)
  slider = SliderSpinBox(parent=popup, startVal=0, endVal=100, value=5, grid=(0 ,0))
  line = HLine(parent=popup, grid=(1 ,0))
  slider2 = SliderSpinBox(parent=popup, startVal=0, endVal=100, value=5, grid=(2, 0))
  popup.show()
  popup.raise_()
  app.start()

