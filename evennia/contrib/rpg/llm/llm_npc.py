"""
Basic class for NPC that makes use of an LLM (Large Language Model) to generate replies.

It comes with a `talk` command; use `talk npc <something>` to talk to the NPC. The NPC will
respond using the LLM response.

Makes use of the LLMClient for communicating with the server. The NPC will also
echo a 'thinking...' message if the LLM server takes too long to respond.


"""

from collections import defaultdict
from random import choice

from django.conf import settings
from twisted.internet import reactor, task
from twisted.internet.defer import CancelledError, inlineCallbacks

from evennia import AttributeProperty, Command, DefaultCharacter
from evennia.utils.utils import make_iter

from .llm_client import LLMClient

# fallback if not specified anywhere else. Check order is
# npc.db.prompt_prefix, npcClass.prompt_prefix, then settings.LLM_PROMPT_PREFIX, then this
DEFAULT_PROMPT_PREFIX = (
    "You are roleplaying as {name}, a {desc} existing in {location}. "
    "Answer with short sentences. Only respond as {name} would. "
    "From here on, the conversation between {name} and {character} begins."
)


class LLMNPC(DefaultCharacter):
    """An NPC that uses the LLM server to generate its responses. If the server is slow, it will
    echo a thinking message to the character while it waits for a response."""

    # use this to override the prefix per class. Assign an Attribute to override per-instance.
    prompt_prefix = None

    response_template = AttributeProperty(
        "$You() $conj(say) (to $You(character)): {response}", autocreate=False
    )
    thinking_timeout = AttributeProperty(2, autocreate=False)  # seconds
    thinking_messages = AttributeProperty(
        [
            "{name} thinks about what you said ...",
            "{name} ponders your words ...",
            "{name} ponders ...",
        ],
        autocreate=False,
    )

    max_chat_memory_size = AttributeProperty(25, autocreate=False)
    # this is a store of {character: [chat, chat, ...]}
    chat_memory = AttributeProperty(defaultdict(list))

    @property
    def llm_client(self):
        if not self.ndb.llm_client:
            self.ndb.llm_client = LLMClient()
        return self.ndb.llm_client

    @property
    def llm_prompt_prefix(self):
        """get prefix, first from Attribute, then from class variable,
        then from settings, then from default"""
        return self.attributes.get(
            "prompt_prefix",
            default=getattr(
                settings, "LLM_PROMPT_PREFIX", self.prompt_prefix or DEFAULT_PROMPT_PREFIX
            ),
        )

    def _add_to_memory(self, character, who_talked, speech):
        """Add a person's speech to the memory. This is stored as name: chat for the LLM."""
        memory = self.chat_memory[character]
        memory.append(f"{who_talked.get_display_name(self)}: {speech}")

        # trim the memory if it's getting too long in order to save space
        memory = memory[-self.max_chat_memory_size :]
        self.chat_memory[character] = memory

    def build_prompt(self, character, speech):
        """
        Build the prompt to send to the LLM server.

        Args:
            character (Object): The one talking to the NPC.
            speech (str): The latest speech from the character.

        Returns:
            str: The prompt to return.

        """
        name = self.get_display_name(character)
        charname = character.get_display_name(self)
        memory = self.chat_memory[character]

        # get starting prompt
        prompt = self.llm_prompt_prefix.format(
            name=name,
            desc=self.db.desc or "someone",
            location=self.location.key if self.location else "the void",
            character=charname,
        )
        prompt += "\n" + "\n".join(mem for mem in memory)
        return prompt

    @inlineCallbacks
    def at_talked_to(self, speech, character):
        """Called when this NPC is talked to by a character."""

        def _respond(response):
            """Async handling of the server response"""

            if thinking_defer and not thinking_defer.called:
                # abort the thinking message if we were fast enough
                thinking_defer.cancel()

            if response:
                # remember this response
                self._add_to_memory(character, self, response)
            else:
                response = "... I'm sorry, I was distracted. Can you repeat?"

            response = self.response_template.format(
                name=self.get_display_name(character), response=response
            )

            # tell the character about it
            if character.location:
                character.location.msg_contents(
                    response,
                    mapping={"character": character},
                    from_obj=self,
                )
            else:
                # fallback if character is not in a location
                character.msg(f"{self.get_display_name(character)} says, {response}")

        # if response takes too long, note that the NPC is thinking.

        def _echo_thinking_message():
            """Echo a random thinking message to the character"""
            thinking_message = choice(
                make_iter(self.db.thinking_messages or self.thinking_messages)
            )
            if character.location:
                thinking_message = thinking_message.format(name="$You()")
                character.location.msg_contents(thinking_message, from_obj=self)
            else:
                thinking_message = thinking_message.format(name=self.get_display_name(character))
                character.msg(thinking_message)

        def _handle_cancel_error(failure):
            """Suppress task-cancel errors only"""
            failure.trap(CancelledError)

        thinking_defer = task.deferLater(
            reactor, self.thinking_timeout, _echo_thinking_message
        ).addErrback(_handle_cancel_error)

        # remember latest input in memory, so it's included in the prompt
        self._add_to_memory(character, character, speech)

        # build the prompt
        prompt = self.build_prompt(character, speech)

        # get the response from the LLM server
        yield self.llm_client.get_response(prompt).addCallback(_respond)


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
                f"$You() $conj(say) (to $You(target)): {self.speech}",
                mapping={"target": target},
                from_obj=self.caller,
            )
        if hasattr(target, "at_talked_to"):
            target.at_talked_to(self.speech, self.caller)
        else:
            self.caller.msg(f"{target.key} doesn't seem to want to talk to you.")
