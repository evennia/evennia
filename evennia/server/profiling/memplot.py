"""
Script that saves memory and idmapper data over time.

Data will be saved to game/logs/memoryusage.log. Note that
the script will append to this file if it already exists.

Call this module directly to plot the log (requires matplotlib and numpy).
"""
from __future__ import division
import os, sys
import time
#TODO!
#sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
#os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'
import ev
from evennia.utils.idmapper import base as _idmapper

LOGFILE = "logs/memoryusage.log"
INTERVAL = 30 # log every 30 seconds

class Memplot(ev.Script):
    """
    Describes a memory plotting action.

    """
    def at_script_creation(self):
        "Called at script creation"
        self.key = "memplot"
        self.desc = "Save server memory stats to file"
        self.start_delay = False
        self.persistent = True
        self.interval = INTERVAL
        self.db.starttime = time.time()

    def at_repeat(self):
        "Regularly save memory statistics."
        pid = os.getpid()
        rmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "rss")).read()) / 1000.0  # resident memory
        vmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "vsz")).read()) / 1000.0  # virtual memory
        total_num, cachedict = _idmapper.cache_size()
        t0 = (time.time() - self.db.starttime) / 60.0 # save in minutes

        with open(LOGFILE, "a") as f:
            f.write("%s, %s, %s, %s\n" % (t0, rmem, vmem, int(total_num)))

if __name__ == "__main__":

    # plot output from the file

    from matplotlib import pyplot as pp
    import numpy

    data = numpy.genfromtxt("../../../game/" + LOGFILE, delimiter=",")
    secs = data[:,0]
    rmem = data[:,1]
    vmem = data[:,2]
    nobj = data[:,3]

    # calculate derivative of obj creation
    #oderiv = (0.5*(nobj[2:] - nobj[:-2]) / (secs[2:] - secs[:-2])).copy()
    #oderiv = (0.5*(rmem[2:] - rmem[:-2]) / (secs[2:] - secs[:-2])).copy()

    fig = pp.figure()
    ax1 = fig.add_subplot(111)
    ax1.set_title("1000 bots (normal players with light building)")
    ax1.set_xlabel("Time (mins)")
    ax1.set_ylabel("Memory usage (MB)")
    ax1.plot(secs, rmem, "r", label="RMEM", lw=2)
    ax1.plot(secs, vmem, "b", label="VMEM", lw=2)
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(secs, nobj, "g--", label="objs in cache", lw=2)
    #ax2.plot(secs[:-2], oderiv/60.0, "g--", label="Objs/second", lw=2)
    #ax2.plot(secs[:-2], oderiv, "g--", label="Objs/second", lw=2)
    ax2.set_ylabel("Number of objects")
    ax2.legend(loc="lower right")
    ax2.annotate("First 500 bots\nconnecting", xy=(10, 4000))
    ax2.annotate("Next 500 bots\nconnecting", xy=(350,10000))
    #ax2.annotate("@reload", xy=(185,600))

#    # plot mem vs cachesize
#    nobj, rmem, vmem = nobj[:262].copy(), rmem[:262].copy(), vmem[:262].copy()
#
#    fig = pp.figure()
#    ax1 = fig.add_subplot(111)
#    ax1.set_title("Memory usage per cache size")
#    ax1.set_xlabel("Cache size (number of objects)")
#    ax1.set_ylabel("Memory usage (MB)")
#    ax1.plot(nobj, rmem, "r", label="RMEM", lw=2)
#    ax1.plot(nobj, vmem, "b", label="VMEM", lw=2)
#

##    # empirical estimate of memory usage: rmem = 35.0 + 0.0157 * Ncache
##    # Ncache = int((rmem - 35.0) / 0.0157)  (rmem in MB)
#
#    rderiv_aver = 0.0157
#    fig = pp.figure()
#    ax1 = fig.add_subplot(111)
#    ax1.set_title("Relation between memory and cache size")
#    ax1.set_xlabel("Memory usage (MB)")
#    ax1.set_ylabel("Idmapper Cache Size (number of objects)")
#    rmem = numpy.linspace(35, 2000, 2000)
#    nobjs = numpy.array([int((mem - 35.0) / 0.0157) for mem in rmem])
#    ax1.plot(rmem, nobjs, "r", lw=2)

    pp.show()
