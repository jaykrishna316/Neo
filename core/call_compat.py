"""Find calls in an importing file that no longer match a changed function's signature."""

import ast
from typing import List, Tuple


def _signature(func) -> dict:
    args = func.args
    positional = [a.arg for a in args.posonlyargs + args.args]
    required = positional[:len(positional) - len(args.defaults)]
    required += [a.arg for a, default in zip(args.kwonlyargs, args.kw_defaults) if default is None]
    return {
        "positional": positional,
        "required": required,
        "keywords": {a.arg for a in args.args + args.kwonlyargs},
        "varargs": args.vararg is not None,
        "varkw": args.kwarg is not None,
    }


def _problems(call: ast.Call, sig: dict) -> List[str]:
    if any(isinstance(arg, ast.Starred) for arg in call.args) or any(k.arg is None for k in call.keywords):
        return []  # unpacked arguments cannot be checked statically
    problems = []
    if len(call.args) > len(sig["positional"]) and not sig["varargs"]:
        problems.append(f"passes {len(call.args)} positional arguments, takes {len(sig['positional'])}")
    supplied = set(sig["positional"][:len(call.args)])
    for keyword in call.keywords:
        if keyword.arg not in sig["keywords"] and not sig["varkw"]:
            problems.append(f"has no parameter '{keyword.arg}'")
        supplied.add(keyword.arg)
    missing = [name for name in sig["required"] if name not in supplied]
    if missing:
        problems.append("is missing " + ", ".join(f"'{name}'" for name in missing))
    return problems


def broken_calls(importer_text: str, module: str, new_source: str,
                 symbols) -> List[Tuple[int, str, str]]:
    """Calls to `symbols` from `module` in importer_text that do not match new_source.

    Returns (line, call text, problem) for each problem found.
    """
    try:
        importer = ast.parse(importer_text)
        new = ast.parse(new_source)
    except SyntaxError:
        return []
    sigs = {node.name: _signature(node) for node in new.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in symbols}
    local_names = {}   # name bound by "from module import f"  -> f
    module_names = set()  # name bound by "import module"
    for node in ast.walk(importer):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            for alias in node.names:
                if alias.name in sigs:
                    local_names[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    module_names.add(alias.asname or alias.name)

    found = []
    for node in ast.walk(importer):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in local_names:
            target = local_names[func.id]
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
              and func.value.id in module_names and func.attr in sigs):
            target = func.attr
        else:
            continue
        for problem in _problems(node, sigs[target]):
            found.append((node.lineno, ast.get_source_segment(importer_text, node), problem))
    return found
