# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import ast
import os


class AstTransformer(ast.NodeTransformer):
    def __init__(self, inst_type, inst_args):
        super().__init__()
        self.inst_type = inst_type
        self.inst_args = inst_args

    def visit_Assign(self, node):
        self.generic_visit(node)
        ret = [node]
        if self.inst_type == "log_var":
            for target in node.targets:
                if type(target) is ast.Name:
                    if target.id in self.inst_args["varnames"]:
                        node_instrument = ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="__viz_tracer__", ctx=ast.Load()),
                                    attr="add_variable",
                                    ctx=ast.Load()
                                ),
                                args=[
                                    ast.Constant(value=target.id),
                                    ast.Name(id=target.id, ctx=ast.Load())
                                ],
                                keywords=[]
                            )
                        )
                        ret.append(node_instrument)

        return ret


class CodeMonkey:
    def __init__(self, code_string, file_name):
        self.code_string = code_string
        self.file_name = file_name
        self._compile = compile
        self.ast_transformers = []

    def add_instrument(self, inst_type, inst_args):
        if inst_type == "log_var":
            self.ast_transformers.append(AstTransformer(inst_type, inst_args))

    def compile(self, source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
        if self.ast_transformers:
            tree = self._compile(source, filename, mode, flags | ast.PyCF_ONLY_AST, dont_inherit, optimize)
            for trans in self.ast_transformers:
                trans.visit(tree)
                ast.fix_missing_locations(tree)
            return self._compile(tree, filename, mode, flags, dont_inherit, optimize)

        return self._compile(source, filename, mode, flags, dont_inherit, optimize)

