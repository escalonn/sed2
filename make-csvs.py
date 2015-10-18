#!/usr/bin/env python3

import collections
import csv
import pathlib
import re
import shutil
import tempfile
import time
import ck2parser

rootpath = ck2parser.rootpath
vanilladir = ck2parser.vanilladir
swmhpath = rootpath / 'SWMH-BETA/SWMH'

def get_province_id(where):
    province_id = {}
    province_title = {}
    for number, title, tree in ck2parser.provinces(where):
        the_id = 'PROV{}'.format(number)
        province_id[title] = the_id
        province_title[the_id] = title
    return province_id, province_title

def get_dynamics(where, cultures, prov_id):
    def recurse(tree):
        for n, v in tree:
            if ck2parser.is_codename(n.val):
                for n2, v2 in v:
                    if n2.val in cultures:
                        if v2.val not in dynamics[n.val]:
                            dynamics[n.val].append(v2.val)
                        if (n.val in prov_id and
                            v2.val not in dynamics[prov_id[n.val]]):
                            dynamics[prov_id[n.val]].append(v2.val)
                recurse(v)

    dynamics = collections.defaultdict(list,
                                       [(v, [k]) for k, v in prov_id.items()])
    for _, tree in ck2parser.parse_files('common/landed_titles/*', where):
        recurse(tree)
    return dynamics

def get_gov_prefixes(where):
    prefixes = []
    for _, tree in ck2parser.parse_files('common/governments/*', where):
        for _, v in tree:
            for n2, v2 in v:
                try:
                    prefix = v2['title_prefix'].val
                except KeyError:
                    continue
                if prefix not in prefixes:
                    prefixes.append(prefix)
    return prefixes

def get_more_keys_to_override(where, localisation, max_provs):
    override = {
        # A Bookmarks.csv
        'VIKING_ERA', 'VIKING_ERA_INFO', 'EARLY_MED', 'EARLY_MED_INFO'
    }
    missing_loc = []
    for _, tree in ck2parser.parse_files('common/bookmarks/*', where):
        for n, v in tree:
            for n2, v2 in v:
                if n2.val in ('name', 'desc'):
                    override.add(v2.val)
                elif n2.val == 'character':
                    override.add('ERA_CHAR_INFO_{}'.format(v2.val))
    for _, tree in ck2parser.parse_files('common/buildings/*', where):
        for n, v in tree:
            for n2, v2 in v:
                override.add(n2.val)
                for n3, v3 in v2:
                    if n3.val == 'desc':
                        override.add(v3.val)
    ul_titles = []
    for _, tree in ck2parser.parse_files('common/job_titles/*', where):
        for n, v in tree:
            ul_titles.append(n.val)
            override.add('desc_' + n.val)
    for _, tree in ck2parser.parse_files('common/minor_titles/*', where):
        for n, v in tree:
            ul_titles.append(n.val)
            override.add(n.val + '_FOA')
            override.add(n.val + '_desc')
    for _, tree in ck2parser.parse_files('common/retinue_subunits/*', where):
        for n, v in tree:
            override.add(n.val)
    for _, tree in ck2parser.parse_files('common/trade_routes/*', where):
        for n, v in tree:
            override.add(n.val)
    for glob in ['history/provinces/*', 'history/titles/*']:
        for _, tree in ck2parser.parse_files(glob, where):
            for n, v in tree:
                if isinstance(n, ck2parser.Date):
                    for n2, v2 in v:
                        if n2.val in ('name', 'adjective'):
                            if v2.val in localisation:
                                override.add(v2.val)
                            else:
                                missing_loc.append(v2.val)
    for i in range(1, max_provs):
        key = 'PROV{}'.format(i)
        if key in localisation:
            override.add(key)
        else:
            missing_loc.append(key)
    return override, missing_loc, ul_titles

