# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import ast
from viztracer.code_monkey import CodeMonkey, AstTransformer
from .base_tmpl import BaseTmpl


class TestCodeMonkey(BaseTmpl):
    def test_pure_compile(self):
        code_string = "a = 1"
        monkey = CodeMonkey(code_string, "test.py")
        _compile = monkey.compile
        _compile(code_string, "test.py", "exec")


class TestAstTransformer(BaseTmpl):
    def test_invalid(self):
        tf = AstTransformer("invalid", "invalid")
        self.assertEqual(tf.get_assign_targets("invalid"), [])
        with self.assertRaises(ValueError):
            tf.get_instrument_node("invalid")

        self.assertEqual(tf.get_assign_targets_with_attr("invalid"), [])

    def test_get_string_of_expr(self):
        test_cases = ["a", "a[0]","a[1:]", "a[0:3]", "a[0:3:1]", "d['a']", "d['a'][0].b", "[a,b]", "(a,b)", "*a"]
        # just for coverage
        invalid_test_cases = ["a[1,2:3]", "a>b"]
        tf = AstTransformer("", "")
        for test_case in test_cases:
            tree = compile(test_case, "test.py", "exec", ast.PyCF_ONLY_AST)
            self.assertEqual(tf.get_string_of_expr(tree.body[0].value), test_case)
        for test_case in invalid_test_cases:
            tree = compile(test_case, "test.py", "exec", ast.PyCF_ONLY_AST)
            tf.get_string_of_expr(tree.body[0].value)

    def test_get_assign_log_nodes(self):
        tf = AstTransformer("log_var", {"varnames": "fi"})
        test_cases = [("fib = 1", 0)]
        for test_case, node_number in test_cases:
            tree = compile(test_case, "test.py", "exec", ast.PyCF_ONLY_AST)
            self.assertEqual(len(tf.get_assign_log_nodes(tree.body[0].targets[0])), node_number)
