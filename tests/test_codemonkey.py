# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
from viztracer.code_monkey import CodeMonkey, AstTransformer


class TestCodeMonkey(unittest.TestCase):
    def test_pure_compile(self):
        code_string = "a = 1"
        monkey = CodeMonkey(code_string, "test.py")
        _compile = monkey.compile
        _compile(code_string, "test.py", "exec")


class TestAstTransformer(unittest.TestCase):
    def test_invalid(self):
        tf = AstTransformer("invalid", "invalid")
        self.assertEqual(tf.get_assign_targets("invalid"), [])
        with self.assertRaises(ValueError):
            tf.get_instrument_node("invalid")
