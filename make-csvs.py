import collections
import csv
import pathlib
import re
import shutil
import tempfile
import ck2parser

rootpath = pathlib.Path('..')
# oldswmhpath = rootpath / 'SWMH/SWMH'
swmhpath = rootpath / 'SWMH-BETA/SWMH_EE'
vanillapath = pathlib.Path(
    'C:/Program Files (x86)/Steam/SteamApps/common/Crusader Kings II')

def valid_codename(string):
    try:
        return re.match(r'[ekdcb]_', string)
    except TypeError:
        return False

def get_locs(where):
    locs = {}
    for path in sorted(where.glob('localisation/*.csv')):
        with path.open(newline='', encoding='cp1252',
                       errors='replace') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                locs[row[0]] = row[1]
    return locs

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

def get_religions(where):
    religions = []
    rel_groups = []
    for path in sorted(where.glob('common/religions/*.txt')):
        with path.open(encoding='cp1252') as f:
            item = ck2parser.parse(f.read())
        religions.extend(n2 for _, v in item for n2, v2 in v if isinstance(v2,
                        list) and n2 not in ['male_names', 'female_names'])
        rel_groups.extend(n for n, v in item)
    return religions, rel_groups

def main():
    csv.register_dialect('ckii', delimiter=';')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                english[row[0]] = row[1]
    province_id = get_province_id(swmhpath)
    cultures = get_cultures(swmhpath)
    religions, rel_groups = get_religions(swmhpath)
    dynamics = get_dynamics(swmhpath, cultures, province_id)
    vanilla = get_locs(vanillapath)
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in sorted((templates / 'localisation').glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_loc.update({row[0]: row[1]
                             for row in csv.reader(csvfile, dialect='ckii')})
    for path in sorted((templates / 'common/landed_titles').glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_lt.update({(row[0], row[1]): row[2]
                            for row in csv.reader(csvfile, dialect='ckii')})

    def recurse(v):
        for n2, v2 in v:
            if not valid_codename(n2):
                continue
            items = []
            for n3, v3 in v2:
                if n3 in lt_keys:
                    if not isinstance(v3, str):
                        v3 = ' '.join(ck2parser.to_string(s) for s in v3)
                    items.append((n3, v3))
            yield n2, items
            yield from recurse(v2)

    with tempfile.TemporaryDirectory() as td:
        templates_t = pathlib.Path(td)
        (templates_t / 'localisation').mkdir(parents=True)
        (templates_t / 'common/landed_titles').mkdir(parents=True)
        for inpath in sorted(swmhpath.glob('localisation/*.csv')):
            outpath = templates_t / 'localisation' / inpath.name
            out_rows = []
            with inpath.open(newline='', encoding='cp1252') as csvfile:
                for row in csv.reader(csvfile, dialect='ckii'):
                    if not row[0].startswith('b_'):
                        out_row = [row[0], prev_loc[row[0]], row[1],
                                   ','.join(dynamics[row[0]]), english[row[0]],
                                   vanilla.get(row[0], '')]
                        out_rows.append(out_row)
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)

        lt_keys_not_cultures = ['title', 'title_female', 'foa', 'title_prefix',
            'short_name', 'name_tier', 'location_ruler_title',
            'dynasty_title_names', 'male_names']
        lt_keys = lt_keys_not_cultures + cultures

        rows = []
        for path in sorted(swmhpath.glob('common/landed_titles/*.txt')):
            with path.open(encoding='cp1252') as f:
                rows.extend(recurse(ck2parser.parse(f.read())))

        for inpath in sorted(swmhpath.glob('common/landed_titles/*.txt')):
            outpath = (templates_t / 'common/landed_titles' /
                       inpath.with_suffix('.csv').name)
            out_rows = []
            with inpath.open(encoding='cp1252') as f:
                item = ck2parser.parse(f.read())
            for title, pairs in recurse(item):
                # here disabled for now: preservation of modifiers added to
                # template and not found in landed_titles (slow)
                # for (t, k), v in prev_lt.items():
                #     if t == title and not any(k == k2 for k2, _ in pairs):
                #         pairs.append((k, ''))
                # also disabled: barony stuff
                if not title.startswith('b_'):
                    for key, value in sorted(pairs,
                        key=lambda x: lt_keys.index(x[0])):
                        out_row = [title, key, prev_lt[title, key], value]
                        out_rows.append(out_row)
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)
        while templates.exists():
            print('Removing old templates...')
            shutil.rmtree(str(templates), ignore_errors=True)
        shutil.copytree(str(templates_t), str(templates))
if __name__ == '__main__':
    main()
