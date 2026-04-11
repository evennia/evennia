import unittest

from django.test import override_settings

from evennia.utils.logger import mask_sensitive_input


class TestMaskSensitiveInput(unittest.TestCase):
    def test_connect(self):
        self.assertEqual(mask_sensitive_input("connect johnny password123"), "connect johnny ***********")
        self.assertEqual(
            mask_sensitive_input('connect "johnny five" "password 123"'),
            'connect "johnny five" **************',
        )
        self.assertEqual(mask_sensitive_input("conn johnny pass"), "conn johnny ********")

    def test_create(self):
        self.assertEqual(mask_sensitive_input("create johnny password123"), "create johnny ***********")
        self.assertEqual(mask_sensitive_input("cr johnny pass"), "cr johnny ********")

    def test_password(self):
        self.assertEqual(
            mask_sensitive_input("@password oldpassword = newpassword"),
            "@password *************************",
        )
        self.assertEqual(
            mask_sensitive_input("password oldpassword newpassword"),
            "password ***********************",
        )

    def test_userpassword(self):
        self.assertEqual(
            mask_sensitive_input("@userpassword johnny = password234"),
            "@userpassword johnny = ***********",
        )

    def test_non_sensitive(self):
        safe = "say connect johnny password123"
        self.assertEqual(mask_sensitive_input(safe), safe)

    @override_settings(AUDIT_MASKS=[{"mylogin": r"^mylogin\s+\w+\s+(?P<secret>.+)$"}])
    def test_override_settings_masks(self):
        self.assertEqual(mask_sensitive_input("mylogin johnny customsecret"), "mylogin johnny ************")
        # default masks are replaced when overridden.
        self.assertEqual(
            mask_sensitive_input("connect johnny password123"),
            "connect johnny password123",
        )
