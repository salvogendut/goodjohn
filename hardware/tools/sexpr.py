"""Small KiCad S-expression reader/writer used by the hardware tooling."""
import json
import re


class Atom(str):
    pass


def loads(text):
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text))

    def read(token):
        if token == '(':
            result = []
            for token in tokens:
                if token == ')':
                    return result
                result.append(read(token))
            raise ValueError('Unclosed expression')
        if token.startswith('"'):
            return json.loads(token)
        return Atom(token)

    result = read(next(tokens))
    if next(tokens, None) is not None:
        raise ValueError('Trailing expression')
    return result


def dumps(node, level=0):
    if isinstance(node, Atom):
        return str(node)
    if isinstance(node, str):
        return json.dumps(node, ensure_ascii=False)
    parts = []
    for child in node:
        prefix = '\n' + '  ' * (level + 1) if isinstance(child, list) else ' '
        parts.append(prefix + dumps(child, level + 1))
    return '(' + ''.join(parts).lstrip() + ')'


def children(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def child(node, key):
    return next(iter(children(node, key)), None)
