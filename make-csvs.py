#!/usr/bin/env python3

import collections
import csv
import pathlib
import re
import shutil
import tempfile
import time
import ck2parser
import localpaths

rootpath = localpaths.rootpath
vanilladir = localpaths.vanilladir
swmhpath = rootpath / 'SWMH-BETA/SWMH'

keys_to_override = {
    # A Bookmarks.csv
    'VIKING_ERA', 'VIKING_ERA_INFO', 'EARLY_MED', 'EARLY_MED_INFO'
}

def get_province_id(where):
    tree = ck2parser.parse_file(where / 'map/default.map')
    defs = tree['definitions'].val
    max_provs = tree['max_provinces'].val
    id_name = {}
    for row in ck2parser.csv_rows(where / 'map' / defs):
        try:
            id_name[int(row[0])] = row[4]
        except (IndexError, ValueError):
            continue
    province_id = {}
    province_title = {}
    for path in ck2parser.files('history/provinces/*', where):
        number, name = path.stem.split(' - ')
        if id_name[int(number)] == name:
            tree = ck2parser.parse_file(path)
            try:
                title = tree['title'].val
            except KeyError:
                continue
            the_id = 'PROV' + number
            province_id[title] = the_id
            province_title[the_id] = title
    return province_id, province_title

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

# def process_history(where, build):
#     for glob in ['history/provinces/*', 'history/titles/*']:
#         for inpath, tree in ck2parser.parse_files(glob, where):
#             for n, v in tree:
#                 if isinstance(n, ck2parser.Date):
#                     for p2 in reversed(v.contents):
#                         n2, v2 = p2
#                         if n2.val in ['name', 'adjective']:
#                             mutated = True
#                             v.contents.remove(p2)
#             if mutated:
#                 outpath = make_outpath(build, inpath, where, vanilladir)
#                 with outpath.open('w', encoding='cp1252', newline='\r\n') as f:
#                     f.write(tree.str())

def get_cultures(where):
    cultures = []
    culture_groups = []
    for _, tree in ck2parser.parse_files('common/cultures/*', where):
        for n, v in tree:
            culture_groups.append(n.val)
            cultures.extend(n2.val for n2, v2 in v
                            if n2.val != 'graphical_cultures')
    return cultures, culture_groups

def get_religions(where):
    religions = []
    religion_groups = []
    for _, tree in ck2parser.parse_files('common/religions/*', where):
        for n, v in tree:
            religion_groups.append(n.val)
            religions.extend(n2.val for n2, v2 in v
                             if (isinstance(v2, ck2parser.Obj) and
                                 n2.val not in ['male_names', 'female_names']))
    return religions, religion_groups

def get_more_keys_to_override(where):
    keys = set()
    for _, tree in ck2parser.parse_files('common/bookmarks/*', where):
        for n, v in tree:
            for n2, v2 in v:
                if n2.val in {'name', 'desc'}:
                    keys.add(v2.val)
                elif n2.val == 'character':
                    keys.add('ERA_CHAR_INFO_{}'.format(v2.val))
    for _, tree in ck2parser.parse_files('common/buildings/*', where):
        for n, v in tree:
            for n2, v2 in v:
                keys.add(n2.val)
                for n3, v3 in v2:
                    if n3.val == 'desc':
                        keys.add(v3.val)
    for _, tree in ck2parser.parse_files('common/cultures/*', where):
        for n, v in tree:
            keys.add(n.val)
            for n2, v2 in v:
                if n2.val != 'graphical_cultures':
                    keys.add(n2.val)
    for _, tree in ck2parser.parse_files('common/job_titles/*', where):
        for n, v in tree:
            keys.add(n.val)
            keys.add(n.val + '_foa')
            keys.add(n.val + '_desc')
    for _, tree in ck2parser.parse_files('common/minor_titles/*', where):
        for n, v in tree:
            keys.add(n.val)
            keys.add(n.val + '_foa')
            keys.add(n.val + '_desc')
    for _, tree in ck2parser.parse_files('common/retinue_subunits/*',
                                         where):
        for n, v in tree:
            keys.add(n.val)
    for _, tree in ck2parser.parse_files('common/trade_routes/*', where):
        for n, v in tree:
            keys.add(n.val)
    for glob in ['history/provinces/*', 'history/titles/*']:
        for _, tree in ck2parser.parse_files(glob, where):
            for n, v in tree:
                if isinstance(n, ck2parser.Date):
                    for n2, v2 in v:
                        if n2.val in ['name', 'adjective']:
                            keys.add(v2.val)  # what about when it's not a key
                            # TODO: investigate case sensitivity of localisation,
                            # including overriding/blanking, and matching.
                            # consider FOA/foa in particular
                            # TODO: confirm correct reading of job_titles and minor_titles
                            # TODO: consider adding localisation to the top of sed.csv
                            # (e.g. Satakunta) rather than rebuilding history files.
                            # TODO: check for missing PROV locs with max_provs
                            # TODO: finally, import ziji-build's noble_regex,
                            # lt_match, prov_match

    return keys

def main():
    global keys_to_override
    start_time = time.time()
    english = collections.defaultdict(str)
    for path in ck2parser.files('English SWMH/localisation/*',
                                basedir=rootpath):
        for row in ck2parser.csv_rows(path):
            try:
                if row[0] not in english:
                    english[row[0]] = row[1]
            except IndexError:
                continue
    prov_id, prov_title = get_province_id(swmhpath)
    cultures, cult_groups = get_cultures(swmhpath)
    religions, rel_groups = get_religions(swmhpath)
    dynamics = get_dynamics(swmhpath, cultures, prov_id)
    vanilla = ck2parser.localisation()
    keys_to_override |= get_more_keys_to_override(swmhpath)
    keys_to_override.update(cultures, cult_groups, religions, rel_groups)
    overridden_keys = set()
    swmh_titles = set()
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    for path in ck2parser.files('localisation/*', basedir=templates):
        prev_loc.update({row[0].strip(): row[1].strip()
                         for row in ck2parser.csv_rows(path)
                         if row[0] and not row[0].startswith('#')})
    for path in ck2parser.files('common/landed_titles/*', basedir=templates):
        prev_lt.update({(row[0].strip(), row[1].strip()): row[2].strip()
                        for row in ck2parser.csv_rows(path)
                        if row[0] and not row[0].startswith('#')})

    # fill swmh_titles and prov_title before calling
    def should_override(key):
        title_match = re.match(r'[ekdcb]_((?!_adj($|_)).)*', key)
        if title_match is not None:
            title = title_match.group()
            if re.fullmatch(r'c_((?!_adj($|_)).)*', key) is not None:
                return False
        else:
            prov_match = re.match(r'PROV\d+', key)
            if prov_match is not None:
                try:
                    title = prov_title[prov_match.group()]
                except KeyError:
                    return False
            else:
                return key in keys_to_override
        return not title.startswith('b_') and title in swmh_titles

    def recurse(tree):
        for n, v in tree:
            if ck2parser.is_codename(n.val):
                swmh_titles.add(n.val)
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
            for row in ck2parser.csv_rows(inpath):
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
                                                  basedir=swmhpath):
            outpath = (templates_t /
                       inpath.with_suffix('.csv').relative_to(swmhpath))
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
            with outpath.open('w', newline='', encoding='cp1252') as csvfile:
                csv.writer(csvfile, dialect='ckii').writerows(out_rows)

        override_rows = [
            ['#CODE', 'SED2', 'SWMH', 'OTHER', 'SED1', 'VANILLA']]
        col_width = [0, 8]
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
