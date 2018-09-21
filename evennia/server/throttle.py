from collections import defaultdict, deque
import time

_LATEST_FAILURES = defaultdict(deque)

class Throttle(object):
    """
    Keeps a running count of failed actions per IP address. 
    
    Available methods indicate whether or not the number of failures exceeds a
    particular threshold.
    
    This version of the throttle is usable by both the terminal server as well
    as the web server, imposes limits on memory consumption by using deques
    with length limits instead of open-ended lists, and removes sparse keys when
    no recent failures have been recorded.
    """
    
    error_msg = 'Too many failed attempts; you must wait a few minutes before trying again.'
    cache_size = 20
    
    @classmethod
    def get(cls, ip=None, storage=_LATEST_FAILURES):
        """
        Convenience function that appends a new event to the table.
    
        Args:
            ip (str, optional): IP address of requestor
    
        Returns:
            storage (dict): When no IP is provided, returns a dict of all 
                current IPs being tracked and the timestamps of their recent 
                failures.
            timestamps (deque): When an IP is provided, returns a deque of 
                timestamps of recent failures only for that IP.
    
        """
        if ip: return storage.get(ip, deque(maxlen=cls.cache_size))
        return storage
    
    @classmethod
    def update(cls, ip):
        """
        Convenience function that appends a new event to the table.
    
        Args:
            ip (str): IP address of requestor
    
        Returns:
            throttled (False): Always returns False
    
        """
        return cls.check(ip)
    
    @classmethod
    def check(cls, ip, maxlim=None, timeout=None, storage=_LATEST_FAILURES):
        """
        This will check the session's address against the
        _LATEST_FAILURES dictionary to check they haven't
        spammed too many fails recently.
    
        Args:
            ip (str): IP address of requestor
            maxlim (int): max number of attempts to allow
            timeout (int): number of timeout seconds after
                max number of tries has been reached.
    
        Returns:
            throttled (bool): True if throttling is active,
                False otherwise.
    
        Notes:
            If maxlim and/or timeout are set, the function will
            just do the comparison, not append a new datapoint.
        """
        now = time.time()
        ip = str(ip)
        if maxlim and timeout:
            # checking mode
            latest_fails = storage[ip]
            if latest_fails and len(latest_fails) >= maxlim:
                # too many fails recently
                if now - latest_fails[-1] < timeout:
                    # too soon - timeout in play
                    return True
                else:
                    # timeout has passed. clear faillist
                    del(storage[ip])
                    return False
            else:
                return False
        else:
            # store the time of the latest fail
            if ip not in storage or not storage[ip].maxlen:
                storage[ip] = deque(maxlen=cls.cache_size)
                
            storage[ip].append(time.time())
            return False