"""
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
from ccpn.framework.constants import CCPNMR_PREFIX

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
__dateModified__ = "$dateModified: 2017-07-07 16:32:31 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import functools
import itertools
import operator
import typing
from collections import OrderedDict
from copy import deepcopy
from ccpn.core import _importOrder
# from ccpn.core.lib import CcpnSorting
from ccpn.core.lib import Util as coreUtil
from ccpn.util import Common as commonUtil
from ccpn.core.lib import Pid
from ccpnmodel.ccpncore.api.memops import Implementation as ApiImplementation
from ccpn.util.Logging import getLogger
from ccpn.core.lib.ContextManagers import deleteObject, notificationBlanking, undoStackBlocking
from ccpn.core.lib.Notifiers import NotifierBase, Notifier


@functools.total_ordering
class AbstractWrapperObject(NotifierBase):
    """Abstract class containing common functionality for subclasses.

    ADVANCED. Core programmers only.


    **Rules for subclasses:**

    All collection attributes are tuples. For objects these are sorted by pid;
    for simple values they are ordered.

    Non-child collection attributes must have addElement() and removeElement
    functions as appropriate.

    For each child class there will be a newChild factory function, to crate
    the child object. There will be a collection attribute for each child,
    grandchild, and generally descendant.

    The object pid is given as NM:key1.key2.key3 ... where NM is the shortClassName,
    and the combination of key1, key2, etc. forms the id, which is the keys of the parent
    classes starting at the top.
    The pid is the object id relative to the project; keys relative to objects lower
    in the hierarchy will omit successively more keys.


    **Code organisation:**

    All code related to a given class lives in the file for the class.
    On importing it, it will insert relevant functions in the parent class.
    All import must be through the ccpn module, where it is guaranteed that
    all modules are imported in the right order.

    All actual data live
    in the data layer underneath these (wrapper) classes and are derived where needed.
    All data storage is done
    at the lower level, not at the wrapper level, and there is no mechanism for
    storing attributes that have been added at the wrapper level. Key and uniqueness
    checking, type checking etc.  is also done at teh lower level.

    Initialising happens by passing in a (lower-level) NmrProject instance to the Project
     __init__;
    all wrapper instances are created automatically starting from there. Unless we change this,
    this means we assume that all data can be found by navigating from an
    NmrProject.

    New classes can be added, provided they match the requirements. All classes
    must form a parent-child tree with the root at Project. All classes must
    must have teh standard class-level attributes, such as  shortClassName, _childClasses,
    and _pluralLinkName.
    Each class must implement the properties id and _parent, and the methods
    _getAllWrappedData,  and rename. Note that the
    properties and the _getAllWrappedData function
    must work from the underlying data, as they will be called before the pid
    and object dictionary data are set up.
    """

    #: Short class name, for PID. Must be overridden for each subclass
    shortClassName = None

    # Class name - necessary since the actual objects may be of a subclass.
    className = 'AbstractWrapperObject'

    _parentClass = None

    #: Name of plural link to instances of class
    _pluralLinkName = 'abstractWrapperClasses'

    #: List of child classes. Must be overridden for each subclass.
    _childClasses = []

    _isGuiClass = False  # Overridden by Gui classes

    # Wrapper-level notifiers that are set up on code import and
    # registered afresh for every new project
    # _coreNotifiers = []

    # Should notifiers be registered separately for this class?
    # Set to False if multiple wrapper classes wrap the same API class (e.g. PeakList, IntegralList;
    # Peak, Integral) so that API level notifiers are only registered once.
    _registerClassNotifiers = True

    # Function to generate custom subclass instances -= overridden in some subclasses
    _factoryFunction = None

    # Default values for parameters to 'new' function. Overridden in subclasses
    _defaultInitValues = None

    # Number of fields that comprise the object's pid; usually 1 but overridden in some subclasses
    # e.g. NmrResidue and Residue. Used to get parent id's
    _numberOfIdFields = 1

    # Implementation methods

    def __init__(self, project: 'Project', wrappedData: ApiImplementation.DataObject):

        # NB project parameter type is Project. Set in Project.py

        # NB wrappedData must be globally unique. CCPN objects all are,
        # but for non-CCPN objects this must be ensured.

        # Check if object is already wrapped
        data2Obj = project._data2Obj
        if wrappedData in data2Obj:
            raise ValueError(
                    'Cannot create new object "%s": one already exists for "%s"' % (self.className, wrappedData))

        # initialise
        self._project = project
        self._wrappedData = wrappedData
        data2Obj[wrappedData] = self

        self._id = None
        self._resetIds()

        #EJB 20181217: test for preDelete
        self._flaggedForDelete = False

    def _resetIds(self):
        # reset id
        oldId = self._id
        project = self._project
        parent = self._parent
        className = self.className
        if parent is None:
            # This is the project
            _id = self._wrappedData.name
            sortKey = ('',)
        elif parent is project:
            _id = str(self._key)
            sortKey = self._localCcpnSortKey
        else:
            _id = '%s%s%s' % (parent._id, Pid.IDSEP, self._key)
            sortKey = parent._ccpnSortKey[2:] + self._localCcpnSortKey
        self._id = _id

        # A bit inelegant, but Nmrresidue is handled specially,
        # with a _ccpnSortKey property
        if className != 'NmrResidue':
            self._ccpnSortKey = (id(project), _importOrder.index(className)) + sortKey

        # update pid:object mapping dictionary
        dd = project._pid2Obj.get(className)
        if dd is None:
            dd = {}
            project._pid2Obj[className] = dd
            project._pid2Obj[self.shortClassName] = dd
        # assert oldId is not None
        if oldId in dd:
            del dd[oldId]
        dd[_id] = self

    def __bool__(self):
        """Truth value: true - wrapper classes are never empty"""
        return True

    def __lt__(self, other):
        """Ordering implementation function, necessary for making lists sortable.
        """

        if hasattr(other, '_ccpnSortKey'):
            return self._ccpnSortKey < other._ccpnSortKey
        else:
            return id(self) < id(other)

    def __eq__(self, other):
        """Python 2 behaviour - objects equal only to themselves."""
        return self is other

    def __ne__(self, other):
        """Python 2 behaviour - objects equal only to themselves."""
        return self is not other

    def __repr__(self):
        """Object string representation; compatible with application.get()
        """
        return "<%s>" % (self.longPid)

    def __str__(self):
        """Readable string representation; potentially subclassed
        """
        return "<%s>" % self.pid

    __hash__ = object.__hash__

    #=========================================================================================
    # CCPN Properties
    #=========================================================================================

    @property
    def className(self) -> str:
        """Class name - necessary since the actual objects may be of a subclass.."""
        return self.__class__.className

    @property
    def shortClassName(self) -> str:
        """Short class name, for PID. Must be overridden for each subclass."""
        return self.__class__.shortClassName

    @property
    def project(self) -> 'Project':
        """The Project (root)containing the object."""
        return self._project

    @property
    def pid(self) -> Pid.Pid:
        """Identifier for the object, unique within the project.
        Set automatically from the short class name and object.id
        E.g. 'NA:A.102.ALA.CA' """
        return Pid.Pid(Pid.PREFIXSEP.join((self.shortClassName, self._id)))

    @property
    def longPid(self) -> Pid.Pid:
        """Identifier for the object, unique within the project.
        Set automatically from the full class name and object.id
        E.g. 'NmrAtom:A.102.ALA.CA' """
        return Pid.Pid(Pid.PREFIXSEP.join((self.className, self._id)))

    def _longName(self, name):
        """long name generated form the name and the object id
        """
        return Pid.Pid(Pid.PREFIXSEP.join((name, self._id)))

    @property
    def isDeleted(self) -> bool:
        """True if this object is deleted."""
        # The many variants are to make sure this catches deleted objects
        # also during the deletion process, for filtering
        return (not hasattr(self, '_wrappedData') or self._wrappedData is None
                or not hasattr(self._project, '_data2Obj') or self._wrappedData.isDeleted)

    # default name to use for objects with a name/title
    # @property
    def _defaultName(self, cls):
        return cls.className.lower()

    @property
    def _ccpnInternalData(self) -> dict:
        """Dictionary containing arbitrary type data for internal use.

        Data can be nested strings, numbers, lists, tuples, (ordered) dicts,
        numpy arrays, pandas structures, CCPN Tensor objects, and any
        object that can be serialised to JSON. This does NOT include CCPN or
        CCPN API objects.

        NB This returns the INTERNAL dictionary. There is NO encapsulation

        Data are kept on save and reload, but there is NO guarantee against
        trampling by other code"""
        result = self._wrappedData.ccpnInternalData
        if result is None:
            # with notificationBlanking():
            #     result = self._wrappedData.ccpnInternalData = {}
            result = {}
        return result

    @_ccpnInternalData.setter
    def _ccpnInternalData(self, value):
        if not (isinstance(value, dict)):
            raise ValueError("_ccpnInternalData must be a dictionary, was %s" % value)
        self._wrappedData.ccpnInternalData = value

    @property
    def comment(self) -> str:
        """Free-form text comment"""
        return self._none2str(self._wrappedData.details)

    @comment.setter
    def comment(self, value: str):
        self._wrappedData.details = self._str2none(value)

    #=========================================================================================
    # CCPN functionalities
    #=========================================================================================

    CCPNMR_NAMESPACE = '_ccpNmrV3internal'

    def _setInternalParameter(self, parameterName:str, value):
        """Sets parameterName for CCPNINTERNAL namespace to value; value must be json seriliasable"""
        self.setParameter(self.CCPNMR_NAMESPACE, parameterName, value)

    def _getInternalParameter(self, parameterName:str):
        """Gets parameterName for CCPNINTERNAL namespace"""
        return self.getParameter(self.CCPNMR_NAMESPACE, parameterName)

    def _hasInternalParameter(self, parameterName:str):
        """Returns true if parameterName for CCPNINTERNAl namespace exists"""
        return self.hasParameter(self.CCPNMR_NAMESPACE, parameterName)

    def setParameter(self, namespace:str, parameterName:str, value):
        """Sets parameterName for namespace to value; value must be json serialisable"""
        data = deepcopy(self._ccpnInternalData)
        space = data.setdefault(namespace, {})
        space[parameterName] = value
        # Explicit assignment to force saving
        # self._wrappedData.__dict__['isModfied'] = True
        # self._ccpnInternalData = {}
        # self._ccpnInternalData.update(data)
        self._wrappedData.ccpnInternalData = data

    def getParameter(self, namespace:str, parameterName:str):
        """Returns value of parameterName for namespace; returns None if not present"""
        data = self._ccpnInternalData
        space = data.get(namespace)
        if space is None:
            return None
        return space.get(parameterName)

    def hasParameter(self, namespace:str, parameterName:str):
        """Returns true if parameterName for namespace exists"""
        data = self._ccpnInternalData
        space = data.get(namespace)
        if space is None:
            return False
        return parameterName in space

    def _setNonApiAttributes(self, attribs):
        """Set the non-api attributes that are stored in ccpnInternal
        """
        if not isinstance(attribs, dict):
            raise TypeError('ERROR: %s must be a dict' % str(attribs))

        for att, value in attribs.items():
            setattr(self, att, value)

    @staticmethod
    def _str2none(value):
        """Covenience to convert an empty string to None; V2 requirement for some attributes
        """
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Non-string type for value argument')
        return None if len(value) == 0 else value

    @staticmethod
    def _none2str(value):
        """Covenience to None return to an empty string; V2 requirement for some attributes
        """
        return '' if value is None else value

    def _saveObjectOrder(self, objs, key):
        """Convenience: save pids of objects under key in the CcpNmr internal space.
        Order can be restored with _restoreObjectOrder
        """
        pids = [obj.pid for obj in objs]
        self._setInternalParameter(key, pids)

    def _restoreObjectOrder(self, objs, key) -> list:
        """Convenience: restore order of objects from saved pids under key in the CcpNmr internal space.
        Order needed to be stored previously with _saveObjectOrder
        """
        if not isinstance(objs, (list,tuple)):
            raise ValueError('Expected a list or tuple for "objects" argument')

        result = objs
        pids = self._getInternalParameter(key)
        # see if we can use the pids to reconstruct the order
        if pids is not None:
            objectsDict = dict([(s.pid, s) for s in objs])
            result = [objectsDict[p] for p in pids if p in objectsDict]
            if len(result) != len(objs):
                # we failed
                result = objs
        return result

    #=========================================================================================
    # CCPN abstract properties
    #=========================================================================================

    @property
    def _key(self) -> str:
        """Object local identifier, unique for a given type with a given parent.

        Set automatically from other (immutable) object attributes."""
        raise NotImplementedError("Code error: function not implemented")

    @property
    def _parent(self):
        """Parent (containing) object."""
        raise NotImplementedError("Code error: function not implemented")

    @property
    def id(self) -> str:
        """Identifier for the object, used to generate the pid and longPid.

        Generated by combining the id of the containing object,
        with the value of one or more key attributes that uniquely identify the object in context.::

          E.g. the id for an Atom, 'A.55.VAL.HA' is generated from:

          - 'A' *Chain.shortName*

          - '55' *Residue.sequenceCode*

          - 'VAL' *Residue.residueType*

          - 'HA' *Atom.name*"""

        return self._id

    @property
    def _localCcpnSortKey(self) -> typing.Tuple:
        """Local sorting key, in context of parent.
        NBNB Must be overridden is some subclasses to get proper sorting order"""

        if hasattr(self._wrappedData, 'serial'):
            return (self._wrappedData.serial,)
        else:
            return (self._key,)

    def _newInstance(self, *kwds):
        """Instantiate a new instance, including the wrappedData
        Should be subclassed
        """
        pass

    #=========================================================================================
    # Abstract /Api methods
    #=========================================================================================

    def _printClassTree(self, node=None, tabs=0):
        """Simple Class-tree printing method
         """
        if node is None:
            node = self
        s = '\t' * tabs + '%s' % (node.className)
        if node._isGuiClass:
            s += '  (GuiClass)'
        print(s)
        for child in node._childClasses:
            self._printClassTree(child, tabs=tabs + 1)

    def _getChildrenByClass(self, klass) -> list:
        """GWV: Convenience: get the children of type klass of self.
        klass is string (e.g. 'Peak') or V3 core class
        returns empty list if klass is not a child of self
        """
        klass = klass if isinstance(klass, str) else getattr(klass, 'className')
        result = self._getChildren(classes=[klass]).get(klass)
        if result is None:
            return []
        return result

    def _getChildren(self, classes=['all']) -> OrderedDict:
        """GWV; Return a dict of (className, ChildrenList) pairs
        classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
        CCPNINTERNAL: used throughout
        """
        _get = self._project._data2Obj.get
        data = OrderedDict()
        for className, apiChildren in self._getApiChildren(classes=classes).items():
            children = data.setdefault(className, [])
            for apiChild in apiChildren:
                child = _get(apiChild)
                if child is not None:
                    children.append(child)
        return data

    def _getApiChildren(self, classes=['all']) -> OrderedDict:
        """GWV; Return a dict of (className, apiChildrenList) pairs
         classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
         CCPNINTERNAL: used throughout
         """
        data = OrderedDict()
        for childClass in self._childClasses:

            if ('all' in classes) or \
                    (childClass._isGuiClass and 'gui' in classes) or \
                    (not childClass._isGuiClass and 'nonGui' in classes) or \
                    childClass.className in classes:

                childApis = data.setdefault(childClass.className, [])
                for apiObj in childClass._getAllWrappedData(self):
                    childApis.append(apiObj)

        return data

    def _getApiSiblings(self) -> list:
        """GWV; Return a list of apiSiblings of self
         CCPNINTERNAL: used throughout
         """
        if self._parent is None:
            # We are at the root (i.e. Project), no siblings
            return []
        else:
            return self._parent._getApiChildren().get(self.className)

    def _getSiblings(self) -> list:
        """GWV; Return a list of siblings of self
         CCPNINTERNAL: used throughout
         """
        if self._parent is None:
            # We are at the root (i.e. Project), no siblings
            return []
        else:
            return self._parent._getChildren().get(self.className)

    def _getDirectChildren(self):
        """RF; Get list of all objects that have self as a parent
        """
        getDataObj = self._project._data2Obj.get
        result = list(getDataObj(y) for x in self._childClasses for y in x._getAllWrappedData(self))
        return result

    def _restoreChildren(self, classes=['all']):
        """GWV: A method to restore the children of self
        classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
        For restore 3.1 branch
        """
        _classMap = dict([(cls.className, cls) for cls in self._childClasses])

        # loop over all the child-classses
        for clsName, apiChildren in self._getApiChildren(classes=classes).items():

            cls = _classMap.get(clsName)
            if cls is None:
                raise RuntimeError('Undefined class "%s"' % clsName)

            for apiChild in apiChildren:

                newInstance = self._newInstanceWithApiData(cls=cls, apiData=apiChild)
                if newInstance is None:
                    raise RuntimeError('Error creating new instance of class "%s"' % clsName)

                # add the newInstance to the appropriate mapping dictionaries
                self._project._data2Obj[apiChild] = newInstance
                _d = self._project._pid2Obj.setdefault(clsName, {})
                _d[newInstance.pid] = newInstance

                # recursively do the children of newInstance
                newInstance._restoreChildren(classes=classes)

    def _newInstanceWithApiData(self, cls, apiData):
        """Return a new instance of cls, initialised with apiData
        For restore 3.1 branch
        """
        if apiData in self._project._data2Obj:
            # This happens with Window, as it get initialised by the Windowstore and then once
            # more as child of Project
            newInstance = self._project._data2Obj[apiData]

        elif hasattr(cls, '_factoryFunction') and getattr(cls, '_factoryFunction') is not None:
            newInstance = cls._factoryFunction(self._project, apiData)

        else:
            newInstance = cls(self._project, apiData)

        if newInstance is None:
            raise RuntimeError('Error creating new instance of class "%s"' % cls.className)

        return newInstance

    def _getApiObjectTree(self) -> tuple:
        """Retrieve the apiObject tree contained by this object

        CCPNINTERNAL   used for undo's, redo's
        """
        #EJB 20181127: taken from memops.Implementation.DataObject.delete
        #                   should be in the model??

        from ccpn.util.OrderedSet import OrderedSet

        apiObject = self._wrappedData

        apiObjectlist = OrderedSet()
        # objects still to be checked
        objsToBeChecked = list()
        # counter keyed on (obj, roleName) for how many objects at other end of link
        linkCounter = {}

        # topObjects to check if modifiable
        topObjectsToCheck = set()

        objsToBeChecked.append(apiObject)
        while len(objsToBeChecked) > 0:
            obj = objsToBeChecked.pop()
            if obj:
                obj._checkDelete(apiObjectlist, objsToBeChecked, linkCounter, topObjectsToCheck)  # This builds the list/set

        for topObjectToCheck in topObjectsToCheck:
            if (not (topObjectToCheck.__dict__.get('isModifiable'))):
                raise ValueError("""%s.delete:
           Storage not modifiable""" % apiObject.qualifiedName
                                 + ": %s" % (topObjectToCheck,)
                                 )

        return tuple(apiObjectlist)

    @classmethod
    def _getAllWrappedData(cls, parent) -> list:
        """get list of wrapped data objects for each class that is a child of parent

        List must be sorted at the API level 1) to give a reproducible order,
        2) using serial (if present) and otherwise a natural (i.e.NON-object) key.
        Wrapper level sorting may be (and sometimes is) different.

        """
        if cls not in parent._childClasses:
            raise Exception
        raise NotImplementedError("Code error: function not implemented")

    def rename(self, value: str):
        """Change the object name or other key attribute(s), changing the object pid,
           and all internal references to maintain consistency.
           Some Objects (Chain, Residue, Atom) cannot be renamed"""
        raise ValueError("%s objects cannot be renamed" % self.__class__.__name__)

    # In addition each class (except for Project) must define a  newClass method
    # The function (e.g. Project.newMolecule), ... must create a new child object
    # AND ALL UNDERLYING DATA, taking in all parameters necessary to do so.
    # This can be done by defining a function (not a method)
    # def newMolecule( self, *args, **kwds):
    # and then doing Project.newMolecule = newMolecule

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    @deleteObject()
    def delete(self):
        """Delete object, with all contained objects and underlying data.
        """

        # NBNB clean-up of wrapper structure is done via notifiers.
        # NBNB some child classes must override this function
        self.deleteAllNotifiers()
        self._wrappedData.delete()

    def getByPid(self, pid: str):
        """Get an arbitrary data object from either its pid (e.g. 'SP:HSQC2') or its longPid
        (e.g. 'Spectrum:HSQC2')

        Returns None for invalid or unrecognised input strings.
        """
        if pid is None or len(pid) is None:
            return None

        obj = None

        # return if the pid does not conform to a pid definition
        if not Pid.Pid.isValid(pid):
            return None

        pid = Pid.Pid(pid)
        dd = self._project._pid2Obj.get(pid.type)
        if dd is not None:
            obj = dd.get(pid.id)
        if obj is not None and obj.isDeleted:
            raise RuntimeError('Pid "%s" defined a deleted object' % pid)
        return obj

        # GWV 20181201: refactored
        # tt = pidstring.split(Pid.PREFIXSEP, 1)
        # if len(tt) == 2:
        #     if tt[0] in ('GM', 'Mark', 'GA', 'Axis', 'GO', 'Module', 'GS', 'Strip',
        #                  'GL', 'PeakListView', 'GI', 'IntegralListView', 'GU', 'MultipletListView',
        #                  'GD', 'SpectrumDisplay', 'GW', 'Window',
        #                  'GV', 'SpectrumView', 'GT', 'Task'):
        #         from warnings import warn
        #         warn('ui.getByGid should be used for getting graphics ({})'.format(pidstring),
        #              category=DeprecationWarning)
        #     dd = self._project._pid2Obj.get(tt[0])
        #     if dd:
        #         return dd.get(tt[1])
        # #
        # return None

    #=========================================================================================
    # CCPN Implementation methods
    #=========================================================================================

    def getByRelativeId(self, newName: str):
        return self._getDescendant(self.project, newName)

    @classmethod
    def _linkWrapperClasses(cls, ancestors: list = None, Project: 'Project' = None):
        """Recursively set up links and functions involving children for wrapper classes

        NB classes that have already been linked are ignored, but their children are still processed"""

        if Project:
            assert ancestors, "Code errors, _linkWrapperClasses called with Project but no ancestors"
            newAncestors = ancestors + [cls]
            if cls not in Project._allLinkedWrapperClasses:
                Project._allLinkedWrapperClasses.append(cls)

                classFullName = repr(cls)[7:-2]

                # add getCls in all ancestors
                funcName = 'get' + cls.className
                #  NB Ancestors is never None at this point
                for ancestor in ancestors:
                    # Add getDescendant function
                    def func(self, relativeId: str) -> cls:
                        return cls._getDescendant(self, relativeId)

                    func.__doc__ = "Get contained %s object by relative ID" % classFullName
                    setattr(ancestor, funcName, func)

                # Add descendant links
                linkName = cls._pluralLinkName
                for ii in range(len(newAncestors) - 1):
                    ancestor = newAncestors[ii]
                    func = functools.partial(AbstractWrapperObject._allDescendants,
                                             descendantClasses=newAncestors[ii + 1:])
                    # func.__annotations__['return'] = typing.Tuple[cls, ...]
                    if cls.className == 'NmrResidue':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in sequential order "
                                + "(for assigned or connected NmrChains), otherwise in creation order. "
                                + "This is identical to the standard sorting order."
                        )
                    elif cls.className == 'ChemicalShift':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in NmrAtom creation order "
                                + "This is different from the standard sorting order"
                        )
                    elif cls.className == 'Spectrum':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in approximate creation order "
                                + "This is different from the standard sorting order"
                        )
                    elif cls.className == 'Residue':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in sequential order "
                                + "This is identical to the standard sorting order"
                        )
                    elif hasattr(cls, 'serial'):
                        docTemplate = ("\- *(%s,)*  - contained %s objects in creation order. "
                                       + "This may differ from the standard sorting order")
                    elif cls.className in ('Data', 'Atom', 'Chain', 'Substance', 'SampleComponent'):
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in name order "
                                + "This is identical to the standard sorting order."
                        )
                    else:
                        docTemplate = ("\- *(%s,)*  - contained %s objects in order of underlying key. "
                                       + "This may differ from the standard sorting order")

                    prop = property(func, None, None, docTemplate % (classFullName, cls.className))
                    setattr(ancestor, linkName, prop)

                # Add standard Notifiers:
                if cls._registerClassNotifiers:
                    className = cls._apiClassQualifiedName
                    Project._apiNotifiers[:0] = [
                        ('_newApiObject', {'cls': cls}, className, '__init__'),
                        ('_startDeleteCommandBlock', {}, className, 'startDeleteBlock'),
                        ('_finaliseApiDelete', {}, className, 'delete'),
                        ('_endDeleteCommandBlock', {}, className, 'endDeleteBlock'),
                        ('_finaliseApiUnDelete', {}, className, 'undelete'),
                        ('_modifiedApiObject', {}, className, ''),
                        ]
        else:
            # Project class. Start generation here
            Project = cls
            ll = Project._allLinkedWrapperClasses
            # if ll:
            #     raise RuntimeError("ERROR: initialisation attempted more than once")
            newAncestors = [cls]
            ll.append(Project)

        # Fill in Project._className2Class map
        dd = Project._className2Class
        dd[cls.className] = dd[cls.shortClassName] = cls

        # recursively call next level down the tree
        for cc in cls._childClasses:
            cc._linkWrapperClasses(newAncestors, Project=Project)

    @classmethod
    def _getChildClasses(cls, recursion: bool = False) -> list:
        """
        :param recursion: use recursion to also add child objects
        :return: list of valid child classes of cls

        NB: Depth-first ordering

        CCPNINTERNAL: Notifier class
        """
        result = []
        for klass in cls._childClasses:
            result.append(klass)
            if recursion:
                result = result + klass._getChildClasses(recursion=recursion)
        return result

    @classmethod
    def _getParentClasses(cls) -> list:
        """Return a list of parent classes, staring with the root (i.e. Project)
        """
        result = []
        klass = cls
        while klass._parentClass is not None:
            result.append(klass._parentClass)
            klass = klass._parentClass
        result.reverse()
        return result

    @classmethod
    def _getDescendant(cls, self, relativeId: str):
        """Get descendant of class cls with relative key relativeId
         Implementation function, used to generate getCls functions
         """
        dd = self._project._pid2Obj.get(cls.className)
        if dd:
            if self is self._project:
                key = relativeId
            else:
                key = '%s%s%s' % (self._id, Pid.IDSEP, relativeId)
            return dd.get(key)
        else:
            return None

    def _allDescendants(self, descendantClasses):
        """get all descendants of type decendantClasses[-1] of self,
        following descendantClasses down the data tree.

        E.g. if called on a chain with descendantClass == [Residue,Atom] the function returns
        a list of all Atoms in a Chain

        NB: the returned list of NmrResidues is sorted; if not: breaks the programme
        """

        # GWV 20181201: refactored to use _getChildren and recursion
        # project = self._project
        # data2Obj = project._data2Obj
        # objects = [self]
        #
        # for cls in descendantClasses:
        #
        #     # function gets wrapped data for all children starting from parent
        #     func = cls._getAllWrappedData
        #     # data is iterator of wrapped data for children starting from all parents
        #     ll = itertools.chain(*(func(x) for x in objects))
        #     # objects is all wrapper objects for next child level down
        #     # NB this may sometimes (during undo/redo) get called when not all objects
        #     # are finalised - hence the test if y is None
        #     objects = list(y for y in (data2Obj.get(x) for x in ll) if y is not None)
        #     if cls.className == 'NmrResidue':
        #         # These must always be sorted
        #         objects.sort()
        # #
        # return objects
        from ccpn.core.NmrResidue import NmrResidue  # Local import to avoid cycles

        if descendantClasses is None or len(descendantClasses) == 0:
            # we should never be here
            raise RuntimeError('Error getting all decendants from %s; decendants tree is empty' % self)

        if len(descendantClasses) == 1:
            # we are at the end of the recursion tree; return the children of type decendantClass[0] of self
            if descendantClasses[0] not in self._childClasses:
                raise RuntimeError('Invalid decentdantClass %s for %s' % (descendantClasses[0], self))
            className = descendantClasses[0].className
            # Passing the 'classes' argument limits the dict to className only (for speed)
            objs = self._getChildren(classes=[className])[className]
            # NB: the returned list of NmrResidues is sorted; if not: breaks the programme
            if descendantClasses[0].className == NmrResidue.className:
                objs.sort()
            # print('_allDecendants for %-30s of class %-20r: %s' % \
            #       (self, descendantClasses[0].__name__, objs))
            return objs

        # we are not at the end; traverse down the tree
        objs = []
        className = descendantClasses[0].className
        # Passing the 'classes' argument limits the dict to className only (for speed)
        for obj in self._getChildren(classes=className)[className]:
            children = AbstractWrapperObject._allDescendants(obj, descendantClasses=descendantClasses[1:])
            objs.extend(children)
        return objs

    def _initializeAll(self):
        """Initialize children, using existing objects in data model"""

        project = self._project
        data2Obj = project._data2Obj

        for childClass in self._childClasses:
            # recursively create children
            for apiObj in childClass._getAllWrappedData(self):
                obj = data2Obj.get(apiObj)
                if obj is None:
                    factoryFunction = childClass._factoryFunction
                    if factoryFunction is None:
                        obj = childClass(project, apiObj)
                    else:
                        obj = factoryFunction(project, apiObj)
                try:
                    obj._initializeAll()
                except Exception as er:
                    getLogger().warn('Error initialising object %s. %s1' %(obj,er))
                # getLogger().info(str(obj))   # ejb - temp

    def _unwrapAll(self):
        """remove wrapper from object and child objects
        For special case where wrapper objects are removed without deleting wrappedData"""
        project = self._project
        data2Obj = project._data2Obj

        for childClass in self._childClasses:

            # recursively unwrap children
            for apiObj in childClass._getAllWrappedData(self):
                obj = data2Obj.get(apiObj)
                if obj is not None:
                    obj._unwrapAll()
                    del self._pid2Obj[obj.shortClassName][obj._id]
                del data2Obj[apiObj]

    def _setUniqueStringKey(self, defaultValue: str, keyTag: str = 'name') -> str:
        """(re)set self._wrappedData.keyTag to make it a unique key, using defaultValue
        if not set NB - is called BEFORE data2obj etc. dictionaries are set"""

        wrappedData = self._wrappedData
        if not hasattr(wrappedData, keyTag):
            raise ValueError("Cannot set unique %s for %s: %s object has no attribute %s"
                             % (keyTag, self.className, wrappedData.__class__, keyTag))

        undo = self._project._undo
        if undo is not None:
            undo.increaseBlocking()
        try:
            if wrappedData not in self._project._data2Obj:
                # Necessary because otherwise we likely will have notifiers - that would then break
                wrappedData.root.override = True
            # Set default value if present value is None
            value = getattr(wrappedData, keyTag)
            if value is None:
                value = defaultValue

            # Set to new, unique value if present value is a duplicate
            competitorDict = set(getattr(x, keyTag)
                                 for x in self._getAllWrappedData(self._parent)
                                 if x is not wrappedData)

            if value in competitorDict and hasattr(wrappedData, 'serial'):
                # First try appending serial
                value = '%s-%s' % (value, wrappedData.serial)

            while value in competitorDict:
                # Keep incrementing suffix till value is unique
                value = commonUtil.incrementName(value)

            # Set the unique result
            setattr(wrappedData, keyTag, value)

        finally:
            if wrappedData not in self._project._data2Obj:
                wrappedData.root.override = False
            if undo is not None:
                undo.decreaseBlocking()

    def _getDirectChildren(self):
        """Get list of all objects that have self as a parent
        """
        getDataObj = self._project._data2Obj.get
        result = list(getDataObj(y) for x in self._childClasses for y in x._getAllWrappedData(self))
        return result

    # Notifiers and related functions:

    #GWV 20181123:
    # @classmethod
    # def _setupCoreNotifier(cls, target: str, func: typing.Callable,
    #                        parameterDict: dict = {}, onceOnly: bool = False):
    #     """Set up notifiers for class cls that do not depend on individual objects -
    #     These will be registered whenever a new project is initialised.
    #     Parameters are eventually passed to the project.registerNotifier() function
    #     (with cls converted to cls.className). Please see the Project.registerNotifier
    #     documentation for a precise parameter description
    #
    #     Note that these notifiers are NOT cleared once set up.
    #     """
    #
    #     # CCPNINTERNAL - used in top level class definitions, Current (ONLY)
    #
    #     # NB _coreNotifiers is a class attribute of AbstractWrapperObject
    #     # So all tuples are appended to the same list, living in AbstractWrapperObject
    #     cls._coreNotifiers.append((cls.className, target, func, parameterDict, onceOnly))

    # def _finaliseRename(self):
    #   """Reset internal attributes after values determining PID have changed
    #   """
    #
    #   # reset id
    #   project = self._project
    #   oldId = self._id
    #   parent = self._parent
    #   if parent is None:
    #     _id = ''
    #   elif parent is project:
    #     _id = str(self._key)
    #   else:
    #     _id = '%s%s%s'% (parent._id, Pid.IDSEP, self._key)
    #   self._id = _id
    #
    #   # update pid:object mapping dictionary
    #   dd = project._pid2Obj[self.className]
    #   del dd[oldId]
    #   dd[_id] = self

    # def _finaliseRelatedObjectFromRename(self, oldPid, pathToObject: str, action: str):
    #     """Finalise related objects after rename
    #     Alternative to _finaliseRelatedObject for calling from rename notifier.
    #     """
    #     target = operator.attrgetter(pathToObject)(self)
    #     if not target:
    #         pass
    #     elif isinstance(target, AbstractWrapperObject):
    #         target._finaliseAction(action)
    #     else:
    #         # This must be an iterable
    #         for obj in target:
    #             obj._finaliseAction(action)
    #
    # def _finaliseRelatedObject(self, pathToObject: str, action: str):
    #     """ Finalise 'action' type notifiers for getattribute(pathToObject)(self)
    #     pathToObject is a navigation path (may contain dots) and must yield an object
    #     or an iterable of objects. Can NOT be called from a rename notifier"""
    #
    #     target = operator.attrgetter(pathToObject)(self)
    #     if not target:
    #         pass
    #     elif isinstance(target, AbstractWrapperObject):
    #         target._finaliseAction(action)
    #     else:
    #         # This must be an iterable
    #         for obj in target:
    #             obj._finaliseAction(action)

    def _finaliseAction(self, action: str):
        """Do wrapper level finalisation, and execute all notifiers

        action is one of: 'create', 'delete', 'change', 'rename'"""

        project = self.project
        if project._notificationBlanking:
            return

        className = self.className
        # NB 'AbstractWrapperObject' not currently in use (Sep 2016), but kept for future needs
        iterator = (project._context2Notifiers.setdefault((name, action), OrderedDict())
                    for name in (className, 'AbstractWrapperObject'))
        pendingNotifications = project._pendingNotifications

        #EJB 20181217: test for preDelete
        #       required for some table updates that need to ignore cell contents that
        #       are about to be deleted.
        #       e.g. deleting an nmrAtom from nmrResidue - 'delete' fired but nmrAtom still exists
        #       so the row update must be able to ignore 'deleted' nmrAtoms
        if action == 'delete':
            self._flaggedForDelete = True
        else:
            self._flaggedForDelete = False

        if action == 'rename':
            # Special case

            oldPid = self.pid

            # Wrapper-level processing
            self._resetIds()

            # Call notifiers with special signature
            if project._notificationSuspension:
                for dd in iterator:
                    for notifier, onceOnly in dd.items():
                        pendingNotifications.append((notifier, onceOnly, self, oldPid))
            else:
                for dd in iterator:
                    for notifier in tuple(dd):
                        notifier(self, oldPid)

            for obj in self._getDirectChildren():
                obj._finaliseAction('rename')

        else:
            # Normal case - just call notifiers
            if project._notificationSuspension and action != 'delete':
                # NB Deletion notifiers must currently be executed immediately
                for dd in iterator:
                    for notifier, onceOnly in dd.items():
                        pendingNotifications.append((notifier, onceOnly, self))
            else:
                for dd in iterator:
                    for notifier in tuple(dd):
                        notifier(self)

    def _validateName(self, value: str, attribName: str = None, allowWhitespace: bool = False, allowEmpty: bool = False, allowNone: bool = False):
        attrib = attribName if attribName else self.className
        if value is not None:
            if not isinstance(value, str):
                raise TypeError("%s name must be a string" % attrib)
            if not value and not allowEmpty:
                raise ValueError("%s name must be set" % attrib)
            if Pid.altCharacter in value:
                raise ValueError("Character %s not allowed in %s name" % (Pid.altCharacter, attrib))
            if not allowWhitespace and commonUtil.contains_whitespace(value):
                raise ValueError("whitespace not allowed in %s name" % attrib)
        elif not allowNone:
            raise ValueError("None not allowed in %s name" % attrib)

        previous = self.getByRelativeId(value)
        if previous not in (None, self):
            raise ValueError("%s already exists" % previous.longPid)

        # will only get here if all the tests pass
        return True

    def resetSerial(self, newSerial: int):
        """ADVANCED Reset serial of object to newSerial, resetting parent link
        and the nextSerial of the parent.

        Raises ValueError for objects that do not have a serial
        (or, more precisely, where the _wrappedData does not have a serial)."""

        commonUtil.resetSerial(self._wrappedData, newSerial)
        self._resetIds()

    def getAsDict(self, _includePrivate=False) -> OrderedDict:
        """
        :return: Ordered dictionary of all class properties and their values. Key= str of property Value=any
        """
        od = OrderedDict()
        for i in dir(self):
            try: # deals with badly set property which will raise an error instead of returning an attribute.
                att = getattr(self, i)
                if not callable(att):
                    if _includePrivate:
                            od[i] = att
                    else:
                        if not i.startswith('_'):
                            od[i] = att
            except Exception as e:
                getLogger().warn('Potential error for the property %s in creating dictionary from object: %s . Error: %s'  % (i, self, e))
        return od

    # def _startCommandEchoBlock(self, funcName, *params, values=None, defaults=None, parName=None, propertySetter=False,
    #                            quiet=False):
    #     """Start block for command echoing, set undo waypoint, and echo command to ui and logger
    #
    #     *params, values, and defaults are used by coreUtil.commandParameterString to set the function
    #     parameter string - see the documentation of commandParameterString for details
    #     """
    #
    #     # if not hasattr(self, 'blockindent'):
    #     #   self.blockindent = 1
    #     # getLogger().info('.'*self.blockindent+'>>>start_'+str(funcName))
    #     # self.blockindent+=4
    #
    #     #CCPNINTERNAL
    #
    #     project = self._project
    #
    #     parameterString = coreUtil.commandParameterString(*params, values=values, defaults=defaults)
    #
    #     if self is project:
    #         if propertySetter:
    #             if parameterString:
    #                 command = "project.%s = %s" % (funcName, parameterString)
    #             else:
    #                 command = "project.%s" % funcName
    #         else:
    #             command = "project.%s(%s)" % (funcName, parameterString)
    #     else:
    #         if propertySetter:
    #             if parameterString:
    #                 command = "project.getByPid('%s').%s = %s" % (self.pid, funcName, parameterString)
    #             else:
    #                 command = "project.getByPid('%s').%s" % (self.pid, funcName)
    #         else:
    #             command = "project.getByPid('%s').%s(%s)" % (self.pid, funcName, parameterString)
    #
    #     if parName:
    #         command = ''.join((parName, ' = ', command))
    #
    #     project._appBase._startCommandBlock(command, quiet=quiet)

    # def _endCommandEchoBlock(self):
    #     """End block for command echoing"""
    #     # self.blockindent-=4
    #     # if self.blockindent<0:
    #     #   print ('****')
    #     #   self.blockindent=0
    #     # getLogger().info('..'+'.'*self.blockindent+'>>>end_')
    #
    #     self._project._appBase._endCommandBlock()


AbstractWrapperObject.getByPid.__annotations__['return'] = AbstractWrapperObject
