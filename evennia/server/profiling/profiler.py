"""
Evennia memory profiler, whitenoise 2023

This is currently a work in progress and is not ready for production use if you have other
options. This is meant to take on memory profiling alternatives like `memory_profiler`, but
with the ability to understand Evennia more, have a bit more flexibility, and not require a
third-party library for debugging memory issues.

This profiler uses tracemalloc as its backend for memory analysis, and wraps some `gc`
functionality for the user. To use this tool will require some understanding of Python's
internals with regards to allocation and memory management.
"""
import gc
import inspect
import tracemalloc
import linecache
import sys
from datetime import datetime
from functools import wraps

TRASH = [
    tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
    tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
    tracemalloc.Filter(False, "<frozen ntpath>"),
    tracemalloc.Filter(False, "<frozen abc>")
]

KB = 1024
MB = 1024*1024
GB = 1024*1024*1024

def top(snapshot, key_type='lineno', limit=10, precision=1, filters=[], stream=None):
    """
    Gives the top culprits for memory allocation given a tracemalloc snapshot. Additionally,
    linecache is used to provide the file and line that causes the allocation. Frame information
    is used to put into the output where this call is so you know which memory trace you are
    looking at.

    Args:
        snapshot (tracemalloc.Snapshot): The tracemalloc snapshot to analyze.
        key_type (str or 'lineno'): Tracemalloc statistics argument.
        limit (int or 10): Number of tracemalloc stats to go through.
        precision (int or 1): How many decimal places to put on the allocated size.
        filters (list): Can take tracemalloc.Filter objects or strings for common use-cases.
        stream (file or None): Output stream can take a file object or a socket as file.
    """
    # if no stream is provided, we default to sys.stdout everywhere
    if stream is None:
        stream = sys.stdout

    # For the implementation of Python frames, see: 
    # https://github.com/python/cpython/blob/main/Objects/frameobject.c
    # Each thing that goes onto the stack in Python (like function calls)
    # is encapsulated in a PyFrame, or Python Interpreter Frame. This Frame
    # has the information about locals, globals, file, line number, etc, of
    # the code it is executing. We can also time travel back through frames,
    # which we need to do here because calling top() is its own frame, and
    # we want to get the frame that called top().
    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    # always filter trash
    snapshot = snapshot.filter_traces(TRASH)

    # optionally filter other stuff as well
    if len(filters):
        if "filename" in filters:
            snapshot = snapshot.filter_traces([
                tracemalloc.Filter(True, filename_pattern=file)
            ])
        else:
            snapshot = snapshot.filter_traces(filters)

    # get the statistics we are after from tracemalloc
    stats = snapshot.statistics(key_type)

    # write our output
    # TODO: clean this up to use table-like formatting (<:12 stuff)

    # note where this call is coming from via our frame information above
    stream.write("[{}] <{}:{}>\n".format(datetime.now(), file, lineno))
    stream.write("====[ EVENNIA TRACE ]====\n")
    # enumerate the stats object
    for index, stat in enumerate(stats[:limit], 1):
        # each stat has a traceback with frame data
        tb = stat.traceback[0]
        stream.write("#{0}: {1}:{2} {3:.{4}f} KB\n".format(index, tb.filename, tb.lineno, stat.size / KB, precision))
        # linecache, given the frame data, can pull the actual line of code that was interpreted
        # this line caused the allocation
        line = linecache.getline(tb.filename, tb.lineno).strip()
        if line:
            stream.write("\t{}\n".format(line))
    stream.write("\n")

    # since we only grabbled up to limit (:limit), there are probably leftovers
    remaining = stats[limit:]
    if remaining:
        size = sum(stat.size for stat in remaining)
        stream.write("Output truncated at {} lines\n".format(limit))
        stream.write("{} remaining lines: {} KB\n".format(len(remaining), size / 1024))

    # give totals    
    total = sum(stat.size for stat in stats)
    stream.write("Total allocated size: {} KB\n".format(total / 1024))
    stream.write("\n")

def compare(start, end, limit=10, stream=None):
    """
    Compares two tracemalloc.Snapshot objects to find the differences in memory from one
    to the next.

    Args:
        start (tracemalloc.Snapshot): The starting point for the comparison.
        end (tracemalloc.Snapshot): The end point for the comparison.
        limit (int or 10): Number of tracemalloc stats to go through.
        stream (file or None): Output stream can take a file object or a socket as file.
    """
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    stream.write("[{}] <{}:{}>\n".format(datetime.now(), file, lineno))
    stream.write("====[ EVENNIA TRACE COMPARISON ]====\n")

    stats = end.compare_to(start, 'lineno')
    if len(stats) == 0:
        stream.write("NULL\n")
    for stat in stats[:limit]:
        stream.write(stat)
    remaining = stats[limit:]
    if remaining:
        stream.write("Output truncated at {} lines\n".format(limit))
        stream.write("{} remaining lines\n".format(len(remaining)))
    stream.write("\n")

# TODO: Implement required underlying data for compare_all to work without args
def compare_all(snaps, limit=10, stream=None):
    """
    Compares all snapshots given and gives changes over time across the list.

    Args:
        snaps (list): List of tracemalloc.Snapshot objects to compare across time.
        limit (int or 10): Number of tracemalloc stats to go through.
        stream (file or None): Output stream can take a file object or a socket as file.
    """
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    stream.write("[{}] <{}:{}>\n".format(datetime.now(), file, lineno))
    stream.write("====[ EVENNIA TRACE COMPARE_ALL ]====\n")
    first = snaps[0]
    for snap in snaps[1:]:
        stats = snap.compare_to(first, 'lineno')

        for stat in stats[:limit]:
            stream.write(stat)
        remaining = stats[limit:]
        if remaining:
            stream.write("Output truncated at {} lines\n".format(limit))
            stream.write("{} remaining lines\n".format(len(remaining)))

def dprint(input, stream=None):
    """
    Writes a debug message to a stream for additional information while profiling.

    Args:
        input (str): The message you want to write to stream
        stream (file or None): Output stream can take a file object or a socket as file.
    """
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    out = "[{}] {}\nFrom: <{}:{}>\n\n".format(datetime.now(), input, file, lineno)

    stream.write(out)

    del frame

def get_referrers(obj, stream=None, collect=True):
    """
    Gets all referrers to an object and writes them to stream or stdout. Referrers
    are objects that have a "strong reference" to the given object, which will
    prevent it from being labeled as garbage and collected. This ultimately prevents
    the Python memory manager from marking the memory block as 'free' which can
    introduce leaks if referrers are unintentionally left hanging.

    Args:
        obj (object): The Python object to find strong references to.
        stream (file or None): Output stream can take a file object or a socket as file.
        collect (bool or True): Whether or not to run garbage collection prior to getting refs.
    """
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    if collect:
        gc.collect()
    
    referrers = gc.get_referrers(obj)
    stream.write("[{}] <{}:{}>\n".format(datetime.now(), file, lineno))
    stream.write("==== EVENNIA GC GET_REFERRERS ====\n")
    stream.write("Found {} referrers to {}\n".format(len(referrers), obj))
    stream.write("Referrers:\n")
    for r in referrers:
        stream.write("{}\n".format(r))
    stream.write("==================================\n\n")

    del frame

def collect():
    """
    This is a convenience wrapper around gc.collect so you do not have to import the gc module
    in your own code if you do not wish to.
    """
    gc.collect()