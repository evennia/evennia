# MIT Licensed
# Copyright (c) 2009-2010 Peter Shinners <pete@shinners.org> 
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

"""
This module intends to be a full featured replacement for Python's reload
function. It is targeted towards making a reload that works for Python
plugins and extensions used by longer running applications.

Reimport currently supports Python 2.4 through 2.6.

By its very nature, this is not a completely solvable problem. The goal of
this module is to make the most common sorts of updates work well. It also
allows individual modules and package to assist in the process. A more
detailed description of what happens is at
http://code.google.com/p/reimport .
"""


__all__ = ["reimport", "modified"]


import sys
import os
import gc
import inspect
import weakref
import traceback
import time



__version__ = "1.2"
__author__ = "Peter Shinners <pete@shinners.org>"
__license__ = "MIT"
__url__ = "http://code.google.com/p/reimport"



_previous_scan_time = time.time() - 1.0
_module_timestamps = {}


# find the 'instance' old style type
class _OldClass: pass
_InstanceType = type(_OldClass())
del _OldClass



def reimport(*modules):
    """Reimport python modules. Multiple modules can be passed either by
        name or by reference. Only pure python modules can be reimported.
        
        For advanced control, global variables can be placed in modules
        that allows finer control of the reimport process.
        
        If a package module has a true value for "__package_reimport__"
        then that entire package will be reimported when any of its children
        packages or modules are reimported.
        
        If a package module defines __reimported__ it must be a callable
        function that accepts one argument and returns a bool. The argument
        is the reference to the old version of that module before any
        cleanup has happend. The function should normally return True to
        allow the standard reimport cleanup. If the function returns false
        then cleanup will be disabled for only that module. Any exceptions
        raised during the callback will be handled by traceback.print_exc,
        similar to what happens with tracebacks in the __del__ method.
        """
    __internal_swaprefs_ignore__ = "reimport"
    reloadSet = set()

    if not modules:
        return

    # Get names of all modules being reloaded
    for module in modules:
        name, target = _find_exact_target(module)
        if not target:
            raise ValueError("Module %r not found" % module)
        if not _is_code_module(target):
            raise ValueError("Cannot reimport extension, %r" % name)

        reloadSet.update(_find_reloading_modules(name))

    # Sort module names 
    reloadNames = _package_depth_sort(reloadSet, False)

    # Check for SyntaxErrors ahead of time. This won't catch all
    # possible SyntaxErrors or any other ImportErrors. But these
    # should be the most common problems, and now is the cleanest
    # time to abort.
    # I know this gets compiled again anyways. It could be
    # avoided with py_compile, but I will not be the creator
    # of messy .pyc files!
    for name in reloadNames:
        filename = getattr(sys.modules[name], "__file__", None)
        if not filename:
            continue
        pyname = os.path.splitext(filename)[0] + ".py"
        try:
            data = open(pyname, "rU").read() + "\n"
        except (IOError, OSError):
            continue
        
        compile(data, pyname, "exec", 0, False)  # Let this raise exceptions

    # Move modules out of sys
    oldModules = {}
    for name in reloadNames:
        oldModules[name] = sys.modules.pop(name)
    ignores = (id(oldModules), id(__builtins__))
    prevNames = set(sys.modules)

    # Python will munge the parent package on import. Remember original value
    parentPackageName = name.rsplit(".", 1)
    parentPackage = None
    parentPackageDeleted = lambda: None
    if len(parentPackageName) == 2:
        parentPackage = sys.modules.get(parentPackageName[0], None)
        parentValue = getattr(parentPackage, parentPackageName[1], parentPackageDeleted)

    # Reimport modules, trying to rollback on exceptions
    try:
        for name in reloadNames:
            if name not in sys.modules:
                __import__(name)

    except StandardError:
        # Try to dissolve any newly import modules and revive the old ones
        newNames = set(sys.modules) - prevNames
        newNames = _package_depth_sort(newNames, True)
        for name in newNames:
            _unimport_module(sys.modules[name], ignores)
            assert name not in sys.modules

        sys.modules.update(oldModules)
        raise

    newNames = set(sys.modules) - prevNames
    newNames = _package_depth_sort(newNames, True)

    # Update timestamps for loaded time
    now = time.time() - 1.0
    for name in newNames:
        _module_timestamps[name] = (now, True)

    # Fix Python automatically shoving of children into parent packages
    if parentPackage and parentValue:
        if parentValue == parentPackageDeleted:
            delattr(parentPackage, parentPackageName[1])
        else:
            setattr(parentPackage, parentPackageName[1], parentValue)
    parentValue = parentPackage = parentPackageDeleted = None 

    # Push exported namespaces into parent packages
    pushSymbols = {}
    for name in newNames:
        oldModule = oldModules.get(name)
        if not oldModule:
            continue
        parents = _find_parent_importers(name, oldModule, newNames)
        pushSymbols[name] = parents
    for name, parents in pushSymbols.iteritems():
        for parent in parents:
            oldModule = oldModules[name]
            newModule = sys.modules[name]
            _push_imported_symbols(newModule, oldModule, parent)
    # Rejigger the universe
    for name in newNames:
        old = oldModules.get(name)
        if not old:
            continue
        new = sys.modules[name]
        rejigger = True
        reimported = getattr(new, "__reimported__", None)
        if reimported:
            try:
                rejigger = reimported(old)
            except StandardError:
                # What else can we do? the callbacks must go on
                # Note, this is same as __del__ behaviour. /shrug
                traceback.print_exc()

        if rejigger:
            _rejigger_module(old, new, ignores)
        else:
            _unimport_module(new, ignores)



