from evennia.contrib.base_systems import components
from evennia.contrib.base_systems.components import (
    Component,
    DBField,
    TagField,
    signals,
)
from evennia.contrib.base_systems.components.holder import (
    ComponentHolderMixin,
    ComponentProperty,
)
from evennia.contrib.base_systems.components.signals import as_listener
from evennia.objects.objects import DefaultCharacter
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaTest


class ComponentTestA(Component):
    name = "test_a"
    my_int = DBField(default=1)
    my_list = DBField(default=[])

class ComponentTestA(Component):
    name = "test_a"
    my_int = DBField(default=1)
    my_list = DBField(default=[])

class ComponentTestB(Component):
    name = "test_b"
    my_int = DBField(default=1)
    my_list = DBField(default=[])
    default_tag = TagField(default="initial_value")
    single_tag = TagField(enforce_single=True)
    multiple_tags = TagField()
    default_single_tag = TagField(default="initial_value", enforce_single=True)


class RuntimeComponentTestC(Component):
    name = "test_c"
    my_int = DBField(default=6)
    my_dict = DBField(default={})
    added_tag = TagField(default="added_value")

class RuntimeComponentTestC_Inherit(RuntimeComponentTestC):
    name = "test_c_inherit"
    added_tag = TagField(default="added_value_inherit")
    added_tag_inherit = TagField(default="added_value")
    different_tag = TagField(default="different_value_inherit")

class CharacterWithComponents(ComponentHolderMixin, DefaultCharacter):
    test_a = ComponentProperty("test_a")
    test_b = ComponentProperty("test_b", my_int=3, my_list=[1, 2, 3])


class InheritedTCWithComponents(CharacterWithComponents):
    test_c = ComponentProperty("test_c")


