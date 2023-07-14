"""
Basic class for NPC that makes use of an LLM (Large Language Model) to generate replies.

It comes with a `talk` command; use `talk npc <something>` to talk to the NPC. The NPC will
respond using the LLM response.

Makes use of the LLMClient for communicating with the server. The NPC will also
echo a 'thinking...' message if the LLM server takes too long to respond.


"""

from random import choice

from evennia import Command, DefaultCharacter
from evennia.utils.utils import make_iter
from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks

from .llm_client import LLMClient


class LLMNPC(DefaultCharacter):
    """An NPC that uses the LLM server to generate its responses. If the server is slow, it will
    echo a thinking message to the character while it waits for a response."""

    response_template = "{name} says: {response}"
    thinking_timeout = 2  # seconds
    thinking_messages = [
        "{name} thinks about what you said ...",
        "{name} ponders your words ...",
        "{name} ponders ...",
    ]

    @property
    def llm_client(self):
        if not hasattr(self, "_llm_client"):
            self._llm_client = LLMClient()
        return self._llm_client

    @inlineCallbacks
    def at_talked_to(self, speech, character):
        """Called when this NPC is talked to by a character."""

        def _respond(response):
            """Async handling of the server response"""

            if thinking_defer and not thinking_defer.called:
                # abort the thinking message if we were fast enough
                thinking_defer.cancel()

            character.msg(
                self.response_template.format(
                    name=self.get_display_name(character), response=response
                )
            )

        def _echo_thinking_message():
            """Echo a random thinking message to the character"""
            thinking_messages = make_iter(self.db.thinking_messages or self.thinking_messages)
            character.msg(choice(thinking_messages).format(name=self.get_display_name(character)))

        # if response takes too long, note that the NPC is thinking.
        thinking_defer = task.deferLater(reactor, self.thinking_timeout, _echo_thinking_message)

        # get the response from the LLM server
        yield self.llm_client.get_response(speech).addCallback(_respond)


class CmdLLMTalk(Command):
    """
    Talk to an NPC

    Usage:
        talk npc <something>
        talk npc with spaces in name = <something>

    """

    key = "talk"

    def parse(self):
        args = self.args.strip()
        if "s=" in args:
            name, *speech = args.split("=", 1)
        else:
            name, *speech = args.split(" ", 1)
        self.target_name = name
        self.speech = speech[0] if speech else ""

    def func(self):
        if not self.target_name:
            self.caller.msg("Talk to who?")
            return

        location = self.caller.location
        target = self.caller.search(self.target_name)
        if not target:
            return
        if location:
            location.msg_contents(
                f'$You() talk to $You({target.key}), saying "{self.speech}"',
                mapping={target.key: target},
                from_obj=self.caller,
            )
        if hasattr(target, "at_talked_to"):
            target.at_talked_to(self.speech, self.caller)
        else:
            self.caller.msg(f"{target.key} doesn't seem to want to talk to you.")
