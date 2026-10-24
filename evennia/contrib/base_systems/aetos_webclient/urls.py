"""
Optional URLs for the Aetos progressive web app (M20).

A game that wants Aetos installable adds one line to its own `urls.py`::

    urlpatterns += aetos_urls.urlpatterns

Everything else about Aetos works without this. That is deliberate: the PWA is
progressive enhancement on top of progressive enhancement, and a required third
install step would cost every game something to benefit the few that want an
installable client.

WHY THIS NEEDS A VIEW AT ALL
----------------------------

A service worker's scope is the directory it is served from. One at
`/static/aetos/aetos-service-worker.js` can only control `/static/aetos/`, which
is not where the client lives -- so it would register successfully, control
nothing, and appear to work. The worker has to be served from the webclient path
to control the webclient.

The manifest could have been a static file, but it belongs beside the worker: a
game that has not added these URLs should get *no* PWA rather than half of one,
and keeping both here makes that automatic.

"""

from django.http import HttpResponse
from django.urls import path
from django.views.decorators.cache import cache_control

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, constants

#: The worker file, read from the same static directory the client ships.
_WORKER_PATH = AETOS_STATIC_DIR + "/aetos/aetos-service-worker.js"


@cache_control(max_age=0, no_cache=True, must_revalidate=True)
def service_worker(request):
    """
    Serve the Aetos service worker from the webclient's own path.

    Deliberately uncached. A cached service worker is a worker that cannot be
    replaced, which turns any mistake in it into a permanent one for everybody
    who loaded it -- the single failure mode a service worker must not have.

    Args:
        request (HttpRequest): The incoming request.

    Returns:
        HttpResponse: The worker source, with the asset version substituted.

    """
    with open(_WORKER_PATH, encoding="utf-8") as handle:
        source = handle.read()

    # The cache name carries the asset version, so a version bump orphans the
    # old cache instead of merging into it and serving stale JavaScript.
    source = source.replace("__AETOS_ASSET_VERSION__", constants.ASSET_VERSION)

    return HttpResponse(source, content_type="application/javascript")


@cache_control(max_age=3600)
def web_manifest(request):
    """
    Serve the web app manifest.

    Kept minimal and icon-free. Aetos ships no artwork of its own, so declaring
    icons it does not have would produce a broken install prompt; a game that
    wants a branded icon supplies this view's output itself, which is a
    reasonable thing to want and a bad thing to fake.

    Args:
        request (HttpRequest): The incoming request.

    Returns:
        JsonResponse: The manifest.

    """
    from django.http import JsonResponse

    return JsonResponse(
        {
            "name": "Aetos Web Client",
            "short_name": "Aetos",
            "description": "A graphical web client for text games.",
            "start_url": "../webclient/",
            "scope": "../webclient/",
            # "standalone" rather than "fullscreen": fullscreen hides the
            # system back gesture and status bar, and a client that swallows
            # the way out of itself is one somebody has to force-quit.
            "display": "standalone",
            "orientation": "any",
            # Neutral rather than branded, and dark because the client is. A
            # light splash before a dark client is a flash in the face, which
            # for a player who chose dark because light hurts is not cosmetic.
            "background_color": "#14171c",
            "theme_color": "#14171c",
        }
    )


urlpatterns = [
    # Served from the webclient path so the worker's scope covers the client.
    path("webclient/aetos-service-worker.js", service_worker, name="aetos-service-worker"),
    path("webclient/aetos-manifest.json", web_manifest, name="aetos-manifest"),
]
