class EventHandler(object):
    """
    This is loaded as EVENT_HANDLER on the evennia API. It is used for dispatching messages for game events to
    specific other objects/methods.

    Standard Events (*args, **kwargs):
        account_create (account) - called when an Account is created.
        account_login(account, session) - called when an Account connects cold - no pre-existing sessions.
        account_logout(account, session) - called when an Account's last session is terminated.

    """

    def __init__(self):
        self.event_storage = dict()

    def subscribe(self, event, to_call):
        """
        Subscribes a callable to listen for a specific event.

        Args:
            event (str): The event's name/key. If it does not exist, it will be created as a new set.
            to_call (callable): The method to call. This is probably some method on an object or a function.

        Returns:
            None
        """
        if event not in self.event_storage:
            self.event_storage[event] = set()
        self.event_storage[event].add(to_call)

    def unsubscribe(self, event, no_call):
        """
        Removes a callable from a subscribed event. If there was no subscription, nothing happens.

        Args:
            event (str): The event's name/key. If it does not exist, nothing happens.
            no_call (callable): The method to no longer call.

        Returns:
            Nothing.
        """
        if event not in self.event_storage:
            return
        self.event_storage[event].remove(no_call)

    def trigger(self, event, *args, **kwargs):
        """


        Args:
            event:
            *args:
            **kwargs:

        Returns:
            Nothing.
        """
        for c in self.event_storage.get(event, set()):
            c(*args, **kwargs)


EVENT_HANDLER = EventHandler()
