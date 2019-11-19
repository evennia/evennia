from mock import Mock, patch

from evennia.utils.test_resources import EvenniaTest

from .bodyfunctions import BodyFunctions


@patch("evennia.contrib.tutorial_examples.bodyfunctions.random")
class TestBodyFunctions(EvenniaTest):
    script_typeclass = BodyFunctions

    def setUp(self):
        super(TestBodyFunctions, self).setUp()
        self.script.obj = self.char1

    def tearDown(self):
        super(TestBodyFunctions, self).tearDown()
        # if we forget to stop the script, DirtyReactorAggregateError will be raised
        self.script.stop()

    def test_at_repeat(self, mock_random):
        """test that no message will be sent when below the 66% threshold"""
        mock_random.random = Mock(return_value=0.5)
        old_func = self.script.send_random_message
        self.script.send_random_message = Mock()
        self.script.at_repeat()
        self.script.send_random_message.assert_not_called()
        # test that random message will be sent
        mock_random.random = Mock(return_value=0.7)
        self.script.at_repeat()
        self.script.send_random_message.assert_called()
        self.script.send_random_message = old_func

    def test_send_random_message(self, mock_random):
        """Test that correct message is sent for each random value"""
        old_func = self.char1.msg
        self.char1.msg = Mock()
        # test each of the values
        mock_random.random = Mock(return_value=0.05)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You tap your foot, looking around.")
        mock_random.random = Mock(return_value=0.15)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You have an itch. Hard to reach too.")
        mock_random.random = Mock(return_value=0.25)
        self.script.send_random_message()
        self.char1.msg.assert_called_with(
            "You think you hear someone behind you. ... " "but when you look there's noone there."
        )
        mock_random.random = Mock(return_value=0.35)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You inspect your fingernails. Nothing to report.")
        mock_random.random = Mock(return_value=0.45)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You cough discreetly into your hand.")
        mock_random.random = Mock(return_value=0.55)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You scratch your head, looking around.")
        mock_random.random = Mock(return_value=0.65)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You blink, forgetting what it was you were going to do.")
        mock_random.random = Mock(return_value=0.75)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You feel lonely all of a sudden.")
        mock_random.random = Mock(return_value=0.85)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You get a great idea. Of course you won't tell anyone.")
        mock_random.random = Mock(return_value=0.95)
        self.script.send_random_message()
        self.char1.msg.assert_called_with("You suddenly realize how much you love Evennia!")
        self.char1.msg = old_func
