"""General undo handle supporting undo/redo stack

PyApiGen.py inserts the following line:

from ccpn.core.lib.Undo import _deleteAllApiObjects, restoreOriginalLinks, no_op

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
__dateModified__ = "$dateModified: 2020-01-28 09:52:39 +0000 (Tue, January 28, 2020) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial, update_wrapper
from collections import deque
from ccpn.util.Logging import getLogger
from enum import Enum

MAXUNDOWAYPOINTS = 25
MAXUNDOOPERATIONS = 10000


def _deleteAllApiObjects(objsToBeDeleted):
    """Delete all API objects in collection, together.
    Does NOT look for additional deletes or do any checks. Programmer beware!!!
    Does NOT do undo handling, as it is designed to be used within the Undo machinery
    """

    # CCPNINTERNAL
    # NBNB Use with EXTREME CARE, and make sure you get ALL API objects being created

    for obj in objsToBeDeleted:
        if (obj.__dict__.get('isDeleted')):
            raise ValueError("""%s: _deleteAllApiObjects
       called on deleted object""" % obj.qualifiedName
                             )

    for obj in objsToBeDeleted:
        for notify in obj.__class__._notifies.get('preDelete', ()):
            notify(obj)

    for obj in objsToBeDeleted:
        # objsToBeDeleted is passed in so that the references to the children of object are severed
        obj._singleDelete(objsToBeDeleted)

    # do Notifiers
    for obj in objsToBeDeleted:
        for notify in obj.__class__._notifies.get('delete', ()):
            notify(obj)


def restoreOriginalLinks(obj2Value, linkName):
    """Set obj values using obj2Value dictionary"""
    for obj, val in obj2Value.items():
        setattr(obj, linkName, val)


def no_op():
    """Does nothing - for special undo situations where only one direction must act"""
    return


def resetUndo(memopsRoot, maxWaypoints=MAXUNDOWAYPOINTS, maxOperations=MAXUNDOOPERATIONS,
              debug: bool = False, application=None):
    """Set or reset undo stack, using passed-in parameters.
    NB setting either parameter to 0 removes the undo stack."""

    undo = memopsRoot._undo
    if undo is not None:
        undo.clear()

    if maxWaypoints and maxOperations:
        memopsRoot._undo = Undo(maxWaypoints=maxWaypoints, maxOperations=maxOperations,
                                debug=debug, application=application)
    else:
        memopsRoot._undo = None

class UndoEvents(Enum):
    UNDO_UNDO=1
    UNDO_REDO=2
    UNDO_CLEAR=3
    UNDO_ADD=4
    UNDO_MARK_SAVE=5
    UNDO_MARK_CLEAN=6

class Observer():

    def __init__(self):
        self._callbacks = set()

    def add(self,callback):
        self._callbacks.add(callback)

    def clear(self):
        self._callbacks.clear()

    def remove(self,callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def call(self,action):
        for callback in self._callbacks:
            action(callback)

class Undo(deque):
    """Implementation of an undo and redo stack, with possibility of waypoints.
       A waypoint is the level at which an undo happens, and each of them could
       consist of multiple individual undo operations.

       To create a waypoint use newWaypoint().
    """

    # TODO: get rid of debug and use logging function instead
    def __init__(self, maxWaypoints=MAXUNDOWAYPOINTS, maxOperations=MAXUNDOOPERATIONS, debug=False, application=None):
        """Create Undo object with maximum stack length maxUndoCount"""

        self.maxWaypoints = maxWaypoints
        self.maxOperations = maxOperations
        self.nextIndex = 0  # points to next free slot (or first slot to redo)
        self.waypoints = []  # array of last item in each waypoint
        self._blocked = False  # Block/unblock switch - internal use only
        self._undoItemBlockingLevel = 0  # Blocking level - modify with increase/decreaseBlocking only
        self._waypointBlockingLevel = 0  # Waypoint blocking - modify with increase/decreaseWaypointBlocking/ only
        self._newItemCount = 0  # the number of new items that have been added since the last new waypoint
        self._itemAtLastSave = None
        self._stackCleared =  False
        self._lastEventMarkClean = False
        self.undoChanged =  Observer()

        if maxWaypoints:
            self.newWaypoint()  # DO NOT CHANGE THIS ONE
        deque.__init__(self)

        # Reset to True to unblank errors during undo/redo
        self._debug = debug
        self.application = application

    @property
    def undoItemBlocking(self):
        """Undo blocking. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""
        return self._undoItemBlockingLevel > 0

    @property
    def undoItemBlockingLevel(self):
        """Undo blocking Level. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""

        # needed for a single occurrence in api
        return self._undoItemBlockingLevel

    #GST to ejb is this a good way to do it?
    def markSave(self):
        if len(self) > 0:
            lastItem = self.nextIndex-1
            self._itemAtLastSave =  self[lastItem]
        self._stackCleared = False
        self._lastEventMarkClean = True
        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_MARK_SAVE))

    def isDirty(self):
        result = False

        lastItem = self.nextIndex-1

        if self._stackCleared:
            result = True
        elif len(self) > 0 and (self._itemAtLastSave == None):
            result = True
        elif len(self) > 0 and lastItem > 0 and (self[lastItem] != self._itemAtLastSave):
            result = True
            result = True
        return result

    def markClean(self):
        self._itemAtSave = None
        self._stackCleared = False
        self._lastEventMarkClean = True
        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_MARK_CLEAN))

    def increaseBlocking(self):
        """Set one more level of blocking"""
        self._undoItemBlockingLevel += 1

    def decreaseBlocking(self):
        """Reduce level of blocking - when level reaches zero, undo is unblocked"""
        if self._undoItemBlockingLevel > 0:
            self._undoItemBlockingLevel -= 1

    @property
    def undoList(self):
        try:
            undoState = (self.maxWaypoints,
                         self.maxOperations,
                         self.nextIndex,
                         self.waypoints,
                         self._blocked,
                         self.undoItemBlocking,
                         len(self),
                         self._newItemCount,
                         self[-1],
                         [(undoFunc[0].__name__, undoFunc[1].__name__) for undoFunc in self],
                         [undoFunc[0].__name__ for undoFunc in self],
                         [undoFunc[1].__name__ for undoFunc in self])
        except:
            undoState = (self.maxWaypoints,
                         self.maxOperations,
                         self.nextIndex,
                         self.waypoints,
                         self._blocked,
                         self.undoItemBlocking,
                         len(self),
                         self._newItemCount,
                         None, None, None, None)
        return undoState

    @property
    def waypointBlocking(self):
        """Undo blocking. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""
        return self._waypointBlockingLevel > 0

    def increaseWaypointBlocking(self):
        """Set one more level of blocking"""
        self._waypointBlockingLevel += 1

    def decreaseWaypointBlocking(self):
        """Reduce level of blocking - when level reaches zero, undo is unblocked"""
        if self.waypointBlocking:
            self._waypointBlockingLevel -= 1

    def newWaypoint(self):
        """Start new waypoint
        """
        if self.maxWaypoints < 1:
            raise ValueError("Attempt to set waypoint on Undo object that does not allow them")

        waypoints = self.waypoints

        if self._blocked or self._undoItemBlockingLevel or self.waypointBlocking:  # ejb - added self._blocked 9/6/17
            return

        # set the number of items added to the undo deque since the new waypoint was created
        self._newItemCount = 0

        if self.nextIndex < 1:
            return

        if waypoints and waypoints[-1] == self.nextIndex - 1:  # don't need to add a new waypoint
            return  # if is the same as the last one

        waypoints.append(self.nextIndex - 1)  # add the new waypoint to the end

        # if the list is too big then cull the first item
        if len(waypoints) > self.maxWaypoints:
            nRemove = waypoints[0]
            self.nextIndex -= nRemove
            for ii in range(nRemove):
                _popLeftItem = self.popleft()

            del waypoints[0]
            for ii, junk in enumerate(waypoints):
                waypoints[ii] -= nRemove


    def _wrappedPartial(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func

    def _newItem(self, undoPartial=None, redoPartial=None):
        """Add predefined partial(*) item to the undo stack.
        """
        if self._blocked or self._undoItemBlockingLevel:
            return

        if self._debug:
            getLogger().debug('undo._newItem %s %s %s' % (self.undoItemBlocking, undoPartial,
                                                          redoPartial))

        # clear out redos that are no longer going to be doable
        for n in range(len(self) - self.nextIndex):
            self.pop()

        # add new undo/redo methods to the deque - keep a count
        self.append((undoPartial, redoPartial))
        self._newItemCount += 1

        # fix waypoints:
        ll = self.waypoints
        while ll and ll[-1] >= self.nextIndex:
            ll.pop()

        # correct for maxOperations
        if len(self) > self.maxOperations:
            self.popleft()
            ll = self.waypoints
            if ll:
                for n, val in enumerate(ll):
                    ll[n] = val - 1
                if ll[0] < 0:
                    del ll[0]
        else:
            self.nextIndex += 1

        self._lastEventMarkClean = False
        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_ADD))

    def newItem(self, undoMethod, redoMethod, undoArgs=None, undoKwargs=None,
                redoArgs=None, redoKwargs=None):
        """Add item to the undo stack.
        """
        if self._blocked or self._undoItemBlockingLevel:
            return

        if self._debug:
            getLogger().debug('undo.newItem %s %s %s %s %s %s %s' % (self.undoItemBlocking, undoMethod,
                                                                     redoMethod, undoArgs,
                                                                     undoKwargs, redoArgs,
                                                                     redoKwargs))

        if not undoArgs:
            undoArgs = ()
        if not redoArgs:
            redoArgs = ()

        # clear out redos that are no longer going to be doable
        for n in range(len(self) - self.nextIndex):
            self.pop()

        # add new data
        if undoKwargs is None:
            undoCall = self._wrappedPartial(undoMethod, *undoArgs)
        else:
            undoCall = self._wrappedPartial(undoMethod, *undoArgs, **undoKwargs)
        if redoKwargs is None:
            redoCall = self._wrappedPartial(redoMethod, *redoArgs)
        else:
            redoCall = self._wrappedPartial(redoMethod, *redoArgs, **redoKwargs)

        # add new undo/redo methods to the deque - keep a count
        newItem = (undoCall, redoCall)
        self.append(newItem)
        self._newItemCount += 1

        # fix waypoints:
        ll = self.waypoints
        while ll and ll[-1] >= self.nextIndex:
            ll.pop()

        # correct for maxOperations
        if len(self) > self.maxOperations:
            self.popleft()
            ll = self.waypoints
            if ll:
                for n, val in enumerate(ll):
                    ll[n] = val - 1
                if ll[0] < 0:
                    del ll[0]
        else:
            self.nextIndex += 1


        #GST hack to get round bug
        #GST when extra
        #badKeys = ('includePositiveContours', 'includeNegativeContours', 'spectrumAliasing')
        #badKeys = tuple(sorted(badKeys))

        #testKeys = undoArgs[0].keys()
        #testKeys = tuple(sorted(testKeys))
        if self._lastEventMarkClean: #and testKeys != badKeys:
            self.undoChanged.call(lambda x : x(UndoEvents.UNDO_ADD))
        else:
            self.markSave()


    def undo(self):
        """Undo one operation - or one waypoint if waypoints are set

        For now errors are handled by printing a warning and clearing the undo object
        """

        # TBD: what should we do if undoMethod() throws an exception?

        if self.nextIndex == 0:
            return

        elif self.maxWaypoints:
            undoTo = -1
            for val in self.waypoints:
                if val < self.nextIndex - 1:
                    undoTo = val
                else:
                    break

        else:
            undoTo = max(self.nextIndex - 2, -1)

        # block addition of items while operating
        self._blocked = True
        from ccpn.core.lib.ContextManagers import undoBlock

        try:
            with undoBlock():
                undoCall = redoCall = None
                for n in range(self.nextIndex - 1, undoTo, -1):
                    undoCall, redoCall = self[n]

                    if undoCall:
                        undoCall()
                self.nextIndex = undoTo + 1

        except Exception as e:
            from ccpn.util.Logging import getLogger

            getLogger().warning("Error while undoing (%s). Undo stack is cleared." % e)
            if self._debug:
                print("UNDO DEBUG: error in undo. Last undo function was:", undoCall)
                raise
            self._stackCleared()
            self.clear()
        finally:
            # Added by Rasmus March 2015. Surely we need to reset self._blocked?
            self._blocked = False

        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_UNDO))

    def redo(self):
        """Redo one waypoint - or one operation if waypoints are not set.

        For now errors are handled by printing a warning and clearing the undo object
        """

        if self.nextIndex >= len(self):
            return

        elif self.maxWaypoints:
            redoTo = len(self) - 1
            for val in reversed(self.waypoints):
                if val >= self.nextIndex:
                    redoTo = val
                else:
                    break

        else:
            redoTo = min(self.nextIndex, len(self))

        # block addition of items while operating
        self._blocked = True
        from ccpn.core.lib.ContextManagers import undoBlock

        try:
            with undoBlock():
                for n in range(self.nextIndex, redoTo + 1):
                    undoCall, redoCall = self[n]

                    if redoCall:
                        redoCall()
                self.nextIndex = redoTo + 1

        except Exception as e:
            from ccpn.util.Logging import getLogger

            getLogger().warning("Error while redoing (%s). Undo stack is cleared." % e)
            if self._debug:
                print("REDO DEBUG: error in redo. Last redo call was:", redoCall)
                raise
            self._stackCleared()
            self.clear()
        finally:
            # Added by Rasmus March 2015. Surely we need to reset self._blocked?
            self._blocked = False

        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_REDO))

    def clear(self):
        """Clear and reset undo object
        """
        self.nextIndex = 0
        self.waypoints.clear()
        self._blocked = False
        self._undoItemBlockingLevel = 0
        deque.clear(self)
        self.markClean()
        self.undoChanged.call(lambda x : x(UndoEvents.UNDO_CLEAR))

    def canUndo(self) -> bool:
        """True if an undo operation can be performed
        """
        return self.nextIndex > 0

    def canRedo(self) -> bool:
        """True if a redo operation can be performed
        """
        return self.nextIndex < len(self)

    def numItems(self):
        """Return the number of undo items currently on the undo deque
        """
        return len(self)

    @property
    def newItemsAdded(self):
        """Return the number of new items that have been added to the undo deque since
        the last new waypoint was created
        """
        return self._newItemCount

    def clearRedoItems(self):
        """Clear the items above the current next index, if there has been an error adding items
        """
        # remove unwanted items from the top of the undo deque
        while len(self) > self.nextIndex:
            self.pop()

        # fix waypoints - remove any that are left beyond the new end of the undo deque:
        ll = self.waypoints
        while ll and ll[-1] >= self.nextIndex - 1:
            ll.pop()

        self._newItemCount = 0
