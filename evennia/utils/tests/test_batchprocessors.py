"""Tests for batchprocessors """

import codecs
from django.test import TestCase
from evennia.utils import batchprocessors, utils
import mock


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
