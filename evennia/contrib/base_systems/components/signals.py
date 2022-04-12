def as_listener(func=None, signal_name=None):
    if not func and signal_name:
        def wrapper(func):
            func._listener_signal_name = signal_name
            return func
        return wrapper

    signal_name = func.__name__
    func._listener_signal_name = signal_name
    return func


def as_responder(func=None, signal_name=None):
    if not func and signal_name:
        def wrapper(func):
            func._responder_signal_name = signal_name
            return func
        return wrapper

    signal_name = func.__name__
    func._responder_signal_name = signal_name
    return func


class SignalsHandler(object):
    def __init__(self, host):
        self.host = host
        self.listeners = {}
        self.responders = {}
        self.add_object_listeners_and_responders(host)

    def add_listener(self, signal_name, callback):
        signal_listeners = self.listeners.setdefault(signal_name, [])
        if callback not in signal_listeners:
            signal_listeners.append(callback)

    def add_responder(self, signal_name, callback):
        signal_responders = self.responders.setdefault(signal_name, [])
        if callback not in signal_responders:
            signal_responders.append(callback)

    def remove_listener(self, signal_name, callback):
        signal_listeners = self.listeners.get(signal_name)
        if not signal_listeners:
            return

        if callback in signal_listeners:
            signal_listeners.remove(callback)

    def remove_responder(self, signal_name, callback):
        signal_responders = self.responders.get(signal_name)
        if not signal_responders:
            return

        if callback in signal_responders:
            signal_responders.remove(callback)

    def trigger(self, signal_name, *args, **kwargs):
        """ This method fires a signal but does not return anything """
        callbacks = self.listeners.get(signal_name)
        if not callbacks:
            return

        for callback in callbacks:
            callback(*args, **kwargs)

    def query(self, signal_name, *args, default=None, aggregate_func=None, **kwargs):
        """ This method fires a signal query that retrieves values """
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
        type_host = type(obj)
        for att_name, att_obj in type_host.__dict__.items():
            listener_signal_name = getattr(att_obj, '_listener_signal_name', None)
            if listener_signal_name:
                callback = getattr(obj, att_name)
                self.add_listener(signal_name=listener_signal_name, callback=callback)

            responder_signal_name = getattr(att_obj, '_responder_signal_name', None)
            if responder_signal_name:
                callback = getattr(obj, att_name)
                self.add_responder(signal_name=responder_signal_name, callback=callback)

    def remove_object_listeners_and_responders(self, obj):
        type_host = type(obj)
        for att_name, att_obj in type_host.__dict__.items():
            listener_signal_name = getattr(att_obj, '_listener_signal_name', None)
            if listener_signal_name:
                callback = getattr(obj, att_name)
                self.remove_listener(signal_name=listener_signal_name, callback=callback)

            responder_signal_name = getattr(att_obj, '_responder_signal_name', None)
            if responder_signal_name:
                callback = getattr(obj, att_name)
                self.remove_responder(signal_name=responder_signal_name, callback=callback)
