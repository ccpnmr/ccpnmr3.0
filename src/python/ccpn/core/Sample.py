"""
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
__dateModified__ = "$dateModified: 2017-07-07 16:32:30 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-10 11:42:40 +0000 (Mon, April 10, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from datetime import datetime
from typing import Sequence, Tuple, Optional
from functools import partial
from ccpn.core.Project import Project
from ccpn.core.PseudoDimension import PseudoDimension
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumHit import SpectrumHit
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.util import Common as commonUtil
from ccpn.core.lib import Pid
from ccpn.util import Constants
from ccpnmodel.ccpncore.api.ccp.lims.Sample import Sample as ApiSample
from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpn.util.decorators import logCommand
from ccpn.core.lib.ContextManagers import newObject, renameObject


class Sample(AbstractWrapperObject):
    """Corresponds to an NMR (or other) sample, with properties such as amount, pH,
    and sample identifiers. The composition is given through the contained SampleComponent objects."""

    #: Short class name, for PID.
    shortClassName = 'SA'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Sample'

    _parentClass = Project

    #: Name of plural link to instances of class
    _pluralLinkName = 'samples'

    # the attribute name used by current
    _currentAttributeName = 'samples'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiSample._metaclass.qualifiedName()

    # CCPN properties
    @property
    def _apiSample(self) -> ApiSample:
        """ CCPN sample matching Sample"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """sample name, corrected to use for id"""
        return self._wrappedData.name.translate(Pid.remapSeparators)

    @property
    def name(self) -> str:
        """actual sample name"""
        return self._wrappedData.name

    @name.setter
    def name(self, value: str):
        """set sample name"""
        self.rename(value)

    @property
    def serial(self) -> int:
        """Sample serial number, used for sorting"""
        return self._wrappedData.serial

    @property
    def _parent(self) -> Project:
        """Parent (containing) object."""
        return self._project

    @property
    def pH(self) -> float:
        """pH of sample"""
        return self._wrappedData.ph

    @pH.setter
    def pH(self, value: float):
        self._wrappedData.ph = value

    @property
    def ionicStrength(self) -> float:
        """ionicStrength of sample"""
        return self._wrappedData.ionicStrength

    @ionicStrength.setter
    def ionicStrength(self, value: float):
        self._wrappedData.ionicStrength = value

    @property
    def amount(self) -> float:
        """amount of sample, in unit of amountUnit. In most cases this is the volume, but
        there are other possibilities, e.g. for solid state NMR."""
        return self._wrappedData.amount

    @amount.setter
    def amount(self, value: float):
        self._wrappedData.amount = value

    @property
    def amountUnit(self) -> str:
        """amountUnit for sample, one of : 'L', 'g', 'mole' """
        result = self._wrappedData.amountUnit
        # if result is not None and result not in Constants.amountUnits:
        #   self._project._logger.warning(
        #     "Unsupported stored value %s for Sample.amountUnit."
        #     % result)
        #
        return result

    @amountUnit.setter
    def amountUnit(self, value: str):
        # if value not in Constants.amountUnits:
        #   self._project._logger.warning(
        #     "Setting unsupported value %s for Sample.amountUnit."
        #     % value)
        self._wrappedData.amountUnit = value

    @property
    def isHazardous(self) -> bool:
        """True if this Sample is a hazard?"""
        return self._wrappedData.isHazardous

    @isHazardous.setter
    def isHazardous(self, value: bool):
        self._wrappedData.isHazardous = value

    @property
    def isVirtual(self) -> bool:
        """True if this sample is virtual and does not describe an actual Sample..
        Virtual samples serve as templates and may not be linked to Spectra"""
        return self._wrappedData.isVirtual

    @isVirtual.setter
    def isVirtual(self, value: bool):
        self._wrappedData.isVirtual = value

    @property
    def creationDate(self) -> datetime:
        """Creation timestamp for sample (not for the description record)"""
        return self._wrappedData.creationDate

    @creationDate.setter
    def creationDate(self, value: datetime):
        self._wrappedData.creationDate = value

    @property
    def batchIdentifier(self) -> str:
        """batch identifier for sample"""
        return self._wrappedData.batchIdentifier

    @batchIdentifier.setter
    def batchIdentifier(self, value: str):
        self._wrappedData.batchIdentifier = value

    @property
    def plateIdentifier(self) -> str:
        """plate identifier for sample"""
        return self._wrappedData.plateIdentifier

    @plateIdentifier.setter
    def plateIdentifier(self, value: str):
        self._wrappedData.plateIdentifier = value

    @property
    def rowNumber(self) -> int:
        """Row number on plate"""
        return self._wrappedData.rowPosition

    @rowNumber.setter
    def rowNumber(self, value):
        self._wrappedData.rowPosition = value

    @property
    def columnNumber(self) -> int:
        """Column number on plate"""
        return self._wrappedData.colPosition

    @columnNumber.setter
    def columnNumber(self, value: int):
        self._wrappedData.colPosition = value

    # @property
    # def comment(self) -> str:
    #     """Free-form text comment"""
    #     return self._wrappedData.details
    #
    # @comment.setter
    # def comment(self, value: str):
    #     self._wrappedData.details = value

    @property
    def spectra(self) -> Tuple[Spectrum, ...]:
        """ccpn.Spectra acquired using
         ccpn.Sample (excluding multiSample spectra)"""
        ff = self._project._data2Obj.get
        return tuple(sorted(ff(y) for x in self._wrappedData.nmrExperiments
                            for y in x.dataSources))

    @spectra.setter
    def spectra(self, value: Sequence[Spectrum]):
        self._wrappedData.nmrExperiments = set(x._wrappedData.experiment for x in value)

    @property
    def spectrumHits(self) -> Tuple[SpectrumHit, ...]:
        """SpectrumHits that were found using Sample"""
        ff = self._project._data2Obj.get
        return tuple(sorted(ff(x) for x in self._apiSample.spectrumHits))

    @property
    def pseudoDimensions(self) -> PseudoDimension:
        """Pseudodimensions where sample is used for only one point along the sampled dimension"""
        ff = self._project._data2Obj.get
        return tuple(sorted(ff(x) for x in self._apiSample.sampledDataDims))

    def _fetchSampleComponent(self, name: str):
        """Fetch SampleComponent with name=name, creating it if necessary"""

        # self._startCommandEchoBlock('fetchSampleComponent', name, parName='newSampleComponent')
        ff = self._project._data2Obj.get
        # try:
        result = (ff(self._wrappedData.findFirstSampleComponent(name=name)) or
                  self.newSampleComponent(name=name))
        # finally:
        #   self._endCommandEchoBlock()

        return result

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Project) -> list:
        """get wrappedData (Sample.Samples) for all Sample children of parent NmrProject.sampleStore
        Set sampleStore to default if not set"""
        return parent._wrappedData.sampleStore.sortedSamples()

    @renameObject()
    @logCommand(get='self')
    def rename(self, value: str):
        """Rename Sample, changing its name and Pid.
        """
        self._validateName(value=value, allowWhitespace=False)

        # rename functions from here
        oldName = self.name
        self._wrappedData.__dict__['name'] = value
        return (oldName,)

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    #===========================================================================================
    # new'Object' and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    @logCommand(get='self')
    def newSampleComponent(self, name: str = None, labelling: str = None,
                           comment: str = None, **kwds):
        """Create new SampleComponent within Sample.

        Automatically creates the corresponding Substance if the name is not already taken.

        See the SampleComponent class for details.

        Optional keyword arguments can be passed in; see SampleComponent._newSampleComponent for details.

        :param name:
        :param labelling:
        :param comment: optional comment string
        :return: a new SampleComponent instance.
        """
        from ccpn.core.SampleComponent import _newSampleComponent

        return _newSampleComponent(self, name=name, labelling=labelling, comment=comment, **kwds)


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(Sample)
def _newSample(self: Project, name: str = None, pH: float = None, ionicStrength: float = None,
               amount: float = None, amountUnit: str = None, isVirtual: bool = False, isHazardous: bool = None,
               creationDate: datetime = None, batchIdentifier: str = None, plateIdentifier: str = None,
               rowNumber: int = None, columnNumber: int = None, comment: str = None, serial: int = None) -> Sample:
    """Create new Sample.

    See the Sample class for details.

    :param name:
    :param pH:
    :param ionicStrength:
    :param amount:
    :param amountUnit:
    :param isVirtual:
    :param isHazardous:
    :param creationDate:
    :param batchIdentifier:
    :param plateIdentifier:
    :param rowNumber:
    :param columnNumber:
    :param comment:
    :param serial: optional serial number.
    :return: a new Sample instance.
    """

    nmrProject = self._wrappedData
    apiSampleStore = nmrProject.sampleStore

    if not name:
        # Make default name
        nextNumber = len(self.samples)
        sampleName = self._defaultName(Sample)
        name = '%s_%s' % (sampleName, nextNumber) if nextNumber > 0 else sampleName
    names = [d.name for d in self.samples]
    while name in names:
        name = commonUtil.incrementName(name)

    if not isinstance(name, str):
        raise TypeError("Sample name must be a string")
    elif not name:
        raise ValueError("Sample name must be set")
    elif Pid.altCharacter in name:
        raise ValueError("Character %s not allowed in ccpn.Sample.name" % Pid.altCharacter)

    if amountUnit is not None and amountUnit not in Constants.amountUnits:
        self._project._logger.warning(
                "Unsupported value %s for Sample.amountUnit."
                % amountUnit)
        raise ValueError("Sample.amountUnit must be in the list: %s" % Constants.amountUnits)

    newApiSample = apiSampleStore.newSample(name=name, ph=pH, ionicStrength=ionicStrength,
                                            amount=amount, amountUnit=amountUnit,
                                            isVirtual=isVirtual,
                                            isHazardous=isHazardous, creationDate=creationDate,
                                            batchIdentifier=batchIdentifier,
                                            plateIdentifier=plateIdentifier, rowPosition=rowNumber,
                                            colPosition=columnNumber, details=comment)
    result = self._data2Obj.get(newApiSample)
    if result is None:
        raise RuntimeError('Unable to generate new Sample item')

    if serial is not None:
        try:
            result.resetSerial(serial)
        except ValueError:
            self.project._logger.warning("Could not reset serial of %s to %s - keeping original value"
                                         % (result, serial))

    return result


def getter(self: Spectrum) -> Optional[Sample]:
    return self._project._data2Obj.get(self._apiDataSource.experiment.sample)


def setter(self, value: Sample):
    self._wrappedData.experiment.sample = None if value is None else value._apiSample


Spectrum.sample = property(getter, setter, None,
                           "ccpn.Sample used to acquire ccpn.Spectrum")


def getter(self: SpectrumHit) -> Sample:
    return self._project._data2Obj.get(self._apiSpectrumHit.sample)


SpectrumHit.sample = property(getter, None, None,
                              "ccpn.Sample in which ccpn.SpectrumHit (for screening/metabolomics) is found"
                              )


def getter(self: PseudoDimension) -> Tuple[Sample, ...]:
    ff = self._project._data2Obj.get
    return tuple(ff(x) for x in self._wrappedData.samples())


def setter(self: PseudoDimension, value) -> Tuple[Sample, ...]:
    self._wrappedData.sample = [x._wrappedDAta for x in value]


PseudoDimension.orderedSamples = property(getter, setter, None,
                                          "Samples used to acquire the individual points in this sampled dimension"
                                          )
del getter
del setter

#EJB 20181205: moved to Project
# Project.newSample = _newSample
# del _newSample

# Notifiers - added to trigger crosslink changes
className = Nmr.Experiment._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('Sample', 'Spectrum')}, className, 'setSample'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'setSample'),
         )
        )
className = ApiSample._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('Sample', 'Spectrum')}, className, 'addNmrExperiment'),
         ('_modifiedLink', {'classNames': ('Sample', 'Spectrum')}, className, 'removeNmrExperiment'),
         ('_modifiedLink', {'classNames': ('Sample', 'Spectrum')}, className, 'setNmrExperiments'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'addNmrExperiment'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'removeNmrExperiment'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'setNmrExperiments'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'addSampledDataDim'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'removeSampledDataDim'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'setSampledDataDims'),
         ('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className, 'addSampledDataDim'),
         ('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className,
          'removeSampledDataDim'),
         ('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className, 'setSampledDataDims'),
         )
        )
className = Nmr.SampledDataDim._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className, 'addSample'),
         ('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className, 'removeSample'),
         ('_modifiedLink', {'classNames': ('Sample', 'PseudoDimension')}, className, 'setSamples'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'addSample'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'removeSample'),
         ('_modifiedLink', {'classNames': ('Sample', 'SpectrumHit')}, className, 'setSamples'),
         )
        )
