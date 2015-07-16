#!/usr/bin/env python3

import collections
import csv
import pathlib
import re
import shutil
import tempfile
import ck2parser

rootpath = pathlib.Path('..')
swmhpath = rootpath / 'SWMH-BETA/SWMH'
vanillapath = pathlib.Path(
    'C:/Program Files (x86)/Steam/SteamApps/common/Crusader Kings II')

def get_locs(where):
    locs = {}
    for path in ck2parser.files(where, 'localisation/*.csv'):
        with path.open(newline='', encoding='cp1252',
                       errors='replace') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                locs[row[0]] = row[1]
    return locs

def get_province_id(where):
    province_id = collections.OrderedDict()
    for path in ck2parser.files(where, 'history/provinces/*.txt'):
        tree = ck2parser.parse_file(path)
        try:
            # print(*tree[0][:3], sep='\n')
            # raise SystemExit()
            title = next(v[1] for _, n, _, v in tree[0] if n == 'title')
        except StopIteration:
            continue
        number = int(path.name.split(' - ', maxsplit=1)[0])
        province_id[title] = 'PROV{}'.format(number)
    return province_id

def get_dynamics(where, cultures, prov_id):
    dynamics = collections.defaultdict(list,
                                       [(v, [k]) for k, v in prov_id.items()])

    def recurse(v, n=None):
        for _, n1, _, v1 in v:
            if not ck2parser.is_codename(n1):
                continue
            for _, n2, _, v2 in v1[1]:
                if n2 in cultures:
                    if v2[1] not in dynamics[n1]:
                        dynamics[n1].append(v2[1])
                    if n1 in prov_id and v2[1] not in dynamics[prov_id[n1]]:
                        dynamics[prov_id[n1]].append(v2[1])
            recurse(v1[1], n1)

    for path in ck2parser.files(where, 'common/landed_titles/*.txt'):
        recurse(ck2parser.parse_file(path)[0])
    return dynamics

def get_cultures(where):
    cultures = []
    for path in ck2parser.files(where, 'common/cultures/*.txt'):
        tree = ck2parser.parse_file(path)
        cultures.extend(n2 for _, _, _, v in tree[0]
                        for _, n2, _, v2 in v[1]
                        if isinstance(v2[1], list) and
                        n2 not in ['male_names', 'female_names'])
    return cultures

def get_religions(where):
    religions = []
    rel_groups = []
    for path in ck2parser.files(where, 'common/religions/*.txt'):
        tree = ck2parser.parse_file(path)
        religions.extend(n2 for _, _, _, v in tree[0]
                         for _, n2, _, v2 in v[1]
                         if isinstance(v2[1], list) and
                         n2 not in ['male_names', 'female_names'])
        rel_groups.extend(n for _, n, *_ in tree[0])
    return religions, rel_groups

def main():
    english = collections.defaultdict(str)
    for path in ck2parser.files(rootpath, 'English SWMH/localisation/*.csv'):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                english[row[0]] = row[1]
    province_id = get_province_id(swmhpath)
    cultures = get_cultures(swmhpath)
    religions, rel_groups = get_religions(vanillapath)
    # print(cultures)
    # print(religions)
    # print(rel_groups)
    # raise SystemExit()
    dynamics = get_dynamics(swmhpath, cultures, province_id)
    vanilla = get_locs(vanillapath)
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in ck2parser.files(templates, 'localisation/*.csv'):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_loc.update({row[0].strip(): row[1].strip()
                             for row in csv.reader(csvfile, dialect='ckii')
                             if row[0] and '#' not in row[0]})
    for path in ck2parser.files(templates, 'common/landed_titles/*.csv'):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_lt.update({(row[0].strip(), row[1].strip()): row[2].strip()
                            for row in csv.reader(csvfile, dialect='ckii')
                            if row[0] and '#' not in row[0]})

    def recurse(v):
        for _, n2, _, v2 in v:
            if not ck2parser.is_codename(n2):
                continue
            items = []
            for _, n3, _, v3 in v2[1]:
                if n3 in lt_keys:
                    val = v3[1]
                    if not isinstance(val, str):
                        val = ' '.join(ck2parser.to_string(s) for s in val)
                    items.append((n3, val))
            yield n2, items
            yield from recurse(v2[1])

    with tempfile.TemporaryDirectory() as td:
        templates_t = pathlib.Path(td)
        (templates_t / 'localisation').mkdir(parents=True)
        (templates_t / 'common/landed_titles').mkdir(parents=True)
        for inpath in ck2parser.files(swmhpath, 'localisation/*.csv'):
            outpath = templates_t / 'localisation' / inpath.name
            out_rows = [
                ['#CODE', 'SED2', 'SWMH', 'OTHERSWMH', 'SED1', 'VANILLA']
            ]
            col_width = [0, 8]
            with inpath.open(newline='', encoding='cp1252') as csvfile:
                for row in csv.reader(csvfile, dialect='ckii'):
                    if row[0] and not row[0].startswith('b_'):
                        if '#' in row[0]:
                            row = [','.join(row)] + [''] * (len(row) - 1)
                        out_row = [row[0], prev_loc[row[0]], row[1],
                                   ','.join(dynamics[row[0]]), english[row[0]],
                                   vanilla.get(row[0], '')]
                        out_rows.append(out_row)
                        if '#' not in row[0]:
                            col_width[0] = max(len(row[0]), col_width[0])
            for i, out_row in enumerate(out_rows):
                if '#' not in out_row[0] or i == 0:
                    for col, width in enumerate(col_width):
                        out_row[col] = out_row[col].ljust(width)
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)

        lt_keys_not_cultures = ['title', 'title_female', 'foa', 'title_prefix',
            'short_name', 'name_tier', 'location_ruler_title',
            'dynasty_title_names', 'male_names']
        lt_keys = lt_keys_not_cultures + cultures

        for inpath in ck2parser.files(swmhpath, 'common/landed_titles/*.txt'):
            outpath = (templates_t / 'common/landed_titles' /
                       inpath.with_suffix('.csv').name)
            out_rows = [
                ['#TITLE', 'KEY', 'SED2', 'SWMH']
            ]
            col_width = [0, 0, 8]
            item = ck2parser.parse_file(inpath)
            for title, pairs in recurse(item[0]):
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
                        # don't allow changes to anything but dynamic names...
                        # just for now
                        if key in lt_keys_not_cultures:
                            out_row[2] = value
                        out_rows.append(out_row)
                        for c in range(2):
                            col_width[c] = max(len(out_row[c]), col_width[c])
            for out_row in out_rows:
                for col, width in enumerate(col_width):
                    out_row[col] = out_row[col].ljust(width)
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)
        while templates.exists():
            print('Removing old templates...')
            shutil.rmtree(str(templates), ignore_errors=True)
        shutil.copytree(str(templates_t), str(templates))
if __name__ == '__main__':
    main()
