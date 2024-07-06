from evennia.objects.objects import DefaultCharacter
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaTest

from . import signals
from .component import Component
from .dbfield import DBField, TagField
from .holder import ComponentHolderMixin, ComponentProperty
from .signals import as_listener


class ComponentTestA(Component):
    name = "test_a"
    my_int = DBField(default=1)
    my_list = DBField(default=[], autocreate=True)


class ShadowedComponentTestA(ComponentTestA):
    name = "shadowed_test_a"
    slot = "ic_a"


class InheritedComponentTestA(ComponentTestA):
    name = "inherited_test_a"
    slot = "ic_a"

    my_other_int = DBField(default=2)


class ReplacementComponentTestA(InheritedComponentTestA):
    name = "replacement_inherited_test_a"
    slot = "ic_a"

    replacement_field = DBField(default=6)


class ComponentTestB(Component):
    name = "test_b"
    my_int = DBField(default=1)
    my_list = DBField(default=[], autocreate=True)
    default_tag = TagField(default="initial_value")
    single_tag = TagField(enforce_single=True)
    multiple_tags = TagField()
    default_single_tag = TagField(default="initial_value", enforce_single=True)


class RuntimeComponentTestC(Component):
    name = "test_c"
    my_int = DBField(default=6)
    my_dict = DBField(default={}, autocreate=True)
    added_tag = TagField(default="added_value")


class ComponentTestD(Component):
    name = "test_d"

    mixed_in = DBField(default=8)


class ShadowedCharacterMixin:
    ic_a = ComponentProperty("shadowed_test_a")


class CharacterMixinWithComponents:
    ic_a = ComponentProperty("inherited_test_a", my_other_int=33)
    test_d = ComponentProperty("test_d")


class CharacterWithComponents(
    ComponentHolderMixin, ShadowedCharacterMixin, CharacterMixinWithComponents, DefaultCharacter
):
    test_a = ComponentProperty("test_a")
    test_b = ComponentProperty("test_b", my_int=3, my_list=[1, 2, 3])
    ic_a = ComponentProperty("inherited_test_a", my_other_int=4)


class InheritedTCWithComponents(CharacterWithComponents):
    test_c = ComponentProperty("test_c")


