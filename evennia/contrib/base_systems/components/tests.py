from evennia.contrib.base_systems.components import Component, DBField, TagField
from evennia.contrib.base_systems.components.holder import ComponentProperty, ComponentHolderMixin
from evennia.objects.objects import DefaultCharacter
from evennia.utils.test_resources import EvenniaTest


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


class CharacterWithComponents(ComponentHolderMixin, DefaultCharacter):
    test_a = ComponentProperty("test_a")
    test_b = ComponentProperty("test_b", my_int=3, my_list=[1, 2, 3])


class TestComponents(EvenniaTest):
    character_typeclass = CharacterWithComponents

    def test_character_has_class_components(self):
        assert self.char1.test_a
        assert self.char1.test_b

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
        test_c = self.char1.components.get('test_c')

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

    def test_can_access_component_regular_get(self):
        assert self.char1.cmp.test_a is self.char1.components.get('test_a')

    def test_returns_none_with_regular_get_when_no_attribute(self):
        assert self.char1.cmp.does_not_exist is None

    def test_host_has_class_component_tags(self):
        assert self.char1.tags.has(key="test_a", category="components")
        assert self.char1.tags.has(key="test_b", category="components")
        assert self.char1.tags.has(key="initial_value", category="test_b__default_tag")
        assert self.char1.test_b.default_tag == "initial_value"
        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(category="test_b__single_tag")
        assert not self.char1.tags.has(category="test_b__multiple_tags")

    def test_host_has_added_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        self.char1.components.add(rct)
        test_c = self.char1.components.get('test_c')

        assert self.char1.tags.has(key="test_c", category="components")
        assert self.char1.tags.has(key="added_value", category="test_c__added_tag")
        assert test_c.added_tag == "added_value"

    def test_host_has_added_default_component_tags(self):
        self.char1.components.add_default("test_c")
        test_c = self.char1.components.get("test_c")

        assert self.char1.tags.has(key="test_c", category="components")
        assert self.char1.tags.has(key="added_value", category="test_c__added_tag")
        assert test_c.added_tag == "added_value"

    def test_host_remove_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        assert self.char1.tags.has(key="test_c", category="components")
        handler.remove(rct)

        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(key="added_value", category="test_c__added_tag")

    def test_host_remove_by_name_component_tags(self):
        rct = RuntimeComponentTestC.create(self.char1)
        handler = self.char1.components
        handler.add(rct)
        assert self.char1.tags.has(key="test_c", category="components")
        handler.remove_by_name("test_c")

        assert not self.char1.tags.has(key="test_c", category="components")
        assert not self.char1.tags.has(key="added_value", category="test_c__added_tag")

    def test_component_tags_only_hold_one_value_when_enforce_single(self):
        test_b = self.char1.components.get('test_b')
        test_b.single_tag = "first_value"
        test_b.single_tag = "second value"

        assert self.char1.tags.has(key="second value", category="test_b__single_tag")
        assert test_b.single_tag == "second value"
        assert not self.char1.tags.has(key="first_value", category="test_b__single_tag")

    def test_component_tags_default_value_is_overridden_when_enforce_single(self):
        test_b = self.char1.components.get('test_b')
        test_b.default_single_tag = "second value"

        assert self.char1.tags.has(key="second value", category="test_b__default_single_tag")
        assert test_b.default_single_tag == "second value"
        assert not self.char1.tags.has(key="first_value", category="test_b__default_single_tag")

    def test_component_tags_support_multiple_values_by_default(self):
        test_b = self.char1.components.get('test_b')
        test_b.multiple_tags = "first value"
        test_b.multiple_tags = "second value"
        test_b.multiple_tags = "third value"

        assert all(val in test_b.multiple_tags for val in ("first value", "second value", "third value"))
        assert self.char1.tags.has(key="first value", category="test_b__multiple_tags")
        assert self.char1.tags.has(key="second value", category="test_b__multiple_tags")
        assert self.char1.tags.has(key="third value", category="test_b__multiple_tags")
