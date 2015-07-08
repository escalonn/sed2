#!/usr/bin/env python3

import collections
import csv
import pathlib
import re
import shutil
import ck2parser

rootpath = pathlib.Path('..')
swmhpath = rootpath / 'SWMH-BETA/SWMH'
sed2path = rootpath / 'SED2'

def get_cultures(where):
    cultures = []
    for path in ck2parser.files(where, 'common/cultures/*.txt'):
        tree = ck2parser.parse_file(path)
        cultures.extend(n2 for _, v in tree for n2, v2 in v if isinstance(v2,
                                                                         list))
    return cultures

def main():
    templates_loc = sed2path / 'templates/localisation'
    templates_lt = sed2path / 'templates/common/landed_titles'
    build = sed2path / 'build'
    build_loc = build / 'localisation'
    build_lt = build / 'common/landed_titles'
    while build.exists():
        print('Removing old build...')
        shutil.rmtree(str(build), ignore_errors=True)
    build_loc.mkdir(parents=True)
    build_lt.mkdir(parents=True)

    for inpath in ck2parser.files(swmhpath, 'localisation/*.csv'):
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
    lt_keys = ['title', 'title_female', 'foa', 'title_prefix', 'short_name',
        'name_tier', 'location_ruler_title', 'dynasty_title_names',
        'male_names'] + cultures

    def update_tree(v, sed2, lt_keys):
        for n2, v2 in v:
            if ck2parser.is_codename(n2):
                if n2.startswith('b_'):
                    for n3, v3 in reversed(v2):
                        if n3 in cultures:
                            v2.remove((n3, v3))
                else:
                    for n3, v3 in reversed(v2):
                        if n3 in lt_keys:
                            v2.remove((n3, v3))
                    if sed2[n2]:
                        index = next((i for i, (n3, _) in enumerate(v2)
                                      if ck2parser.is_codename(n3)), len(v2))
                        v2[index:index] = sed2[n2]
                update_tree(v2, sed2, lt_keys)

    for inpath in ck2parser.files(swmhpath, 'common/landed_titles/*.txt'):
        template = templates_lt / inpath.with_suffix('.csv').name
        outpath = build_lt / inpath.name
        sed2 = collections.defaultdict(list)
        with template.open(encoding='cp1252', newline='') as csvfile:
            for title, key, val, *_ in csv.reader(csvfile, dialect='ckii'):
                title, key, val = title.strip(), key.strip(), val.strip()
                if val:
                    if key in ['male_names', 'female_names']:
                        val = [x.strip('"')
                               for x in re.findall(r'[^"\s]+|"[^"]*"', val)]
                    sed2[title].append((key, val))
        item = ck2parser.parse_file(inpath)
        update_tree(item, sed2, lt_keys)
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(ck2parser.to_string(item, fq_keys=cultures))

if __name__ == '__main__':
    main()
