import os
import tempfile
from hashlib import md5

from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from mock import MagicMock, patch

from . import general_context, staticfiles


class TestGeneralContext(TestCase):
    maxDiff = None

    @patch("evennia.web.utils.general_context.GAME_NAME", "test_name")
    @patch("evennia.web.utils.general_context.GAME_SLOGAN", "test_game_slogan")
    @patch("evennia.web.utils.general_context.REGISTER_ENABLED", "register_enabled_testvalue")
    @patch(
        "evennia.web.utils.general_context.WEBSOCKET_CLIENT_ENABLED",
        "websocket_client_enabled_testvalue",
    )
    @patch("evennia.web.utils.general_context.WEBCLIENT_ENABLED", "webclient_enabled_testvalue")
    @patch("evennia.web.utils.general_context.WEBSOCKET_PORT", "websocket_client_port_testvalue")
    @patch("evennia.web.utils.general_context.WEBSOCKET_URL", "websocket_client_url_testvalue")
    @patch("evennia.web.utils.general_context.REST_API_ENABLED", True)
    def test_general_context(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        request.session = {"account": None, "puppet": None}

        response = general_context.general_context(request)

        self.assertEqual(
            response,
            {
                "account": None,
                "puppet": None,
                "game_name": "test_name",
                "game_slogan": "test_game_slogan",
                "evennia_userapps": ["Accounts"],
                "evennia_entityapps": ["Objects", "Scripts", "Comms", "Help"],
                "evennia_setupapps": ["Permissions", "Config"],
                "evennia_connectapps": ["Irc"],
                "evennia_websiteapps": ["Flatpages", "News", "Sites"],
                "register_enabled": "register_enabled_testvalue",
                "webclient_enabled": "webclient_enabled_testvalue",
                "websocket_enabled": "websocket_client_enabled_testvalue",
                "websocket_port": "websocket_client_port_testvalue",
                "websocket_url": "websocket_client_url_testvalue",
                "rest_api_enabled": True,
                "server_hostname": "localhost",
                "ssh_enabled": False,
                "ssh_ports": [4004],
                "telnet_enabled": True,
                "telnet_ports": [4000],
                "telnet_ssl_enabled": False,
                "telnet_ssl_ports": [4003],
            },
        )


class TestCacheBustingStaticFilesStorage(SimpleTestCase):
    """
    Test the static-files storage that adds content hashes to static file names.

    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage = self._get_storage()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _get_storage(self):
        return staticfiles.CacheBustingStaticFilesStorage(
            location=self.tmpdir.name, base_url="/static/"
        )

    def _collect(self, files, storage=None):
        """
        Store files and post-process them, like `collectstatic` does.

        """
        storage = storage or self.storage
        for name, content in files.items():
            if storage.exists(name):
                storage.delete(name)
            storage.save(name, ContentFile(content))
        paths = {name: (storage, name) for name in files}
        for _, _, processed in storage.post_process(paths):
            if isinstance(processed, Exception):
                raise processed

    def _hashed(self, name, content):
        root, ext = os.path.splitext(name)
        return f"{root}.{md5(content).hexdigest()[:12]}{ext}"

    def test_url_is_hashed(self):
        self._collect({"css/site.css": b"body {}"})
        hashed_name = self._hashed("css/site.css", b"body {}")
        self.assertEqual(self.storage.url("css/site.css"), f"/static/{hashed_name}")
        self.assertTrue(self.storage.exists(hashed_name))

    @override_settings(DEBUG=True)
    def test_url_is_hashed_in_debug_mode(self):
        self._collect({"css/site.css": b"body {}"})
        hashed_name = self._hashed("css/site.css", b"body {}")
        self.assertEqual(self.storage.url("css/site.css"), f"/static/{hashed_name}")

    def test_url_of_file_missing_from_manifest_is_not_hashed(self):
        self._collect({"css/site.css": b"body {}"})
        self.assertEqual(self.storage.url("css/missing.css"), "/static/css/missing.css")

    def test_url_without_manifest_is_not_hashed(self):
        self.assertEqual(self.storage.url("css/site.css"), "/static/css/site.css")

    def test_missing_css_reference_is_left_unchanged(self):
        logo = b"not-really-a-png"
        css = (
            b'.a { background: url("../img/logo.png"); }\n'
            b'.b { background: url("../img/missing.png"); }\n'
        )
        self._collect({"img/logo.png": logo, "css/site.css": css})

        hashed_css = self.storage.url("css/site.css").removeprefix("/static/")
        with self.storage.open(hashed_css) as fil:
            content = fil.read().decode()

        self.assertIn(f'url("../{self._hashed("img/logo.png", logo)}")', content)
        self.assertIn('url("../img/missing.png")', content)

    def test_manifest_is_reloaded_when_changed_on_disk(self):
        self._collect({"css/site.css": b"body {}"})
        self.assertEqual(
            self.storage.url("css/site.css"),
            f"/static/{self._hashed('css/site.css', b'body {}')}",
        )

        # collectstatic is usually run by another process, with its own storage instance
        self._collect({"css/site.css": b"body { color: red; }"}, storage=self._get_storage())
        # make sure the change is seen also on file systems with coarse mtimes
        manifest_path = self.storage.path(self.storage.manifest_name)
        mtime_ns = os.stat(manifest_path).st_mtime_ns + 10**9
        os.utime(manifest_path, ns=(mtime_ns, mtime_ns))

        self.assertEqual(
            self.storage.url("css/site.css"),
            f"/static/{self._hashed('css/site.css', b'body { color: red; }')}",
        )

    def test_unreadable_manifest_keeps_previous_manifest(self):
        self._collect({"css/site.css": b"body {}"})
        # simulate catching collectstatic in the middle of writing the manifest
        with open(self.storage.path(self.storage.manifest_name), "w") as fil:
            fil.write('{"paths": {"css/site.css": ')

        self.assertEqual(
            self.storage.url("css/site.css"),
            f"/static/{self._hashed('css/site.css', b'body {}')}",
        )
