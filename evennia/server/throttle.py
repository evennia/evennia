from collections import defaultdict, deque
from evennia.utils import logger
import time


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

    error_msg = "Too many failed attempts; you must wait a few minutes before trying again."

    def __init__(self, **kwargs):
        """
        Allows setting of throttle parameters.

        Kwargs:
            limit (int): Max number of failures before imposing limiter
            timeout (int): number of timeout seconds after
                max number of tries has been reached.
            cache_size (int): Max number of attempts to record per IP within a
                rolling window; this is NOT the same as the limit after which
                the throttle is imposed!
        """
        self.storage = defaultdict(deque)
        self.cache_size = self.limit = kwargs.get("limit", 5)
        self.timeout = kwargs.get("timeout", 5 * 60)

    def get(self, ip=None):
        """
        Convenience function that returns the storage table, or part of.

        Args:
            ip (str, optional): IP address of requestor

        Returns:
            storage (dict): When no IP is provided, returns a dict of all
                current IPs being tracked and the timestamps of their recent
                failures.
            timestamps (deque): When an IP is provided, returns a deque of
                timestamps of recent failures only for that IP.

        """
        if ip:
            return self.storage.get(ip, deque(maxlen=self.cache_size))
        else:
            return self.storage

    def update(self, ip, failmsg="Exceeded threshold."):
        """
        Store the time of the latest failure.

        Args:
            ip (str): IP address of requestor
            failmsg (str, optional): Message to display in logs upon activation
                of throttle.

        Returns:
            None

        """
        # Get current status
        previously_throttled = self.check(ip)

        # Enforce length limits
        if not self.storage[ip].maxlen:
            self.storage[ip] = deque(maxlen=self.cache_size)

        self.storage[ip].append(time.time())

        # See if this update caused a change in status
        currently_throttled = self.check(ip)

        # If this makes it engage, log a single activation event
        if not previously_throttled and currently_throttled:
            logger.log_sec(
                "Throttle Activated: %s (IP: %s, %i hits in %i seconds.)"
                % (failmsg, ip, self.limit, self.timeout)
            )

    def check(self, ip):
        """
        This will check the session's address against the
        storage dictionary to check they haven't spammed too many
        fails recently.

        Args:
            ip (str): IP address of requestor

        Returns:
            throttled (bool): True if throttling is active,
                False otherwise.

        """
        now = time.time()
        ip = str(ip)

        # checking mode
        latest_fails = self.storage[ip]
        if latest_fails and len(latest_fails) >= self.limit:
            # too many fails recently
            if now - latest_fails[-1] < self.timeout:
                # too soon - timeout in play
                return True
            else:
                # timeout has passed. clear faillist
                del self.storage[ip]
                return False
        else:
            return False
