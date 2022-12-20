"""
Tests for the REST API.

"""
from collections import namedtuple

from django.core.exceptions import ObjectDoesNotExist
from django.test import override_settings
from django.urls import include, path, reverse
from rest_framework.test import APIClient

from evennia.utils.test_resources import BaseEvenniaTest
from evennia.web.api import serializers

urlpatterns = [
    path(r"^", include("evennia.web.website.urls")),
    path(r"^api/", include("evennia.web.api.urls", namespace="api")),
]


@override_settings(REST_API_ENABLED=True, ROOT_URLCONF=__name__, AUTH_USERNAME_VALIDATORS=[])
class TestEvenniaRESTApi(BaseEvenniaTest):
    client_class = APIClient
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.account.is_superuser = True
        self.account.save()
        self.client.force_login(self.account)
        # scripts do not have default locks. Without them, even superuser access check fails
        self.script.locks.add("edit: perm(Admin); examine: perm(Admin); delete: perm(Admin)")

    def tearDown(self):
        try:
            super().tearDown()
        except ObjectDoesNotExist:
            pass

    def get_view_details(self, action):
        """Helper function for generating list of named tuples"""
        View = namedtuple(
            "View",
            [
                "view_name",
                "obj",
                "list",
                "serializer",
                "list_serializer",
                "create_data",
                "retrieve_data",
            ],
        )
        views = [
            View(
                "object-%s" % action,
                self.obj1,
                [self.obj1, self.char1, self.exit, self.room1, self.room2, self.obj2, self.char2],
                serializers.ObjectDBSerializer,
                serializers.ObjectListSerializer,
                {"db_key": "object-create-test-name"},
                serializers.ObjectDBSerializer(self.obj1).data,
            ),
            View(
                "character-%s" % action,
                self.char1,
                [self.char1, self.char2],
                serializers.ObjectDBSerializer,
                serializers.ObjectListSerializer,
                {"db_key": "character-create-test-name"},
                serializers.ObjectDBSerializer(self.char1).data,
            ),
            View(
                "exit-%s" % action,
                self.exit,
                [self.exit],
                serializers.ObjectDBSerializer,
                serializers.ObjectListSerializer,
                {"db_key": "exit-create-test-name"},
                serializers.ObjectDBSerializer(self.exit).data,
            ),
            View(
                "room-%s" % action,
                self.room1,
                [self.room1, self.room2],
                serializers.ObjectDBSerializer,
                serializers.ObjectListSerializer,
                {"db_key": "room-create-test-name"},
                serializers.ObjectDBSerializer(self.room1).data,
            ),
            View(
                "script-%s" % action,
                self.script,
                [self.script],
                serializers.ScriptDBSerializer,
                serializers.ScriptListSerializer,
                {"db_key": "script-create-test-name"},
                serializers.ScriptDBSerializer(self.script).data,
            ),
            View(
                "account-%s" % action,
                self.account2,
                [self.account, self.account2],
                serializers.AccountSerializer,
                serializers.AccountListSerializer,
                {"username": "account-create-test-name"},
                serializers.AccountSerializer(self.account2).data,
            ),
        ]
        return views

    def test_retrieve(self):
        views = self.get_view_details("detail")
        for view in views:
            with self.subTest(msg="Testing {} retrieve".format(view.view_name)):
                view_url = reverse("api:{}".format(view.view_name), kwargs={"pk": view.obj.pk})
                response = self.client.get(view_url)
                self.assertEqual(response.status_code, 200)
                self.assertDictEqual(response.data, view.retrieve_data)

    def test_update(self):
        views = self.get_view_details("detail")
        for view in views:
            with self.subTest(msg="Testing {} update".format(view.view_name)):
                view_url = reverse("api:{}".format(view.view_name), kwargs={"pk": view.obj.pk})
                # test both PUT (update) and PATCH (partial update) here
                for new_key, method in (("foobar", "put"), ("fizzbuzz", "patch")):
                    field = "username" if "account" in view.view_name else "db_key"
                    data = {field: new_key}
                    response = getattr(self.client, method)(view_url, data=data)
                    self.assertEqual(response.status_code, 200)
                    view.obj.refresh_from_db()
                    self.assertEqual(getattr(view.obj, field), new_key)
                    self.assertEqual(response.data[field], new_key)

    def test_delete(self):
        views = self.get_view_details("detail")
        for view in views:
            with self.subTest(msg="Testing {} delete".format(view.view_name)):
                view_url = reverse("api:{}".format(view.view_name), kwargs={"pk": view.obj.pk})
                response = self.client.delete(view_url)
                self.assertEqual(response.status_code, 204)
                with self.assertRaises(ObjectDoesNotExist):
                    view.obj.refresh_from_db()

    def test_list(self):
        views = self.get_view_details("list")
        for view in views:
            with self.subTest(msg=f"Testing {view.view_name} "):
                view_url = reverse(f"api:{view.view_name}")
                response = self.client.get(view_url)
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual(
                    response.data["results"], [view.list_serializer(obj).data for obj in view.list]
                )

    def test_create(self):
        views = self.get_view_details("list")
        for view in views:
            with self.subTest(msg=f"Testing {view.view_name} create"):
                # create is a POST request off of <type>-list
                view_url = reverse(f"api:{view.view_name}")
                # check failures from not sending required fields
                response = self.client.post(view_url)
                self.assertEqual(response.status_code, 400)
                # check success when sending the required data
                response = self.client.post(view_url, data=view.create_data)
                self.assertEqual(response.status_code, 201, f"Response was {response.data}")

    def test_set_attribute(self):
        views = self.get_view_details("set-attribute")
        for view in views:
            with self.subTest(msg=f"Testing {view.view_name}"):
                view_url = reverse(f"api:{view.view_name}", kwargs={"pk": view.obj.pk})
                # check failures from not sending required fields
                response = self.client.post(view_url)
                self.assertEqual(response.status_code, 400, f"Response was: {response.data}")
                # test adding an attribute
                self.assertEqual(view.obj.db.some_test_attr, None)
                attr_name = "some_test_attr"
                attr_data = {"db_key": attr_name, "db_value": "test_value"}
                response = self.client.post(view_url, data=attr_data)
                self.assertEqual(response.status_code, 200, f"Response was: {response.data}")
                self.assertEquals(view.obj.attributes.get(attr_name), "test_value")
                # now test removing it
                attr_data = {"db_key": attr_name}
                response = self.client.post(view_url, data=attr_data)
                self.assertEqual(response.status_code, 200, f"Response was: {response.data}")
                self.assertEquals(view.obj.attributes.get(attr_name), None)
