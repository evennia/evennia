import ev
from src.server.sessionhandler import SESSIONS

def charmatch(me, name, local_only=False):
    """
        Feed this a name, and it will return character matches. It will return
    only one match if the name is exact or unambiguous, and it will return
    multiple if there are multiple people online who match, but none of which
    are exact matches. All results are returned in a list. An empty list is
    returned if there is no match.
        Me is the object that will be returned if the query is 'me'.
    """
    if name.lower() == "me":
        return me
    if local_only:
        target = []
        targets = me.search(name, ignore_errors=True)
        if type(targets) == list:
            for thing in targets:
                if utils.inherits_from(thing, settings.BASE_CHARACTER_TYPECLASS):
                    target.append(thing)
        elif not targets:
            pass
        else:
            target.append(targets)
        return target[0]
    else:
        target = me.search(name, global_search=True, quiet=True, use_nicks=True)
        if target:
            return target[0]
    matches = []
    for session in SESSIONS.sessions.values():
        character = session.get_character()
        if character and character.name.lower().startswith(name.lower()):
            matches.append(character)
    if not len(matches):
        return None
    else:
        return matches[0]