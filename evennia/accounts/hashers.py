"""
Password hashing utilities and non-blocking Twisted wrappers for Evennia.

Evennia's Server runs on a single-threaded Twisted reactor, so synchronous
password hashing stalls all connected players. This module provides:

- `EvenniaScryptPasswordHasher`: an OWASP-compliant Scrypt hasher tuned for
  lower single-core latency (`N=2**15, r=8, p=1`, ~32 MiB) than Django's
  default PBKDF2 or `p=5` Scrypt, with no external dependencies.
- `defer_check_password` and `defer_make_password`: Twisted helpers that
  offload pure, stateless password hashing to a worker thread when the
  reactor is running (releasing the GIL in OpenSSL/C) without touching
  Django's ORM or idmapper cache from off-thread.

"""

from django.contrib.auth.hashers import (
    ScryptPasswordHasher,
)
from django.contrib.auth.hashers import check_password as django_check_password
from django.contrib.auth.hashers import (
    make_password,
)
from twisted.internet import defer, reactor, threads

__all__ = (
    "EvenniaScryptPasswordHasher",
    "verify_and_upgrade_password",
    "defer_check_password",
    "defer_make_password",
)


class EvenniaScryptPasswordHasher(ScryptPasswordHasher):
    """
    OWASP-compliant Scrypt password hasher tuned for single-core latency.

    Django's built-in `ScryptPasswordHasher` defaults to `N=2**14, r=8, p=5`
    (~16 MiB), which runs 5 lanes sequentially on a single thread in
    `hashlib.scrypt`. Using `N=2**15, r=8, p=1` (~32 MiB) meets OWASP's
    recommended scrypt parameters while cutting single-core hash time roughly
    in half with zero external dependencies.

    """

    work_factor = 2**15
    block_size = 8
    parallelism = 1
    # OpenSSL's default maxmem is 32 MiB, which is slightly too tight for
    # N=2**15, r=8 overhead; allow up to 64 MiB.
    maxmem = 64 * 1024 * 1024


def verify_and_upgrade_password(raw_password, encoded):
    """
    Verify a raw password against an encoded hash without touching the database.

    If verification succeeds and the hash uses a non-preferred algorithm or
    outdated parameters, an upgraded hash string is computed in the same call.

    Args:
        raw_password (str): Cleartext password to verify.
        encoded (str): Stored Django-formatted password hash string.

    Returns:
        tuple[bool, str | None]: `(is_valid, upgraded_hash)`. `upgraded_hash`
            is a newly encoded password string if the hash should be persisted
            as an upgrade, or `None` otherwise.

    """
    upgraded = []

    def _capture_upgrade(password):
        upgraded.append(make_password(password))

    is_valid = django_check_password(raw_password, encoded, setter=_capture_upgrade)
    return is_valid, (upgraded[0] if upgraded else None)


def defer_check_password(raw_password, encoded):
    """
    Verify (and optionally re-hash) a password without blocking the reactor.

    When the Twisted reactor is running, executes `verify_and_upgrade_password`
    in Twisted's worker thread pool (where OpenSSL releases the GIL). When the
    reactor is not running (e.g. unit tests or CLI commands), executes
    synchronously and returns an already-fired `Deferred`.

    Args:
        raw_password (str): Cleartext password to verify.
        encoded (str): Stored Django-formatted password hash string.

    Returns:
        Deferred: Fires with `(is_valid, upgraded_hash)`.

    """
    if reactor.running:
        return threads.deferToThread(verify_and_upgrade_password, raw_password, encoded)
    return defer.succeed(verify_and_upgrade_password(raw_password, encoded))


def defer_make_password(raw_password):
    """
    Encode a cleartext password without blocking the reactor.

    When the Twisted reactor is running, executes Django's `make_password` in
    Twisted's worker thread pool (where OpenSSL releases the GIL). When the
    reactor is not running (e.g. unit tests or CLI commands), executes
    synchronously and returns an already-fired `Deferred`.

    Args:
        raw_password (str or None): Cleartext password to hash, or `None` for
            an unusable password.

    Returns:
        Deferred: Fires with the encoded password hash string.

    """
    if reactor.running:
        return threads.deferToThread(make_password, raw_password)
    return defer.succeed(make_password(raw_password))
