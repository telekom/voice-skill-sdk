#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest
from sys import exc_info

from skill_sdk.caching.keys import FunctionCallKeyGenerator


class TestFunctionCallKeyGeneratorWoType(unittest.TestCase):

    def setUp(self):
        self.keygen = FunctionCallKeyGenerator('test', hashing=False, type_safe=False, protocol=3)

    def test_function(self):
        result = self.keygen(str, None, None)
        self.assertEqual(result, b'test_\x80\x03X\x03\x00\x00\x00strq\x00NN\x87q\x01.')

    def test_function_full_qualified_name(self):
        result = self.keygen(exc_info, None, None)
        self.assertEqual(result, b'test_\x80\x03X\x08\x00\x00\x00exc_infoq\x00NN\x87q\x01.')

    def test_args(self):
        result = self.keygen(str, [1, 'abc', None], None)
        self.assertEqual(result,
                         b'test_\x80\x03X\x03\x00\x00\x00strq\x00]q\x01(K\x01X\x03\x00\x00\x00abcq\x02NeN\x87q\x03.')

    def test_kwargs(self):
        result = self.keygen(str, None, {'a': 5})
        self.assertEqual(result,
                         b'test_\x80\x03X\x03\x00\x00\x00strq\x00N}q\x01X\x01\x00\x00\x00aq\x02K\x05s\x87q\x03.')


class TestFunctionCallKeyGeneratorWithType(unittest.TestCase):

    def setUp(self):
        self.keygen = FunctionCallKeyGenerator('test', hashing=False, type_safe=True, protocol=3)

    def test_function(self):
        result = self.keygen(str, None, None)
        self.assertEqual(result, b'test_\x80\x03X\x08\x00\x00\x00str_typeq\x00NN\x87q\x01.')

    def test_args(self):
        result = self.keygen(str, [1, 'abc', None], None)
        self.assertEqual(result,
                         b'test_\x80\x03X\x08\x00\x00\x00str_typeq\x00]q\x01(K\x01X\x03\x00\x00\x00abcq\x02NeN\x87q\x03.')

    def test_kwargs(self):
        result = self.keygen(str, None, {'a': 5})
        self.assertEqual(result,
                         b'test_\x80\x03X\x08\x00\x00\x00str_typeq\x00N}q\x01X\x01\x00\x00\x00aq\x02K\x05s\x87q\x03.')


class TestFunctionCallKeyGeneratorWithHashing(unittest.TestCase):

    def setUp(self):
        self.keygen = FunctionCallKeyGenerator('test', hashing=True, type_safe=True, protocol=3)

    def test_function(self):
        result = self.keygen(str, None, None)
        self.assertEqual(result,
                         b'test_4\xec\x1d\xb7\xbbN\xd1r\x08I\x9f\xdd`]\x1b\xb0\x83[}\xcf\x8e/\xf4L\xfaU\xa6\x9fk(S\x94\xf3'
                         b'\x04-6}{0]\xf1\xbbZ\x9b\xb9\x8c\x81\xaa@\xb5\x8d(\x17\xf6\xb00TY\xc0W\xaemfC')

    def test_args(self):
        result = self.keygen(str, [1, 'abc', None], None)
        self.assertEqual(result,
                         b'test_K\x95(\x1b\xf0\x06 \xce\xf5c1y\xbf\xccS~Y\xd6\x19\x10"UN1\x16o\xa5"\xd3\xa4B*\xc4#\x1c\xdcj'
                         b'a\x02hU7\xfd\xf8\\x\x0e\xde\x81\xa8\'\x0b\x7f\xde\xb2\x9a>\x8bU\xf4\xb2\x05}P')

    def test_kwargs(self):
        result = self.keygen(str, None, {'a': 5})
        self.assertEqual(result,
                         b"test_\xd0\x94\xa6r-\xf8\x96\xc3\xaf\x11\x8e\x9d\x13\xaf'GL\xd3\x0f>\xf3\x1cz\xb2l\xecUj)\xf2k"
                         b"\xa2\xbdu\xe4\x14\xd8\x95>\xe2\x19\xbcd\x1c\x890\xf7g\x92\xef\xc7M\xa5\xd3\xf8R~2\xe1\x1a\x93"
                         b"\xdeO>")


class TestKeyGeneratorPrefixFromConfig(unittest.TestCase):

    def setUp(self):
        self.keygen = FunctionCallKeyGenerator(hashing=False, type_safe=False, protocol=3)

    def test_function(self, *_):
        result = self.keygen(str, None, None)
        self.assertEqual(result,
                         b'unnamed-skill_\x80\x03X\x03\x00\x00\x00strq\x00NN\x87q\x01.')
