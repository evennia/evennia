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

# snaps = []

# def snapshot():
#     snaps.append(tracemalloc.take_snapshot())

# def trace(func, stream=None, frames=None):
#     if stream is None:
#         stream = sys.stdout

#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         if not tracemalloc.is_tracing():
#             if frames:
#                 tracemalloc.start(frames)
#             else:
#                 tracemalloc.start()

#         result = func(*args, **kwargs)

#         collect()
#         snapshot()
#         tracemalloc.stop()
#         top(stream)

#         return result

#     return wrapper

def top(snapshot, key_type='lineno', limit=10, precision=1, filters=[], stream=None):
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    # always filter trash
    snapshot = snapshot.filter_traces(TRASH)

    if len(filters):
        if "filename" in filters:
            snapshot = snapshot.filter_traces([
                tracemalloc.Filter(True, filename_pattern=file)
            ])
        else:
            snapshot = snapshot.filter_traces(filters)

    stats = snapshot.statistics(key_type)


    stream.write("[{}] <{}:{}>\n".format(datetime.now(), file, lineno))
    stream.write("====[ EVENNIA TRACE ]====\n")
    for index, stat in enumerate(stats[:limit], 1):
        tb = stat.traceback[0]
        stream.write("#{0}: {1}:{2} {3:.{4}f} KB\n".format(index, tb.filename, tb.lineno, stat.size / KB, precision))
        line = linecache.getline(tb.filename, tb.lineno).strip()
        if line:
            stream.write("\t{}\n".format(line))
    stream.write("\n")

    remaining = stats[limit:]
    if remaining:
        size = sum(stat.size for stat in remaining)
        stream.write("Output truncated at {} lines\n".format(limit))
        stream.write("{} remaining lines: {} KB\n".format(len(remaining), size / 1024))
    
    total = sum(stat.size for stat in stats)
    stream.write("Total allocated size: {} KB\n".format(total / 1024))
    stream.write("\n")

def compare(start, end, limit=10, stream=None):
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

def compare_all(snaps, limit=10, stream=None):
    if stream is None:
        stream = sys.stdout

    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

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

# def stats(snapshot, )

def dprint(input, stream=None):
    if stream is None:
        stream = sys.stdout

    # get the last frame processed by Python
    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    file = info.filename
    lineno = frame.f_lineno

    out = "[{}] {}\nFrom: <{}:{}>\n\n".format(datetime.now(), input, file, lineno)

    stream.write(out)

    del frame

def get_referrers(obj, stream=None, collect=True):
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
    gc.collect()