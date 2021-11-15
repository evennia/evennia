from evennia.contrib.components import ComponentHolderMixin, Component, DBField, ComponentProperty
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


class RuntimeComponentTestC(Component):
    name = "test_c"
    my_int = DBField(default=6)
    my_dict = DBField(default={})


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

    def test_character_assigns_default_value_without_template(self):
        assert self.char1.test_a.my_int == 1
        assert self.char1.test_a.my_list == []

    def test_character_assigns_provided_values_with_template(self):
        assert self.char1.test_b.my_int == 3
        assert self.char1.test_b.my_list == [1, 2, 3]

    def test_character_can_register_runtime_component(self):
        rct = RuntimeComponentTestC.as_template()
        self.char1.components.add(rct)
        test_c = self.char1.components.get('test_c')

        assert test_c
        assert test_c.my_int == 6
        assert test_c.my_dict == {}

    def test_component_template_is_standalone(self):
        rct = RuntimeComponentTestC.as_template(my_int=10)

        assert rct.my_int == 10

    def test_component_duplicates_correctly(self):
        rct = RuntimeComponentTestC.as_template(my_int=10)
        new_rct = rct.duplicate(self.char1)
        self.char1.components.add(new_rct)
        test_c = self.char1.components.get('test_c')

        assert test_c.my_int == 10
        assert new_rct is not rct
