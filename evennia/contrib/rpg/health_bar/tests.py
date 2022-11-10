"""
Test health bar contrib

"""

from evennia.utils.test_resources import BaseEvenniaTest

from . import health_bar


class TestHealthBar(BaseEvenniaTest):
    def test_healthbar(self):
        expected_bar_str = "|[R|w|n|[B|w            test0 / 200test             |n"
        self.assertEqual(
            health_bar.display_meter(
                0, 200, length=40, pre_text="test", post_text="test", align="center"
            ),
            expected_bar_str,
        )
        expected_bar_str = "|[R|w     |n|[B|w       test24 / 200test            |n"
        self.assertEqual(
            health_bar.display_meter(
                24, 200, length=40, pre_text="test", post_text="test", align="center"
            ),
            expected_bar_str,
        )
        expected_bar_str = "|[Y|w           test100 /|n|[B|w 200test            |n"
        self.assertEqual(
            health_bar.display_meter(
                100, 200, length=40, pre_text="test", post_text="test", align="center"
            ),
            expected_bar_str,
        )
        expected_bar_str = "|[G|w           test180 / 200test        |n|[B|w    |n"
        self.assertEqual(
            health_bar.display_meter(
                180, 200, length=40, pre_text="test", post_text="test", align="center"
            ),
            expected_bar_str,
        )
        expected_bar_str = "|[G|w           test200 / 200test            |n|[B|w|n"
        self.assertEqual(
            health_bar.display_meter(
                200, 200, length=40, pre_text="test", post_text="test", align="center"
            ),
            expected_bar_str,
        )
