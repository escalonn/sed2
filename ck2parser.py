#!/usr/bin/env python3

import csv
import datetime
import operator
import re
import funcparserlib
import funcparserlib.lexer
import funcparserlib.parser

csv.register_dialect('ckii', delimiter=';', doublequote=False,
                     quotechar='\0', quoting=csv.QUOTE_NONE, strict=True)

def files(where, glob):
    yield from sorted(where.glob(glob), key=operator.attrgetter('parts'))

def is_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

token_specs = [
    ('comment', (r'#.*',)),
    ('whitespace', (r'\s+',)),
    ('op', (r'[={}]',)),
    ('date', (r'\d*\.\d*\.\d*',)),
    ('number', (r'\d+(\.\d+)?',)),
    ('quoted_string', (r'"[^"#\r\n]*"',)),
    ('unquoted_string', (r'[^\s"#={}]+',))
]
useless = ['whitespace', 'comment']
tokenize = funcparserlib.lexer.make_tokenizer(token_specs)

def unquote(string):
    return string[1:-1]

def make_number(string):
    try:
        return int(string)
    except ValueError:
        return float(string)

def make_date(string):
    # CKII appears to default to 0, not 1, but that's awkward to handle
    # with datetime, and it only comes up for b_embriaco anyway
    year, month, day = ((int(x) if x else 1) for x in string.split('.'))
    return datetime.date(year, month, day)

def some(tok_type):
    return (funcparserlib.parser.some(lambda tok: tok.type == tok_type) >>
            (lambda tok: tok.value))

def op(string):
    return funcparserlib.parser.skip(funcparserlib.parser.a(
        funcparserlib.lexer.Token('op', string)))

many = funcparserlib.parser.many
fwd = funcparserlib.parser.with_forward_decls
endmark = funcparserlib.parser.skip(funcparserlib.parser.finished)
comments = many(some('comment'))                                                # list(str)
unquoted_string = some('unquoted_string')                                       # str
quoted_string = some('quoted_string') >> unquote                                # str
number = some('number') >> make_number                                          # Number
date = some('date') >> make_date                                                # datetime.date
key = comments + (unquoted_string | quoted_string | number | date)              # tuple(list(str), *)
value = fwd(lambda: obj | key)                                                  # tuple
pair = key + comments + op('=') + value                                         # tuple(list(str), *, list(str), tuple)
obj = fwd(lambda: comments + op('{') + many(pair | value) + comments + op('}')) # tuple(list(str), list(tuple), list(str))
toplevel = many(pair | value) + comments + endmark                              # tuple(list(tuple), list(str))

def parse(s):
    return toplevel.parse([t for t in tokenize(s) if t.type not in useless])

def parse_file(path, encoding='cp1252'):
    with path.open(encoding=encoding) as f:
        try:
            tree = parse(f.read())
        except funcparserlib.parser.NoParseError:
            print(path)
            raise
    return tree

def to_string(x, indent=-1, fq_keys=[], force_quote=False):
    if isinstance(x, str):
        # unquoted_string or quoted_string
        return '"{}"'.format(x) if force_quote or re.search(r'\s', x) else x
    if isinstance(x, tuple):
        if len(x) == 4:
            # pair
            return '{}{} {}= {}'.format(
                to_string(x[0], indent),
                to_string(x[1]),
                to_string(x[2], indent),
                to_string(x[3], indent, fq_keys, x[1] in fq_keys))
        if len(x) == 2 and not isinstance(x[1], list):
            # key
            return (to_string(x[0], indent) +
                    to_string(x[1], force_quote=force_quote))
        if indent == -1:
            # top-level many(pair | value)
            return ('\n'.join(to_string(y, 0, fq_keys) for y in x[0]) +
                    to_string(x[1]))
        # obj
        if (not x[0] and len(x[1]) == 3 and not x[2] and
            all(len(y) == 2 and not y[0] and isinstance(y[1], int) for y in x[1])):
            return '{{ {0[1]} {1[1]} {2[1]} }}'.format(*x[1])
        sep = '\n' + '\t' * (indent + 1)
        return '{}{{{}{}}}'.format(
            to_string(x[0], indent),
            (sep + sep.join(to_string(y, indent + 1, fq_keys) for y in x[1]) +
             '\n' + '\t' * indent) if x[1] else '',
            ('\t' + to_string(x[2][:-1], indent + 1) + x[2][-1] +
             '\n' + '\t' * indent if x[2] else ''))
    if isinstance(x, list):
        # comments
        if not x:
            return ''
        if isinstance(x[0], str):
            ws = '\n' + '\t' * indent
            return ws.join(x) + ws
    if isinstance(x, datetime.date):
        return '{0.year}.{0.month}.{0.day}'.format(x)
    return str(x)
