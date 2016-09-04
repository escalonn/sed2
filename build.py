#!/usr/bin/env python3

import collections
import csv
import datetime
import re
import shutil
import sys
from ck2parser import (rootpath, files, csv_rows, is_codename, get_cultures,
                       Obj, Pair, String, SimpleParser, FullParser)
from print_time import print_time

no_provinces = '--no-provinces' in sys.argv[1:]

version = 'v2.2.6'
if no_provinces:
    version += '-noprovinces'

swmhpath = rootpath / 'SWMH-BETA/SWMH'
minipath = rootpath / 'MiniSWMH/MiniSWMH'
sed2path = rootpath / 'sed2'
emfpath = rootpath / 'EMF/EMF'
emfswmhpath = rootpath / 'EMF/EMF+SWMH'
# emfminipath = rootpath / 'EMF/EMF+MiniSWMH'

province_loc_files = [
    'A_SWMHcounties.csv', 'A_SWMHnewprovinces.csv', 'A_SWMHprovinces.csv']

@print_time
def main():
    full_parser = FullParser()
    full_parser.newlines_to_depth = 0
    templates = sed2path / 'templates'
    templates_sed2 = templates / 'SED2'
    templates_loc = templates_sed2 / 'localisation'
    templates_lt = templates_sed2 / 'common/landed_titles'
    templates_viet_loc = templates / 'SED2+VIET/localisation'
    templates_emf_loc = templates / 'SED2+EMF/localisation'
    build = sed2path / 'build'
    build_sed2 = build / 'SED2'
    build_loc = build_sed2 / 'localisation'
    build_lt = build_sed2 / 'common/landed_titles'
    build_viet_loc = build / 'SED2+VIET/localisation'
    build_emf_loc = build / 'SED2+EMF/localisation'
    build_mini_lt = build / 'SED2+MiniSWMH/common/landed_titles'
    # build_emf_lt = build / 'SED2+EMF/common/landed_titles'
    # build_emfmini_lt = build / 'SED2+EMF+MiniSWMH/common/landed_titles'
    while build.exists():
        print('Removing old build...')
        shutil.rmtree(str(build), ignore_errors=True)
    build_loc.mkdir(parents=True)
    build_lt.mkdir(parents=True)
    build_viet_loc.mkdir(parents=True)
    build_emf_loc.mkdir(parents=True)
    build_mini_lt.mkdir(parents=True)
    # build_emf_lt.mkdir(parents=True)
    # build_emfmini_lt.mkdir(parents=True)
    swmh_files = set()
    sed2 = {}
    keys_to_blank = set()

    for path in files('localisation/*', basedir=swmhpath):
        swmh_files.add(path.name)

    for inpath in files('*', basedir=templates_loc):
        for row in csv_rows(inpath, comments=True):
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
            for row in csv_rows(inpath):
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
    # determine files overriding SWMH locs
    overridden_files = swmh_files & {path.name for path in
        files('localisation/*', [emfswmhpath], basedir=emfpath)}
    inpath = templates_emf_loc / '0_SED+EMF.csv'
    original_file = None
    sed2rows = [[''] * 15]
    sed2rows[0][:6] = ['#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
    sed2rows[0][-1] = 'x'
    for row in csv_rows(inpath, comments=True):
        if row[0].startswith('#CODE'):
            continue
        if row[0].startswith('#'):
            original_file = row[0][1:]
            continue
        if no_provinces and re.match(r'[cb]_|PROV\d+', row[0]):
            continue
        sed2row = [''] * 15
        sed2row[0] = row[0].strip()
        sed2row[1] = row[1].strip()
        sed2row[-1] = 'x'
        if sed2row[1] or sed2row[0] in keys_to_blank:
            sed2rows.append(sed2row)
        elif original_file in overridden_files:
            sed2row[1] = sed2[sed2row[0]]
            sed2rows.append(sed2row)
    outpath = build_emf_loc / inpath.name
    with outpath.open('w', encoding='cp1252', newline='') as csvfile:
        csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    # VIET
    inpath = templates_viet_loc / 'SED+VIET.csv'
    sed2rows = [[''] * 15]
    sed2rows[0][:6] = ['#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
    sed2rows[0][-1] = 'x'
    for row in csv_rows(inpath):
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

    for inpath in files('localisation/*', basedir=swmhpath):
        if no_provinces and inpath.name in province_loc_files:
            continue
        outpath = build_loc / inpath.name
        sed2rows = [[''] * 15]
        sed2rows[0][:6] = [
            '#CODE', 'ENGLISH', 'FRENCH', 'GERMAN', '', 'SPANISH']
        sed2rows[0][-1] = 'x'
        for row in csv_rows(inpath):
            sed2row = [''] * 15
            sed2row[0] = row[0]
            sed2row[1] = sed2.get(row[0], row[1])
            sed2row[-1] = 'x'
            if sed2row[1] or sed2row[0] in keys_to_blank:
                sed2rows.append(sed2row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    simple_parser = SimpleParser()
    simple_parser.moddirs = [swmhpath]
    cultures = get_cultures(simple_parser, groups=False)
    lt_keys = [
        'title', 'title_female', 'foa', 'title_prefix', 'short_name',
        'name_tier', 'location_ruler_title', 'dynasty_title_names',
        'male_names'] + cultures
    full_parser.fq_keys = cultures

    def update_tree(v, sed2, lt_keys):
        for n2, v2 in v:
            if is_codename(n2.val):
                if n2.val.startswith('b_') and not no_provinces:
                    for p3 in reversed(v2.contents):
                        if p3.key.val in cultures:
                            v2.contents.remove(p3)
                elif not no_provinces or re.match(r'[ekd]_', n2.val):
                    for p3 in reversed(v2.contents):
                        if p3.key.val in lt_keys:
                            v2.contents.remove(p3)
                    if sed2[n2.val]:
                        index = next(
                            (i for i, (n3, _) in enumerate(v2)
                             if is_codename(n3.val)), len(v2))
                        v2.contents[index:index] = sed2[n2.val]
                update_tree(v2, sed2, lt_keys)

    sed2 = {}
    for inpath, tree in full_parser.parse_files('common/landed_titles/*',
                                                basedir=swmhpath):
        template = templates_lt / inpath.with_suffix('.csv').name
        outpath = build_lt / inpath.name
        sed2[template] = collections.defaultdict(list)
        for row in csv_rows(template):
            title, key, val = (s.strip() for s in row[:3])
            if val:
                if key in ['male_names', 'female_names']:
                    val = Obj([String(x.strip('"'))
                               for x in re.findall(r'[^"\s]+|"[^"]*"', val)])
                sed2[template][title].append(Pair.from_kv(key, val))
        update_tree(tree, sed2[template], lt_keys)
        with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
            f.write(tree.str(full_parser))

    # for moddir, builddir in zip([emfswmhpath, minipath, emfminipath],
    #     [build_emf_lt, build_mini_lt, build_emfmini_lt]):
    #     for inpath, tree in full_parser.parse_files('common/landed_titles/*',
    #                                                 basedir=moddir):
    #         if (inpath.name == 'emf_heresy_titles_SWMH.txt' and
    #             moddir == build_emf_lt):
    #             continue
    #             # lame hardcoded exception since we still don't have
    #             # templates for any non-SWMH landed_titles
    #         template = templates_lt / inpath.with_suffix('.csv').name
    #         if template in sed2:
    #             out = builddir / inpath.name
    #             update_tree(tree, sed2[template], lt_keys)
    #             with out.open('w', encoding='cp1252', newline='\r\n') as f:
    #                 f.write(tree.str(full_parser))

    for inpath, tree in full_parser.parse_files('common/landed_titles/*',
                                                basedir=minipath):
        template = templates_lt / inpath.with_suffix('.csv').name
        if template in sed2:
            outpath = build_mini_lt / inpath.name
            update_tree(tree, sed2[template], lt_keys)
            with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
                f.write(tree.str(full_parser))

    with (build_sed2 / 'version.txt').open('w', encoding='cp1252',
                                      newline='\r\n') as f:
        print('{} - {}'.format(version, datetime.date.today()), file=f)

if __name__ == '__main__':
    main()
