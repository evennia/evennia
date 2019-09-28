from django.conf import settings
from django.utils.text import slugify
from django.test import Client, override_settings
from django.urls import reverse
from evennia.utils import class_from_module
from evennia.utils.test_resources import EvenniaTest


class EvenniaWebTest(EvenniaTest):

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
        super(EvenniaWebTest, self).setUp()

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
        super(WebclientTest, self).test_get()

    @override_settings(WEBCLIENT_ENABLED=False)
    def test_get_disabled(self):
        self.authenticated_response = 404
        self.unauthenticated_response = 404
        super(WebclientTest, self).test_get()


class ChannelListTest(EvenniaWebTest):
    url_name = "channels"


class ChannelDetailTest(EvenniaWebTest):
    url_name = "channel-detail"

    def setUp(self):
        super(ChannelDetailTest, self).setUp()

        klass = class_from_module(self.channel_typeclass)

        # Create a channel
        klass.create("demo")

    def get_kwargs(self):
        return {"slug": slugify("demo")}


class CharacterCreateView(EvenniaWebTest):
    url_name = "character-create"
    unauthenticated_response = 302

    @override_settings(MULTISESSION_MODE=0)
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

    @override_settings(MULTISESSION_MODE=2)
    @override_settings(MAX_NR_CHARACTERS=10)
    def test_valid_access_multisession_2(self):
        "Account1 should be able to create a new character"
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
            "Invalid access should return a 4xx code-- either obj not found or permission denied! (Returned %s)"
            % response.status_code,
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
