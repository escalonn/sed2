import csv
import datetime
import operator
import pathlib
import re
from funcparserlib import lexer
from funcparserlib import parser

vanilladir = pathlib.Path(
    'C:/Program Files (x86)/Steam/SteamApps/common/Crusader Kings II')

csv.register_dialect('ckii', delimiter=';', doublequote=False,
                     quotechar='\0', quoting=csv.QUOTE_NONE, strict=True)

TAB_WIDTH = 4
CHARS_PER_LINE = 120

fq_keys = []

def force_quote(key):
    global fq_keys
    return isinstance(key, String) and key.val in fq_keys

# give mod dirs in descending lexicographical order of mod name (Z-A),
# modified for dependencies as necessary.
def files(glob, *moddirs, basedir=vanilladir):
    result_paths = {p.relative_to(d): p
                    for d in (basedir,) + moddirs for p in d.glob(glob)}
    for _, p in sorted(result_paths.items(), key=lambda t: t[0].parts):
        yield p

def localisation(moddir=None):
    def process_csv(path):
        with path.open(newline='', encoding='cp1252', errors='replace') as f:
            for row in csv.reader(f, dialect='ckii'):
                try:
                    locs[row[0]] = row[1]
                except IndexError:
                    continue

    locs = {}
    loc_glob = 'localisation/*.csv'
    for path in files(loc_glob):
        process_csv(path)
    if moddir:
        for path in files(loc_glob, basedir=moddir):
            process_csv(path)
    return locs

def is_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

def chars(line):
    line = str(line).splitlines()[-1]
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
tokenize = lexer.make_tokenizer(token_specs)

class Comment(object):
    def __init__(self, string):
        if string[0] == '#':
            string = string[1:]
        self.val = string.strip(' \t')

    def __str__(self):
        return ('# ' if self.val and self.val[0] != '#' else '#') + self.val

class Stringifiable(object):
    def __init__(self):
        self.indent = 0

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, value):
        self._indent = value

    @property
    def indent_col(self):
        return self.indent * TAB_WIDTH

class TopLevel(Stringifiable):
    def __init__(self, contents, post_comments):
        self.contents = contents
        self.post_comments = [Comment(s) for s in post_comments]
        super().__init__()

    def __len__(self):
        return len(self.contents)

    def __contains__(self, item):
        return item in self.contents

    def __iter__(self):
        return iter(self.contents)

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, value):
        self._indent = value
        for item in self:
            item.indent = value

    def str(self):
        s = ''.join(x.str() for x in self)
        if self.post_comments:
            s += '\n'.join(str(c) for c in self.post_comments) + '\n'
        return s

class Commented(Stringifiable):
    def __init__(self, pre_comments, string, post_comment):
        self.pre_comments = [Comment(s) for s in pre_comments]
        self.val = self.str_to_val(string)
        self.post_comment = Comment(post_comment) if post_comment else None
        super().__init__()

    @classmethod
    def from_str(cls, string):
        return cls([], string, None)

    @property
    def has_comments(self):
        return self.pre_comments or self.post_comment

    str_to_val = lambda _, x: x

    def val_str(self):
        val_is, _ = self.val_inline_str(self.indent_col)
        return self.indent * '\t' + val_is

    def val_inline_str(self, col):
        s = str(self.val)
        return s, col + chars(s)

    def str(self):
        s = self.indent * '\t'
        if self.pre_comments:
            s += ('\n' + s).join(str(self.pre_comments)) + '\n'
        s += self.val_str()
        if self.post_comment:
            s += ' ' + str(self.post_comment)
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
            s += sep.join(str(c) for c in self.pre_comments) + sep
            nl += len(self.pre_comments)
            col = self.indent_col
        val_is, col_val = self.val_inline_str(col)
        s += val_is
        col = col_val
        if self.post_comment:
            s += ' ' + str(self.post_comment) + sep
            nl += 1
            col = self.indent_col
        return s, (nl, col)

class String(Commented):
    def __init__(self, *args):
        super().__init__(*args)
        self.force_quote = False

    def val_inline_str(self, col):
        s = self.val
        if self.force_quote or re.search(r'\s', s):
            s = '"{}"'.format(s)
        return s, col + chars(s)

class Number(Commented):
    def str_to_val(self, string):
        try:
            return int(string)
        except ValueError:
            return float(string)
    
class Date(Commented):
    def str_to_val(self, string):
        # CKII appears to default to 0, not 1, but that's awkward to handle
        # with datetime, and it only comes up for b_embriaco anyway
        year, month, day = ((int(x) if x else 1) for x in string.split('.'))
        return datetime.date(year, month, day)

    def val_inline_str(self, col):
        s = '{0.year}.{0.month}.{0.day}'.format(self.val)
        return s, col + chars(s)
    
class Op(Commented):
    pass

class Pair(Stringifiable):
    def __init__(self, key, tis, value):
        self.key = key
        self.tis = tis
        self.value = value
        if force_quote(self.key):
            self.value.force_quote = True
        super().__init__()

    @classmethod
    def from_kv(cls, key, value):
        if not isinstance(key, Stringifiable):
            key = String.from_str(key)
        if not isinstance(value, Stringifiable):
            value = String.from_str(value)
        return cls(key, Op.from_str('='), value)

    def __iter__(self):
        yield self.key
        yield self.value

    @property
    def has_comments(self):
        return any(x.has_comments for x in [self.key, self.tis, self.value])

    @property
    def indent(self):
        return self._indent

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
            if self.indent:
                s += self_is[:-self.indent]
            else:
                s += self_is
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
            if tis_is[0] == '\n':
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
            val_s = self.value.str()
            s += '\n' + val_s + self.indent * '\t'
            nl += 1 + val_s.count('\n')
            col = self.indent_col
        else:
            if val_is[0] == '\n':
                s = s[:-1]
                col -= 1
            s += val_is
            nl += nl_val
            col = col_val
        return s, (nl, col)

