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

TAB_WIDTH = 4
CHARS_PER_LINE = 120

def files(where, glob):
    yield from sorted(where.glob(glob), key=operator.attrgetter('parts'))

def is_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

def chars(line):
    line = line.splitlines()[-1]
    return len(line) + line.count('\t') * (TAB_WIDTH - 1)

token_specs = [
    ('comment', (r'#(.*\S)?',)),
    ('whitespace', (r'[ \t]+',)),
    ('newline', (r'\r?\n',)),
    ('op', (r'[={}]',)),
    ('date', (r'\d*\.\d*\.\d*',)),
    ('number', (r'\d+(\.\d+)?',)),
    ('quoted_string', (r'"[^"#\r\n]*"',)),
    ('unquoted_string', (r'[^\s"#={}]+',))
]
useless = ['whitespace']
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

class Stringifiable(object):
    def __init__(self, args):
        self.indent = 0

    @property
    def indent(self):
        return self._indent

    @property
    def indent_col(self):
        return self.indent * TAB_WIDTH

class Commented(Stringifiable):
    def __init__(self, args):
        super().__init__(args)
        pre_comments, string, post_comment = args
        self.pre_comments = pre_comments
        self.value = str_to_val(string)
        self.post_comment = post_comment

    @property
    def has_comments(self):
        return self.pre_comments or self.post_comment

    str_to_val = lambda x: x

    def val_str(self):
        val_is, _ = self.val_inline_str(self.indent_col)
        return self.indent * '\t' + val_is

    def val_inline_str(self, col):
        s = str(self.value)
        return s, col + chars(s)

    def str(self):
        s = self.indent * '\t'
        if self.pre_comments:
            s += ('\n' + s).join(self.pre_comments) + '\n'
        s += self.val_str()
        if post_comment:
            s += ' ' + self.post_comment
        s += '\n'
        return s

    def inline_str(self, col):
        nl = 0
        sep = '\n' + self.indent * '\t'
        s = ''
        if self.pre_comments:
            if (col > self.indent_col and
                col + chars(self.pre_comments[0]) > CHARS_PER_LINE):
                s += sep
                nl += 1
            s += sep.join(self.pre_comments) + sep
            nl += len(self.pre_comments)
            col = self.indent_col
        val_is, col_val = self.val_inline_str(col)
        s += val_is
        col = col_val
        if self.post_comment:
            s += ' ' + self.post_comment + sep
            nl += 1
            col = self.indent_col
        return s, (nl, col)

class CK2String(Commented):
    def val_inline_str(self, col):
        s = '"{}"'.format(x) if re.search(r'\s', x) else x
        return s, col + chars(s)

class CK2Number(Commented):
    def str_to_val(string):
        try:
            return int(string)
        except ValueError:
            return float(string)
    
class CK2Date(Commented):
    def str_to_val(string):
        # CKII appears to default to 0, not 1, but that's awkward to handle
        # with datetime, and it only comes up for b_embriaco anyway
        year, month, day = ((int(x) if x else 1) for x in string.split('.'))
        return datetime.date(year, month, day)

    def val_inline_str(self, col):
        s = '{0.year}.{0.month}.{0.day}'.format(self.value)
        return s, col + chars(s)
    
class CK2Op(Commented):
    pass

class CK2Pair(Stringifiable):
    def __init__(self, args):
        self.key, self.tis, self.value = args
        super().__init__(args)

    @indent.setter
    def indent(self, value):
        self._indent = value
        self.key.indent = value
        self.tis.indent = value
        self.value.indent = value

    def str(self):
        s = self.indent * '\t'
        self_is, _ = self.inline_str(self.indent_col)
        if self_is[-1].isspace():
            s += self_is[:-self.indent]
        else:
            s += self_is + '\n'
        return s

    def inline_str(self, col):
        s = ''
        nl = 0
        key_is, (nl_key, col_key) = self.key.inline_str(col)
        s += key_is
        nl += nl_key
        col = col_key
        if not s[-1].isspace():
            s += ' '
            col += 1
        tis_is, (nl_tis, col_tis) = self.tis.inline_str(col)
        if col > self.indent_col and col_tis > CHARS_PER_LINE:
            if not s[-2].isspace():
                s = s[:-1]
            tis_s = self.tis.str()
            s += '\n' + tis_s
            nl += 1 + tis_s.count('\n')
            col = self.indent_col
        else:
            if tis_is[0] = '\n':
                s = s[:-1]
                col -= 1
            s += tis_is
            nl += nl_tis
            col = col_tis
        if not s[-1].isspace():
            s += ' '
            col += 1
        val_is, (nl_val, col_val) = self.value.inline_str(col)
        if col > self.indent_col and col_val > CHARS_PER_LINE:
            if not s[-2].isspace():
                s = s[:-1]
            val_s = self.val.str()
            s += '\n' + val_s + self.indent * '\t'
            nl += 1 + val_s.count('\n')
            col = self.indent_col
        else:
            if val_is[0] = '\n':
                s = s[:-1]
                col -= 1
            s += val_is
            nl += nl_val
            col = col_val
            if not self.value.post_comment:
                s += '\n' + self.indent * '\t'
                nl += 1
                col = self.indent_col
        return s, (nl, col)