def modified(path=None):
    """Find loaded modules that have changed on disk under the given path.
        If no path is given then all modules are searched.
        """
    global _previous_scan_time
    modules = []
    
    if path:
        path = os.path.normpath(path) + os.sep
        
    defaultTime = (_previous_scan_time, False)
    pycExt = __debug__ and ".pyc" or ".pyo"
    
    for name, module in sys.modules.items():
        filename = _is_code_module(module)
        if not filename:
            continue

        filename = os.path.normpath(filename)
        prevTime, prevScan = _module_timestamps.setdefault(name, defaultTime)
        if path and not filename.startswith(path):
            continue

        # Get timestamp of .pyc if this is first time checking this module
        if not prevScan:
            pycName = os.path.splitext(filename)[0] + pycExt
            if pycName != filename:
                try:
                    prevTime = os.path.getmtime(pycName)
                except OSError:
                    pass
            _module_timestamps[name] = (prevTime, True)

        # Get timestamp of source file
        try:
            diskTime = os.path.getmtime(filename)
        except OSError:
            diskTime = None
                
        if diskTime is not None and prevTime < diskTime:
            modules.append(name)

    _previous_scan_time = time.time()
    return modules



def _is_code_module(module):
    """Determine if a module comes from python code"""
    # getsourcefile will not return "bare" pyc modules. we can reload those?
    try:
        return inspect.getsourcefile(module) or ""
    except TypeError:
        return ""



def _find_exact_target(module):
    """Given a module name or object, find the
            base module where reimport will happen."""
    # Given a name or a module, find both the name and the module
    actualModule = sys.modules.get(module)
    if actualModule is not None:
        name = module
    else:
        for name, mod in sys.modules.iteritems():
            if mod is module:
                actualModule = module
                break
        else:
            return "", None

    # Find highest level parent package that has package_reimport magic
    parentName = name
    while True:
        splitName = parentName.rsplit(".", 1)
        if len(splitName) <= 1:
            return name, actualModule
        parentName = splitName[0]
        
        parentModule = sys.modules.get(parentName)
        if getattr(parentModule, "__package_reimport__", None):
            name = parentName
            actualModule = parentModule



def _find_reloading_modules(name):
    """Find all modules that will be reloaded from given name"""
    modules = [name]
    childNames = name + "."
    for name in sys.modules.keys():
        if name.startswith(childNames) and _is_code_module(sys.modules[name]):
            modules.append(name)
    return modules



def _package_depth_sort(names, reverse):
    """Sort a list of module names by their package depth"""
    def packageDepth(name):
        return name.count(".")
    return sorted(names, key=packageDepth, reverse=reverse)



def _find_module_exports(module):
    allNames = getattr(module, "__all__", ())
    if not allNames:
        allNames = [n for n in dir(module) if n[0] != "_"]
    return set(allNames)



