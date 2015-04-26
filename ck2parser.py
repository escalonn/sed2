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