class CK2Obj(Stringifiable):
    def __init__(self, args):
        self.kel, self.contents, self.ker = args
        super().__init__(args)

    @indent.setter
    def indent(self, value):
        self._indent = value
        self.kel.indent = value
        for item in self.contents:
            item.indent = value + 1
        self.ker.indent = value

    def str(self):
        s = self.indent * '\t'
        self_is, _ = self.inline_str(self.indent_col)
        if self_is[-1].isspace():
            s += self_is[:-self.indent]
        else:
            s += self_is + '\n'
        return s

    def inline_str(self):
        s = ''
        nl = 0
        kel_is, (nl_kel, col_kel) = self.kel.inline_str(col)
        s += kel_is
        nl += nl_kel
        col += col_kel
        if (not self.kel.has_comments and not self.ker.has_comments and
            (not self.contents or
             (len(self.contents) == 1 and not self.contents[0].has_comments or
              (all(isinstance(x, Commented) and not x.has_comments
               for x in self.contents))))):
            # attempt one line object
            s_oneline, col_oneline = s, col
            for item in self.contents:
                item_is, (_, col_item) = item.inline_str(1 + col_oneline)
                s_oneline += ' ' + item_is
                col_oneline = col_item
                if col_oneline + 2 > CHARS_PER_LINE:
                    break
            else:
                if self.contents:
                    s_oneline += ' '
                    col_oneline += 1
                ker_is, (_, col_ker) = self.ker.inline_str(col_oneline)
                s_oneline += ker_is
                col_oneline = col_ker
                return s_oneline, (0, col_oneline)
        if isinstance(self.contents[0], CK2Pair):
            if s[-1].isspace():
                s = s[:-self.indent]
            else:
                s += '\n'
                nl += 1
            for item in self.contents:
                item_s = item.str()
                s += item_s + '\n'
                nl += item_s.count('\n') + 1
            s += self.indent * '\t'
        else:
            sep = '\n' + (self.indent + 1) * '\t'
            sep_col = chars(sep)
            col = sep_col
            for item in self.contents:
                if not s[-1].isspace():
                    s += ' '
                    col += 1
                item_is, (nl_item, col_item) = item.inline_str(col)
                if col > self.indent_col and col_item > CHARS_PER_LINE:
                    if not s[-2].isspace():
                        s = s[:-1]
                    s += sep
                    nl += 1
                    col = sep_col
                    item_is, (nl_item, col_item) = item.inline_str(col)
                s += item_is
                nl += nl_item
                col = col_item
            if not s[-1].isspace():
                s += '\n' + self.indent * '\t'
                nl += 1
                col = self.indent_col
        ker_is, (nl_ker, col_ker) = self.ker.inline_str(col)
        s += ker_is
        nl += nl_ker
        col += col_ker
        return s, (nl, col)

many = funcparserlib.parser.many
maybe = funcparserlib.parser.maybe
fwd = funcparserlib.parser.with_forward_decls
skip = funcparserlib.parser.skip
endmark = skip(funcparserlib.parser.finished)
comment = some('comment') + skip(many(lambda tok: tok.type == 'newline'))
commented = lambda x: many(comment) + x + maybe(comment) >> tuple

def op(string):
    return commented(funcparserlib.parser.a(
        funcparserlib.lexer.Token('op', string))) >> CK2Op

unquoted_string = commented(some('unquoted_string')) >> CK2String
quoted_string = commented(some('quoted_string') >> unquote) >> CK2String
number = commented(some('number')) >> CK2Number
date = commented(some('date')) >> CK2Date
key = unquoted_string | number | date
value = fwd(lambda: obj | key | quoted_string)
pair = key + op('=') + value >> CK2Pair
obj = op('{') + many(pair) + op('}') >> CK2Obj
toplevel = many(pair) + many(comment) + endmark

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
