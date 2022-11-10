"""
TutorialMirror

A simple mirror object to experiment with.

"""

from evennia import DefaultObject, logger
from evennia.utils import is_iter, make_iter


class TutorialMirror(DefaultObject):
    """
    A simple mirror object that
    - echoes back the description of the object looking at it
    - echoes back whatever is being sent to its .msg - to the
      sender, if given, otherwise to the location of the mirror.

    """

    def return_appearance(self, looker, **kwargs):
        """
        This formats the description of this object. Called by the 'look' command.

        Args:
            looker (Object): Object doing the looking.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).
        """

        if isinstance(looker, self.__class__):
            # avoid infinite recursion by having two mirrors look at each other
            return "The image of yourself stretches into infinity."
        return f"{self.key} shows your reflection:\n{looker.db.desc}"

    def msg(self, text=None, from_obj=None, **kwargs):
        """
        Simply override .msg to echo back to the messenger or to the current
        location.

        Args:
            text (str or tuple, optional): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (obj or iterable)
                given, at_msg_send will be called. This value will be
                passed on to the protocol. If iterable, will execute hook
                on all entities in it.
        """
        if not text:
            text = "<silence>"
        text = text[0] if is_iter(text) else text
        if from_obj:
            for obj in make_iter(from_obj):
                obj.msg(f'{self.key} echoes back to you:\n"{text}".')
        elif self.location:
            self.location.msg_contents(f'{self.key} echoes back:\n"{text}".', exclude=[self])
        else:
            # no from_obj and no location, just log
            logger.log_msg(f"{self.key}.msg was called without from_obj and .location is None.")
