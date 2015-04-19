import csv
import pathlib
import shutil

def main():
    csv.register_dialect('ckii', delimiter=';')
    rootpath = pathlib.Path('..')
    build = rootpath / 'SED2/build'
    if build.exists():
        shutil.rmtree(str(build))
    build.mkdir()
    (build / 'localisation').mkdir()
    for inpath in rootpath.glob('SWMH/SWMH/localisation/*.csv'):
        templatepath = rootpath / 'SED2/templates' / inpath.name
        outpath = build / 'localisation' / inpath.name
        with templatepath.open(encoding='cp1252', newline='') as csvfile:
            sed2 = {row[0]: row[1] for row in csv.reader(csvfile, dialect='ckii')}
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            swmhrows = [row for row in csv.reader(csvfile, dialect='ckii')]
        sed2rows = []
        for row in swmhrows:
            if not row[0].startswith('#'):
                row[1] = sed2[row[0]]
                row[2:] = [''] * (len(row) - 2)
            sed2rows.append(row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

if __name__ == '__main__':
    main()
