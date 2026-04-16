"""Tests for batchprocessors"""

import codecs
import textwrap

import mock
from django.test import TestCase

from evennia.utils import batchprocessors, utils


class TestBatchprocessorErrors(TestCase):
    @mock.patch.object(utils, "pypath_to_realpath", return_value=[])
    def test_read_batchfile_raises_IOError(self, _):
        with self.assertRaises(IOError):
            batchprocessors.read_batchfile("foopath")

    @mock.patch.object(utils, "pypath_to_realpath", return_value=["pathfoo"])
    @mock.patch.object(codecs, "open", side_effect=ValueError("decodeerr"))
    @mock.patch.object(batchprocessors, "_ENCODINGS", ["fooencoding"])
    def test_read_batchfile_raises_UnicodeDecodeError(self, *_):
        with self.assertRaises(UnicodeDecodeError, msg="decodeerr"):
            batchprocessors.read_batchfile("foopath")


class TestBatchCommandProcessor(TestCase):
    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_2_commands(self, mocked_read):
        mocked_read.return_value = textwrap.dedent(
            r"""
        @create rock
        #

        @set rock/desc =
        A big rock. You can tell is ancient.
        #

        """
        )
        commands = batchprocessors.BATCHCMD.parse_file("foopath")
        self.assertEqual(
            ["@create rock", "@set rock/desc =\nA big rock. You can tell is ancient."], commands
        )

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_INSERT(self, mocked_read):
        mocked_read.side_effect = [
            textwrap.dedent(
                r"""
            @create sky
            #
            #INSERT another.ev
            #
            @create sun
            #
            """
            ),
            textwrap.dedent(
                r"""
            @create bird
            #
            @create cloud
            #
            """
            ),
        ]
        commands = batchprocessors.BATCHCMD.parse_file("foopath")
        self.assertEqual(commands, ["@create sky", "@create bird", "@create cloud", "@create sun"])
        self.assertEqual(
            mocked_read.mock_calls,
            [mock.call("foopath", file_ending=".ev"), mock.call("another.ev", file_ending=".ev")],
        )

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_INSERT_raises_IOError(self, mocked_read):
        mocked_read.side_effect = [
            textwrap.dedent(
                r"""
            @create sky
            #
            #INSERT x
            #
            @create sun
            #
            """
            ),
            IOError,
        ]
        with self.assertRaises(IOError, msg="#INSERT x failed."):
            batchprocessors.BATCHCMD.parse_file("foopath")
        self.assertEqual(
            mocked_read.mock_calls,
            [mock.call("foopath", file_ending=".ev"), mock.call("x", file_ending=".ev")],
        )

class TestReadBatchFile(TestCase):
    """Test read_batchfile line ending normalization."""

    @mock.patch.object(utils, "pypath_to_realpath", return_value=["testpath"])
    @mock.patch.object(codecs, "open")
    def test_normalizes_crlf_to_lf(self, mocked_open, _):
        """Test that CRLF line endings are normalized to LF.

        See: https://github.com/evennia/evennia/issues/3847
        """
        mocked_file = mock.MagicMock()
        mocked_file.read.return_value = "@create sky\r\n#INSERT another.ev\r\n"
        mocked_open.return_value.__enter__.return_value = mocked_file

        result = batchprocessors.read_batchfile("foopath")
        self.assertEqual(result, "@create sky\n#INSERT another.ev\n")

    @mock.patch.object(utils, "pypath_to_realpath", return_value=["testpath"])
    @mock.patch.object(codecs, "open")
    def test_normalizes_cr_to_lf(self, mocked_open, _):
        """Test that old Mac CR line endings are normalized to LF."""
        mocked_file = mock.MagicMock()
        mocked_file.read.return_value = "@create sky\r#INSERT another.ev\r"
        mocked_open.return_value.__enter__.return_value = mocked_file

        result = batchprocessors.read_batchfile("foopath")
        self.assertEqual(result, "@create sky\n#INSERT another.ev\n")


