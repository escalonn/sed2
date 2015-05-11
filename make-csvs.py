# title/title_female, a way to override what the proper ruler title is for
# weird titles.  E.g., might contain "Pimp" in a CK2 mod about NYC feudalism
# and their equivalent of mercenary companies.
# title_prefix, you get this one.  used to be commonly like "Tribe of" for
# general-purpose tribes.  breaking out the pieces of the full title displayed
# in game like this allows the script to display different components of the
# title in different ways, depending upon usage.
# foa, form of address, "Your Grace" (not even sure what uses this)
# also a foa_female IIRC
# short_name means the game won't attempt to prefix the title name with its
# rank-based default title_prefix (e.g., displaying "Kingdom of <TITLE>" vs.
# "<TITLE>") when displaying the title name.
# location_ruler_title is very weird and really only applies to the Pope or
# other landless titles.  it means that places in which the game shows the
# title holder's name will get an "in <their current landed capital's name>"
# appended to their ruler title ("title" keyword equiv).  so "Pope in Arles,"
# etc.
# dynasty_title_names is only used to disabled dynasty-based title naming when
# it would otherwise be called for due to ruler culture.
# e.g., k_rum uses this so that it's never called Seljuk or what have you
# despite the holders always having a culture that is dynasty_title_names = yes
# --> can't actually force dynasty_title_names = yes from a title definition
# (only no), if you wanted the inverse behavior

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
    prev_loc = collections.defaultdict(str)
    prev_lt = collections.defaultdict(str)

    templates = rootpath / 'SED2/templates'
    templates_loc = templates / 'localisation'
    for path in sorted(templates_loc.glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_loc.update({row[0]: row[1]
                             for row in csv.reader(csvfile, dialect='ckii')})
    templates_lt = templates / 'common/landed_titles'
    for path in sorted(templates_lt.glob('*.csv')):
        with path.open(newline='', encoding='cp1252') as csvfile:
            prev_lt.update({(row[0], row[1]): row[2]
                            for row in csv.reader(csvfile, dialect='ckii')})
    if templates.exists():
        shutil.rmtree(str(templates))
    templates_loc.mkdir(parents=True)
    templates_lt.mkdir(parents=True)
    for inpath in sorted(swmhpath.glob('localisation/*.csv')):
        outpath = templates_loc / inpath.name
        out_rows = []
        with inpath.open(newline='', encoding='cp1252') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                out_row = [row[0], prev_loc[row[0]], row[1],
                           ','.join(dynamics[row[0]]), english[row[0]]]
                out_rows.append(out_row)
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(out_rows)

    lt_keys = ['title', 'title_female', 'foa', 'title_prefix', 'short_name',
        'name_tier', 'location_ruler_title', 'dynasty_title_names',
        'male_names'] + cultures

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

    rows = []
    for path in sorted(swmhpath.glob('common/landed_titles/*.txt')):
        with path.open(encoding='cp1252') as f:
            rows.extend(recurse(ck2parser.parse(f.read())))

    for inpath in sorted(swmhpath.glob('common/landed_titles/*.txt')):
        outpath = templates_lt / inpath.with_suffix('.csv').name
        out_rows = []
        with inpath.open(encoding='cp1252') as f:
            item = ck2parser.parse(f.read())
        for title, pairs in recurse(item):
            for (t, k), v in prev_lt.items():
                if t == title and not any(k == k2 for k2, _ in pairs):
                    pairs.append((k, ''))
            for key, val in sorted(pairs, key=lambda x: lt_keys.index(x[0])):
                out_row = [title, key, prev_lt[title, key], val]
                out_rows.append(out_row)
        with outpath.open('w', newline='', encoding='cp1252') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(out_rows)

if __name__ == '__main__':
    main()
