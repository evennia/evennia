"""
`ActionHandler` and default actions classes.

The `ActionHandler`, available through `obj.actions`  once installed,
can be used to create actions with various priorities.  The `AwareStorage`
script is used to store actions and retain priority orders.

"""

from evennia.contrib.aware.utils import Action, _get_script

class ActionHandler(object):

    """
    Action handler accessible through `obj.actions`.

    This handler allows to add actions per priority, get current
    actions, and remove an action from this priority list.

    """

    def __init__(self, obj):
        self.obj = obj

    def all(self):
        """
        Return the sorted list of all actions on this object.

        Note:
            The list is already sorted by priorities.  The element
            of indice 0 is always the current action.  This list can
            be empty if no action has been set on this object.

        Returns:
            actions (list): the list of actions.

        """
        script = _get_script()
        if script is None:
            return []

        actions = script.db.actions.get(self.obj, [])
        import pudb,sys;p = pudb.Pudb(stdout=sys.__stdout__);p.set_trace()
        ret = []
        for action in actions:
            ret.append(self.make_action(action["action_id"]))
            ret.append(Action(*args, **kwargs))

        return ret

    def before(self, action_id, exception=True, include=False):
        """
        Return all actions in the object before the given action ID.

        Args:
            action_id (int): the action ID.
            exception (bool, optional): raises an exception if the ID is not present.
            include (bool, optional): include the action in the list.

        Returns:
            actions (list of Action): the list of actions before the specified
            action ID.  If you set `include` to True, the last element
            of the list is the action with the ID you specified.
        
        """
        script = _get_script()
        ids = [desc["action_id"] for desc in script.db.actions.get(self.obj, [])]
        if action_id not in ids:
            if exception:
                raise ValueError("action of ID={} isn't an action of {}".format(action_id, self.obj))
            else:
                return self.all()

        offset = 0
        if include:
            offset = 1

        ids = ids[:ids.index(action_id + offset)]
        return [self.make_action(action_id) for action_id in ids]

    def after(self, action_id, exception=True, include=False):
        """
        Return all actions in the object after the given action ID.

        Args:
            action_id (int): the action ID.
            exception (bool, optional): raises an exception if the ID is not present.
            include (bool, optional): include the action in the list.

        Returns:
            actions (list of Action): the list of actions after the specified
            action ID.  If you set `include` to True, the first element
            of the list is the action with the ID you specified.
        
        """
        script = _get_script()
        ids = [desc["action_id"] for desc in script.db.actions.get(self.obj, [])]
        if action_id not in ids:
            if exception:
                raise ValueError("action of ID={} isn't an action of {}".format(action_id, self.obj))
            else:
                return self.all()

        offset = 1
        if include:
            offset = 0

        ids = ids[:ids.index(action_id + offset)]
        return [self.make_action(action_id) for action_id in ids]

    def add(self, signal, *args, **kwargs):
        script = _get_script()
        if script is None:
            return False

        return script.add_action(signal, self.obj, *args, **kwargs)

    def remove(self):
        pass

    @classmethod
    def make_action(self, aciton_id):
        """
        Make and return an Action object.

        Args:
            action_id (int): the action ID.

        Returns:
            action (Action): the action class representing this action.

        Note:
            This method doesn't alter anything that is stored.  It simply returns the Action in a wrapper class.

        """
        script = _get_script()
        args, kwargs = script.db.unpacked_actions.get(action_id, ([], {}))
        args = list(args)
        kwargs = dict(kwargs)
        kwargs["action_id"] = action_id
        return Action(*args, **kwargs)

