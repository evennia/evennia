"""
Tests for the Aetos Web Client installation mechanism.

Aetos is installed by prepending its template directory to `TEMPLATES[0]["DIRS"]`
and registering the package in `INSTALLED_APPS`. That mechanism depends on a small
number of structural facts about both Aetos and stock Evennia. These tests pin
those facts down so that an upstream change which would silently break
installation fails loudly here instead of in a user's browser.

"""

import re
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.test import TestCase

import evennia
from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    AETOS_TEMPLATE_DIR,
    constants,
)
from evennia.contrib.base_systems.aetos_webclient.apps import AetosWebClientConfig

CONTRIB_DIR = Path(__file__).resolve().parent.parent


def _strip_template_comments(text):
    """
    Remove Django template and HTML comment blocks.

    Aetos documents *why* it avoids the stock CDN hosts, naming them explicitly.
    That documentation must not trip assertions about what the template loads.

    Args:
        text (str): Template source.

    Returns:
        str: Source with comments removed.

    """
    without_django = re.sub(r"{% comment %}.*?{% endcomment %}", "", text, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", "", without_django, flags=re.DOTALL)


class TestAetosConstants(TestCase):
    """The values Aetos treats as a public contract."""

    def test_protocol_version_is_an_integer(self):
        """Protocol version is a plain integer, not a string."""
        self.assertIsInstance(constants.PROTOCOL_VERSION, int)

    def test_protocol_version_is_v1(self):
        """Guard against an accidental protocol bump; that is a breaking change."""
        self.assertEqual(constants.PROTOCOL_VERSION, 1)

    def test_client_name(self):
        """The handshake identifier games match on."""
        self.assertEqual(constants.CLIENT_NAME, "aetos")


class TestAetosAppConfig(TestCase):
    """The Django application registration."""

    def test_app_config_points_at_this_package(self):
        """A wrong dotted name would make Django fail to find the app."""
        self.assertEqual(
            AetosWebClientConfig.name,
            "evennia.contrib.base_systems.aetos_webclient",
        )

    def test_app_label_does_not_collide_with_a_stock_app(self):
        """
        A duplicate label raises ImproperlyConfigured at startup.

        Checked against the apps Evennia ships rather than against whatever is
        loaded right now. The earlier version compared with the live registry,
        which meant the test passed only in a game dir that had *not* installed
        Aetos -- so it failed in every game that had, including the lab. It was
        asserting a fact about the deployment while claiming to assert one
        about the label.

        """
        self.assertEqual(AetosWebClientConfig.label, "aetos_webclient")
        stock_labels = {
            config.label
            for config in django_apps.get_app_configs()
            if config.name != AetosWebClientConfig.name
        }
        self.assertNotIn(AetosWebClientConfig.label, stock_labels)


class TestAetosExportedPaths(TestCase):
    """The paths a game's settings.py imports in order to install Aetos."""

    def test_template_dir_exists_and_holds_the_template(self):
        """This directory is what a game prepends to TEMPLATES DIRS."""
        template_dir = Path(AETOS_TEMPLATE_DIR)
        self.assertTrue(template_dir.is_dir())
        self.assertTrue((template_dir / constants.WEBCLIENT_TEMPLATE_NAME).is_file())

    def test_static_dir_exists_and_is_namespaced(self):
        """
        Static files are collected into one shared tree, so Aetos namespaces its
        assets under static/aetos/ to avoid colliding with any other app.

        """
        static_dir = Path(AETOS_STATIC_DIR)
        self.assertTrue((static_dir / "aetos" / "js" / "aetos.js").is_file())
        self.assertTrue((static_dir / "aetos" / "css" / "aetos.css").is_file())
        self.assertTrue((static_dir / "aetos" / "css" / "ansi.css").is_file())
        stray = [path.name for path in static_dir.iterdir() if path.name != "aetos"]
        self.assertEqual(stray, [])

    def test_exported_paths_are_absolute(self):
        """A relative path would resolve against the game's working directory."""
        self.assertTrue(Path(AETOS_TEMPLATE_DIR).is_absolute())
        self.assertTrue(Path(AETOS_STATIC_DIR).is_absolute())


class TestAetosTemplateContract(TestCase):
    """
    Aetos provides its own base template.

    Aetos previously extended Evennia's `webclient/base.html`. That base loads
    eight third-party CDN resources -- jQuery, Bootstrap, Popper, Favico and
    GoldenLayout -- for the stock GUI. Aetos is vanilla JavaScript and uses none
    of them, so extending it meant every install phoned out to five third
    parties, broke on an offline network, and depended on an unpinned "latest"
    URL that could change under it without warning.

    Aetos therefore supplies its own base, replicating only the transport
    bootstrap. `evennia.js` is still Evennia's own file, referenced unmodified
    from Evennia's own static directory rather than copied.

    """

    def setUp(self):
        self.template_text = (
            Path(AETOS_TEMPLATE_DIR) / constants.WEBCLIENT_TEMPLATE_NAME
        ).read_text(encoding="utf-8")
        self.base_text = (Path(AETOS_TEMPLATE_DIR) / "aetos" / "base.html").read_text(
            encoding="utf-8"
        )

    def test_extends_the_aetos_base(self):
        self.assertIn('{%% extends "%s" %%}' % constants.AETOS_BASE_TEMPLATE, self.template_text)

    def test_does_not_load_the_stock_gui(self):
        """Two GUIs fighting over the same DOM would be unrecoverable."""
        self.assertNotIn("webclient_gui.js", self.template_text)
        self.assertNotIn("webclient_gui.js", self.base_text)

    def test_base_loads_evennias_transport_unmodified(self):
        """
        Aetos must use Evennia's own transport rather than reimplementing it.
        Referenced from Evennia's static directory, never copied or patched.

        """
        self.assertIn(constants.EVENNIA_TRANSPORT_SCRIPT, self.base_text)

    def test_base_supplies_the_transport_variables_evennia_js_expects(self):
        """
        evennia.js reads these globals. Omitting one breaks the connection in a
        way that looks like a server fault rather than a template bug.

        They were `var` declarations in an inline script until M26, when the
        last inline script was removed so the page could carry a real
        Content-Security-Policy. The values now travel as `<meta>` tags and are
        assigned by `transport_bootstrap.js`, so this checks the template still
        supplies each one -- the contract with `evennia.js` is unchanged, only
        the delivery.

        """
        for name in (
            "aetos-websocket-active",
            "aetos-browser-sessid",
            "aetos-websocket-url",
            "aetos-websocket-port",
        ):
            self.assertIn('name="%s"' % name, self.base_text, "missing %r" % name)
        self.assertIn("transport_bootstrap.js", self.base_text)


class TestNoExternalResources(TestCase):
    """
    Aetos loads nothing from a third-party host.

    Blueprint section 2.2 sets a core-only dependency target. Beyond dependency
    hygiene this matters practically: a game on an offline or firewalled network
    must still work, a player's browser should not have to contact five third
    parties to play a MUD, and an unpinned CDN URL is a silent breaking-change
    vector for every install at once.

    """

    def _templates(self):
        return list(Path(AETOS_TEMPLATE_DIR).rglob("*.html"))

    def test_no_template_loads_an_external_resource(self):
        offenders = []
        for path in self._templates():
            code = _strip_template_comments(path.read_text(encoding="utf-8"))
            for line in code.splitlines():
                if 'src="http' in line or "src=http" in line or 'href="http' in line:
                    offenders.append("%s: %s" % (path.name, line.strip()[:80]))
        self.assertEqual(offenders, [], "external resources found: %s" % offenders)

    def test_no_reference_to_the_stock_cdn_hosts(self):
        """
        Named individually so a regression reports exactly which dependency
        crept back in.

        """
        hosts = (
            "code.jquery.com",
            "maxcdn.bootstrapcdn.com",
            "golden-layout.com",
            "cdn.rawgit.com",
            "cdnjs.cloudflare.com",
        )
        for path in self._templates():
            code = _strip_template_comments(path.read_text(encoding="utf-8"))
            for host in hosts:
                self.assertNotIn(host, code, "%s references %s" % (path.name, host))


class TestStockAssumptionsStillHold(TestCase):
    """
    Guards on the upstream behaviour the installation mechanism depends upon.

    If any of these change in Evennia, the Aetos installation instructions need
    revisiting -- and this is where that should surface.

    """

    def test_stock_base_template_still_exists(self):
        """Aetos extends this template; its removal would break the client."""
        base = Path(evennia.__file__).parent / "web" / "templates" / "webclient" / "base.html"
        self.assertTrue(base.is_file())

    def test_stock_base_still_defines_the_guilib_import_block(self):
        """The seam Aetos overrides must still be present in stock."""
        base = Path(evennia.__file__).parent / "web" / "templates" / "webclient" / "base.html"
        self.assertIn("{% block guilib_import %}", base.read_text(encoding="utf-8"))

    def test_dirs_are_searched_before_installed_apps(self):
        """
        Aetos must prepend to DIRS rather than rely on the app-directory loader.

        Django searches every DIRS entry before any installed app, and stock
        Evennia always places its own web/templates/webclient in DIRS. An
        app-level template named webclient.html therefore can never win on its
        own. This test documents that dependency by asserting that APP_DIRS is
        enabled *and* that the stock webclient template directory is in DIRS --
        the exact combination that makes the prepend necessary.

        """
        engine = settings.TEMPLATES[0]
        self.assertTrue(engine.get("APP_DIRS"))
        stock_webclient_dir = str(Path(evennia.__file__).parent / "web" / "templates" / "webclient")
        self.assertIn(stock_webclient_dir, [str(entry) for entry in engine["DIRS"]])
