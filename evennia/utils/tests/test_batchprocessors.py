"""Tests for batchprocessors """

import codecs
from django.test import TestCase
from evennia.utils import batchprocessors, utils
import mock
import textwrap


class TestBatchprocessorErrors(TestCase):

    @mock.patch.object(utils, 'pypath_to_realpath', return_value=[])
    def test_read_batchfile_raises_IOError(self, _):
        with self.assertRaises(IOError):
            batchprocessors.read_batchfile('foopath')

    @mock.patch.object(utils, 'pypath_to_realpath', return_value=['pathfoo'])
    @mock.patch.object(codecs, 'open', side_effect=ValueError('decodeerr'))
    @mock.patch.object(batchprocessors, '_ENCODINGS', ['fooencoding'])
    def test_read_batchfile_raises_UnicodeDecodeError(self, *_):
        with self.assertRaises(UnicodeDecodeError, msg='decodeerr'):
            batchprocessors.read_batchfile('foopath')


class TestBatchCommandProcessor(TestCase):

    @mock.patch.object(batchprocessors, 'read_batchfile')
    def test_parses_2_commands(self, mocked_read):
        mocked_read.return_value = textwrap.dedent(
        r"""
        @create rock
        #

        @set rock/desc =
        A big rock. You can tell is ancient.
        #

        """)
        commands = batchprocessors.BATCHCMD.parse_file('foopath')
        self.assertEqual([
            '@create rock', '@set rock/desc =\nA big rock. You can tell is ancient.'],
            commands)

    @mock.patch.object(batchprocessors, 'read_batchfile')
    def test_parses_INSERT(self, mocked_read):
        mocked_read.side_effect = [
        textwrap.dedent(r"""
            @create sky
            #
            #INSERT another.ev
            #
            @create sun
            #
            """),
        textwrap.dedent(r"""
            @create bird
            #
            @create cloud
            #
            """)
        ]
        commands = batchprocessors.BATCHCMD.parse_file('foopath')
        self.assertEqual(
            commands,
            ['@create sky', '@create bird', '@create cloud', '@create sun'])
        self.assertEqual(mocked_read.mock_calls, [
            mock.call('foopath', file_ending='.ev'),
            mock.call('another.ev', file_ending='.ev')])

    @mock.patch.object(batchprocessors, 'read_batchfile')
    def test_parses_INSERT_raises_IOError(self, mocked_read):
        mocked_read.side_effect = [
        textwrap.dedent(r"""
            @create sky
            #
            #INSERT x
            #
            @create sun
            #
            """),
            IOError
        ]
        with self.assertRaises(IOError, msg='#INSERT x failed.'):
            commands = batchprocessors.BATCHCMD.parse_file('foopath')
        self.assertEqual(mocked_read.mock_calls, [
            mock.call('foopath', file_ending='.ev'),
            mock.call('x', file_ending='.ev')])

