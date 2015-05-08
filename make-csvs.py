import collections
import csv
import pathlib
import re
import shutil
import ck2parser

rootpath = pathlib.Path('..')
# oldswmhpath = rootpath / 'SWMH/SWMH'
swmhpath = rootpath / 'SWMH-BETA/SWMH_EE'

def valid_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

def get_province_id(where):
    province_id = collections.OrderedDict()
    for path in sorted(where.glob('history/provinces/*.txt')):
        with path.open(encoding='cp1252') as f:
            tree = ck2parser.parse(f.read())
        try:
            title = next(v for n, v in tree if n == 'title')
        except StopIteration:
            continue
        number = int(path.name.split(' - ', maxsplit=1)[0])
        province_id[title] = 'PROV{}'.format(number)
    return province_id

def get_dynamics(where, cultures, prov_id):
    dynamics = collections.defaultdict(list,
                                       [(v, [k]) for k, v in prov_id.items()])

    def recurse(v, n=None):
        for n1, v1 in v:
            if not valid_codename(n1):
                continue
            assert n1 not in dynamics
            for n2, v2 in v1:
                if n2 in cultures:
                    if v2 not in dynamics[n1]:
                        dynamics[n1].append(v2)
                    if n1 in prov_id and v2 not in dynamics[prov_id[n1]]:
                        dynamics[prov_id[n1]].append(v2)
            recurse(v1, n1)

    for path in sorted(where.glob('common/landed_titles/*.txt')):
        with path.open(encoding='cp1252') as f:
            recurse(ck2parser.parse(f.read()))
    return dynamics

def get_cultures(where):
    cultures = []
    for path in sorted(where.glob('common/cultures/*.txt')):
        with path.open(encoding='cp1252') as f:
            tree = ck2parser.parse(f.read())
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
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(list)

    templates = rootpath / 'SED2/templates'
    templates_loc = templates / 'localisation'
    for path in sorted(templates_loc.glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_loc.update(tuple(row[:2])
                                for row in csv.reader(csvfile, dialect='ckii'))
    templates_lt = templates / 'common/landed_titles'
    for path in sorted(templates_lt.glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                prev_lt[row[0]].append(row[1:]) # TODO or something
    if templates.exists():
        shutil.rmtree(str(templates))
    templates_loc.mkdir(parents=True)
    templates_lt.mkdir(parents=True)
    for inpath in sorted(swmhpath.glob('localisation/*.csv')):
        outpath = templates_loc / inpath.name
        out_rows = []
        with inpath.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                out_row = [row[0], prev_map[row[0]], row[1],
                           ','.join(dynamics[row[0]]), english[row[0]]]
                out_rows.append(out_row)
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(out_rows)
    for inpath in sorted(swmhpath.glob('common/landed_titles/*.txt')):
        outpath = templates_lt / inpath.with_suffix('.csv').name
        out_rows = []
        with inpath.open(encoding='cp1252') as f:
            item = ck2parser.parse(f.read())
        # TODO something something using prev_lt and item
        # out_row = [row[0], prev_map[row[0]], row[1],
        #            ','.join(dynamics[row[0]]), english[row[0]]]
        # out_rows.append(out_row)
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(out_rows)

if __name__ == '__main__':
    main()
