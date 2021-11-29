# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import ast
import copy
from functools import reduce
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Union

from .util import color_print


class AstTransformer(ast.NodeTransformer):
    def __init__(self, inst_type: str, inst_args: Dict[str, dict]) -> None:
        super().__init__()
        self.inst_type: str = inst_type
        self.inst_args: Dict[str, dict] = inst_args
        self.curr_lineno: int = 0
        self.log_func_exec_enable: bool = False

    def visit_Assign(self, node: ast.Assign) -> Union[ast.stmt, List[ast.stmt]]:
        return self._visit_generic_assign(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> Union[ast.stmt, List[ast.stmt]]:
        return self._visit_generic_assign(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Union[ast.stmt, List[ast.stmt]]:
        return self._visit_generic_assign(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if self.inst_type == "log_func_exec":
            for funcname in self.inst_args["funcnames"]:
                if re.fullmatch(funcname, node.name):
                    self.log_func_exec_enable = True
        elif self.inst_type == "log_func_entry":
            for funcname in self.inst_args["funcnames"]:
                if re.fullmatch(funcname, node.name):
                    node.body.insert(0, self.get_instrument_node("Function Entry", node.name))
        elif self.inst_type in ("log_var", "log_number"):
            instrumented_nodes: List[ast.stmt] = []
            args = node.args
            if sys.version_info >= (3, 8):
                func_args_name = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
            else:
                # python 3.6 and 3.7 does not have posonlyargs
                func_args_name = [a.arg for a in args.args + args.kwonlyargs]
            if "vararg" in args._fields and args.vararg:
                func_args_name.append(args.vararg.arg)
            if "kwarg" in args._fields and args.kwarg:
                func_args_name.append(args.kwarg.arg)
            for name in func_args_name:
                for pattern in self.inst_args["varnames"]:
                    if re.fullmatch(pattern, name):
                        instrumented_nodes.append(self.get_instrument_node("Variable Assign", name))
                        break

        self.generic_visit(node)

        if self.inst_type == "log_func_exec":
            self.log_func_exec_enable = False
        elif self.inst_type in ("log_var", "log_number") and instrumented_nodes:
            node.body = instrumented_nodes + node.body
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        if self.inst_type in ("log_var", "log_number"):
            instrumented_nodes = self.get_assign_log_nodes(node.target)

        self.generic_visit(node)

        if self.inst_type in ("log_var", "log_number"):
            if instrumented_nodes:
                node.body = instrumented_nodes + node.body
        return node

    def visit_Raise(self, node: ast.Raise) -> Union[ast.AST, List[ast.AST]]:
        if self.inst_type == "log_exception":
            instrument_node = self.get_instrument_node_by_node("Exception", node.exc)
            return [instrument_node, node]
        return node

    def _visit_generic_assign(self, node: Union[ast.Assign, ast.AugAssign, ast.AnnAssign]) -> List[ast.stmt]:
        self.generic_visit(node)
        ret: List[ast.stmt] = [node]
        self.curr_lineno = node.lineno
        if self.inst_type in ("log_var", "log_number", "log_attr", "log_func_exec"):
            if isinstance(node, ast.AugAssign) or isinstance(node, ast.AnnAssign):
                instrumented_nodes = self.get_assign_log_nodes(node.target)
                if instrumented_nodes:
                    ret.extend(instrumented_nodes)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    instrumented_nodes = self.get_assign_log_nodes(target)
                    if instrumented_nodes:
                        ret.extend(instrumented_nodes)
        return ret

    def get_assign_targets(self, node: ast.expr) -> List[str]:
        """
        :param ast.Node node:
        """
        if isinstance(node, ast.Name):
            return [node.id]
        elif isinstance(node, ast.Attribute) or isinstance(node, ast.Subscript) or isinstance(node, ast.Starred):
            return self.get_assign_targets(node.value)
        elif isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            return reduce(lambda a, b: a + b, [self.get_assign_targets(elt) for elt in node.elts])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return []

    def get_assign_targets_with_attr(self, node: ast.AST) -> List[ast.Attribute]:
        """
        :param ast.Node node:
        """
        if isinstance(node, ast.Attribute):
            return [node]
        elif isinstance(node, ast.Name) or isinstance(node, ast.Subscript) or isinstance(node, ast.Starred):
            return []
        elif isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            return reduce(lambda a, b: a + b, [self.get_assign_targets_with_attr(elt) for elt in node.elts])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return []

    def get_assign_log_nodes(self, target) -> List[ast.stmt]:
        """
        given a target of any type of Assign, return the instrumented node
        that log this variable
        if this target is not supposed to be logged, return []
        """
        ret: List[ast.stmt] = []
        if self.inst_type == "log_var" or self.inst_type == "log_number":
            target_ids = self.get_assign_targets(target)
            for target_id in target_ids:
                for varname in self.inst_args["varnames"]:
                    if re.fullmatch(varname, target_id):
                        ret.append(self.get_instrument_node("Variable Assign", target_id))
                        break
        elif self.inst_type == "log_attr":
            target_nodes = self.get_assign_targets_with_attr(target)
            for target_node in target_nodes:
                for varname in self.inst_args["varnames"]:
                    if re.fullmatch(varname, target_node.attr):
                        ret.append(self.get_instrument_node_by_node("Attribute Assign", target_node))
                        break
        elif self.inst_type == "log_func_exec":
            if self.log_func_exec_enable:
                target_ids = self.get_assign_targets(target)
                for target_id in target_ids:
                    ret.append(self.get_instrument_node("Variable Assign", target_id))

        return ret

    def get_instrument_node(self, trigger: str, name: str) -> ast.Expr:
        if self.inst_type in ("log_var", "log_number"):
            if self.inst_type == "log_var":
                event = "instant"
            elif self.inst_type == "log_number":
                event = "counter"
            return self.get_add_variable_node(
                name=f"{trigger} - {name}",
                var_node=ast.Name(id=name, ctx=ast.Load()),
                event=event
            )
        elif self.inst_type == "log_func_exec":
            return self.get_add_func_exec_node(
                name=f"{name}",
                val=ast.Name(id=name, ctx=ast.Load()),
                lineno=self.curr_lineno
            )
        elif self.inst_type == "log_func_entry":
            return self.get_add_variable_node(
                name=f"{trigger} - {name}",
                var_node=ast.Constant(value="{} is called".format(name)),
                event="instant"
            )
        else:
            raise ValueError("{} is not supported".format(name))

    def get_instrument_node_by_node(self, trigger: str, node: Optional[ast.expr]) -> ast.Expr:
        var_node: ast.expr
        if node is None:
            name = f"{trigger}"
            var_node = ast.Constant(value=None)
        else:
            name = f"{trigger} - {self.get_string_of_expr(node)}"
            var_node = self.copy_node_with_load(node)
        return self.get_add_variable_node(
            name=name,
            var_node=var_node,
            event="instant"
        )

    def get_add_variable_node(self, name, var_node, event) -> ast.Expr:
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

    def get_add_func_exec_node(self, name, val, lineno) -> ast.Expr:
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

    def copy_node_with_load(self, node: ast.expr) -> ast.expr:
        """
        copy the whole node tree but change all Store to Load
        """
        new_node = copy.deepcopy(node)
        for n in ast.walk(new_node):
            # Fix Store to Load
            if "ctx" in n._fields and isinstance(n.ctx, ast.Store):  # type: ignore
                n.ctx = ast.Load()  # type: ignore
        return new_node

    def get_string_of_expr(self, node: Union[ast.expr, ast.slice]) -> str:
        """
        Try to do "unparse" of the node
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return "'{}'".format(node.value)
            else:
                return "{}".format(node.value)
        elif isinstance(node, ast.Num):
            return "{}".format(node.n)
        elif isinstance(node, ast.Str):
            return "'{}'".format(node.s)
        elif isinstance(node, ast.Attribute):
            return "{}.{}".format(self.get_string_of_expr(node.value), node.attr)
        elif isinstance(node, ast.Subscript):
            return "{}[{}]".format(self.get_string_of_expr(node.value), self.get_string_of_expr(node.slice))
        elif isinstance(node, ast.Call):
            return "{}()".format(self.get_string_of_expr(node.func))
        elif isinstance(node, ast.Starred):
            return "*{}".format(self.get_string_of_expr(node.value))
        elif isinstance(node, ast.Tuple):
            return "({})".format(",".join([self.get_string_of_expr(elt) for elt in node.elts]))
        elif isinstance(node, ast.List):
            return "[{}]".format(",".join([self.get_string_of_expr(elt) for elt in node.elts]))
        elif sys.version_info < (3, 9) and isinstance(node, ast.Index):
            return self.get_string_of_expr(node.value)
        elif isinstance(node, ast.Slice):
            lower = self.get_string_of_expr(node.lower) if "lower" in node._fields and node.lower else ""
            upper = self.get_string_of_expr(node.upper) if "upper" in node._fields and node.upper else ""
            step = self.get_string_of_expr(node.step) if "step" in node._fields and node.step else ""
            if step:
                return "{}:{}:{}".format(lower, upper, step)
            elif upper:
                return "{}:{}".format(lower, upper)
            else:
                return "{}:".format(lower)
        elif sys.version_info < (3, 9) and isinstance(node, ast.ExtSlice):
            return ",".join([self.get_string_of_expr(dim) for dim in node.dims])
        color_print("WARNING", "Unexpected node type {} for ast.Assign. \
            Please report to the author github.com/gaogaotiantian/viztracer".format(type(node)))
        return ""


class SourceProcessor:
    """
    Pre-process comments like #!viztracer: log_instant("event")
    """
    def __init__(self):
        self.re_patterns = [
            # !viztracer: log_var("var", var)
            (re.compile(r"(\s*)#\s*!viztracer:\s*(log_.*?\(.*\))\s*$"), self.line_transform),
            # a = 3  # !viztracer: log
            (re.compile(r"(.*\S.*)#\s*!viztracer:\s*log\s*$"), self.inline_transform),
            # !viztracer: log_var("var", var) if var > 3
            (re.compile(r"(\s*)#\s*!viztracer:\s*(log_.*?\(.*\))\s*if\s+(.*?)\s*$"), self.line_transform_condition),
            # a = 3  # !viztracer: log if a != 3
            (re.compile(r"(.*\S.*)#\s*!viztracer:\s*log\s*if\s+(.*?)\s*$"), self.inline_transform_condition)
        ]

    def process(self, source: Any):
        if isinstance(source, bytes):
            source = source.decode("utf-8")
        elif not isinstance(source, str):
            return source

        new_lines = []

        for line in source.splitlines():
            for pattern, transform in self.re_patterns:
                m = pattern.match(line)
                if m:
                    new_lines.append(transform(m))
                    break
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def line_transform(self, re_match):
        return f"{re_match.group(1)}__viz_tracer__.{re_match.group(2)}"

    def line_transform_condition(self, re_match):
        return f"{re_match.group(1)}if {re_match.group(3)}: __viz_tracer__.{re_match.group(2)};"

    def inline_transform(self, re_match):
        stmt = re_match.group(1)
        if "=" in stmt:
            val_assigned = stmt[:stmt.index("=")].strip()
            return f"{stmt}; __viz_tracer__.log_var('{val_assigned}', ({val_assigned}))"
        return f"{stmt}; __viz_tracer__.log_instant('{stmt.strip()}')"

    def inline_transform_condition(self, re_match):
        stmt = re_match.group(1)
        if "=" in stmt:
            val_assigned = stmt[:stmt.index("=")].strip()
            return f"{stmt}; __viz_tracer__.log_var('{val_assigned}', ({val_assigned}), cond={re_match.group(2)})"
        return f"{stmt}; __viz_tracer__.log_instant('{stmt.strip()}', cond={re_match.group(2)});"


class CodeMonkey:
    def __init__(self, file_name: str) -> None:
        self.file_name: str = file_name
        self._compile: Callable = compile
        self.source_processor: Optional[SourceProcessor] = None
        self.ast_transformers: List[AstTransformer] = []

    def add_instrument(self, inst_type: str, inst_args: Dict[str, Dict]) -> None:
        self.ast_transformers.append(AstTransformer(inst_type, inst_args))

    def add_source_processor(self):
        self.source_processor = SourceProcessor()

    def compile(self, source, filename, mode, flags=0, dont_inherit=False, optimize=-1):
        if self.source_processor is not None:
            source = self.source_processor.process(source)
        if self.ast_transformers:
            tree = self._compile(source, filename, mode, flags | ast.PyCF_ONLY_AST, dont_inherit, optimize)
            for trans in self.ast_transformers:
                trans.visit(tree)
                ast.fix_missing_locations(tree)
            return self._compile(tree, filename, mode, flags, dont_inherit, optimize)

        return self._compile(source, filename, mode, flags, dont_inherit, optimize)
