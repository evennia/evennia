"""
Components - ChrisLR 2022

This file contains classes functions related to signals.
"""


def as_listener(func=None, signal_name=None):
    """
    Decorator style function that marks a method to be connected as listener.
    It will use the provided signal name and default to the decorated function name.

    Args:
        func (callable): The method to mark as listener
        signal_name (str): The name of the signal to listen to, defaults to function name.
    """
    if not func and signal_name:

        def wrapper(func):
            func._listener_signal_name = signal_name
            return func

        return wrapper

    signal_name = func.__name__
    func._listener_signal_name = signal_name
    return func


def as_responder(func=None, signal_name=None):
    """
    Decorator style function that marks a method to be connected as responder.
    It will use the provided signal name and default to the decorated function name.

    Args:
        func (callable): The method to mark as responder
        signal_name (str): The name of the signal to respond to, defaults to function name.
    """
    if not func and signal_name:

        def wrapper(func):
            func._responder_signal_name = signal_name
            return func

        return wrapper

    signal_name = func.__name__
    func._responder_signal_name = signal_name
    return func


class SignalsHandler(object):
    """
    This object handles all about signals.
    It holds the connected listeners and responders.
    It allows triggering signals or querying responders.
    """

    def __init__(self, host):
        self.host = host
        self.listeners = {}
        self.responders = {}
        self.add_object_listeners_and_responders(host)

    def add_listener(self, signal_name, callback):
        """
        Connect a listener to a specific signal.

        Args:
            signal_name (str): The name of the signal to listen to
            callback (callable): The callable that is called when the signal is triggered
        """

        signal_listeners = self.listeners.setdefault(signal_name, [])
        if callback not in signal_listeners:
            signal_listeners.append(callback)

    def add_responder(self, signal_name, callback):
        """
        Connect a responder to a specific signal.

        Args:
            signal_name (str): The name of the signal to respond to
            callback (callable): The callable that is called when the signal is queried
        """

        signal_responders = self.responders.setdefault(signal_name, [])
        if callback not in signal_responders:
            signal_responders.append(callback)

    def remove_listener(self, signal_name, callback):
        """
        Removes a listener for a specific signal.

        Args:
            signal_name (str): The name of the signal to disconnect from
            callback (callable): The callable that was used to connect
        """

        signal_listeners = self.listeners.get(signal_name)
        if not signal_listeners:
            return

        if callback in signal_listeners:
            signal_listeners.remove(callback)

    def remove_responder(self, signal_name, callback):
        """
        Removes a responder for a specific signal.

        Args:
            signal_name (str): The name of the signal to disconnect from
            callback (callable): The callable that was used to connect
        """
        signal_responders = self.responders.get(signal_name)
        if not signal_responders:
            return

        if callback in signal_responders:
            signal_responders.remove(callback)

    def trigger(self, signal_name, *args, **kwargs):
        """
        Triggers a specific signal with specified args and kwargs
        This method does not return anything

        Args:
            signal_name (str): The name of the signal to trigger
        """

        callbacks = self.listeners.get(signal_name)
        if not callbacks:
            return

        for callback in callbacks:
            callback(*args, **kwargs)

    def query(self, signal_name, *args, default=None, aggregate_func=None, **kwargs):
        """
        Queries a specific signal with specified args and kwargs
        This method will return the responses from its connected responders.
        If an aggregate_func is specified, it is called with the responses
        and its result is returned instead.

        Args:
            signal_name (str): The name of the signal to trigger
            default (any): The value to use when no responses are given
                           It will be passed to aggregate_func if it is also given.
            aggregate_func (callable): The function to process the results before returning.

        Returns:
            list: An iterable of the responses
                  OR the aggregated result when aggregate_func is specified.

        """
        callbacks = self.responders.get(signal_name)

        if not callbacks:
            default = [] if default is None else default
            if aggregate_func:
                return aggregate_func(default)
            return default

        responses = []
        for callback in callbacks:
            response = callback(*args, **kwargs)
            if response is not None:
                responses.append(response)

        if aggregate_func and responses:
            return aggregate_func(responses)

        return responses

    def add_object_listeners_and_responders(self, obj):
        """
        This connects the methods marked as listener or responder from an object.

        Args:
            obj (object): The instance of an object to connect to this handler.
        """
        type_host = type(obj)
        for att_name, att_obj in type_host.__dict__.items():
            listener_signal_name = getattr(att_obj, "_listener_signal_name", None)
            if listener_signal_name:
                callback = getattr(obj, att_name)
                self.add_listener(signal_name=listener_signal_name, callback=callback)

            responder_signal_name = getattr(att_obj, "_responder_signal_name", None)
            if responder_signal_name:
                callback = getattr(obj, att_name)
                self.add_responder(signal_name=responder_signal_name, callback=callback)

    def remove_object_listeners_and_responders(self, obj):
        """
        This disconnects the methods marked as listener or responder from an object.

        Args:
            obj (object): The instance of an object to disconnect from this handler.
        """
        type_host = type(obj)
        for att_name, att_obj in type_host.__dict__.items():
            listener_signal_name = getattr(att_obj, "_listener_signal_name", None)
            if listener_signal_name:
                callback = getattr(obj, att_name)
                self.remove_listener(signal_name=listener_signal_name, callback=callback)

            responder_signal_name = getattr(att_obj, "_responder_signal_name", None)
            if responder_signal_name:
                callback = getattr(obj, att_name)
                self.remove_responder(signal_name=responder_signal_name, callback=callback)