def _find_parent_importers(name, oldModule, newNames):
    """Find parents of reimported module that have all exported symbols"""
    parents = []

    # Get exported symbols
    exports = _find_module_exports(oldModule)
    if not exports:
        return parents

    # Find non-reimported parents that have all old symbols
    parent = name
    while True:
        names = parent.rsplit(".", 1)
        if len(names) <= 1:
            break
        parent = names[0]
        if parent in newNames:
            continue
        parentModule = sys.modules[parent]
        if not exports - set(dir(parentModule)):
            parents.append(parentModule)
    
    return parents


def _push_imported_symbols(newModule, oldModule, parent):
    """Transfer changes symbols from a child module to a parent package"""
    # This assumes everything in oldModule is already found in parent
    oldExports = _find_module_exports(oldModule)
    newExports = _find_module_exports(newModule)

    # Delete missing symbols
    for name in oldExports - newExports:
        delattr(parent, name)
    
    # Add new symbols
    for name in newExports - oldExports:
        setattr(parent, name, getattr(newModule, name))
    
    # Update existing symbols
    for name in newExports & oldExports:
        oldValue = getattr(oldModule, name)
        if getattr(parent, name) is oldValue:
            setattr(parent, name, getattr(newModule, name))
    


# To rejigger is to copy internal values from new to old
# and then to swap external references from old to new


def _rejigger_module(old, new, ignores):
    """Mighty morphin power modules"""
    __internal_swaprefs_ignore__ = "rejigger_module"
    oldVars = vars(old)
    newVars = vars(new)
    ignores += (id(oldVars),)
    old.__doc__ = new.__doc__

    # Get filename used by python code
    filename = new.__file__

    for name, value in newVars.iteritems():
        if name in oldVars:
            oldValue = oldVars[name]
            if oldValue is value:
                continue

            if _from_file(filename, value):
                if inspect.isclass(value):
                    _rejigger_class(oldValue, value, ignores)
                    
                elif inspect.isfunction(value):
                    _rejigger_func(oldValue, value, ignores)
        
        setattr(old, name, value)

    for name in oldVars.keys():
        if name not in newVars:
            value = getattr(old, name)
            delattr(old, name)
            if _from_file(filename, value):
                if inspect.isclass(value) or inspect.isfunction(value):
                    _remove_refs(value, ignores)
    
    _swap_refs(old, new, ignores)



def _from_file(filename, value):
    """Test if object came from a filename, works for pyc/py confusion"""
    try:
        objfile = inspect.getsourcefile(value)
    except TypeError:
        return False
    return bool(objfile) and objfile.startswith(filename)



def _rejigger_class(old, new, ignores):
    """Mighty morphin power classes"""
    __internal_swaprefs_ignore__ = "rejigger_class"    
    oldVars = vars(old)
    newVars = vars(new)
    ignores += (id(oldVars),)    

    for name, value in newVars.iteritems():
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if name in oldVars:
            oldValue = oldVars[name]
            if oldValue is value:
                continue

            if inspect.isclass(value) and value.__module__ == new.__module__:
                _rejigger_class(oldValue, value, ignores)
            
            elif inspect.isfunction(value):
                _rejigger_func(oldValue, value, ignores)

        setattr(old, name, value)
    
    for name in oldVars.keys():
        if name not in newVars:
            value = getattr(old, name)
            delattr(old, name)
            _remove_refs(value, ignores)

    _swap_refs(old, new, ignores)



def _rejigger_func(old, new, ignores):
    """Mighty morphin power functions"""
    __internal_swaprefs_ignore__ = "rejigger_func"    
    old.func_code = new.func_code
    old.func_doc = new.func_doc
    old.func_defaults = new.func_defaults
    old.func_dict = new.func_dict
    _swap_refs(old, new, ignores)



def _unimport_module(old, ignores):
    """Remove traces of a module"""
    __internal_swaprefs_ignore__ = "unimport_module"
    oldValues = vars(old).values()
    ignores += (id(oldValues),)    

    # Get filename used by python code
    filename = old.__file__
    fileext = os.path.splitext(filename)
    if fileext in (".pyo", ".pyc", ".pyw"):
        filename = filename[:-1]

    for value in oldValues:
        try: objfile = inspect.getsourcefile(value)
        except TypeError: objfile = ""
        
        if objfile == filename:
            if inspect.isclass(value):
                _unimport_class(value, ignores)
                
            elif inspect.isfunction(value):
                _remove_refs(value, ignores)

    _remove_refs(old, ignores)



