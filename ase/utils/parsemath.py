"""A Module to safely parse/evaluate Mathematical Expressions"""
import ast
import operator as op
import math
import inspect

max_value = 1e17

# Take all functions from math module as allowed functions
allowed_math_fxn = {}
for object in inspect.getmembers(math):
    if inspect.isbuiltin(object[1]):
        allowed_math_fxn[object[0]] = object[1]


# Redefine mathematical operations to prevent DNS attacks
def add(a, b):
    """Redefine add function to prevent too large numbers"""
    if any(abs(n) > max_value for n in [a, b]):
        raise ValueError((a,b))
    return op.add(a, b)


def sub(a, b):
    """Redefine sub function to prevent too large numbers"""
    if any(abs(n) > max_value for n in [a, b]):
        raise ValueError((a,b))
    return op.sub(a, b)


def mul(a, b):
    """Redefine mul function to prevent too large numbers"""
    if a==0.0 or b == 0.0:
        pass
    elif math.log10(abs(a)) + math.log10(abs(b)) > math.log10(max_value):
        raise ValueError((a,b))
    return op.mul(a, b)


def div(a, b):
    """Redefine div function to prevent too large numbers"""
    if b == 0.0:
        raise ValueError((a,b))
    elif a == 0.0:
        pass
    elif math.log10(abs(a)) - math.log10(abs(b)) > math.log10(max_value):
        raise ValueError((a,b))
    return op.truediv(a, b)


def power(a, b):
    """Redefine pow function to prevent too large numbers"""
    if a == 0.0:
        return 0.0
    elif b / math.log(max_value, a) >= 1:
        raise ValueError((a,b))
    return op.pow(a, b)


# The list of allowed operators with defined functions they should operate on
operators = {
    ast.Add: add,
    ast.Sub: sub,
    ast.Mult: mul,
    ast.Div: div,
    ast.Pow: power,
    ast.USub: op.neg,
}


def get_function(node):
    """Get the function from an ast.node"""

    # The function call can be to a bare function or a module.function
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        return node.func.attr
    else:
        raise TypeError("node.func is of the wrong type")


def _eval(node):
    """Evaluate a mathematical expression string parsed by ast"""
    # Allow evaluate certain types of operators
    if isinstance(node, ast.Num): # <number>
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return operators[type(node.op)](_eval(node.left), _eval(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        return operators[type(node.op)](_eval(node.operand))
    elif isinstance(node, ast.Call): # using math.function
        func = get_function(node)
        # Evaluate all arguments
        evaled_args = [_eval(arg) for arg in node.args]
        return allowed_math_fxn[func](*evaled_args)
    else:
        raise TypeError(node)


def limit(max_=None):
    """Return decorator that limits allowed returned values."""
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            try:
                mag = abs(ret)
            except TypeError:
                pass # not applicable
            else:
                if mag > max_:
                    raise ValueError(ret)
            return ret
        return wrapper
    return decorator


_eval = limit(max_=max_value)(_eval)


def eval_expression(expression, param_dct=dict()):
    """Parse a mathematical expression, after replacing parameters with the values in param_dict"""
    if not isinstance(expression, str):
        raise TypeError("The expression must be a string")
    if len(expression) > 1e4:
        raise ValueError("The expression is too long.")

    expression_rep = expression.strip()

    if "()" in expression_rep:
        raise ValueError("Invalid operation in expression")

    for key, val in param_dct.items():
        expression_rep = expression_rep.replace(key, str(val))

    return _eval(ast.parse(expression_rep, mode='eval').body)

