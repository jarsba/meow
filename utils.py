import ast
import operator as op
from pathlib import Path
import os
from typing import Tuple

allowed_operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                     ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                     ast.USub: op.neg}


def eval_expr(expr):
    """
    >>> eval_expr('2^6')
    4
    >>> eval_expr('2**6')
    64
    >>> eval_expr('1 + 2*3**(4^5) / (6 + -7)')
    -5.0
    """
    return eval_(ast.parse(expr, mode='eval').body)


def eval_(node):
    if isinstance(node, ast.Num):  # <number>
        return node.n
    elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
        return allowed_operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
        return allowed_operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


def format_filename(filename, extension):
    return f"{filename}.{extension}"


def extract_filename_without_extension(path) -> str:
    filename = Path(path).stem
    return filename


# Split file path from extension and convert file extension to lower case
def split_file_from_extension(path, without_dot=True) -> Tuple[str, str]:
    filename, extension = os.path.splitext(path)
    if without_dot:
        extension = extension.replace('.', '').lower()
    return filename, extension


def extract_folder_from_path(path) -> str:
    return os.path.dirname(path)

