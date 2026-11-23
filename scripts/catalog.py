"""Export or upsert paper/figure metadata without editing SQLite by hand."""
import argparse
import json
from pathlib import Path
from common import read, write, validate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['export','upsert'])
    parser.add_argument('kind',choices=['papers','figures'])
    parser.add_argument('file',type=Path)
    args=parser.parse_args()
    name=args.kind+'.json'
    if args.action=='export':
        args.file.write_text(json.dumps(read(name),ensure_ascii=False,indent=2)+'\n','utf-8')
        return
    incoming=json.loads(args.file.read_text('utf-8'))
    if not isinstance(incoming,list):parser.error('input must be a JSON array')
    records={v['id']:v for v in read(name)}
    for value in incoming:
        if not isinstance(value,dict) or not value.get('id'):parser.error('each record requires an id')
        records[value['id']]={**records.get(value['id'],{}),**value}
    updated=list(records.values())
    validate(updated if args.kind=='papers' else read('papers.json'),
             updated if args.kind=='figures' else read('figures.json'),read('scope.json'))
    write(name,updated)
    print(f'Upserted {len(incoming)} {args.kind} records into SQLite.')

if __name__=='__main__':main()
