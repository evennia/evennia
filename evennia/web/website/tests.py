from django.conf import settings
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.text import slugify

from evennia.help import filehelp
from evennia.utils import class_from_module
from evennia.utils.create import create_help_entry
from evennia.utils.test_resources import BaseEvenniaTest

_FILE_HELP_ENTRIES = None


class EvenniaWebTest(BaseEvenniaTest):

    # Use the same classes the views are expecting
    account_typeclass = settings.BASE_ACCOUNT_TYPECLASS
    object_typeclass = settings.BASE_OBJECT_TYPECLASS
    character_typeclass = settings.BASE_CHARACTER_TYPECLASS
    exit_typeclass = settings.BASE_EXIT_TYPECLASS
    room_typeclass = settings.BASE_ROOM_TYPECLASS
    script_typeclass = settings.BASE_SCRIPT_TYPECLASS
    channel_typeclass = settings.BASE_CHANNEL_TYPECLASS

    # Default named url
    url_name = "index"

    # Response to expect for unauthenticated requests
    unauthenticated_response = 200

    # Response to expect for authenticated requests
    authenticated_response = 200

    def setUp(self):
        super().setUp()

        # Add chars to account rosters
        self.account.db._playable_characters = [self.char1]
        self.account2.db._playable_characters = [self.char2]

        for account in (self.account, self.account2):
            # Demote accounts to Player permissions
            account.permissions.add("Player")
            account.permissions.remove("Developer")

            # Grant permissions to chars
            for char in account.db._playable_characters:
                char.locks.add("edit:id(%s) or perm(Admin)" % account.pk)
                char.locks.add("delete:id(%s) or perm(Admin)" % account.pk)
                char.locks.add("view:all()")

    def test_valid_chars(self):
        "Make sure account has playable characters"
        self.assertTrue(self.char1 in self.account.db._playable_characters)
        self.assertTrue(self.char2 in self.account2.db._playable_characters)

    def get_kwargs(self):
        return {}

    def test_get(self):
        # Try accessing page while not logged in
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()))
        self.assertEqual(response.status_code, self.unauthenticated_response)

    def login(self):
        return self.client.login(username="TestAccount", password="testpassword")

    def test_get_authenticated(self):
        logged_in = self.login()
        self.assertTrue(logged_in, "Account failed to log in!")

        # Try accessing page while logged in
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)

        self.assertEqual(response.status_code, self.authenticated_response)


# ------------------------------------------------------------------------------


class AdminTest(EvenniaWebTest):
    url_name = "django_admin"
    unauthenticated_response = 302


class IndexTest(EvenniaWebTest):
    url_name = "index"


class RegisterTest(EvenniaWebTest):
    url_name = "register"


class LoginTest(EvenniaWebTest):
    url_name = "login"


class LogoutTest(EvenniaWebTest):
    url_name = "logout"


class PasswordResetTest(EvenniaWebTest):
    url_name = "password_change"
    unauthenticated_response = 302


class WebclientTest(EvenniaWebTest):
    url_name = "webclient:index"

    @override_settings(WEBCLIENT_ENABLED=True)
    def test_get(self):
        self.authenticated_response = 200
        self.unauthenticated_response = 200
        super().test_get()

    @override_settings(WEBCLIENT_ENABLED=False)
    def test_get_disabled(self):
        self.authenticated_response = 404
        self.unauthenticated_response = 404
        super().test_get()


class ChannelListTest(EvenniaWebTest):
    url_name = "channels"


class ChannelDetailTest(EvenniaWebTest):
    url_name = "channel-detail"

    def setUp(self):
        super().setUp()

        klass = class_from_module(
            self.channel_typeclass, fallback=settings.FALLBACK_CHANNEL_TYPECLASS
        )

        # Create a channel
        klass.create("demo")

    def get_kwargs(self):
        return {"slug": slugify("demo")}


class HelpListTest(EvenniaWebTest):
    url_name = "help"


HELP_ENTRY_DICTS = [
    {"key": "unit test file entry", "category": "General", "text": "cache test file entry text"}
]


class HelpDetailTest(EvenniaWebTest):
    url_name = "help-entry-detail"

    def setUp(self):
        super().setUp()

        # create a db help entry
        create_help_entry("unit test db entry", "unit test db entry text", category="General")

    def get_kwargs(self):
        return {"category": slugify("general"), "topic": slugify("unit test db entry")}

    def test_view(self):
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.context["entry_text"], "unit test db entry text")

    def test_object_cache(self):
        # clear file help entries, use local HELP_ENTRY_DICTS to recreate new entries
        global _FILE_HELP_ENTRIES
        if _FILE_HELP_ENTRIES is None:
            from evennia.help.filehelp import FILE_HELP_ENTRIES as _FILE_HELP_ENTRIES
        help_module = "evennia.web.website.tests"
        self.file_help_store = _FILE_HELP_ENTRIES.__init__(help_file_modules=[help_module])

        # request access to an entry
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.context["entry_text"], "unit test db entry text")
        # request a second entry, verifing the cached object is not provided on a new topic request
        entry_two_args = {"category": slugify("general"), "topic": slugify("unit test file entry")}
        response = self.client.get(reverse(self.url_name, kwargs=entry_two_args), follow=True)
        self.assertEqual(response.context["entry_text"], "cache test file entry text")


