# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import ast
import textwrap

from viztracer.code_monkey import AstTransformer, CodeMonkey

from .base_tmpl import BaseTmpl
from .cmdline_tmpl import CmdlineTmpl


class TestCodeMonkey(BaseTmpl):
    def test_pure_compile(self):
        code_string = "a = 1"
        monkey = CodeMonkey("test.py")
        _compile = monkey.compile
        _compile(code_string, "test.py", "exec")

    def test_compile_empty_exception(self):
        code_string = textwrap.dedent(
            """
            try:
                a = 3 / 0
            except Exception as e:
                raise
            """)
        monkey = CodeMonkey("test.py")
        monkey.add_instrument("log_exception", {})
        _compile = monkey.compile
        _compile(code_string, "test.py", "exec")

    def test_source_processor(self):
        monkey = CodeMonkey("test.py")
        monkey.add_source_processor()
        tree = compile("a = 0", "test.py", "exec", ast.PyCF_ONLY_AST)
        _compile = monkey.compile
        # make sure AST can compile
        _compile(tree, "test.py", "exec")

        # some unittest
        self.assertIs(monkey.source_processor.process(tree), tree)
        self.assertEqual(monkey.source_processor.process(
            "# !viztracer: log_instant('test')"),
            "__viz_tracer__.log_instant('test')")
        self.assertEqual(monkey.source_processor.process(
            "a = 3  # !viztracer: log"),
            "a = 3  ; __viz_tracer__.log_var('a', (a))")
        self.assertEqual(monkey.source_processor.process(
            "f()  # !viztracer: log"),
            "f()  ; __viz_tracer__.log_instant('f()')")


class TestAstTransformer(BaseTmpl):
    def test_invalid(self):
        tf = AstTransformer("invalid", "invalid")
        self.assertEqual(tf.get_assign_targets("invalid"), [])
        with self.assertRaises(ValueError):
            tf.get_instrument_node("Exception", "invalid")

        self.assertEqual(tf.get_assign_targets_with_attr("invalid"), [])

    def test_get_string_of_expr(self):
        test_cases = ["a", "a[0]", "a[1:]", "a[0:3]", "a[0:3:1]", "d['a']", "d['a'][0].b", "[a,b]", "(a,b)", "*a"]
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


file_magic_comment = """
def test():
    pass
# !viztracer: log_instant("test")
a = 3  # !viztracer: log
# !viztracer: log_var("a", a)
# !viztracer: log_var("a", a) if a == 3
# !viztracer: log_var("a", a) if a != 3
a = 3  # !viztracer: log if a == 3
a = 3  # !viztracer: log if a != 3
test()  # !viztracer: log if a == 3
"""


class TestMagicComment(CmdlineTmpl):
    def test_log_var(self):
        def check_func(data):
            instant_count = 0
            var_count = 0
            for event in data["traceEvents"]:
                if event["ph"] == "i":
                    self.assertIn("test", event["name"])
                    instant_count += 1
                elif event["ph"] == "C":
                    self.assertEqual(event["name"], "a")
                    self.assertEqual(event["args"], {"value": 3})
                    var_count += 1
            self.assertEqual(instant_count, 2)
            self.assertEqual(var_count, 4)

        self.template(["viztracer", "--magic_comment", "cmdline_test.py"], script=file_magic_comment, check_func=check_func)