def _unimport_class(old, ignores):
    """Remove traces of a class"""
    __internal_swaprefs_ignore__ = "unimport_class"    
    oldItems = vars(old).items()
    ignores += (id(oldItems),)    

    for name, value in oldItems:
        if name in ("__dict__", "__doc__", "__weakref__"):
            continue

        if inspect.isclass(value) and value.__module__ == old.__module__:
            _unimport_class(value, ignores)
            
        elif inspect.isfunction(value):
            _remove_refs(value, ignores)

    _remove_refs(old, ignores)



_recursive_tuple_swap = set()


def _bonus_containers():
    """Find additional container types, if they are loaded. Returns
        (deque, defaultdict).
        Any of these will be None if not loaded. 
        """
    deque = defaultdict = None
    collections = sys.modules.get("collections", None)
    if collections:
        deque = getattr(collections, "collections", None)
        defaultdict = getattr(collections, "defaultdict", None)
    return deque, defaultdict



def _find_sequence_indices(container, value):
    """Find indices of value in container. The indices will
        be in reverse order, to allow safe editing.
        """
    indices = []
    for i in range(len(container)-1, -1, -1):
        if container[i] is value:
            indices.append(i)
    return indices


def _swap_refs(old, new, ignores):
    """Swap references from one object to another"""
    __internal_swaprefs_ignore__ = "swap_refs"    
    # Swap weak references
    refs = weakref.getweakrefs(old)
    if refs:
        try:
            newRef = weakref.ref(new)
        except ValueError:
            pass
        else:
            for oldRef in refs:
                _swap_refs(oldRef, newRef, ignores + (id(refs),))
    del refs

    deque, defaultdict = _bonus_containers()

    # Swap through garbage collector
    referrers = gc.get_referrers(old)
    for container in referrers:
        if id(container) in ignores:
            continue
        containerType = type(container)
        
        if containerType is list or containerType is deque:
            for index in _find_sequence_indices(container, old):
                container[index] = new
        
        elif containerType is tuple:
            # protect from recursive tuples
            orig = container
            if id(orig) in _recursive_tuple_swap:
                continue
            _recursive_tuple_swap.add(id(orig))
            try:
                container = list(container)
                for index in _find_sequence_indices(container, old):
                    container[index] = new
                container = tuple(container)
                _swap_refs(orig, container, ignores + (id(referrers),))
            finally:
                _recursive_tuple_swap.remove(id(orig))
        
        elif containerType is dict or containerType is defaultdict:
            if "__internal_swaprefs_ignore__" not in container:
                try:
                    if old in container:
                        container[new] = container.pop(old)
                except TypeError:  # Unhashable old value
                    pass
                for k,v in container.iteritems():
                    if v is old:
                        container[k] = new

        elif containerType is set:
            container.remove(old)
            container.add(new)

        elif containerType is type:
            if old in container.__bases__:
                bases = list(container.__bases__)
                bases[bases.index(old)] = new
                container.__bases__ = tuple(bases)
        
        elif type(container) is old:
            container.__class__ = new
        
        elif containerType is _InstanceType:
            if container.__class__ is old:
                container.__class__ = new

       

def _remove_refs(old, ignores):
    """Remove references to a discontinued object"""
    __internal_swaprefs_ignore__ = "remove_refs"
    
    # Ignore builtin immutables that keep no other references
    if old is None or isinstance(old, (int, basestring, float, complex)):
        return

    deque, defaultdict = _bonus_containers()
    
    # Remove through garbage collector
    for container in gc.get_referrers(old):
        if id(container) in ignores:
            continue
        containerType = type(container)

        if containerType is list or containerType is deque:
            for index in _find_sequence_indices(container, old):
                del container[index]
        
        elif containerType is tuple:
            orig = container
            container = list(container)
            for index in _find_sequence_indices(container, old):
                del container[index]
            container = tuple(container)
            _swap_refs(orig, container, ignores)
        
        elif containerType is dict or containerType is defaultdict:
            if "__internal_swaprefs_ignore__" not in container:
                try:
                    container.pop(old, None)
                except TypeError:  # Unhashable old value
                    pass
                for k,v in container.items():
                    if v is old:
                        del container[k]

        elif containerType is set:
            container.remove(old)
