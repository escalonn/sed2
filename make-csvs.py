#!/usr/bin/env python3

import collections
import csv
import pathlib
import re
import shutil
import tempfile
import ck2parser

rootpath = pathlib.Path('C:/Users/Nicholas/Documents/CK2')
swmhpath = rootpath / 'SWMH-BETA/SWMH'

def get_province_id(where):
    tree = ck2parser.parse_file(where / 'map/default.map')
    defs = next(v.val for n, v in tree if n.val == 'definitions')
    id_name = {}
    with (where / 'map' / defs).open(newline='', encoding='cp1252') as csvfile:
        for row in csv.reader(csvfile, dialect='ckii'):
            try:
                id_name[int(row[0])] = row[4]
            except (IndexError, ValueError):
                continue
    province_id = {}
    for path in ck2parser.files('history/provinces/*.txt', where):
        number, name = path.stem.split(' - ')
        if id_name[int(number)] == name:
            tree = ck2parser.parse_file(path)
            try:
                title = next(v.val for n, v in tree if n.val == 'title')
            except StopIteration:
                continue
            province_id[title] = 'PROV' + number
    return province_id

def get_dynamics(where, cultures, prov_id):
    dynamics = collections.defaultdict(list,
                                       [(v, [k]) for k, v in prov_id.items()])

    def recurse(v, n=None):
        for n1, v1 in v:
            if not ck2parser.is_codename(n1.val):
                continue
            for n2, v2 in v1:
                if n2.val in cultures:
                    if v2.val not in dynamics[n1.val]:
                        dynamics[n1.val].append(v2.val)
                    if (n1.val in prov_id and
                        v2.val not in dynamics[prov_id[n1.val]]):
                        dynamics[prov_id[n1.val]].append(v2.val)
            recurse(v1, n1)

    for path in ck2parser.files('common/landed_titles/*.txt', where):
        recurse(ck2parser.parse_file(path))
    return dynamics

def get_cultures(where):
    cultures = []
    for path in ck2parser.files('common/cultures/*.txt', where):
        tree = ck2parser.parse_file(path)
        cultures.extend(n2.val for _, v in tree for n2, v2 in v
                        if n2.val != 'graphical_cultures')
    return cultures

def get_religions(where):
    religions = []
    rel_groups = []
    for path in ck2parser.files('common/religions/*.txt', where):
        tree = ck2parser.parse_file(path)
        religions.extend(n2.val for _, v in tree for n2, v2 in v
                         if (isinstance(v2, ck2parser.Obj) and
                             n2.val not in ['male_names', 'female_names']))
        rel_groups.extend(n.val for n, v in tree)
    return religions, rel_groups

def main():
    english = collections.defaultdict(str)
    for path in ck2parser.files('English SWMH/localisation/*.csv',
                                basedir=rootpath):
        with path.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                try:
                    english[row[0]] = row[1]
                except IndexError:
                    continue
    prov_id = get_province_id(swmhpath)
    cultures = get_cultures(swmhpath)
    religions, rel_groups = get_religions(swmhpath)
    dynamics = get_dynamics(swmhpath, cultures, prov_id)
    vanilla = ck2parser.localisation()
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in ck2parser.files('localisation/*.csv', basedir=templates):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_loc.update({row[0].strip(): row[1].strip()
                             for row in csv.reader(csvfile, dialect='ckii')
                             if row[0] and '#' not in row[0]})
    for path in ck2parser.files('common/landed_titles/*.csv',
                                basedir=templates):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_lt.update({(row[0].strip(), row[1].strip()): row[2].strip()
                            for row in csv.reader(csvfile, dialect='ckii')
                            if row[0] and '#' not in row[0]})

    def recurse(v):
        for n2, v2 in v:
            if not ck2parser.is_codename(n2.val):
                continue
            items = []
            for n3, v3 in v2:
                if n3.val in lt_keys:
                    if isinstance(v3, ck2parser.Obj):
                        value = ' '.join(s.val for s in v3)
                    else:
                        value = v3.val
                    items.append((n3.val, value))
            yield n2.val, items
            yield from recurse(v2)

    with tempfile.TemporaryDirectory() as td:
        templates_t = pathlib.Path(td)
        (templates_t / 'localisation').mkdir(parents=True)
        (templates_t / 'common/landed_titles').mkdir(parents=True)
        for inpath in ck2parser.files('localisation/*.csv', basedir=swmhpath):
            outpath = templates_t / 'localisation' / inpath.name
            out_rows = [
                ['#CODE', 'SED2', 'SWMH', 'OTHERSWMH', 'SED1', 'VANILLA']]
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

        lt_keys_not_cultures = [
            'title', 'title_female', 'foa', 'title_prefix', 'short_name',
            'name_tier', 'location_ruler_title', 'dynasty_title_names',
            'male_names']
        lt_keys = lt_keys_not_cultures + cultures

        for inpath in ck2parser.files('common/landed_titles/*.txt',
                                      basedir=swmhpath):
            outpath = (templates_t / 'common/landed_titles' /
                       inpath.with_suffix('.csv').name)
            out_rows = [
                ['#TITLE', 'KEY', 'SED2', 'SWMH']]
            col_width = [0, 0, 8]
            tree = ck2parser.parse_file(inpath)
            for title, pairs in recurse(tree):
                # here disabled for now: preservation of modifiers added to
                # template and not found in landed_titles (slow)
                # for (t, k), v in prev_lt.items():
                #     if t == title and not any(k == k2 for k2, _ in pairs):
                #         pairs.append((k, ''))
                # also disabled: barony stuff
                if not title.startswith('b_'):
                    for key, value in sorted(
                        pairs, key=lambda p: lt_keys.index(p[0])):
                        out_row = [title, key, prev_lt[title, key], value]
                        # don't allow changes to anything but dynamic names...
                        # just for now
                        if key in lt_keys_not_cultures:
                            out_row[2] = out_row[3]
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