class TestComponents(EvenniaTest):
    character_typeclass = CharacterWithComponents

    def test_character_has_class_components(self):
        self.assertTrue(self.char1.test_a)
        self.assertTrue(self.char1.test_b)

    def test_character_components_set_fields_properly(self):
        test_a_fields = self.char1.test_a._fields
        self.assertIn("my_int", test_a_fields)
        self.assertIn("my_list", test_a_fields)
        self.assertEqual(len(test_a_fields), 2)

        test_b_fields = self.char1.test_b._fields
        self.assertIn("my_int", test_b_fields)
        self.assertIn("my_list", test_b_fields)
        self.assertIn("default_tag", test_b_fields)
        self.assertIn("single_tag", test_b_fields)
        self.assertIn("multiple_tags", test_b_fields)
        self.assertIn("default_single_tag", test_b_fields)
        self.assertEqual(len(test_b_fields), 6)

        test_ic_a_fields = self.char1.ic_a._fields
        self.assertIn("my_int", test_ic_a_fields)
        self.assertIn("my_list", test_ic_a_fields)
        self.assertIn("my_other_int", test_ic_a_fields)
        self.assertEqual(len(test_ic_a_fields), 3)

    def test_inherited_typeclass_does_not_include_child_class_components(self):
        char_with_c = create.create_object(
            InheritedTCWithComponents, key="char_with_c", location=self.room1, home=self.room1
        )
        self.assertTrue(self.char1.test_a)
        self.assertFalse(self.char1.cmp.get("test_c"))
        self.assertTrue(char_with_c.test_c)

    def test_character_instances_components_properly(self):
        self.assertIsInstance(self.char1.test_a, ComponentTestA)
        self.assertIsInstance(self.char1.test_b, ComponentTestB)

    def test_character_assigns_default_value(self):
        self.assertEqual(self.char1.test_a.my_int, 1)
        self.assertEqual(self.char1.test_a.my_list, [])

    def test_character_assigns_default_provided_values(self):
        self.assertEqual(self.char1.test_b.my_int, 3)
        self.assertEqual(self.char1.test_b.my_list, [1, 2, 3])

    def test_character_has_autocreated_values(self):
        att_name = "test_b::my_list"
        self.assertEqual(self.char1.attributes.get(att_name), [1, 2, 3])

    def test_component_inheritance_properly_overrides_slots(self):
        self.assertEqual(self.char1.ic_a.name, "inherited_test_a")
        component_names = set(c[0] for c in self.char1._get_class_components())
        self.assertNotIn("shadowed_test_a", component_names)

    def test_component_inheritance_assigns_proper_values(self):
        self.assertEqual(self.char1.ic_a.my_int, 1)
        self.assertEqual(self.char1.ic_a.my_other_int, 4)

    def test_host_mixins_assigns_components(self):
        self.assertEqual(self.char1.test_d.mixed_in, 8)

    def test_character_can_register_runtime_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        self.char1.components.add(rct)
        test_c = self.char1.components.get("test_c")

        self.assertTrue(test_c)
        self.assertEqual(test_c.my_int, 6)
        self.assertEqual(test_c.my_dict, {})

    def test_handler_can_add_default_component(self):
        self.char1.components.add_default("test_c")
        test_c = self.char1.components.get("test_c")

        self.assertTrue(test_c)
        self.assertEqual(test_c.my_int, 6)

    def test_handler_has_returns_true_for_any_components(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)

        self.assertTrue(handler.has("test_a"))
        self.assertTrue(handler.has("test_b"))
        self.assertTrue(handler.has("test_c"))

    def test_can_remove_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        handler.remove(rct)

        self.assertTrue(handler.has("test_a"))
        self.assertTrue(handler.has("test_b"))
        self.assertFalse(handler.has("test_c"))

    def test_can_remove_component_by_name(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        handler.remove_by_name("test_c")

        self.assertTrue(handler.has("test_a"))
        self.assertTrue(handler.has("test_b"))
        self.assertFalse(handler.has("test_c"))

    def test_cannot_replace_component(self):
        with self.assertRaises(Exception):
            self.char1.test_a = None

    def test_can_get_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)

        self.assertIs(handler.get("test_c"), rct)

    def test_can_access_component_regular_get(self):
        self.assertIs(self.char1.cmp.test_a, self.char1.components.get("test_a"))

    def test_returns_none_with_regular_get_when_no_attribute(self):
        self.assertIs(self.char1.cmp.does_not_exist, None)

    def test_host_has_class_component_tags(self):
        self.assertTrue(self.char1.tags.has(key="test_a", category="components"))
        self.assertTrue(self.char1.tags.has(key="test_b", category="components"))
        self.assertTrue(self.char1.tags.has(key="initial_value", category="test_b::default_tag"))
        self.assertTrue(self.char1.test_b.default_tag == "initial_value")
        self.assertFalse(self.char1.tags.has(key="test_c", category="components"))
        self.assertFalse(self.char1.tags.has(category="test_b::single_tag"))
        self.assertFalse(self.char1.tags.has(category="test_b::multiple_tags"))

    def test_host_has_added_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        self.char1.components.add(rct)
        test_c = self.char1.components.get("test_c")

        self.assertTrue(self.char1.tags.has(key="test_c", category="components"))
        self.assertTrue(self.char1.tags.has(key="added_value", category="test_c::added_tag"))
        self.assertEqual(test_c.added_tag, "added_value")

    def test_host_has_added_default_component_tags(self):
        self.char1.components.add_default("test_c")
        test_c = self.char1.components.get("test_c")

        self.assertTrue(self.char1.tags.has(key="test_c", category="components"))
        self.assertTrue(self.char1.tags.has(key="added_value", category="test_c::added_tag"))
        self.assertEqual(test_c.added_tag, "added_value")

    def test_host_remove_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        self.assertTrue(self.char1.tags.has(key="test_c", category="components"))
        handler.remove(rct)

        self.assertFalse(self.char1.tags.has(key="test_c", category="components"))
        self.assertFalse(self.char1.tags.has(key="added_value", category="test_c::added_tag"))

    def test_host_remove_by_name_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        self.assertTrue(self.char1.tags.has(key="test_c", category="components"))
        handler.remove_by_name("test_c")

        self.assertFalse(self.char1.tags.has(key="test_c", category="components"))
        self.assertFalse(self.char1.tags.has(key="added_value", category="test_c::added_tag"))

    def test_component_tags_only_hold_one_value_when_enforce_single(self):
        test_b = self.char1.components.get("test_b")
        test_b.single_tag = "first_value"
        test_b.single_tag = "second value"

        self.assertTrue(self.char1.tags.has(key="second value", category="test_b::single_tag"))
        self.assertEqual(test_b.single_tag, "second value")
        self.assertFalse(self.char1.tags.has(key="first_value", category="test_b::single_tag"))

    def test_component_tags_default_value_is_overridden_when_enforce_single(self):
        test_b = self.char1.components.get("test_b")
        test_b.default_single_tag = "second value"

        self.assertTrue(
            self.char1.tags.has(key="second value", category="test_b::default_single_tag")
        )
        self.assertTrue(test_b.default_single_tag == "second value")
        self.assertFalse(
            self.char1.tags.has(key="first_value", category="test_b::default_single_tag")
        )

    def test_component_tags_support_multiple_values_by_default(self):
        test_b = self.char1.components.get("test_b")
        test_b.multiple_tags = "first value"
        test_b.multiple_tags = "second value"
        test_b.multiple_tags = "third value"

        self.assertTrue(
            all(
                val in test_b.multiple_tags
                for val in ("first value", "second value", "third value")
            )
        )
        self.assertTrue(self.char1.tags.has(key="first value", category="test_b::multiple_tags"))
        self.assertTrue(self.char1.tags.has(key="second value", category="test_b::multiple_tags"))
        self.assertTrue(self.char1.tags.has(key="third value", category="test_b::multiple_tags"))

    def test_mutables_are_not_shared_when_autocreate(self):
        self.char1.test_a.my_list.append(1)
        self.assertIsNot(self.char1.test_a.my_list, self.char2.test_a.my_list)

    def test_replacing_class_component_slot_with_runtime_component(self):
        self.char1.components.add_default("replacement_inherited_test_a")
        self.assertEqual(self.char1.ic_a.replacement_field, 6)


