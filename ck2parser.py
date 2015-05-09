import datetime
import funcparserlib
import funcparserlib.lexer
import funcparserlib.parser

token_specs = [
    ('comment', (r'#.*',)),
    ('whitespace', (r'\s+',)),
    ('op', (r'[={}]',)),
    ('date', (r'\d*\.\d*\.\d*',)),
    ('number', (r'\d+(\.\d+)?',)),
    ('quoted_string', (r'"[^"#]*"',)),
    ('unquoted_string', (r'[^\s"#={}]+',))
]
useless = ['comment', 'whitespace']
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
unquoted_string = some('unquoted_string')
quoted_string = some('quoted_string') >> unquote
number = some('number') >> make_number
date = some('date') >> make_date
key = unquoted_string | quoted_string | number | date
value = fwd(lambda: obj | key)
pair = fwd(lambda: key + op('=') + value)
obj = fwd(lambda: op('{') + many(pair | value) + op('}'))
toplevel = many(pair | value) + endmark

def parse(s):
    return toplevel.parse([t for t in tokenize(s) if t.type not in useless])

def to_string(x, indent=0, quote=False):
    if isinstance(x, tuple):
        # quote all RHS strings
        return to_string(x[0]) + ' = ' + to_string(x[1], indent, quote=True)
    elif isinstance(x, list):
        sep = '\n' + '\t' * (indent + 1)
        return ('{' + sep +
                sep.join(to_string(y, indent + 1) for y in x) + sep + '}')
    elif isinstance(x, datetime.date):
        return x.year + '.' + x.month + '.' + x.day
    elif isinstance(x, str):
        return '"' + x + '"' if quote else x
    else:
        return str(x)
