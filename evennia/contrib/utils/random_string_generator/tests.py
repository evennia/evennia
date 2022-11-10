"""
Random string tests.

"""

from evennia.utils.test_resources import BaseEvenniaTest

from . import random_string_generator

SIMPLE_GENERATOR = random_string_generator.RandomStringGenerator("simple", "[01]{2}")


class TestRandomStringGenerator(BaseEvenniaTest):
    def test_generate(self):
        """Generate and fail when exhausted."""
        generated = []
        for i in range(4):
            generated.append(SIMPLE_GENERATOR.get())

        generated.sort()
        self.assertEqual(generated, ["00", "01", "10", "11"])

        # At this point, we have generated 4 strings.
        # We can't generate one more
        with self.assertRaises(random_string_generator.ExhaustedGenerator):
            SIMPLE_GENERATOR.get()
