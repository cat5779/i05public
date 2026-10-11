"""Verify all bundled paper bytes against the original queue; no screening."""
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def verify():
    queue=json.loads((ROOT/'QUEUE.json').read_text(encoding='utf-8'))['papers']
    manifest=json.loads((ROOT/'PAPERS_MANIFEST.json').read_text(encoding='utf-8'))
    expected={(r['batch'],r['number']):r for r in queue}
    seen=set(); problems=[]; total=0
    for item in manifest['papers']:
        key=(item['batch'],item['number'])
        if key in seen: problems.append('DUPLICATE:'+str(key))
        seen.add(key)
        try:
            path=(ROOT/item['path']).resolve()
            if not path.is_relative_to(ROOT.resolve()): raise ValueError('PATH_OUTSIDE_PACKAGE')
            data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
            row=expected[key]
            source=json.loads(path.with_suffix('.source.json').read_text(encoding='utf-8'))
            if digest!=item['sha256'] or digest!=row['source_sha256'] or digest!=source['text_sha256']: raise ValueError('HASH_MISMATCH')
            if item['paper_id']!=row['paper_id'] or source['paper_id']!=row['paper_id']: raise ValueError('IDENTITY_MISMATCH')
            if len(data)!=item['bytes']: raise ValueError('BYTE_COUNT')
            if len(data.decode('utf-8').splitlines())!=item['lines']: raise ValueError('LINE_COUNT')
            total+=len(data)
        except Exception as exc: problems.append(str(key)+':'+str(exc))
    if seen!=set(expected): problems.append('MANIFEST_QUEUE_SET_MISMATCH')
    if manifest['count']!=len(queue) or len(queue)!=540: problems.append('COUNT_MISMATCH')
    if total!=manifest['total_bytes']: problems.append('TOTAL_BYTES')
    print(json.dumps({'status':'PASS' if not problems else 'FAIL','count':len(seen),'total_bytes':total,'problems':problems,'scope':'Exact input bytes and identity only, not mathematical correctness'},ensure_ascii=False))
    return 1 if problems else 0
if __name__=='__main__': raise SystemExit(verify())
