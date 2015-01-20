import collections
import csv
import json
import pathlib

def main():
    csv.register_dialect('ckii', delimiter=';')
    rootpath = pathlib.Path('/mnt/hgfs/Shared')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(encoding='latin-1', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if row[0] not in english:
                    english[row[0]] = row[1]
    for inpath in rootpath.glob('SWMH/localisation/*.csv'):
        with inpath.open(encoding='latin-1', newline='') as csvfile:
            rows = [[row[0], english[row[0]], row[1]]
                    for row in csv.reader(csvfile, dialect='ckii')]
        outpath = rootpath / 'SED2/localisation' / inpath.name
        with outpath.open('w', encoding='latin-1', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(rows)

if __name__ == '__main__':
    main()