class CharWithSignal(ComponentHolderMixin, DefaultCharacter):
    @signals.as_listener
    def my_signal(self):
        setattr(self, "my_signal_is_called", True)

    @signals.as_listener
    def my_other_signal(self):
        setattr(self, "my_other_signal_is_called", True)

    @signals.as_responder
    def my_response(self):
        return 1

    @signals.as_responder
    def my_other_response(self):
        return 2


class ComponentWithSignal(Component):
    name = "test_signal_a"

    @signals.as_listener
    def my_signal(self):
        setattr(self, "my_signal_is_called", True)

    @signals.as_listener
    def my_other_signal(self):
        setattr(self, "my_other_signal_is_called", True)

    @signals.as_responder
    def my_response(self):
        return 1

    @signals.as_responder
    def my_other_response(self):
        return 2

    @signals.as_responder
    def my_component_response(self):
        return 3


class TestComponentSignals(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1 = create.create_object(
            CharWithSignal,
            key="Char",
        )

    def test_host_can_register_as_listener(self):
        self.char1.signals.trigger("my_signal")

        self.assertTrue(self.char1.my_signal_is_called)
        self.assertFalse(getattr(self.char1, "my_other_signal_is_called", None))

    def test_host_can_register_as_responder(self):
        responses = self.char1.signals.query("my_response")

        self.assertIn(1, responses)
        self.assertNotIn(2, responses)

    def test_component_can_register_as_listener(self):
        char = self.char1
        char.components.add(ComponentWithSignal.create(char))
        char.signals.trigger("my_signal")

        component = char.cmp.test_signal_a
        self.assertTrue(component.my_signal_is_called)
        self.assertFalse(getattr(component, "my_other_signal_is_called", None))

    def test_component_can_register_as_responder(self):
        char = self.char1
        char.components.add(ComponentWithSignal.create(char))
        responses = char.signals.query("my_response")

        self.assertIn(1, responses)
        self.assertNotIn(2, responses)

    def test_signals_can_add_listener(self):
        result = []

        def my_fake_listener():
            result.append(True)

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal")

        self.assertTrue(result)

    def test_signals_can_add_responder(self):
        def my_fake_responder():
            return 1

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response")

        self.assertIn(1, responses)

    def test_signals_can_remove_listener(self):
        result = []

        def my_fake_listener():
            result.append(True)

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.remove_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal")

        self.assertFalse(result)

    def test_signals_can_remove_responder(self):
        def my_fake_responder():
            return 1

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        self.char1.signals.remove_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response")

        self.assertFalse(responses)

    def test_signals_can_trigger_with_args(self):
        result = []

        def my_fake_listener(arg1, kwarg1):
            result.append((arg1, kwarg1))

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal", 1, kwarg1=2)

        self.assertIn((1, 2), result)

    def test_signals_can_query_with_args(self):
        def my_fake_responder(arg1, kwarg1):
            return (arg1, kwarg1)

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response", 1, kwarg1=2)

        self.assertIn((1, 2), responses)

    def test_signals_trigger_does_not_fail_without_listener(self):
        self.char1.signals.trigger("some_unknown_signal")

    def test_signals_query_does_not_fail_wihout_responders(self):
        self.char1.signals.query("no_responders_allowed")

    def test_signals_query_with_aggregate(self):
        def my_fake_responder(arg1, kwarg1):
            return (arg1, kwarg1)

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response", 1, kwarg1=2)

        self.assertIn((1, 2), responses)

    def test_signals_can_add_object_listeners_and_responders(self):
        result = []

        class FakeObj:
            @as_listener
            def my_signal(self):
                result.append(True)

        self.char1.signals.add_object_listeners_and_responders(FakeObj())
        self.char1.signals.trigger("my_signal")

        self.assertTrue(result)

    def test_signals_can_remove_object_listeners_and_responders(self):
        result = []

        class FakeObj:
            @as_listener
            def my_signal(self):
                result.append(True)

        obj = FakeObj()
        self.char1.signals.add_object_listeners_and_responders(obj)
        self.char1.signals.remove_object_listeners_and_responders(obj)
        self.char1.signals.trigger("my_signal")

        self.assertFalse(result)

    def test_component_handler_signals_connected_when_adding_default_component(self):
        char = self.char1
        char.components.add_default("test_signal_a")
        responses = char.signals.query("my_component_response")

        self.assertIn(3, responses)

    def test_component_handler_signals_disconnected_when_removing_component(self):
        char = self.char1
        comp = ComponentWithSignal.create(char)
        char.components.add(comp)
        char.components.remove(comp)
        responses = char.signals.query("my_component_response")

        self.assertFalse(responses)

    def test_component_handler_signals_disconnected_when_removing_component_by_name(self):
        char = self.char1
        char.components.add_default("test_signal_a")
        char.components.remove_by_name("test_signal_a")
        responses = char.signals.query("my_component_response")

        self.assertFalse(responses)
