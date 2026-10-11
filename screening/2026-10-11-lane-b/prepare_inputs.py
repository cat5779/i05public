"""Prepare a claimed batch from bundled papers, or a matching JSONL.gz cache."""
import argparse, bisect, datetime, gzip, hashlib, json, os, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def write_one(out, row, source):
    text=source['text']
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    if digest!=row['source_sha256'] or digest!=source.get('text_sha256'):
        raise RuntimeError('INPUT_VERSION_MISMATCH:'+row['paper_id'])
    stem=f'{row["number"]:03d}'; target=out/'inputs'
    (target/(stem+'.tex')).write_text(text,encoding='utf-8',newline='')
    lines=text.splitlines()
    save(target/(stem+'.source.json'),{k:v for k,v in source.items() if k!='text'}|{'actual_sha256':digest,'lines':len(lines),'chars':len(text)})
    starts=[0]; position=0
    for ln in text.splitlines(keepends=True): position+=len(ln); starts.append(position)
    spans=[(0,min(160,len(lines)))]
    for hit in row['hits']:
        if not 0<=hit['start']<=hit['end']<=len(text): raise RuntimeError('INVALID_HIT_OFFSETS:'+row['paper_id'])
        a=bisect.bisect_right(starts,hit['start'])-1
        b=bisect.bisect_right(starts,hit['end'])
        spans.append((max(0,a-45),min(len(lines),b+65)))
    merged=[]
    for a,b in sorted(spans):
        if merged and a<=merged[-1][1]: merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else: merged.append((a,b))
    dossier='\n\n'.join(f'LINES {a+1}-{b}\n'+'\n'.join(f'{i+1}: {lines[i]}' for i in range(a,b)) for a,b in merged)
    (target/(stem+'.dossier.txt')).write_text(dossier,encoding='utf-8')
    print('READY',stem,row['paper_id'],flush=True)

def prepare(args):
    storage=args.storage_root.resolve()
    bundled=args.body_root is None
    body=(HERE/'papers') if bundled else args.body_root.resolve()
    out=args.out.resolve()
    if not storage.is_dir(): raise RuntimeError('STORAGE_ROOT_MISSING')
    if not out.is_relative_to(storage) or (not bundled and not body.is_relative_to(storage)):
        raise RuntimeError('OUTPUT_AND_EXTERNAL_CACHE_MUST_BE_WITHIN_STORAGE_ROOT')
    claim=HERE/'claims'/(args.batch+'.json')
    if not claim.exists(): raise RuntimeError('CLAIM_REQUIRED_BEFORE_PREPARATION')
    claimed=json.loads(claim.read_text(encoding='utf-8-sig'))
    if claimed.get('batch')!=args.batch or claimed.get('status') not in ('CLAIMED','PREPARING','READY','RUNNING'):
        raise RuntimeError('CLAIM_NOT_ACTIVE')
    if out.exists(): raise RuntimeError('OUTPUT_EXISTS_PRESERVE_AND_INSPECT_NO_BLIND_RERUN')
    rows=[r for r in json.loads((HERE/'QUEUE.json').read_text(encoding='utf-8'))['papers'] if r['batch']==args.batch]
    if len(rows)!=30: raise RuntimeError('UNKNOWN_OR_INCOMPLETE_BATCH')
    try: import psutil
    except ImportError: raise RuntimeError('PSUTIL_REQUIRED_FOR_MEMORY_PROTECTION') from None
    lock=storage/'.strict_screen_prepare.lock'
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: print('PREPARE_BUSY_RETRY_AFTER_AT_LEAST_60_SECONDS'); return 2
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream: stream.write(json.dumps({'pid':os.getpid(),'utc':utc(),'batch':args.batch}))
        if shutil.disk_usage(storage).free<20*10**9 or psutil.virtual_memory().available<1024**3:
            print('RESOURCE_WAIT_NO_ALLOCATION_RETRY_AFTER_AT_LEAST_60_SECONDS'); return 2
        total=0
        for directory,_,files in os.walk(storage):
            for name in files:
                try: total+=(Path(directory)/name).stat().st_size
                except FileNotFoundError: pass
        if bundled and not body.resolve().is_relative_to(storage):
            total+=sum(p.stat().st_size for p in body.rglob('*') if p.is_file())
        if total>=130*10**9:
            print('SOFT_STORAGE_STOP_NO_ALLOCATION'); return 2
        shards={r['source_shard'] for r in rows}
        if bundled:
            for row in rows:
                stem=f'{row["number"]:03d}'
                for suffix in ('.tex','.source.json'):
                    if not (body/row['batch']/(stem+suffix)).is_file(): raise RuntimeError('BUNDLED_SOURCE_MISSING:'+row['paper_id'])
        else:
            for shard in shards:
                if not (body/(Path(shard).stem+'.body.jsonl.gz')).is_file():
                    raise RuntimeError('SOURCE_CACHE_MISSING:'+shard)
        out.mkdir(parents=True)
        save(out/'assignment.json',rows)
        (out/'inputs').mkdir(); (out/'results').mkdir()
        save(out/'PREPARING.json',{'batch':args.batch,'utc':utc()})
        if bundled:
            for row in rows:
                folder=body/row['batch']; stem=f'{row["number"]:03d}'
                source=json.loads((folder/(stem+'.source.json')).read_text(encoding='utf-8'))
                source['text']=(folder/(stem+'.tex')).read_bytes().decode('utf-8')
                if source['paper_id']!=row['paper_id']: raise RuntimeError('BUNDLED_IDENTITY_MISMATCH')
                write_one(out,row,source)
            shards=[]
        for shard in sorted(shards):
            wanted={r['paper_id']:r for r in rows if r['source_shard']==shard}
            with gzip.open(body/(Path(shard).stem+'.body.jsonl.gz'),'rt',encoding='utf-8') as stream:
                for line in stream:
                    source=json.loads(line)
                    if source['paper_id'] not in wanted: continue
                    row=wanted.pop(source['paper_id'])
                    write_one(out,row,source)
                    if not wanted: break
            if wanted: raise RuntimeError('SOURCE_PAPERS_MISSING:'+','.join(wanted))
        save(out/'INPUTS_COMPLETE.json',{'batch':args.batch,'count':30,'paper_ids':[r['paper_id'] for r in rows],'utc':utc()})
        print('INPUTS_COMPLETE',args.batch)
        return 0
    except Exception as exc:
        if out.exists(): save(out/'BLOCKED.json',{'utc':utc(),'stage':'PREPARATION','reason':str(exc),'completed':False})
        raise
    finally:
        lock.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',required=True)
    parser.add_argument('--body-root',type=Path,help='Optional: matching external cache; omit to use bundled papers')
    parser.add_argument('--storage-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    raise SystemExit(prepare(parser.parse_args()))
