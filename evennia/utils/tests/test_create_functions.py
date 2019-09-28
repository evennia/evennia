"""
Tests of create functions

"""

from evennia.utils.test_resources import EvenniaTest
from evennia.scripts.scripts import DefaultScript
from evennia.utils import create


class TestCreateScript(EvenniaTest):
    def test_create_script(self):
        class TestScriptA(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.persistent = False

        script = create.create_script(TestScriptA, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.key == "test_script"
        script.stop()

    def test_create_script_w_repeats_equal_1(self):
        class TestScriptB(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 1
                self.persistent = False

        # script is already stopped (interval=1, start_delay=False)
        script = create.create_script(TestScriptB, key="test_script")
        assert script is None

    def test_create_script_w_repeats_equal_1_persisted(self):
        class TestScriptB1(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 1
                self.persistent = True

        # script is already stopped (interval=1, start_delay=False)
        script = create.create_script(TestScriptB1, key="test_script")
        assert script is None

    def test_create_script_w_repeats_equal_2(self):
        class TestScriptC(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 2
                self.persistent = False

        script = create.create_script(TestScriptC, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.repeats == 2
        assert script.key == "test_script"
        script.stop()

    def test_create_script_w_repeats_equal_1_and_delayed(self):
        class TestScriptD(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.start_delay = True
                self.repeats = 1
                self.persistent = False

        script = create.create_script(TestScriptD, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.repeats == 1
        assert script.key == "test_script"
        script.stop()
