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
    for inpath in rootpath.glob('SWMH/localisation/*.csv'):
        templatepath = rootpath / 'SED2/templates' / inpath.name
        outpath = build / 'localisation' / inpath.name
        with templatepath.open(encoding='cp1252', newline='') as csvfile:
            sed2 = {row[0]: row[1] for row in csv.reader(csvfile, dialect='ckii')}
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            swmhrows = [row for row in csv.reader(csvfile, dialect='ckii')]
        sed2rows = []
        for row in swmhrows:
            if row[0].startswith('#') or sed2[row[0]] == '':
                loc = row[1]
            else:
                loc = sed2[row[0]]
            row[1] = row[2] = row[3] = row[5] = loc
            sed2rows.append(row)
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(sed2rows)

if __name__ == '__main__':
    main()
