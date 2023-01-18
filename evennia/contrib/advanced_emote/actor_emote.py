from commands.command import Command
import re
import nltk
from .data.verbs import verbs

class CmdI(Command):
    """
    Sends a message in Actor Mode.
    
    Usage:
      I <emote>
      My <emote>
      Mine <emote>
    
    Example:
      I smile to the room.
      My eyes scan the room.
      Mine is an evil laugh.
    """
    key = "I"
    aliases = ["My", "Mine"]
    locks = "cmd:all()"
    arg_regex = ""

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 'm, at which we don't want to separate
        I and the emote with a space.
        """
        args = self.args
        if args and not args[0] in ["'", ","]:
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        """Hook function"""
        if not self.args:
            """They were probably trying to get at their inventory."""
            """Todo: make this cause the caller to call inv directly."""
        else:
            punctuation = [".", ";", "!", "?"]
            nospace_joins = [","] + punctuation
            noun_hints = ["a", "her", "his", "their", "the"]
            prepositions = ["aboard", "about", "above", "across", "after", "against", "along", "alongside", "amid", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "besides", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "excepting", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "opposite", "out", "outside", "over", "past", "regarding", "round", "save", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "unto", "up", "upon", "via", "with", "within", "without"]
            from_key = self.caller.key
            from_gender = self.caller.attributes.get("gender", default="plural")
            unparsed_msg = f"{self.cmdstring.capitalize()}{self.args}"
            msg_tokens = nltk.word_tokenize(unparsed_msg)
            msg_tokens_pos = nltk.pos_tag(msg_tokens)
            contents = self.caller.location.contents
            sentence_end = 1
            capitalize = 1
            recent_subjects = [self.caller.key]
            prev_pos = ""
            prev_token = ""
            for w, token_tuple in enumerate(msg_tokens_pos):
                cur_pos = msg_tokens_pos[w][1]
                cur_token = token_tuple[0]
                capitalize = 1 if sentence_end else 0
                sentence_end = 1 if cur_token in punctuation else 0
                # Part of speech corrections for emotes.
                if cur_token.endswith("ly") and cur_pos == "VBP":
                    cur_pos = "RB"
                if (prev_token not in noun_hints) and (prev_pos not in ["JJ"]) and (cur_token in verbs):
                    cur_pos = "VB"
                # Handle pronouns and conjugation
                if (cur_token == "me"):
                    cur_token = f"$pron(You, {from_gender})" if capitalize else f"$pron(you, {from_gender})"
                elif (cur_token in prepositions):
                    cur_pos = "IN"
                elif (cur_token == "my"):
                    cur_token = f"$pron(Your, {from_gender})" if capitalize else f"$pron(your, {from_gender})"
                elif (cur_token == "mine"):
                    cur_token = f"$pron(Yours, {from_gender})" if capitalize else f"$pron(yours, {from_gender})"
                elif (cur_token == "myself"):
                    cur_token = f"$pron(Yourself, {from_gender})" if capitalize else f"$pron(yourself, {from_gender})"
                elif (cur_token == "I"):
                    recent_subjects = [self.caller.key] + recent_subjects
                    cur_token = f"$You({from_key}, {from_gender})" if capitalize else f"$pron(you, {from_gender})"
                elif cur_pos in ["VB", "VBP"] and recent_subjects[0] and prev_token not in ["to"]:
                    cur_token = f"$conj({cur_token})"
                elif (cur_token == "It"):
                    recent_subjects = [""] + recent_subjects
                else:
                    for receiver in contents:
                        to_gender = receiver.attributes.get("gender", default="plural")
                        if (receiver.key in recent_subjects[0:1]):
                            if (cur_token in ["he", "him", "his"]) and (to_gender == "male"):
                                cur_token = f"$prot({cur_token}, {receiver.key})"
                            if (cur_token in ["she", "her"]) and (to_gender == "female"):
                                cur_token = f"$prot({cur_token}, {receiver.key})"
                            if (cur_token == ["they", "them", "their"]) and (to_gender == "plural"):
                                cur_token = f"$prot({cur_token}, {receiver.key})"
                        if (cur_token == receiver.name):
                            cur_token = f"$you({receiver.key})"
                            recent_subjects = [receiver.key] + recent_subjects
                prev_pos = cur_pos
                prev_token = cur_token
                msg_tokens[w] = cur_token
            msg = "".join([" "+i if not i.startswith("'") and i not in nospace_joins else i for i in msg_tokens]).strip()
            mapping = {}
            for receiver in contents:
                mapping[receiver.key] = receiver
            self.caller.location.msg_contents(msg, from_obj=self.caller, mapping=mapping)