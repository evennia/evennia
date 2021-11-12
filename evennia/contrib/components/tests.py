import mock

from evennia import DefaultCharacter
from evennia.utils.test_resources import EvenniaTest

from . import listing
from evennia.contrib.components import ComponentHolderMixin, Component, DBField


@listing.register
class ComponentTestA(Component):
    name = "test_a"
    my_int = DBField('my_int', default_value=1)
    my_list = DBField('my_list', default_value=list)

@listing.register
class ComponentTestB(Component):
    name = "test_b"
    my_int = DBField('my_int', default_value=1)
    my_list = DBField('my_list', default_value=list)


@listing.register
class RuntimeComponentTestC(Component):
    name = "test_c"
    my_int = DBField('my_int', default_value=6)
    my_dict = DBField('my_dict', default_value=dict)


class CharacterWithComponents(ComponentHolderMixin, DefaultCharacter):
    class_components = [
        ComponentTestA,
        ComponentTestB.as_template(my_int=3, my_list=[1, 2, 3])
    ]


class TestComponents(EvenniaTest):
    character_typeclass = CharacterWithComponents

    def test_character_has_class_components(self):
        assert self.char1.test_a
        assert self.char1.test_b

    def test_character_instances_components_properly(self):
        assert isinstance(self.char1.test_a, ComponentTestA)
        assert isinstance(self.char1.test_b, ComponentTestB)

    def test_character_assigns_default_value_without_template(self):
        assert self.char1.test_a.my_int == 1
        assert self.char1.test_a.my_list == []

    def test_character_assigns_provided_values_with_template(self):
        assert self.char1.test_b.my_int == 3
        assert self.char1.test_b.my_list == [1, 2, 3]

    def test_character_can_register_runtime_component(self):
        rct = RuntimeComponentTestC.default_create(None)
        self.char1.register_component(rct)

        assert self.char1.test_c
        assert self.char1.test_c.my_int == 6
        assert self.char1.test_c.my_dict == {}
        assert len(self.char1.runtime_component_names) == 1
        assert self.char1.runtime_component_names[0] == "test_c"

    def test_component_puppet_hooks_called(self):
        self.char1.test_b.at_post_puppet = mock.Mock()
        self.char1.test_b.at_post_unpuppet = mock.Mock()
        self.char1.at_post_puppet()
        self.char1.at_post_unpuppet(self.account)
        self.char1.test_b.at_post_puppet.assert_called()
        self.char1.test_b.at_post_unpuppet.assert_called()

    def test_all_components_show_in_components_instance(self):
        rct = RuntimeComponentTestC.default_create(None)
        self.char1.register_component(rct)
        components = self.char1.component_instances

        assert components.get("test_a") is self.char1.test_a
        assert components.get("test_b") is self.char1.test_b
        assert components.get("test_c") is rct
