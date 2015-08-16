#!/usr/bin/env python3

import collections
import csv
import datetime
import re
import shutil
import ck2parser
import localpaths

version = 'v2.0-RC4'

rootpath = localpaths.rootpath
swmhpath = rootpath / 'SWMH-BETA/SWMH'
sed2path = rootpath / 'SED2'

def get_cultures(where):
    cultures = []
    for path in ck2parser.files('common/cultures/*.txt', where):
        tree = ck2parser.parse_file(path)
        cultures.extend(n2.val for _, v in tree for n2, v2 in v
                        if n2.val != 'graphical_cultures')
    return cultures

def main():
    templates_loc = sed2path / 'templates/localisation'
    templates_lt = sed2path / 'templates/common/landed_titles'
    build = sed2path / 'SED2'
    build_loc = build / 'localisation'
    build_lt = build / 'common/landed_titles'
    while build.exists():
        print('Removing old build...')
        shutil.rmtree(str(build), ignore_errors=True)
    build_loc.mkdir(parents=True)
    build_lt.mkdir(parents=True)

    for inpath in ck2parser.files('localisation/*.csv', basedir=swmhpath):
        template = templates_loc / inpath.name
        outpath = build_loc / inpath.name
        with template.open(encoding='cp1252', newline='') as csvfile:
            sed2 = {row[0].strip(): row[1].strip()
                    for row in csv.reader(csvfile, dialect='ckii')}
        sed2rows = []
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if (row[0] and not row[0].startswith('#') and
                    sed2.get(row[0], True)):
                    row[1] = sed2.get(row[0], row[1])
                    row[2:] = [''] * (len(row) - 2)
                    sed2rows.append(row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    cultures = get_cultures(swmhpath)
    lt_keys = [
        'title', 'title_female', 'foa', 'title_prefix', 'short_name',
        'name_tier', 'location_ruler_title', 'dynasty_title_names',
        'male_names'] + cultures
    ck2parser.fq_keys = cultures

    def update_tree(v, sed2, lt_keys):
        for n2, v2 in v:
            if ck2parser.is_codename(n2.val):
                if n2.val.startswith('b_'):
                    for p3 in reversed(v2.contents):
                        if p3.key.val in cultures:
                            v2.contents.remove(p3)
                else:
                    for p3 in reversed(v2.contents):
                        if p3.key.val in lt_keys:
                            v2.contents.remove(p3)
                    if sed2[n2.val]:
                        index = next(
                            (i for i, (n3, _) in enumerate(v2)
                             if ck2parser.is_codename(n3.val)), len(v2))
                        v2.contents[index:index] = sed2[n2.val]
                        v2.indent = v2.indent
                update_tree(v2, sed2, lt_keys)

    for inpath in ck2parser.files('common/landed_titles/*.txt',
                                  basedir=swmhpath):
        template = templates_lt / inpath.with_suffix('.csv').name
        outpath = build_lt / inpath.name
        sed2 = collections.defaultdict(list)
        with template.open(encoding='cp1252', newline='') as csvfile:
            for title, key, val, *_ in csv.reader(csvfile, dialect='ckii'):
                title, key, val = title.strip(), key.strip(), val.strip()
                if val:
                    if key in ['male_names', 'female_names']:
                        val = ck2parser.Obj.from_iter(
                            ck2parser.String.from_str(x.strip('"'))
                            for x in re.findall(r'[^"\s]+|"[^"]*"', val))
                    sed2[title].append(ck2parser.Pair.from_kv(key, val))
        tree = ck2parser.parse_file(inpath)
        # from pprint import pprint
        # # pprint(tree.str())
        # pprint(tree.contents[0].str())
        update_tree(tree, sed2, lt_keys)
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(tree.str())

    with (build / 'version.txt').open('w', encoding='cp1252',
                                      newline='\r\n') as f:
        print('{} - {}'.format(version, datetime.date.today()), file=f)

if __name__ == '__main__':
    main()
