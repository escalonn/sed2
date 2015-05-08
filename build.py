import csv
import pathlib
import re
import shutil
import ck2parser

rootpath = pathlib.Path('..')
swmhpath = rootpath / 'SWMH-BETA/SWMH_EE'
sed2path = rootpath / 'SED2'

def main():
    csv.register_dialect('ckii', delimiter=';')
    templates_loc = sed2path / 'templates/localisation'
    templates_lt = sed2path / 'templates/common/landed_titles'
    build = sed2path / 'build'
    build_loc = build / 'localisation'
    build_lt = build / 'common/landed_titles'
    if build.exists():
        shutil.rmtree(str(build))
    build_loc.mkdir(parents=True)
    build_lt.mkdir(parents=True)

    for inpath in sorted(swmhpath.glob('localisation/*.csv')):
        template = templates_loc / inpath.name
        outpath = build_loc / inpath.name
        with template.open(encoding='cp1252', newline='') as csvfile:
            sed2 = {r[0]: r[1] for r in csv.reader(csvfile, dialect='ckii')}
        sed2rows = []
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if not row[0].startswith('#'):
                    row[1] = sed2[row[0]]
                    row[2:] = [''] * (len(row) - 2)
                    sed2rows.append(row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

    for inpath in sorted(swmhpath.glob('common/landed_titles/*.txt')):
        template = templates_lt / inpath.name
        outpath = build_lt / inpath.name
        with template.open(encoding='cp1252', newline='') as csvfile:
            # TODO 
            # sed2 = {r[0]: r[1] for r in csv.reader(csvfile, dialect='ckii')}
            pass
        with inpath.open(encoding='cp1252') as f:
            item = ck2parser.parse(f.read())
        # TODO fix up item
        pass
        with outpath.open('w', encoding='cp1252') as f:
            f.write(ck2parser.to_string(item))

if __name__ == '__main__':
    main()


# if (not row[0].startswith('#') and
#     not re.fullmatch(r'[ekdcb]_.*_adj_.*', row[0])):
