"""
Script that saves memory and idmapper data over time.

Data will be saved to game/logs/memoryusage.log. Note that
the script will append to this file if it already exists.

Call this module directly to plot the log (requires matplotlib and numpy).
"""
import os, sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'
import ev
from src.utils.idmapper import base as _idmapper

LOGFILE = "logs/memoryusage.log"
INTERVAL = 30 # log every 30 seconds

class Memplot(ev.Script):
    def at_script_creation(self):
        self.key = "memplot"
        self.desc = "Save server memory stats to file"
        self.start_delay = False
        self.persistent = True
        self.interval = INTERVAL
        self.db.starttime = time.time()

    def at_repeat(self):

        pid = os.getpid()
        rmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "rss")).read()) / 1000.0  # resident memory
        vmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "vsz")).read()) / 1000.0  # virtual memory
        total_num, cachedict = _idmapper.cache_size()
        t0 = (time.time() - self.db.starttime) / 60.0 # save in minutes

        with open(LOGFILE, "a") as f:
            f.write("%s, %s, %s, %s\n" % (t0, rmem, vmem, total_num))

if __name__ == "__main__":

    # plot output from the file

    from matplotlib import pyplot as pp
    import numpy

    data = numpy.genfromtxt(LOGFILE, delimiter=",")
    secs = data[:,0]
    rmem = data[:,1]
    vmem = data[:,2]
    nobj = data[:,3]

    # correct for @reload
    #secs[359:] = secs[359:] + secs[358]

    # count total amount of objects
    ntot = data[:,3].copy()
    #ntot[119:] = ntot[119:] + ntot[118] - ntot[119]
    #ntot[359:] = ntot[359:] + ntot[358] - ntot[359]

    fig = pp.figure()
    ax1 = fig.add_subplot(111)
    ax1.set_title("Memory usage")
    ax1.set_xlabel("Time (mins)")
    ax1.set_ylabel("Memory usage (MB)")
    ax1.plot(secs, rmem, "r", label="RMEM", lw=2)
    ax1.plot(secs, vmem, "b", label="VMEM", lw=2)
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(secs, nobj, "g--", label="objs in cache", lw=2)
    ax2.plot(secs, ntot, "r--", label="objs total", lw=2)
    ax2.set_ylabel("Number of objects")
    ax2.legend(loc="lower right")
    ax2.annotate("idmapper\nflush", xy=(70,480))
    ax2.annotate("@reload", xy=(185,600))
    pp.show()