class HelpLockedDetailTest(EvenniaWebTest):
    url_name = "help-entry-detail"

    def setUp(self):
        super().setUp()

        # create a db entry with a lock
        self.db_help_entry = create_help_entry(
            "unit test locked topic",
            "unit test locked entrytext",
            category="General",
            locks="read:perm(Developer)",
        )

    def get_kwargs(self):
        return {"category": slugify("general"), "topic": slugify("unit test locked topic")}

    def test_locked_entry(self):
        # request access to an entry for permission the account does not have
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.context["entry_text"], "Failed to find entry.")

    def test_lock_with_perm(self):
        # log TestAccount in, grant permission required, read the entry
        self.login()
        self.account.permissions.add("Developer")
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.context["entry_text"], "unit test locked entrytext")


class CharacterCreateView(EvenniaWebTest):
    url_name = "character-create"
    unauthenticated_response = 302

    @override_settings(MAX_NR_CHARACTERS=1)
    def test_valid_access_multisession_0(self):
        "Account1 with no characters should be able to create a new one"
        self.account.db._playable_characters = []

        # Login account
        self.login()

        # Post data for a new character
        data = {"db_key": "gannon", "desc": "Some dude."}

        response = self.client.post(reverse(self.url_name), data=data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Make sure the character was actually created
        self.assertTrue(
            len(self.account.db._playable_characters) == 1,
            "Account only has the following characters attributed to it: %s"
            % self.account.db._playable_characters,
        )

    @override_settings(MAX_NR_CHARACTERS=5)
    def test_valid_access_multisession_2(self):
        "Account1 should be able to create multiple new characters"
        # Login account
        self.login()

        # Post data for a new character
        data = {"db_key": "gannon", "desc": "Some dude."}

        response = self.client.post(reverse(self.url_name), data=data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Make sure the character was actually created
        self.assertTrue(
            len(self.account.db._playable_characters) > 1,
            "Account only has the following characters attributed to it: %s"
            % self.account.db._playable_characters,
        )


class CharacterPuppetView(EvenniaWebTest):
    url_name = "character-puppet"
    unauthenticated_response = 302

    def get_kwargs(self):
        return {"pk": self.char1.pk, "slug": slugify(self.char1.name)}

    def test_invalid_access(self):
        "Account1 should not be able to puppet Account2:Char2"
        # Login account
        self.login()

        # Try to access puppet page for char2
        kwargs = {"pk": self.char2.pk, "slug": slugify(self.char2.name)}
        response = self.client.get(reverse(self.url_name, kwargs=kwargs), follow=True)
        self.assertTrue(
            response.status_code >= 400,
            "Invalid access should return a 4xx code-- either obj not found or permission denied!"
            " (Returned %s)" % response.status_code,
        )


class CharacterListView(EvenniaWebTest):
    url_name = "characters"
    unauthenticated_response = 302


class CharacterManageView(EvenniaWebTest):
    url_name = "character-manage"
    unauthenticated_response = 302


class CharacterUpdateView(EvenniaWebTest):
    url_name = "character-update"
    unauthenticated_response = 302

    def get_kwargs(self):
        return {"pk": self.char1.pk, "slug": slugify(self.char1.name)}

    def test_valid_access(self):
        "Account1 should be able to update Account1:Char1"
        # Login account
        self.login()

        # Try to access update page for char1
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.status_code, 200)

        # Try to update char1 desc
        data = {"db_key": self.char1.db_key, "desc": "Just a regular type of dude."}
        response = self.client.post(
            reverse(self.url_name, kwargs=self.get_kwargs()), data=data, follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Make sure the change was made successfully
        self.assertEqual(self.char1.db.desc, data["desc"])

    def test_invalid_access(self):
        "Account1 should not be able to update Account2:Char2"
        # Login account
        self.login()

        # Try to access update page for char2
        kwargs = {"pk": self.char2.pk, "slug": slugify(self.char2.name)}
        response = self.client.get(reverse(self.url_name, kwargs=kwargs), follow=True)
        self.assertEqual(response.status_code, 403)


class CharacterDeleteView(EvenniaWebTest):
    url_name = "character-delete"
    unauthenticated_response = 302

    def get_kwargs(self):
        return {"pk": self.char1.pk, "slug": slugify(self.char1.name)}

    def test_valid_access(self):
        "Account1 should be able to delete Account1:Char1"
        # Login account
        self.login()

        # Try to access delete page for char1
        response = self.client.get(reverse(self.url_name, kwargs=self.get_kwargs()), follow=True)
        self.assertEqual(response.status_code, 200)

        # Proceed with deleting it
        data = {"value": "yes"}
        response = self.client.post(
            reverse(self.url_name, kwargs=self.get_kwargs()), data=data, follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Make sure it deleted
        self.assertFalse(
            self.char1 in self.account.db._playable_characters,
            "Char1 is still in Account playable characters list.",
        )

    def test_invalid_access(self):
        "Account1 should not be able to delete Account2:Char2"
        # Login account
        self.login()

        # Try to access delete page for char2
        kwargs = {"pk": self.char2.pk, "slug": slugify(self.char2.name)}
        response = self.client.get(reverse(self.url_name, kwargs=kwargs), follow=True)
        self.assertEqual(response.status_code, 403)