class TestComponents(EvenniaTest):
    character_typeclass = CharacterWithComponents

    def test_character_has_class_components(self):
        assert self.char1.test_a
        assert self.char1.test_b

    def test_inherited_typeclass_does_not_include_child_class_components(self):
        char_with_c = create.create_object(
            InheritedTCWithComponents, key="char_with_c", location=self.room1, home=self.room1
        )
        assert self.char1.test_a
        assert not self.char1.cmp.get("test_c")
        assert char_with_c.test_c

    def test_character_instances_components_properly(self):
        assert isinstance(self.char1.test_a, ComponentTestA)
        assert isinstance(self.char1.test_b, ComponentTestB)

    def test_character_assigns_default_value(self):
        assert self.char1.test_a.my_int == 1
        assert self.char1.test_a.my_list == []

    def test_character_assigns_default_provided_values(self):
        assert self.char1.test_b.my_int == 3
        assert self.char1.test_b.my_list == [1, 2, 3]

    def test_character_can_register_runtime_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        self.char1.components.add(rct)
        test_c = self.char1.components.get("test_c")

        assert test_c
        assert test_c.my_int == 6
        assert test_c.my_dict == {}

    def test_handler_can_add_default_component(self):
        self.char1.components.add_default("test_c")
        test_c = self.char1.components.get("test_c")

        assert test_c
        assert test_c.my_int == 6

    def test_handler_has_returns_true_for_any_components(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)

        assert handler.has("test_a")
        assert handler.has("test_b")
        assert handler.has("test_c")

    def test_can_remove_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        handler.remove(rct)

        assert handler.has("test_a")
        assert handler.has("test_b")
        assert not handler.has("test_c")

    def test_can_remove_component_by_name(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        handler.remove_by_name("test_c")

        assert handler.has("test_a")
        assert handler.has("test_b")
        assert not handler.has("test_c")

    def test_cannot_replace_component(self):
        with self.assertRaises(Exception):
            self.char1.test_a = None

    def test_can_get_component(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)

        assert handler.get("test_c") is rct

    def test_can_get_component_class(self):
        rtc_class = components.get_component_class("test_c")
        rtc_class_inh = components.get_component_class("test_c_inherit")

        # Test get_component_class gets the correct Class
        assert rtc_class is RuntimeComponentTestC
        assert rtc_class_inh is RuntimeComponentTestC_Inherit

        # We test two different types of objects. char1 will have both the base class
        # and the inheritted class components added to it (this would likely be uncommon
        # to see in practice).  char2 will only have the inheritted class attached
        # (likely the common case).
        rct_char1 = rtc_class.create(self.char1)
        rct_inherit_char1 = rtc_class_inh.create(self.char1)
        rct_inherit_char2 = rtc_class_inh.create(self.char2)

        handler_char1 = self.char1.components
        handler_char2 = self.char2.components
        # Add both base and inheritted instances to char1 
        handler_char1.add(rct_char1)
        handler_char1.add(rct_inherit_char1)
        # Add only inheritted instance to char2
        handler_char2.add(rct_inherit_char2)

        # Test that char1 has both base and inheritted components.
        assert handler_char1.get("test_c") is rct_char1
        assert handler_char1.get("test_c_inherit") is rct_inherit_char1
        # Test that char2 has inheritted component.
        assert handler_char2.get("test_c") is None
        assert handler_char2.get("test_c_inherit") is rct_inherit_char2

        # Char1 assertions on both base and inheritted component tags added.
        assert self.char1.tags.has(key="added_value",             category="test_c::added_tag")
        assert self.char1.tags.has(key="added_value",             category="test_c_inherit::added_tag_inherit")
        assert self.char1.tags.has(key="added_value_inherit",     category="test_c_inherit::added_tag")
        assert self.char1.tags.has(key="different_value_inherit", category="test_c_inherit::different_tag")

        # Char2 assertions on only inheritted component tags added.
        assert self.char2.tags.has(key="added_value",    category="test_c::added_tag") == False
        assert self.char2.tags.has(key="added_value",             category="test_c_inherit::added_tag_inherit")
        assert self.char2.tags.has(key="added_value_inherit",     category="test_c_inherit::added_tag")
        assert self.char2.tags.has(key="different_value_inherit", category="test_c_inherit::different_tag")

    def test_can_access_component_regular_get(self):
        assert self.char1.cmp.test_a is self.char1.components.get("test_a")

    def test_returns_none_with_regular_get_when_no_attribute(self):
        assert self.char1.cmp.does_not_exist is None

    def test_host_has_class_component_tags(self):
        assert self.char1.tags.has(key="test_a", category="components")
        assert self.char1.tags.has(key="test_b", category="components")
        assert self.char1.tags.has(key="initial_value", category="test_b::default_tag")
        assert self.char1.test_b.default_tag == "initial_value"
        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(category="test_b::single_tag")
        assert not self.char1.tags.has(category="test_b::multiple_tags")

    def test_host_has_added_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        self.char1.components.add(rct)
        test_c = self.char1.components.get("test_c")

        assert self.char1.tags.has(key="test_c", category="components")
        assert self.char1.tags.has(key="added_value", category="test_c::added_tag")
        assert test_c.added_tag == "added_value"

    def test_host_has_added_default_component_tags(self):
        self.char1.components.add_default("test_c")
        test_c = self.char1.components.get("test_c")

        assert self.char1.tags.has(key="test_c", category="components")
        assert self.char1.tags.has(key="added_value", category="test_c::added_tag")
        assert test_c.added_tag == "added_value"

    def test_host_remove_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        assert self.char1.tags.has(key="test_c", category="components")
        handler.remove(rct)

        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(key="added_value", category="test_c::added_tag")

    def test_host_remove_by_name_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        assert self.char1.tags.has(key="test_c", category="components")
        handler.remove_by_name("test_c")

        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(key="added_value", category="test_c::added_tag")

    def test_component_tags_only_hold_one_value_when_enforce_single(self):
        test_b = self.char1.components.get("test_b")
        test_b.single_tag = "first_value"
        test_b.single_tag = "second value"

        assert self.char1.tags.has(key="second value", category="test_b::single_tag")
        assert test_b.single_tag == "second value"
        assert not self.char1.tags.has(key="first_value", category="test_b::single_tag")

    def test_component_tags_default_value_is_overridden_when_enforce_single(self):
        test_b = self.char1.components.get("test_b")
        test_b.default_single_tag = "second value"

        assert self.char1.tags.has(key="second value", category="test_b::default_single_tag")
        assert test_b.default_single_tag == "second value"
        assert not self.char1.tags.has(key="first_value", category="test_b::default_single_tag")

    def test_component_tags_support_multiple_values_by_default(self):
        test_b = self.char1.components.get("test_b")
        test_b.multiple_tags = "first value"
        test_b.multiple_tags = "second value"
        test_b.multiple_tags = "third value"

        assert all(
            val in test_b.multiple_tags for val in ("first value", "second value", "third value")
        )
        assert self.char1.tags.has(key="first value", category="test_b::multiple_tags")
        assert self.char1.tags.has(key="second value", category="test_b::multiple_tags")
        assert self.char1.tags.has(key="third value", category="test_b::multiple_tags")


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

        assert self.char1.my_signal_is_called
        assert not getattr(self.char1, "my_other_signal_is_called", None)

    def test_host_can_register_as_responder(self):
        responses = self.char1.signals.query("my_response")

        assert 1 in responses
        assert 2 not in responses

    def test_component_can_register_as_listener(self):
        char = self.char1
        char.components.add(ComponentWithSignal.create(char))
        char.signals.trigger("my_signal")

        component = char.cmp.test_signal_a
        assert component.my_signal_is_called
        assert not getattr(component, "my_other_signal_is_called", None)

    def test_component_can_register_as_responder(self):
        char = self.char1
        char.components.add(ComponentWithSignal.create(char))
        responses = char.signals.query("my_response")

        assert 1 in responses
        assert 2 not in responses

    def test_signals_can_add_listener(self):
        result = []

        def my_fake_listener():
            result.append(True)

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal")

        assert result

    def test_signals_can_add_responder(self):
        def my_fake_responder():
            return 1

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response")

        assert 1 in responses

    def test_signals_can_remove_listener(self):
        result = []

        def my_fake_listener():
            result.append(True)

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.remove_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal")

        assert not result

    def test_signals_can_remove_responder(self):
        def my_fake_responder():
            return 1

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        self.char1.signals.remove_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response")

        assert not responses

    def test_signals_can_trigger_with_args(self):
        result = []

        def my_fake_listener(arg1, kwarg1):
            result.append((arg1, kwarg1))

        self.char1.signals.add_listener("my_fake_signal", my_fake_listener)
        self.char1.signals.trigger("my_fake_signal", 1, kwarg1=2)

        assert (1, 2) in result

    def test_signals_can_query_with_args(self):
        def my_fake_responder(arg1, kwarg1):
            return (arg1, kwarg1)

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response", 1, kwarg1=2)

        assert (1, 2) in responses

    def test_signals_trigger_does_not_fail_without_listener(self):
        self.char1.signals.trigger("some_unknown_signal")

    def test_signals_query_does_not_fail_wihout_responders(self):
        self.char1.signals.query("no_responders_allowed")

    def test_signals_query_with_aggregate(self):
        def my_fake_responder(arg1, kwarg1):
            return (arg1, kwarg1)

        self.char1.signals.add_responder("my_fake_response", my_fake_responder)
        responses = self.char1.signals.query("my_fake_response", 1, kwarg1=2)

        assert (1, 2) in responses

    def test_signals_can_add_object_listeners_and_responders(self):
        result = []

        class FakeObj:
            @as_listener
            def my_signal(self):
                result.append(True)

        self.char1.signals.add_object_listeners_and_responders(FakeObj())
        self.char1.signals.trigger("my_signal")

        assert result

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

        assert not result

    def test_component_handler_signals_connected_when_adding_default_component(self):
        char = self.char1
        char.components.add_default("test_signal_a")
        responses = char.signals.query("my_component_response")

        assert 3 in responses

    def test_component_handler_signals_disconnected_when_removing_component(self):
        char = self.char1
        comp = ComponentWithSignal.create(char)
        char.components.add(comp)
        char.components.remove(comp)
        responses = char.signals.query("my_component_response")

        assert not responses

    def test_component_handler_signals_disconnected_when_removing_component_by_name(self):
        char = self.char1
        char.components.add_default("test_signal_a")
        char.components.remove_by_name("test_signal_a")
        responses = char.signals.query("my_component_response")

        assert not responses
