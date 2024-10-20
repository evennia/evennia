"""
Rate limiting module for Evennia.
whitenoise, 2024

Usage example:
    from evennia.server.rate import Limiter, RateLimitException

    # Create a limiter that allows 5 actions per second, with a burst of 10
    limiter = Limiter(limit=5, burst=10)

    try:
        # Check if an action is allowed
        if limiter.ok():
            # Perform the action
            perform_action()
            
            # Mark the action as completed
            limiter.mark_last()
    except RateLimitException:
        # Handle the case when the rate limit is exceeded
        print("Rate limit exceeded. Please wait before trying again.")

    # You can manually check if an action is allowed without modifying the limiter
    if limiter.allow():
        perform_action()
        limiter.mark_last()

    # You can also check if multiple actions are allowed
    if limiter.allowN(time(), 3):
        # Perform 3 actions
        perform_multiple_actions(3)
        limiter.mark_last()

    # Use the advance method to simulate time passing. This does not modify the limiter.
    # This is useful for testing
    current_time = time()
    future_time = current_time + 2.0  # 2 seconds in the future
    new_time, new_tokens = limiter.advance(future_time)
    print(f"Time advanced by 2 seconds. New token count: {new_tokens}")

    # If you would like to modify the limiter, use the update method
    limiter.update()
    # This performs the advance method up to the current time and modifies limiter with the returns
"""

from time import time

class RateLimitException(Exception):
    """Exception raised when a rate limit is exceeded."""

    pass

# Limiter is fixed and does not support dynamic assignment
class Limiter:
    """
    A rate limiter that uses a token bucket algorithm.
    
    This limiter is fixed and does not support dynamic assignment.
    """

    __slots__ = 'limit', 'burst', 'tokens', 'last', 'last_event'

    def __init__(self, limit, burst):
        """
        Initialize the Limiter.

        Args:
            limit (float): The rate limit (tokens per second).
            burst (float): The maximum number of tokens that can be accumulated.
        """

        self.limit = limit
        self.burst = burst
        self.tokens = float(burst)
        self.last = None
        self.last_event = None

    def advance(self, t):
        """
        Advance the limiter's state to the given time.

        Args:
            t (float): The current time.

        Returns:
            tuple: A tuple containing the new time and token count.
        """

        if self.last is not None:
            last = self.last
            if t < last:
                last = t
        else:
            last = t

        elapsed = t - last
        delta = self.tokens_from_duration(elapsed)
        tokens = self.tokens + delta

        burst = float(self.burst)
        tokens = min(burst, tokens)

        return (last, tokens)

    def allow(self):
        """
        Check if a single token can be consumed at the current time.

        Returns:
            bool: True if allowed, False otherwise.
        """

        return self.allowN(time(), 1)

    def allowN(self, t, count):
        """
        Check if a specified number of tokens can be consumed at a given time.

        Args:
            t (float): The time to check.
            count (int): The number of tokens to check.

        Returns:
            bool: True if allowed, False otherwise.
        """

        _, tokens = self.advance(t)
        
        return tokens >= count

    def ok(self):
        """
        Update the limiter state and check if a token can be consumed.

        Raises:
            RateLimitException: If the rate limit is exceeded.

        Returns:
            bool: True if allowed.
        """

        self.update()

        if self.allow():
            self.tokens -= 1
            return True
        else:
            self.last_event = time()
            raise RateLimitException

    def mark_last(self):
        """Mark the current time as the last event time."""

        self.last = time()

    def tokens_from_duration(self, duration):
        """
        Calculate the number of tokens generated over a given duration.

        Args:
            duration (float): The duration in seconds.

        Returns:
            float: The number of tokens generated.
        """

        if self.limit <= 0:
            return 0
        
        return duration * float(self.limit)

    def update(self):
        """Update the limiter's state to the current time."""

        last, tokens = self.advance(time())
        self.last = last
        self.tokens = min(float(self.burst), tokens)
