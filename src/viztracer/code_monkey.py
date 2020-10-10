# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import ast
import re
from functools import reduce
from .util import color_print


class AstTransformer(ast.NodeTransformer):
    def __init__(self, inst_type, inst_args):
        super().__init__()
        self.inst_type = inst_type
        self.inst_args = inst_args

    def visit_Assign(self, node):
        self.generic_visit(node)
        ret = [node]
        if self.inst_type == "log_var" or self.inst_type == "log_number":
            for target in node.targets:
                instrumented_nodes = self.get_assign_log_nodes(target)
                if instrumented_nodes:
                    ret.extend(instrumented_nodes)
        return ret

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        ret = [node]
        if self.inst_type == "log_var" or self.inst_type == "log_number":
            instrumented_nodes = self.get_assign_log_nodes(node.target)
            if instrumented_nodes:
                ret.extend(instrumented_nodes)
        return ret

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        ret = [node]
        if self.inst_type == "log_var" or self.inst_type == "log_number":
            instrumented_nodes = self.get_assign_log_nodes(node.target)
            if instrumented_nodes:
                ret.extend(instrumented_nodes)
        return ret

    def get_assign_targets(self, node):
        """
        :param ast.Node node: has to be Name or Attribute or Subscribe
        """
        if type(node) is ast.Name:
            return [node.id]
        elif type(node) is ast.Attribute or type(node) is ast.Subscript or type(node) is ast.Starred:
            return self.get_assign_targets(node.value)
        elif type(node) is ast.Tuple or type(node) is ast.List:
            return reduce(lambda a, b: a+b, [self.get_assign_targets(elt) for elt in node.elts])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return []

    def get_assign_log_nodes(self, target):
        """
        given a target of any type of Assign, return the instrumented node
        that log this variable
        if this target is not supposed to be logged, return None
        """
        ret = []
        target_ids = self.get_assign_targets(target)
        for target_id in target_ids:
            for varname in self.inst_args["varnames"]:
                if re.match(varname, target_id):
                    ret.append(self.get_instrument_node(target_id))
                    break
        return ret

    def get_instrument_node(self, name):
        if self.inst_type == "log_var":
            event = "instant"
        elif self.inst_type == "log_number":
            event = "counter"
        else:
            raise ValueError("{} is not supported".format(name))

        node_instrument = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="__viz_tracer__", ctx=ast.Load()),
                    attr="add_variable",
                    ctx=ast.Load()
                ),
                args=[
                    ast.Constant(value=name),
                    ast.Name(id=name, ctx=ast.Load()),
                    ast.Constant(value=event)
                ],
                keywords=[]
            )
        )
        return node_instrument


class CodeMonkey:
    def __init__(self, code_string, file_name):
        self.code_string = code_string
        self.file_name = file_name
        self._compile = compile
        self.ast_transformers = []

    def add_instrument(self, inst_type, inst_args):
        if inst_type == "log_var" or inst_type == "log_number":
            self.ast_transformers.append(AstTransformer(inst_type, inst_args))

    def compile(self, source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
        if self.ast_transformers:
            tree = self._compile(source, filename, mode, flags | ast.PyCF_ONLY_AST, dont_inherit, optimize)
            for trans in self.ast_transformers:
                trans.visit(tree)
                ast.fix_missing_locations(tree)
            return self._compile(tree, filename, mode, flags, dont_inherit, optimize)

        return self._compile(source, filename, mode, flags, dont_inherit, optimize)
