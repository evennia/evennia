"""
Web plugin hooks.
"""


def at_webserver_root_creation(web_root):
    """
    This is called as the web server has finished building its default
    path tree. At this point, the media/ and static/ URIs have already
    been added to the web root.

    Args:
        web_root (twisted.web.resource.Resource): The root
            resource of the URI tree. Use .putChild() to
            add new subdomains to the tree.

    Returns:
        web_root (twisted.web.resource.Resource): The potentially
            modified root structure.

    Example:
        from twisted.web import static
        my_page = static.File("web/mypage/")
        my_page.indexNames = ["index.html"]
        web_root.putChild("mypage", my_page)

    """
    return web_root
