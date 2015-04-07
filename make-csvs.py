import collections
import csv
import pathlib

def main():
    csv.register_dialect('ckii', delimiter=';')
    rootpath = pathlib.Path('..')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(encoding='cp1252', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if row[0] not in english:
                    english[row[0]] = row[1]
    for inpath in rootpath.glob('SWMH/localisation/*.csv'):
        outpath = rootpath / 'SED2/templates' / inpath.name
        prev_map = collections.defaultdict(str)
        if outpath.exists():
            with outpath.open(encoding='cp1252', newline='') as csvfile:
                prev_map.update(tuple(row[:2])
                                for row in csv.reader(csvfile, dialect='ckii'))
        with inpath.open(encoding='cp1252', newline='') as csvfile:
            rows = [[row[0], prev_map[row[0]], row[1], english[row[0]]]
                    for row in csv.reader(csvfile, dialect='ckii')]
        with outpath.open('w', encoding='cp1252', newline='') as csvfile:
            csv.writer(csvfile, dialect='ckii').writerows(rows)

if __name__ == '__main__':
    main()
