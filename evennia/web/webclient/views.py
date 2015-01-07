
"""
This contains a simple view for rendering the webclient
page and serve it eventual static content.

"""
from django.shortcuts import render

from evennia.players.models import PlayerDB


def webclient(request):
    """
    Webclient page template loading.
    """

    # analyze request to find which port we are on
    if int(request.META["SERVER_PORT"]) == 8000:
        # we relay webclient to the portal port
        print "Called from port 8000!"
        #return redirect("http://localhost:8001/webclient/", permanent=True)

    nsess = len(PlayerDB.objects.get_connected_players()) or "none"
    # as an example we send the number of connected players to the template
    pagevars = {'num_players_connected': nsess}

    return render(request, 'webclient.html', pagevars)