class TestBatchCodeProcessor(TestCase):
    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_one_codeblock(self, mocked_read):
        mocked_read.return_value = textwrap.dedent(
            r"""
        print("Hello")
        """
        )
        commands = batchprocessors.BATCHCODE.parse_file("foopath")
        self.assertEqual(['# batchcode code:\n\nprint("Hello")\n'], commands)

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_codeblocks(self, mocked_read):
        mocked_read.return_value = textwrap.dedent(
            r"""
        #CODE
        print("Hello")
        #CODE
        a = 1
        b = [1,
        2, 3]
        """
        )
        commands = batchprocessors.BATCHCODE.parse_file("foopath")
        self.assertEqual(
            [
                "# batchcode code:\n\n",
                '# batchcode code:\n\nprint("Hello")\n',
                "# batchcode code:\n\na = 1\nb = [1,\n2, 3]\n",
            ],
            commands,
        )

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_header_and_two_codeblock(self, mocked_read):
        mocked_read.return_value = textwrap.dedent(
            r"""
        #HEADER
        a = 100
        #CODE
        a += 100
        #CODE
        a += 100
        a == 100
        """
        )
        commands = batchprocessors.BATCHCODE.parse_file("foopath")
        self.assertEqual(
            [
                "# batchcode header:\n\na = 100\n\n\n# batchcode code:\n\n",
                "# batchcode header:\n\na = 100\n\n\n# batchcode code:\n\na += 100\n",
                "# batchcode header:\n\na = 100\n\n\n# batchcode code:\n\na += 100\na == 100\n",
            ],
            commands,
        )

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_INSERT(self, mocked_read):
        mocked_read.side_effect = [
            textwrap.dedent(
                r"""
            a = 1
            #INSERT another.py
            """
            ),
            textwrap.dedent(
                r"""
            print("Hello")
            """
            ),
        ]
        commands = batchprocessors.BATCHCODE.parse_file("foopath")
        self.assertEqual(
            commands,
            [
                "# batchcode code:\n"
                "\n"
                "a = 1\n"
                "# batchcode insert (another.py):# batchcode code:\n"
                "\n"
                'print("Hello")\n'
                "\n"
            ],
        )
        self.assertEqual(
            mocked_read.mock_calls,
            [mock.call("foopath", file_ending=".py"), mock.call("another.py", file_ending=".py")],
        )

    @mock.patch.object(batchprocessors, "read_batchfile")
    def test_parses_INSERT_raises_IOError(self, mocked_read):
        mocked_read.side_effect = [
            textwrap.dedent(
                r"""
            #INSERT x
            """
            ),
            IOError,
        ]
        with self.assertRaises(IOError, msg="#INSERT x failed."):
            batchprocessors.BATCHCODE.parse_file("foopath")
        self.assertEqual(
            mocked_read.mock_calls,
            [mock.call("foopath", file_ending=".py"), mock.call("x", file_ending=".py")],
        )

    @mock.patch("builtins.exec")
    def test_execs_codeblock(self, mocked_exec):
        err = batchprocessors.BATCHCODE.code_exec(
            '# batchcode code:\n\nprint("Hello")\n', extra_environ={}
        )
        self.assertIsNone(err)

    @mock.patch("builtins.exec")
    def test_execs_codeblock_with_extra_environ(self, mocked_exec):
        err = batchprocessors.BATCHCODE.code_exec(
            '# batchcode code:\n\nprint("Hello")\n', extra_environ={"foo": "bar", "baz": True}
        )
        self.assertIsNone(err)

    @mock.patch("builtins.exec")
    def test_execs_codeblock_raises(self, mocked_exec):
        mocked_exec.side_effect = Exception
        err = batchprocessors.BATCHCODE.code_exec(
            '# batchcode code:\n\nprint("Hello")\nprint("Evennia")', extra_environ={}
        )
        self.assertIsNotNone(err)
