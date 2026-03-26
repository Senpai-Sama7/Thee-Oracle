"""
Restricted expression evaluation helpers for workflow conditions.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Mapping


SAFE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "any": any,
    "all": all,
}

_BINARY_OPERATORS: dict[type[ast.AST], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS: dict[type[ast.AST], Callable[[Any], Any]] = {
    ast.Not: operator.not_,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_COMPARATORS: dict[type[ast.AST], Callable[[Any, Any], bool]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
    ast.Is: lambda left, right: left is right,
    ast.IsNot: lambda left, right: left is not right,
}


class _SafeExpressionEvaluator:
    def __init__(
        self,
        variables: Mapping[str, Any],
        functions: Mapping[str, Callable[..., Any]] | None = None,
    ) -> None:
        self.variables = dict(variables)
        self.functions = dict(functions or SAFE_FUNCTIONS)

    def evaluate(self, expression: str) -> Any:
        try:
            return ast.literal_eval(expression)
        except (ValueError, SyntaxError):
            tree = ast.parse(expression, mode="eval")
            return self.visit(tree)

    def visit(self, node: ast.AST) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise ValueError(f"Unsafe syntax: {type(node).__name__}")
        return method(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.variables:
            return self.variables[node.id]
        raise ValueError(f"Unsafe variable access: {node.id}")

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(element) for element in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(element) for element in node.elts)

    def visit_Set(self, node: ast.Set) -> set[Any]:
        return {self.visit(element) for element in node.elts}

    def visit_Dict(self, node: ast.Dict) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None:
                raise ValueError("Dict unpacking is not allowed")
            result[self.visit(key)] = self.visit(value)
        return result

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        if isinstance(node.op, ast.And):
            return all(bool(self.visit(value)) for value in node.values)
        if isinstance(node.op, ast.Or):
            return any(bool(self.visit(value)) for value in node.values)
        raise ValueError(f"Unsafe boolean operator: {type(node.op).__name__}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operator_fn = _UNARY_OPERATORS.get(type(node.op))
        if operator_fn is None:
            raise ValueError(f"Unsafe unary operator: {type(node.op).__name__}")
        return operator_fn(self.visit(node.operand))

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        operator_fn = _BINARY_OPERATORS.get(type(node.op))
        if operator_fn is None:
            raise ValueError(f"Unsafe binary operator: {type(node.op).__name__}")
        return operator_fn(self.visit(node.left), self.visit(node.right))

    def visit_Compare(self, node: ast.Compare) -> bool:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            comparator_fn = _COMPARATORS.get(type(op))
            if comparator_fn is None:
                raise ValueError(f"Unsafe comparator: {type(op).__name__}")
            right = self.visit(comparator)
            if not comparator_fn(left, right):
                return False
            left = right
        return True

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct builtin calls are allowed")
        if node.func.id not in self.functions:
            raise ValueError(f"Unsafe function call: {node.func.id}")
        if any(keyword.arg is None for keyword in node.keywords):
            raise ValueError("Keyword splats are not allowed")

        args = [self.visit(arg) for arg in node.args]
        kwargs = {keyword.arg: self.visit(keyword.value) for keyword in node.keywords if keyword.arg}
        return self.functions[node.func.id](*args, **kwargs)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        return self.visit(node.value)[self.visit(node.slice)]

    def visit_Slice(self, node: ast.Slice) -> slice:
        lower = self.visit(node.lower) if node.lower is not None else None
        upper = self.visit(node.upper) if node.upper is not None else None
        step = self.visit(node.step) if node.step is not None else None
        return slice(lower, upper, step)


def evaluate_expression(
    expression: str,
    variables: Mapping[str, Any],
    functions: Mapping[str, Callable[..., Any]] | None = None,
) -> Any:
    evaluator = _SafeExpressionEvaluator(variables, functions)
    return evaluator.evaluate(expression)


def evaluate_condition(
    expression: str,
    variables: Mapping[str, Any],
    functions: Mapping[str, Callable[..., Any]] | None = None,
) -> bool:
    return bool(evaluate_expression(expression, variables, functions))
