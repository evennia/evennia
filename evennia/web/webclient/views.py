
"""
This contains a simple view for rendering the webclient
page and serve it eventual static content.

"""
from __future__ import print_function
from django.shortcuts import render
from django.contrib.auth import login

from evennia.server.sessionhandler import SESSION_HANDLER
from evennia.players.models import PlayerDB


def webclient(request):
    """
    Webclient page template loading.
    """
    print ("webclient session:", request.session.session_key, request.user, request.user.is_authenticated())

    csession = request.session
    csessid = request.session.session_key
    player = request.user
    # check if user has authenticated to website
    if player.is_authenticated():
        print ("webclient: player auth, trying to connect sessions")
        # Try to login all the player's webclient sessions - only
        # unloggedin ones will actually be logged in.
        for session in SESSION_HANDLER.sessions_from_csessid(csessid):
            print ("session to connect:", session)
            if session.protocol_key in ("websocket", "ajax/comet"):
                SESSION_HANDLER.login(session, player)
        csession["logged_in"] = player.id
    elif csession.get("logged_in"):
        # The webclient has previously registered a login to this browser_session
        print ("webclient: browser_session logged in, trying to login")
        player = PlayerDB.objects.get(csession.get("logged_in"))
        login(player, request)
    else:
        csession["logged_in"] = False

    # make sure to store the browser session's hash so the webclient can get to it
    pagevars = {'browser_sessid': request.session.session_key}

    return render(request, 'webclient.html', pagevars)
