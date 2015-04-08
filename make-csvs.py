import collections
import csv
import datetime
import operator
import pathlib
import re
import funcparserlib
import funcparserlib.lexer
import funcparserlib.parser

rootpath = pathlib.Path('..')

def tokenize(string):
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
    inner_tokenize = funcparserlib.lexer.make_tokenizer(token_specs)
    return (tok for tok in inner_tokenize(string) if tok.type not in useless)

def parse(tokens):
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
    return toplevel.parse(list(tokens))

def valid_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

def get_province_id():
    province_id = {}
    for path in rootpath.glob('SWMH/history/provinces/*.txt'):
        number = int(path.name.split(' - ', maxsplit=1)[0])
        with path.open(encoding='cp1252') as f:
            s = f.read()
        tree = parse(tokenize(s))
        try:
            title = next(v for n, v in tree if n == 'title')
        except StopIteration:
            continue
        province_id[title] = 'PROV{}'.format(number)
    return province_id

def get_dynamics(cultures, province_id):
    path = rootpath / 'SWMH/common/landed_titles/swmh_landed_titles.txt'
    with path.open(encoding='cp1252') as f:
        s = f.read()
    landed_titles = parse(tokenize(s))
    dynamics = collections.defaultdict(set)

    def recurse(v, n=None):
        for n1, v1 in v:
            if not valid_codename(n1):
                continue
            for n2, v2 in v1:
                if n2 in cultures:
                    dynamics[n1].add(v2)
                    if n1 in province_id:
                        dynamics[province_id[n1]].add(v2)
            recurse(v1, n1)

    recurse(landed_titles)
    for k, v in province_id.items():
        dynamics[v].add(k)

    return dynamics

def get_cultures():
    path = rootpath / 'SWMH/common/cultures/00_cultures.txt'
    with path.open(encoding='cp1252') as f:
        s = f.read()
    tree = parse(tokenize(s))
    return [n2 for _, v in tree for n2, v2 in v if isinstance(v2, list)]

def main():
    csv.register_dialect('ckii', delimiter=';')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if row[0] not in english:
                    english[row[0]] = row[1]
    
    province_id = get_province_id()
    cultures = get_cultures()
    dynamics = get_dynamics(cultures, province_id)

    for inpath in rootpath.glob('SWMH/localisation/*.csv'):
        outpath = rootpath / 'SED2/templates' / inpath.name
        prev_map = collections.defaultdict(str)
        if outpath.exists():
            with outpath.open(newline='', encoding='cp1252') as csvfile:
                prev_map.update(tuple(row[:2])
                                for row in csv.reader(csvfile, dialect='ckii'))
        with inpath.open(newline='', encoding='cp1252') as csvfile:
            rows = [[row[0], prev_map[row[0]], row[1], english[row[0]],
                     ','.join(dynamics[row[0]])]
                    for row in csv.reader(csvfile, dialect='ckii')]
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(rows)

if __name__ == '__main__':
    main()
