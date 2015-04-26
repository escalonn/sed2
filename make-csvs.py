import collections
import csv
import datetime
import operator
import pathlib
import re
import shutil
import funcparserlib
import funcparserlib.lexer
import funcparserlib.parser

rootpath = pathlib.Path('..')
oldswmhpath = rootpath / 'SWMH/SWMH'
swmhpath = rootpath / 'SWMH-BETA/SWMH_EE'

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

def get_province_id(where):
    province_id = {}
    for path in sorted(where.glob('history/provinces/*.txt')):
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

def get_dynamics(where, cultures, prov_id):
    dynamics = collections.defaultdict(list)
    for k, v in prov_id.items():
        dynamics[v].append(k)

    def recurse(v, n=None):
        for n1, v1 in v:
            if not valid_codename(n1):
                continue
            for n2, v2 in v1:
                if n2 in cultures:
                    if v2 not in dynamics[n1]:
                        dynamics[n1].append(v2)
                    if n1 in prov_id and v2 not in dynamics[prov_id[n1]]:
                        dynamics[prov_id[n1]].append(v2)
            recurse(v1, n1)

    for path in sorted(where.glob('common/landed_titles/*.txt')):
        with path.open(encoding='cp1252') as f:
            try:
                s = f.read()
            except UnicodeDecodeError:
                print(path)
                raise
        landed_titles = parse(tokenize(s))
        recurse(landed_titles)
    return dynamics

def get_cultures(where):
    cultures = []
    for path in sorted(where.glob('common/cultures/*.txt')):
        with path.open(encoding='cp1252') as f:
            s = f.read()
        tree = parse(tokenize(s))
        cultures.extend(n2 for _, v in tree for n2, v2 in v if isinstance(v2,
                                                                         list))
    return cultures

def main():
    csv.register_dialect('ckii', delimiter=';')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                english[row[0]] = row[1]
    province_id = get_province_id(swmhpath)
    cultures = get_cultures(swmhpath)
    dynamics = get_dynamics(swmhpath, cultures, province_id)
    prev_map = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in sorted(templates.glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_map.update(tuple(row[:2])
                                for row in csv.reader(csvfile, dialect='ckii'))
    if templates.exists():
        shutil.rmtree(str(templates))
    templates.mkdir()
    for inpath in sorted(swmhpath.glob('localisation/*.csv')):
        outpath = templates / inpath.name
        out_rows = []
        with inpath.open(newline='', encoding='cp1252') as csvfile:
            try:
                for row in csv.reader(csvfile, dialect='ckii'):
                    if not re.fullmatch(r'[ekdcb]_.*_adj_.*', row[0]):
                        out_row = [row[0], prev_map[row[0]], row[1],
                                   ','.join(dynamics[row[0]]), english[row[0]]]
                        out_rows.append(out_row)
            except UnicodeDecodeError:
                print(inpath)
                raise
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(out_rows)

if __name__ == '__main__':
    main()