class Obj(Stringifiable):
    def __init__(self, kel, contents, ker):
        self.kel = kel
        self.contents = contents
        self.ker = ker
        super().__init__()

    @classmethod
    def from_iter(cls, contents):
        return cls(Op.from_str('{'), list(contents), Op.from_str('}'))

    def __len__(self):
        return len(self.contents)

    def __contains__(self, item):
        return item in self.contents

    def __iter__(self):
        return iter(self.contents)

    @property
    def has_pairs(self):
        return not self.contents or isinstance(self.contents[0], Pair)

    @property
    def indent(self):
        return self._indent

    @property
    def post_comment(self):
        return self.ker.post_comment

    @property
    def has_comments(self):
        return (self.kel.has_comments or self.ker.has_comments or
                any(x.has_comments for x in self))

    @indent.setter
    def indent(self, value):
        self._indent = value
        self.kel.indent = value
        for item in self:
            item.indent = value + 1
        self.ker.indent = value

    def str(self):
        s = self.indent * '\t'
        self_is, _ = self.inline_str(self.indent_col)
        if self_is[-1].isspace():
            if self.indent:
                s += self_is[:-self.indent]
            else:
                s += self_is
        else:
            s += self_is + '\n'
        return s

    def might_fit_on_line(self):
        if self.kel.has_comments or self.ker.pre_comments:
            return False
        if self.contents and isinstance(self.contents[0], Pair):
            return len(self) == 1 and not self.contents[0].has_comments
        return all(isinstance(x, Commented) and not x.has_comments
                   for x in self)

    def inline_str(self, col):
        s = ''
        nl = 0
        kel_is, (nl_kel, col_kel) = self.kel.inline_str(col)
        s += kel_is
        nl += nl_kel
        col = col_kel
        if self.might_fit_on_line():
            # attempt one line object
            s_oneline, col_oneline = s, col
            for item in self:
                item_is, (nl_item, col_item) = item.inline_str(1 + col_oneline)
                s_oneline += ' ' + item_is
                col_oneline = col_item
                if nl_item > 0 or col_oneline + 2 > CHARS_PER_LINE:
                    break
            else:
                if self.contents:
                    s_oneline += ' '
                    col_oneline += 1
                ker_is, (nl_ker, col_ker) = self.ker.inline_str(col_oneline)
                if (nl_ker == 0 or
                    chars(ker_is.splitlines()[0]) > CHARS_PER_LINE):
                    s_oneline += ker_is
                    return s_oneline, (nl_ker, col_ker)
        if self.has_pairs:
            if s[-1].isspace():
                if self.indent:
                    s = s[:-self.indent]
            else:
                s += '\n'
                nl += 1
            for item in self:
                item_s = item.str()
                s += item_s
                nl += item_s.count('\n')
            s += self.indent * '\t'
            col = self.indent_col
        else:
            sep = '\n' + (self.indent + 1) * '\t'
            sep_col = chars(sep)
            if s[-1].isspace():
                s += '\t'
            else:
                s += sep
                nl += 1
            col = sep_col
            for item in self:
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
        col = col_ker
        return s, (nl, col)

flag = False

def unquote(string):
    return string[1:-1]

def some(tok_type):
    return (parser.some(lambda tok: tok.type == tok_type) >>
            (lambda tok: tok.value)).named(str(tok_type))

unarg = lambda f: lambda x: f(*x)
many = parser.many
maybe = parser.maybe
skip = parser.skip
fwd = parser.with_forward_decls

nl = skip(many(some('newline')))
end = nl + skip(parser.finished)
comment = some('comment')
commented = lambda x: (many(nl + comment) + nl + x + maybe(comment))

def op(s):
    return (commented(parser.a(lexer.Token('op', s)) >>
            (lambda tok: tok.value)) >> unarg(Op))

unquoted_string = commented(some('unquoted_string')) >> unarg(String)
quoted_string = commented(some('quoted_string') >> unquote) >> unarg(String)
number = commented(some('number')) >> unarg(Number)
date = commented(some('date')) >> unarg(Date)

key = unquoted_string | date | number
value = fwd(lambda: obj | key | quoted_string)
pair = key + op('=') + value >> unarg(Pair)
obj = op('{') + (many(pair | value)) + op('}') >> unarg(Obj)
toplevel = many(pair) + many(nl + comment) + end >> unarg(TopLevel)

def parse(s):
    tokens = [t for t in tokenize(s) if t.type not in useless]
    # try:
    tree = toplevel.parse(tokens)
    # except parser.NoParseError:
    #     from pprint import pprint
    #     pprint(list(enumerate(tokens[:20])))
    #     raise
    return tree

def parse_file(path, encoding='cp1252'):
    with path.open(encoding=encoding) as f:
        try:
            tree = parse(f.read())
        except parser.NoParseError:
            print(path)
            raise
    return tree