def main():
    global keys_to_override
    start_time = time.time()
    english = collections.defaultdict(str)
    for path in ck2parser.files('English SWMH/localisation/*',
                                basedir=rootpath):
        for row in ck2parser.csv_rows(path):
            if row[0] not in english:
                english[row[0]] = row[1]
    prov_id, prov_title = get_province_id(swmhpath)
    max_provs = ck2parser.max_provinces(swmhpath)
    cultures, cult_groups = ck2parser.cultures(swmhpath)
    religions, rel_groups = ck2parser.religions(swmhpath)
    dynamics = get_dynamics(swmhpath, cultures, prov_id)
    vanilla = ck2parser.localisation()
    localisation = ck2parser.localisation(swmhpath)
    keys_to_override, keys_to_add, ul_titles = get_more_keys_to_override(
        swmhpath, localisation, max_provs)
    keys_to_override.update(cultures, cult_groups, religions, rel_groups)
    overridden_keys = set()
    titles = set()
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in ck2parser.files('localisation/*', basedir=templates):
        prev_loc.update({row[0].strip(): row[1].strip()
                         for row in ck2parser.csv_rows(path)})
    for path in ck2parser.files('common/landed_titles/*', basedir=templates):
        prev_lt.update({(row[0].strip(), row[1].strip()): row[2].strip()
                        for row in ck2parser.csv_rows(path)})

    gov_prefixes = get_gov_prefixes(swmhpath)
    type_re = '|'.join(['family_palace_', 'vice_royalty_'] + gov_prefixes)
    title_re = '|'.join(ul_titles)
    culture_re = '|'.join(cultures + cult_groups)
    religion_re = '|'.join(religions + rel_groups)
    noble_regex = ('(({})?((baron|count|duke|king|emperor)|'
                   '((barony|county|duchy|kingdom|empire)(_of)?))_?)?({})?'
                   '(_female)?(_({}|{}))?').format(type_re, title_re,
                                                   culture_re, religion_re)

    # fill titles before calling
    def should_override(key):
        title_match = re.match(r'[ekdcb]_((?!_adj($|_)).)*', key)
        if title_match is not None:
            title = title_match.group()
            return (title in titles and not title.startswith('b_') and
                    re.fullmatch(r'c_((?!_adj($|_)).)*', key) is None)
        if key in keys_to_override:
            return True
        noble_match = re.fullmatch(noble_regex, key)
        return noble_match is not None

    def recurse(tree):
        for n, v in tree:
            if ck2parser.is_codename(n.val):
                titles.add(n.val)
                items = []
                for n2, v2 in v:
                    if n2.val in lt_keys:
                        if isinstance(v2, ck2parser.Obj):
                            value = ' '.join(s.val for s in v2)
                        else:
                            value = v2.val
                        items.append((n2.val, value))
                yield n.val, items
                yield from recurse(v)

    with tempfile.TemporaryDirectory() as td:
        templates_t = pathlib.Path(td)
        (templates_t / 'localisation').mkdir(parents=True)
        (templates_t / 'common/landed_titles').mkdir(parents=True)
        swmh_files = set()
        for inpath in ck2parser.files('localisation/*', basedir=swmhpath):
            swmh_files.add(inpath.name)
            outpath = templates_t / inpath.relative_to(swmhpath)
            out_rows = [
                ['#CODE', 'SED2', 'SWMH', 'OTHER', 'SED1', 'VANILLA']]
            col_width = [0, 8]
            for row in ck2parser.csv_rows(inpath, comments=True):
                try:
                    if row[0]:
                        if not row[0].startswith('#'):
                            overridden_keys.add(row[0])
                        if not row[0].startswith('b_'):
                            if row[0].startswith('#'):
                                row = [','.join(row)] + [''] * (len(row) - 1)
                            else:
                                col_width[0] = max(len(row[0]), col_width[0])
                            out_row = [row[0],
                                       prev_loc[row[0]],
                                       row[1],
                                       ','.join(dynamics[row[0]]),
                                       english[row[0]],
                                       vanilla.get(row[0], '')]
                            out_rows.append(out_row)
                except IndexError:
                    continue
            for i, out_row in enumerate(out_rows):
                if not out_row[0].startswith('#') or i == 0:
                    for col, width in enumerate(col_width):
                        out_row[col] = out_row[col].ljust(width)
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)

        lt_keys_not_cultures = [
            'title', 'title_female', 'foa', 'title_prefix', 'short_name',
            'name_tier', 'location_ruler_title', 'dynasty_title_names',
            'male_names']
        lt_keys = lt_keys_not_cultures + cultures

        for inpath, tree in ck2parser.parse_files('common/landed_titles/*',
                                                  swmhpath):
            out_rows = [['#TITLE', 'KEY', 'SED2', 'SWMH']]
            col_width = [0, 0, 8]
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
            outpath = (templates_t / inpath.with_suffix('.csv').
                       relative_to(inpath.parents[2]))
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)

        override_rows = [
            ['#CODE', 'SED2', 'SWMH', 'OTHER', 'SED1', 'VANILLA']]
        col_width = [0, 8]
        for key in keys_to_add:
            out_row = [key, prev_loc[key], '', '', '', key]
            override_rows.append(out_row)
            col_width[0] = max(len(key), col_width[0])
        for path in ck2parser.files('localisation/*'):
            if path.name not in swmh_files:
                override_rows.append(['#' + path.name, '', ''])
                for row in ck2parser.csv_rows(path):
                    try:
                        key, val = row[:2]
                    except ValueError:
                        continue
                    if should_override(key) and key not in overridden_keys:
                        out_row = [key,
                                   prev_loc[key],
                                   '',
                                   ','.join(dynamics[key]),
                                   english[key],
                                   val]
                        override_rows.append(out_row)
                        overridden_keys.add(key)
                        col_width[0] = max(len(key), col_width[0])
        for i, out_row in enumerate(override_rows):
            if not out_row[0].startswith('#') or i == 0:
                for col, width in enumerate(col_width):
                    out_row[col] = out_row[col].ljust(width)
        outpath = templates_t / 'localisation' / 'A SED.csv'
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(override_rows)

        while templates.exists():
            print('Removing old templates...')
            shutil.rmtree(str(templates), ignore_errors=True)
        shutil.copytree(str(templates_t), str(templates))
    end_time = time.time()
    print('Time: {} s'.format(end_time - start_time))

if __name__ == '__main__':
    main()
