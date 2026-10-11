"""Check DONE records and exact line citations; never certify mathematics."""
from pathlib import Path
import collections, datetime, json, sys

REQUIRED='number paper_id title read_mode full_text_read read_ranges total_lines verdict priority plain_summary_zh criticized_target repair same_author publication channels gates gold_candidate silver_candidate old_truth duplicate_key evidence web_sources unresolved_zh started_utc finished_utc'.split()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def check(job):
    if not (job/'DONE.json').is_file(): raise RuntimeError('NO_DONE_NOT_COLLECTABLE')
    assignment=read(job/'assignment.json'); done=read(job/'DONE.json')
    issues=[]; counts=collections.Counter(); reviews=[]
    ids=[a['paper_id'] for a in assignment]
    if len(ids)!=len(set(ids)): issues.append('DUPLICATE_ASSIGNMENT_ID')
    if done.get('count')!=len(ids) or sorted(done.get('paper_ids',[]))!=sorted(ids) or not done.get('finished_utc'):
        issues.append('DONE_IDENTITY_OR_TIMESTAMP')
    for a in assignment:
        stem=f'{a["number"]:03d}'; local=[]
        try:
            x=read(job/'results'/(stem+'.json'))
            lines=(job/'inputs'/(stem+'.tex')).read_text(encoding='utf-8').splitlines()
            for key in REQUIRED:
                if key not in x: local.append('MISSING:'+key)
            if x.get('number')!=a['number'] or x.get('paper_id')!=a['paper_id']: local.append('IDENTITY')
            if x.get('total_lines')!=len(lines): local.append('TOTAL_LINES')
            if x.get('read_mode') not in ('TARGETED_CONTEXT','FULL_TEXT'): local.append('READ_MODE')
            if not isinstance(x.get('full_text_read'),bool): local.append('FULL_TEXT_TYPE')
            if x.get('full_text_read')!=(x.get('read_mode')=='FULL_TEXT'): local.append('READ_MODE_CONFLICT')
            if x.get('priority') not in ('FOLLOW_UP','HISTORICAL_ONLY','UNCERTAIN','EXCLUDE'): local.append('PRIORITY')
            if x.get('verdict') not in ('USEFUL_LEAD','FALSE_TRIGGER','UNRESOLVED'): local.append('VERDICT')
            for group,prefix,allowed in [('channels','T',('YES','POSSIBLE','NO','UNKNOWN')),('gates','G',('YES','NO','UNKNOWN'))]:
                for i in range(1,6):
                    entry=x.get(group,{}).get(f'{prefix}{i}',{})
                    if not isinstance(entry,dict) or entry.get('status') not in allowed or not entry.get('reason_zh'): local.append(f'INVALID_{prefix}{i}')
            evidence=x.get('evidence',[])
            if not 2<=len(evidence)<=5: local.append('EVIDENCE_COUNT')
            for i,e in enumerate(evidence,1):
                lo,hi=e.get('start_line'),e.get('end_line')
                if not isinstance(lo,int) or not isinstance(hi,int) or not 1<=lo<=hi<=len(lines):
                    local.append(f'EVIDENCE_{i}_RANGE'); continue
                quote=e.get('quote','').replace('\r\n','\n').replace('\r','\n')
                if not quote or quote not in '\n'.join(lines[lo-1:hi]): local.append(f'EVIDENCE_{i}_QUOTE')
                if not e.get('kind'): local.append(f'EVIDENCE_{i}_KIND')
            if x.get('gold_candidate') not in ('NONE','UNKNOWN','POSSIBLE_L2'): local.append('GOLD_LABEL')
            if x.get('gold_candidate')=='POSSIBLE_L2': reviews.append({'paper_id':a['paper_id'],'required':'Independent counterexample and all original assumptions'})
            if x.get('silver_candidate')=='DOCUMENTED_SILENT_CHANGE': reviews.append({'paper_id':a['paper_id'],'required':'Fixed old/new texts and checked revision explanations'})
            counts[x.get('priority','MISSING')]+=1
        except Exception as exc: local.append(type(exc).__name__+':'+str(exc))
        issues.extend(stem+':'+item for item in local)
    for name in ('summary.json','report.txt'):
        if not (job/name).is_file(): issues.append('MISSING_DELIVERABLE:'+name)
    result={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job':job.name,'count':len(ids),'status':'COLLECTED_WITH_ISSUES' if issues else 'COLLECTED','priority':dict(counts),'issues':issues,'coordinator_review_required':reviews,'scope':'Identity, required fields and exact local line quotes only; not independent mathematical certification; original answers unchanged'}
    output=job/'coordinator'; output.mkdir(exist_ok=True)
    (output/'record_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 1 if issues else 0
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python -X utf8 validate_job.py JOB_DIRECTORY')
    raise SystemExit(check(Path(sys.argv[1]).resolve()))
