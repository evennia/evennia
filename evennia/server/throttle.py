import time
from collections import deque

from django.core.cache import caches
from django.utils.translation import gettext as _

from evennia.utils import logger


class Throttle:
    """
    Keeps a running count of failed actions per IP address.

    Available methods indicate whether or not the number of failures exceeds a
    particular threshold.

    This version of the throttle is usable by both the terminal server as well
    as the web server, imposes limits on memory consumption by using deques
    with length limits instead of open-ended lists, and uses native Django
    caches for automatic key eviction and persistence configurability.
    """

    error_msg = _("Too many failed attempts; you must wait a few minutes before trying again.")

    def __init__(self, **kwargs):
        """
        Allows setting of throttle parameters.

        Keyword Args:
            name (str): Name of this throttle.
            limit (int): Max number of failures before imposing limiter. If `None`,
                the throttle is disabled.
            timeout (int): number of timeout seconds after
                max number of tries has been reached.
            cache_size (int): Max number of attempts to record per IP within a
                rolling window; this is NOT the same as the limit after which
                the throttle is imposed!
        """
        try:
            self.storage = caches["throttle"]
        except Exception:
            logger.log_trace("Throttle: Errors encountered; using default cache.")
            self.storage = caches["default"]

        self.name = kwargs.get("name", "undefined-throttle")
        self.limit = kwargs.get("limit", 5)
        self.cache_size = kwargs.get("cache_size", self.limit)
        self.timeout = kwargs.get("timeout", 5 * 60)

    def get_cache_key(self, *args, **kwargs):
        """
        Creates a 'prefixed' key containing arbitrary terms to prevent key
        collisions in the same namespace.

        """
        return "-".join((self.name, *args))

    def touch(self, key, *args, **kwargs):
        """
        Refreshes the timeout on a given key and ensures it is recorded in the
        key register.

        Args:
            key(str): Key of entry to renew.

        """
        cache_key = self.get_cache_key(key)
        if self.storage.touch(cache_key, self.timeout):
            self.record_key(key)

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
            cache_key = self.get_cache_key(str(ip))
            return self.storage.get(cache_key, deque(maxlen=self.cache_size))
        else:
            keys_key = self.get_cache_key("keys")
            keys = self.storage.get_or_set(keys_key, set(), self.timeout)
            data = self.storage.get_many((self.get_cache_key(x) for x in keys))

            found_keys = set(data.keys())
            if len(keys) != len(found_keys):
                self.storage.set(keys_key, found_keys, self.timeout)

            return data

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
        cache_key = self.get_cache_key(ip)

        # Get current status
        previously_throttled = self.check(ip)

        # Get previous failures, if any
        entries = self.storage.get(cache_key, [])
        entries.append(time.time())

        # Store updated record
        self.storage.set(cache_key, deque(entries, maxlen=self.cache_size), self.timeout)

        # See if this update caused a change in status
        currently_throttled = self.check(ip)

        # If this makes it engage, log a single activation event
        if not previously_throttled and currently_throttled:
            logger.log_sec(
                f"Throttle Activated: {failmsg} (IP: {ip}, "
                f"{self.limit} hits in {self.timeout} seconds.)"
            )

        self.record_ip(ip)

    def remove(self, ip, *args, **kwargs):
        """
        Clears data stored for an IP from the throttle.

        Args:
            ip(str): IP to clear.

        """
        exists = self.get(ip)
        if not exists:
            return False

        cache_key = self.get_cache_key(ip)
        self.storage.delete(cache_key)
        self.unrecord_ip(ip)

        # Return True if NOT exists
        return not bool(self.get(ip))

    def record_ip(self, ip, *args, **kwargs):
        """
        Tracks keys as they are added to the cache (since there is no way to
        get a list of keys after-the-fact).

        Args:
            ip(str): IP being added to cache. This should be the original
                IP, not the cache-prefixed key.

        """
        keys_key = self.get_cache_key("keys")
        keys = self.storage.get(keys_key, set())
        keys.add(ip)
        self.storage.set(keys_key, keys, self.timeout)
        return True

    def unrecord_ip(self, ip, *args, **kwargs):
        """
        Forces removal of a key from the key registry.

        Args:
            ip(str): IP to remove from list of keys.

        """
        keys_key = self.get_cache_key("keys")
        keys = self.storage.get(keys_key, set())
        try:
            keys.remove(ip)
            self.storage.set(keys_key, keys, self.timeout)
            return True
        except KeyError:
            return False

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
        if self.limit is None:
            # throttle is disabled
            return False

        now = time.time()
        ip = str(ip)

        cache_key = self.get_cache_key(ip)

        # checking mode
        latest_fails = self.storage.get(cache_key)
        if latest_fails and len(latest_fails) >= self.limit:
            # too many fails recently
            if now - latest_fails[-1] < self.timeout:
                # too soon - timeout in play
                self.touch(cache_key)
                return True
            else:
                # timeout has passed. clear faillist
                self.remove(ip)
                return False
        else:
            return False
