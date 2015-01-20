import collections
import csv
import json
import pathlib

def main():
    csv.register_dialect('ckii', delimiter=';', quoting=csv.QUOTE_NONE)
    rootpath = pathlib.Path('/mnt/hgfs/Shared')
    english = collections.defaultdict(str)
    for path in sorted(rootpath.glob('English SWMH/localisation/*.csv')):
        with path.open(encoding='latin-1', newline='') as csvfile:
            for row in csv.reader(csvfile, dialect='ckii'):
                if row[0] not in english:
                    english[row[0]] = row[1]
    jsonobject = {}
    for path in rootpath.glob('SWMH/localisation/*.csv'):
        with path.open(encoding='latin-1', newline='') as csvfile:
            jsonobject[path.name] = [
                (row[0], english[row[0]], row[1])
                for row in csv.reader(csvfile, dialect='ckii')
                if not row[0].startswith('#')]
    with (rootpath / 'SED2/sed2.json').open('w') as jsonfile:
        json.dump(jsonobject, jsonfile, indent=4, sort_keys=True)

if __name__ == '__main__':
    main()
