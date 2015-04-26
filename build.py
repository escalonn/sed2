import csv
import pathlib
import re
import shutil

rootpath = pathlib.Path('..')
swmhpath = rootpath / 'SWMH-BETA/SWMH_EE'

def main():
    csv.register_dialect('ckii', delimiter=';')
    build = rootpath / 'SED2/build'
    if build.exists():
        shutil.rmtree(str(build))
    (build / 'localisation').mkdir(parents=True)
    for inpath in sorted(swmhpath.glob('localisation/*.csv')):
        templatepath = rootpath / 'SED2/templates' / inpath.name
        outpath = build / 'localisation' / inpath.name
        with templatepath.open(encoding='cp1252', newline='') as csvfile:
            sed2 = {r[0]: r[1] for r in csv.reader(csvfile, dialect='ckii')}
        sed2rows = []
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if (not row[0].startswith('#') and
                    not re.fullmatch(r'[ekdcb]_.*_adj_.*', row[0])):
                    row[1] = sed2[row[0]]
                    row[2:] = [''] * (len(row) - 2)
                    sed2rows.append(row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

if __name__ == '__main__':
    main()
