#!/usr/bin/env python3

import collections
import csv
import datetime
import re
import shutil
import sys
import time
import ck2parser

no_provinces = '--no-provinces' in sys.argv[1:]

version = 'v2.2.0-BETA'
if no_provinces:
    version += '-noprovinces'

rootpath = ck2parser.rootpath
swmhpath = rootpath / 'SWMH-BETA/SWMH'
arkopath = rootpath / 'ARKOpack_Armoiries'
sed2path = rootpath / 'SED2'

province_loc_files = [
    'A SWMHcounties.csv', 'A SWMHnewprovinces.csv', 'A SWMHprovinces.csv']

def main():
    start_time = time.time()
    templates = sed2path / 'templates'
    templates_sed2 = templates / 'SED2'
    templates_loc = templates_sed2 / 'localisation'
    templates_lt = templates_sed2 / 'common/landed_titles'
    templates_dyn = templates_sed2 / 'common/dynasties'
    templates_viet_loc = templates / 'SED2+VIET/localisation'
    templates_emf_loc = templates / 'SED2+EMF/localisation'
    templates_arko_dyn = templates / 'SED2+ARKO/common/dynasties'
    build = sed2path / 'build'
    build_sed2 = build / 'SED2'
    build_loc = build_sed2 / 'localisation'
    build_lt = build_sed2 / 'common/landed_titles'
    build_dyn = build_sed2 / 'common/dynasties'
    build_viet_loc = build / 'SED2+VIET/localisation'
    build_emf_loc = build / 'SED2+EMF/localisation'
    build_arko_dyn = build / 'SED2+ARKO/common/dynasties'
    while build.exists():
        print('Removing old build...')
        shutil.rmtree(str(build), ignore_errors=True)
    build_loc.mkdir(parents=True)
    build_lt.mkdir(parents=True)
    build_dyn.mkdir(parents=True)
    build_viet_loc.mkdir(parents=True)
    build_emf_loc.mkdir(parents=True)
    build_arko_dyn.mkdir(parents=True)
    swmh_files = set()
    sed2 = {}
    keys_to_blank = set()

    for path in ck2parser.files('localisation/*', basedir=swmhpath):
        swmh_files.add(path.name)

    for inpath in ck2parser.files('*', basedir=templates_loc):
        for row in ck2parser.csv_rows(inpath, comments=True):
            key, val = row[0].strip(), row[1].strip()
            if not val:
                if re.fullmatch(r' +', row[2]):
                    val = ' '
                elif not row[2] or inpath.name not in swmh_files:
                    keys_to_blank.add(key)
            if not key.startswith('#'):
                if key not in sed2:
                    sed2[key] = val
                else:
                    print('Duplicate localisations for ' + key)
        if inpath.name not in swmh_files:
            outpath = build_loc / inpath.name
            sed2rows = [[''] * 15]
            sed2rows[0][:6] = [
                '#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
            sed2rows[0][-1] = 'x'
            for row in ck2parser.csv_rows(inpath):
                if no_provinces and re.match(r'[cb]_|PROV\d+', row[0]):
                    continue
                sed2row = [''] * 15
                sed2row[0] = row[0].strip()
                sed2row[1] = row[1].strip()
                sed2row[-1] = 'x'
                if sed2row[1] or sed2row[0] in keys_to_blank:
                    sed2rows.append(sed2row)
            with outpath.open('w', encoding='cp1252', newline='') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    # EMF
    inpath = templates_emf_loc / 'A A SED+EMF.csv'
    sed2rows = [[''] * 15]
    sed2rows[0][:6] = ['#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
    sed2rows[0][-1] = 'x'
    for row in ck2parser.csv_rows(inpath):
        if no_provinces and re.match(r'[cb]_|PROV\d+', row[0]):
            continue
        sed2row = [''] * 15
        sed2row[0] = row[0].strip()
        sed2row[1] = row[1].strip()
        sed2row[-1] = 'x'
        if sed2row[1] or sed2row[0] in keys_to_blank:
            sed2rows.append(sed2row)
    outpath = build_emf_loc / inpath.name
    with outpath.open('w', encoding='cp1252', newline='') as csvfile:
        csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    # VIET
    inpath = templates_viet_loc / 'A A SED+VIET.csv'
    sed2rows = [[''] * 15]
    sed2rows[0][:6] = ['#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
    sed2rows[0][-1] = 'x'
    for row in ck2parser.csv_rows(inpath):
        if no_provinces and re.match(r'[cb]_|PROV\d+', row[0]):
            continue
        sed2row = [''] * 15
        sed2row[0] = row[0].strip()
        sed2row[1] = row[1].strip()
        sed2row[-1] = 'x'
        if sed2row[1] or sed2row[0] in keys_to_blank:
            sed2rows.append(sed2row)
    outpath = build_viet_loc / inpath.name
    with outpath.open('w', encoding='cp1252', newline='') as csvfile:
        csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    for inpath in ck2parser.files('localisation/*', basedir=swmhpath):
        if no_provinces and inpath.name in province_loc_files:
            continue
        outpath = build_loc / inpath.name
        sed2rows = [[''] * 15]
        sed2rows[0][:6] = [
            '#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
        sed2rows[0][-1] = 'x'
        for row in ck2parser.csv_rows(inpath):
            sed2row = [''] * 15
            sed2row[0] = row[0]
            sed2row[1] = sed2.get(row[0], row[1])
            sed2row[-1] = 'x'
            if sed2row[1] or sed2row[0] in keys_to_blank:
                sed2rows.append(sed2row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    cultures = ck2parser.cultures(swmhpath, groups=False)
    lt_keys = [
        'title', 'title_female', 'foa', 'title_prefix', 'short_name',
        'name_tier', 'location_ruler_title', 'dynasty_title_names',
        'male_names'] + cultures
    ck2parser.fq_keys = cultures

    def update_lt(tree):
        for n, v in tree:
            if ck2parser.is_codename(n.val):
                if n.val.startswith('b_') and not no_provinces:
                    for p2 in reversed(v.contents):
                        if p2.key.val in cultures:
                            v.contents.remove(p2)
                elif not no_provinces or re.match(r'[ekd]_', n.val):
                    for p2 in reversed(v.contents):
                        if p2.key.val in lt_keys:
                            v.contents.remove(p2)
                    if sed2[n.val]:
                        index = next(
                            (i for i, (n2, _) in enumerate(v)
                             if ck2parser.is_codename(n2.val)), len(v))
                        v.contents[index:index] = sed2[n.val]
                        # propagates indent to children
                        v.indent = v.indent
                update_lt(v)

    for inpath, tree in ck2parser.parse_files('common/landed_titles/*',
                                              basedir=swmhpath):
        template = templates_lt / inpath.with_suffix('.csv').name
        outpath = build_lt / inpath.name
        sed2 = collections.defaultdict(list)
        for row in ck2parser.csv_rows(template):
            title, key, val = (s.strip() for s in row[:3])
            if val:
                if key in ['male_names', 'female_names']:
                    val = ck2parser.Obj.from_iter(
                        ck2parser.String.from_str(x.strip('"'))
                        for x in re.findall(r'[^"\s]+|"[^"]*"', val))
                sed2[title].append(ck2parser.Pair.from_kv(key, val))
        # from pprint import pprint
        # # pprint(tree.str())
        # pprint(tree.contents[0].str())
        update_lt(tree)
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(tree.str())

    # dynasties
    ck2parser.fq_keys = ['name']
    sed2 = collections.defaultdict(str)
    for path in ck2parser.files('common/dynasties/*', basedir=templates_sed2):
        for row in ck2parser.csv_rows(path):
            dyn_id, name = int(row[0]), row[1].strip()
            # logic here concerns how dupe IDs are interpreted
            if name:
                sed2[dyn_id] = name
    for inpath, tree in ck2parser.parse_files('common/dynasties/*', swmhpath):
        for n, v in tree:
            dyn_id = int(n.val)
            if sed2[dyn_id]:
                name = v['name']
                ck2parser.prepend_post_comment(name, name.val)
                name.val = sed2[dyn_id]
        outpath = build_dyn / inpath.name
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(tree.str())

    # ARKO
    # sed2 carried over
    inpath = templates_arko_dyn / 'ARKO.csv'
    for row in ck2parser.csv_rows(inpath):
        dyn_id, name = int(row[0]), row[1].strip()
        # logic here concerns how dupe IDs are interpreted
        # TEMPORARY: let SED definitions override blank SED+ARKO definitions
        if name:
            sed2[dyn_id] = name
    for inpath, tree in ck2parser.parse_files('common/dynasties/*',
                                              basedir=arkopath):
        for n, v in tree:
            dyn_id = int(n.val)
            if sed2[dyn_id]:
                name = v['name']
                ck2parser.prepend_post_comment(name, name.val)
                name.val = sed2[dyn_id]
        outpath = build_arko_dyn / inpath.name
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(tree.str())

    with (build_sed2 / 'version.txt').open('w', encoding='cp1252',
                                      newline='\r\n') as f:
        print('{} - {}'.format(version, datetime.date.today()), file=f)
    end_time = time.time()
    print('Time: {} s'.format(end_time - start_time))

if __name__ == '__main__':
    main()
