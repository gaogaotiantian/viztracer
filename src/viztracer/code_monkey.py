# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import ast
import re
import copy
from functools import reduce
from .util import color_print


class AstTransformer(ast.NodeTransformer):
    def __init__(self, inst_type, inst_args):
        super().__init__()
        self.inst_type = inst_type
        self.inst_args = inst_args
        self.curr_lineno = 0
        self.log_func_exec_enable = False

    def visit_Assign(self, node):
        return self._visit_generic_assign(node)

    def visit_AugAssign(self, node):
        return self._visit_generic_assign(node)

    def visit_AnnAssign(self, node):
        return self._visit_generic_assign(node)

    def visit_FunctionDef(self, node):
        if self.inst_type == "log_func_exec":
            for funcname in self.inst_args["funcnames"]:
                if re.fullmatch(funcname, node.name):
                    self.log_func_exec_enable = True
        elif self.inst_type == "log_func_entry":
            for funcname in self.inst_args["funcnames"]:
                if re.fullmatch(funcname, node.name):
                    node.body.insert(0, self.get_instrument_node(node.name))
        self.generic_visit(node)

        if self.inst_type == "log_func_exec":
            self.log_func_exec_enable = False
        return node

    def visit_Raise(self, node):
        if self.inst_type == "log_exception":
            instrument_node = self.get_instrument_node_by_node(node.exc)
            return [instrument_node, node]
        return node
    
    def _visit_generic_assign(self, node):
        self.generic_visit(node)
        ret = [node]
        self.curr_lineno = node.lineno
        if self.inst_type in ("log_var", "log_number", "log_attr", "log_func_exec"):
            if "target" in node._fields:
                instrumented_nodes = self.get_assign_log_nodes(node.target)
                if instrumented_nodes:
                    ret.extend(instrumented_nodes)
            elif "targets" in node._fields:
                for target in node.targets:
                    instrumented_nodes = self.get_assign_log_nodes(target)
                    if instrumented_nodes:
                        ret.extend(instrumented_nodes)
        return ret

    def get_assign_targets(self, node):
        """
        :param ast.Node node: 
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

    def get_assign_targets_with_attr(self, node):
        """
        :param ast.Node node: 
        """
        if type(node) is ast.Attribute:
            return [node]
        elif type(node) is ast.Name or type(node) is ast.Subscript or type(node) is ast.Starred:
            return []
        elif type(node) is ast.Tuple or type(node) is ast.List:
            return reduce(lambda a, b: a+b, [self.get_assign_targets_with_attr(elt) for elt in node.elts])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return []

    def get_assign_log_nodes(self, target):
        """
        given a target of any type of Assign, return the instrumented node
        that log this variable
        if this target is not supposed to be logged, return []
        """
        ret = []
        if self.inst_type == "log_var" or self.inst_type == "log_number":
            target_ids = self.get_assign_targets(target)
            for target_id in target_ids:
                for varname in self.inst_args["varnames"]:
                    if re.fullmatch(varname, target_id):
                        ret.append(self.get_instrument_node(target_id))
                        break
        elif self.inst_type == "log_attr":
            target_nodes = self.get_assign_targets_with_attr(target)
            for target_node in target_nodes:
                for varname in self.inst_args["varnames"]:
                    if re.fullmatch(varname, target_node.attr):
                        ret.append(self.get_instrument_node_by_node(target_node))
                        break
        elif self.inst_type == "log_func_exec":
            if self.log_func_exec_enable:
                target_ids = self.get_assign_targets(target)
                for target_id in target_ids:
                    ret.append(self.get_instrument_node(target_id))

        return ret

    def get_instrument_node(self, name):
        if self.inst_type in ("log_var", "log_number"):
            if self.inst_type == "log_var":
                event = "instant"
            elif self.inst_type == "log_number":
                event = "counter"
            return self.get_add_variable_node(
                    name=name,
                    var_node=ast.Name(id=name, ctx=ast.Load()),
                    event=event
            )
        elif self.inst_type == "log_func_exec":
            return self.get_add_func_exec_node(
                    name=name,
                    val=ast.Name(id=name, ctx=ast.Load()),
                    lineno=self.curr_lineno
            )
        elif self.inst_type == "log_func_entry":
            return self.get_add_variable_node(
                    name=name,
                    var_node=ast.Constant(value="{} is called".format(name)),
                    event="instant"
            )
        else:
            raise ValueError("{} is not supported".format(name))

    def get_instrument_node_by_node(self, node):
        return self.get_add_variable_node(
                name=self.get_string_of_expr(node),
                var_node=self.copy_node_with_load(node),
                event="instant"
        )

    def get_add_variable_node(self, name, var_node, event):
        node_instrument = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="__viz_tracer__", ctx=ast.Load()),
                    attr="add_variable",
                    ctx=ast.Load()
                ),
                args=[
                    ast.Constant(value=name),
                    var_node,
                    ast.Constant(value=event)
                ],
                keywords=[]
            )
        )
        return node_instrument

    def get_add_func_exec_node(self, name, val, lineno):
        node_instrument = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="__viz_tracer__", ctx=ast.Load()),
                    attr="add_func_exec",
                    ctx=ast.Load()
                ),
                args=[
                    ast.Constant(value=name),
                    ast.Name(id=name, ctx=ast.Load()),
                    ast.Constant(value=lineno)
                ],
                keywords=[]
            )
        )
        return node_instrument

    def copy_node_with_load(self, node):
        """
        copy the whole node tree but change all Store to Load
        """
        new_node = copy.deepcopy(node)
        for n in ast.walk(new_node):
            # Fix Store to Load
            if "ctx" in n._fields and type(n.ctx) is ast.Store:
                n.ctx = ast.Load()
        return new_node

    def get_string_of_expr(self, node):
        """
        Try to do "unparse" of the node
        """
        if type(node) is ast.Name:
            return node.id
        elif type(node) is ast.Constant:
            if type(node.value) is str:
                return "'{}'".format(node.value)
            else:
                return "{}".format(node.value)
        elif type(node) is ast.Num:
            return "{}".format(node.n)
        elif type(node) is ast.Str:
            return "'{}'".format(node.s)
        elif type(node) is ast.Attribute:
            return "{}.{}".format(self.get_string_of_expr(node.value), node.attr)
        elif type(node) is ast.Subscript:
            return "{}[{}]".format(self.get_string_of_expr(node.value), self.get_string_of_expr(node.slice))
        elif type(node) is ast.Call:
            return "{}()".format(self.get_string_of_expr(node.func))
        elif type(node) is ast.Starred:
            return "*{}".format(self.get_string_of_expr(node.value))
        elif type(node) is ast.Tuple:
            return "({})".format(",".join([self.get_string_of_expr(elt) for elt in node.elts]))
        elif type(node) is ast.List:
            return "[{}]".format(",".join([self.get_string_of_expr(elt) for elt in node.elts]))
        elif type(node) is ast.Index:
            return self.get_string_of_expr(node.value)
        elif type(node) is ast.Slice:
            lower = self.get_string_of_expr(node.lower) if "lower" in node._fields and node.lower else ""
            upper = self.get_string_of_expr(node.upper) if "upper" in node._fields and node.upper else ""
            step = self.get_string_of_expr(node.step) if "step" in node._fields and node.step else ""
            if step:
                return "{}:{}:{}".format(lower, upper, step)
            elif upper:
                return "{}:{}".format(lower, upper)
            else:
                return "{}:".format(lower)
        elif type(node) is ast.ExtSlice:
            return ",".join([self.get_string_of_expr(dim) for dim in node.dims])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return ""


class CodeMonkey:
    def __init__(self, code_string, file_name):
        self.code_string = code_string
        self.file_name = file_name
        self._compile = compile
        self.ast_transformers = []

    def add_instrument(self, inst_type, inst_args):
        self.ast_transformers.append(AstTransformer(inst_type, inst_args))

    def compile(self, source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
        if self.ast_transformers:
            tree = self._compile(source, filename, mode, flags | ast.PyCF_ONLY_AST, dont_inherit, optimize)
            for trans in self.ast_transformers:
                trans.visit(tree)
                ast.fix_missing_locations(tree)
            return self._compile(tree, filename, mode, flags, dont_inherit, optimize)

        return self._compile(source, filename, mode, flags, dont_inherit, optimize)
