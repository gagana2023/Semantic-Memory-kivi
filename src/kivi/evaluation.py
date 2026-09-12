"""Durable, local evaluation records. It never feeds evaluation prompts into transcripts."""
import json
import asyncio
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .storage import connect, migrate
from .services import OllamaExtractor, answer_recall, process_one

ROOT = Path(__file__).resolve().parents[2]

def ident(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def _fixture(case_set):
    path = ROOT / "fixtures" / f"{case_set}-evaluation.json"
    if not path.is_file():
        raise ValueError("EVALUATION_CASE_SET_NOT_FOUND")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("case_set") != case_set or not isinstance(data.get("criteria"), list) or not isinstance(data.get("position_claims"), list):
        raise ValueError("EVALUATION_CASE_SET_INVALID")
    return data

def create_run(settings, case_set):
    fixture = _fixture(case_set)
    migrate(settings)
    run_id = ident("eval")
    db = connect(settings)
    try:
        manifest = {"case_set": case_set, "criteria": fixture["criteria"], "position_claims": fixture["position_claims"], "database_path": settings.database_path, "created_at": _now()}
        db.execute("INSERT INTO evaluation_runs (id,case_set,state,manifest_json,created_at) VALUES (?,?, 'queued', ?, ?)", (run_id, case_set, json.dumps(manifest, sort_keys=True), _now()))
        db.commit()
    finally:
        db.close()
    return run_id

def run(settings, run_id):
    """Record one real outcome per fixed case; unavailable contract execution is a failure, never a pass."""
    db = connect(settings)
    try:
        row = db.execute("SELECT * FROM evaluation_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError("EVALUATION_NOT_FOUND")
        if row["state"] == "completed":
            return json.loads(row["report_json"])
        manifest = json.loads(row["manifest_json"])
        db.execute("UPDATE evaluation_runs SET state='running' WHERE id=?", (run_id,)); db.commit()
        before_transcripts = db.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        started = time.perf_counter()
        # The current public contracts persist every Hey Kivi request as a transcript.  Calling
        # them here would violate AC-FR-32's leakage guard, so the missing isolated public
        # evaluation adapter is explicitly recorded for every case.
        cases = [(f"claim:{claim}", "POSITION:" + claim, claim) for claim in manifest["position_claims"]]
        cases += [(f"criterion:{criterion}", criterion, None) for criterion in manifest["criteria"]]
        cases += [("negative:absent_history_answer_must_fail", "AC-FR-32", None)]
        for case_id, criterion, claim in cases:
            evidence = {"leakage_guard": "not_called", "required_adapter": "isolated public-contract evaluation adapter", "service_api_cost_usd": 0.0}
            db.execute("INSERT INTO evaluation_results VALUES (?,?,?,?,?,?,?,?,?,?)", (ident("evr"), run_id, case_id, criterion, claim, "failed", "EVALUATION_PUBLIC_CONTRACT_PATH_UNAVAILABLE", json.dumps(evidence, sort_keys=True), 0.0, _now()))
        after_transcripts = db.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        results = [dict(x) for x in db.execute("SELECT case_id,criterion,claim,outcome,reason,evidence_json,latency_ms FROM evaluation_results WHERE run_id=? ORDER BY case_id", (run_id,))]
        metrics = {"latency_ms": round((time.perf_counter()-started)*1000, 3), "storage_bytes": Path(settings.database_path).stat().st_size if Path(settings.database_path).exists() else 0, "model_cost_usd": 0.0, "service_api_cost_usd": 0.0, "transcripts_before": before_transcripts, "transcripts_after": after_transcripts}
        completeness = {"all_position_claims_have_evidence": len({x["claim"] for x in results if x["claim"]}) == len(manifest["position_claims"]), "all_criteria_have_evidence": set(manifest["criteria"]).issubset({x["criterion"] for x in results}), "evaluation_questions_absent_from_transcripts": before_transcripts == after_transcripts, "no_absent_history_fabrication": False}
        report = {"run_id": run_id, "case_set": manifest["case_set"], "state": "completed", "passed": False, "completeness": completeness, "metrics": metrics, "results": results}
        markdown = "# Kivi evaluation report\n\n" + "\n".join([f"- **{k}**: `{v}`" for k,v in completeness.items()]) + "\n\n## Results\n\n" + "\n".join([f"- `{x['case_id']}` — **{x['outcome']}**: {x['reason']}" for x in results]) + "\n"
        db.execute("UPDATE evaluation_runs SET state='completed',report_json=?,report_markdown=?,completed_at=? WHERE id=?", (json.dumps(report, sort_keys=True), markdown, _now(), run_id)); db.commit()
        return report
    finally:
        db.close()

def report(settings, run_id):
    db = connect(settings)
    try:
        row = db.execute("SELECT state,report_json,report_markdown,error_code FROM evaluation_runs WHERE id=?", (run_id,)).fetchone()
        if not row: raise KeyError("EVALUATION_NOT_FOUND")
        return {"run_id":run_id, "state":row["state"], "report":json.loads(row["report_json"]) if row["report_json"] else None, "markdown":row["report_markdown"], "error_code":row["error_code"]}
    finally: db.close()

def _percentile(values, percentile):
    if not values: return 0.0
    ordered=sorted(values); index=(len(ordered)-1)*percentile
    low=math.floor(index); high=math.ceil(index)
    return round(ordered[low] if low==high else ordered[low]+(ordered[high]-ordered[low])*(index-low),3)

def _table_sizes(db):
    names=[r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    rows={name:db.execute('SELECT COUNT(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in names}
    try:
        sizes={r['name']:r['bytes'] for r in db.execute("SELECT name,SUM(pgsize) bytes FROM dbstat GROUP BY name")}
    except Exception: sizes={}
    return {name:{'rows':count,'bytes':int(sizes.get(name,0) or 0)} for name,count in rows.items()}

def _question_class(case):
    if case.get('answerability')=='unanswerable': return 'unanswerable'
    cap=case.get('capability','').lower()
    if 'preference' in cap: return 'demonstrated-preferences'
    if any(x in cap for x in ('supersession','current-truth','historical','reversal')): return 'superseded-facts'
    if any(x in cap for x in ('episode','reconstruction','time/app')): return 'episodic-retrieval'
    return 'distributed-recovery'

def _materialize_cases(questions):
    """Bind corpus-agnostic Tier 2 contracts to declared Tier 1 fixture facts."""
    tier1={case['id']:case for case in questions['tiers']['tier_1']['questions']}
    bindings={
        't2_direct_fact':'t1_identity_role','t2_distributed_fact':'t1_cedar',
        't2_current_value':'t1_review_slot','t2_old_value':'t1_meterline',
        't2_observed_preference':'t1_pref_slack_opening','t2_duplicate_evidence':'t1_beta_dedup',
        't2_name_disambiguation':'t1_people_disambiguation','t2_stated_conflict':'t1_retention_conflict',
        't2_absent_fact':'t1_absent_atlas_budget','t2_absent_precision':'t1_absent_launch_time'}
    cases=list(tier1.values())
    for template in questions['tiers']['tier_2']['questions']:
        source=tier1[bindings[template['id']]]
        bound=dict(template); bound['question']=source['question']; bound['expected_answer']=source.get('expected_answer'); bound['required_provenance']=source.get('required_provenance',[]); bound['fixture_binding']=source['id']
        if source.get('answerability')=='unanswerable': bound['answerability']='unanswerable'
        cases.append(bound)
    return cases

def _tokens(value):
    return set(re.findall(r"[a-z0-9]+",str(value).lower()))-{'the','a','an','and','is','was','to','of','on','at','from','it'}

def _score(case, response, provenance, has_supersession_evidence=True):
    abstained=response.get('status')=='abstained'
    if case.get('answerability')=='unanswerable':
        return abstained and not response.get('citations'), ('correct_refusal' if abstained else 'fabrication')
    required=set(case.get('required_provenance') or [])
    actual=set(provenance)
    answer=' '.join(response.get('answer') or ([response.get('draft','')] if response.get('draft') else []))
    expected=case.get('expected_answer') or ''
    overlap=len(_tokens(expected)&_tokens(answer))/max(1,len(_tokens(expected)))
    passed=not abstained and required.issubset(actual) and overlap>=0.45
    reasons=[]
    if abstained: reasons.append('unexpected abstention')
    if not required.issubset(actual): reasons.append('missing provenance: '+', '.join(sorted(required-actual)))
    if overlap<0.45: reasons.append(f'answer coverage {overlap:.2f} below 0.45')
    if _question_class(case)=='superseded-facts' and not has_supersession_evidence:
        passed=False; reasons.append('no persisted superseded memory/version supports the current-versus-stale claim')
    return passed, ('matched' if passed else '; '.join(reasons))

def _memory(db, memory_id):
    row=db.execute('SELECT * FROM memories WHERE id=?',(memory_id,)).fetchone()
    if not row: return None
    item=dict(row)
    item['provenance']=[r['transcript_id'] for r in db.execute('SELECT transcript_id FROM memory_evidence WHERE memory_id=? ORDER BY transcript_id',(memory_id,))]
    return item

def _ingestion_events(db, transcript_id):
    """Return every durable admission/consolidation outcome for one source record."""
    events=[]
    for row in db.execute("SELECT memory_id,stage,outcome,detail_json FROM decision_traces WHERE transcript_id=? AND memory_id IS NOT NULL ORDER BY created_at,id",(transcript_id,)):
        if row['stage'] not in {'extraction','consolidation'}: continue
        detail=json.loads(row['detail_json'])
        action='created' if row['stage']=='extraction' and row['outcome']=='admitted' else row['outcome']
        events.append({'action':action,'reason':detail.get('reason','admitted' if action=='created' else row['outcome']),'memory':_memory(db,row['memory_id'])})
    for decision in db.execute("SELECT candidate_index,gate,outcome,reason_code FROM admission_decisions WHERE transcript_id=? ORDER BY candidate_index",(transcript_id,)):
        if decision['outcome'] in {'dropped','duplicate'}:
            events.append({'action':'rejected' if decision['outcome']=='dropped' else 'merged','candidate_index':decision['candidate_index'],'reason':decision['reason_code'],'memory':None})
    return events

def _exclusion_reason(db, trace_id, candidate):
    row=db.execute("SELECT disposition FROM retrieval_candidates WHERE trace_id=? AND memory_id=?",(trace_id,candidate['id'])).fetchone()
    if row and row['disposition']=='near_miss':
        detail=db.execute("SELECT detail_json FROM decision_traces WHERE transcript_id IS NULL AND memory_id=? AND stage='support_validation' ORDER BY created_at DESC LIMIT 1",(candidate['id'],)).fetchone()
        return json.loads(detail['detail_json']).get('missing_facet','missing requested facet') if detail else 'missing requested facet'
    if candidate['basis']!='stated': return 'withheld by disclosure policy'
    return 'retrieved but not selected for the grounded answer'

def run_complete(settings, corpus_path='fixtures/development-500.json', questions_path='EVAL_QUESTIONS.json', ground_truth_path='GROUND_TRUTH.json', output_dir='.', extractor=None, sample_every=25):
    """Reset, ingest through the durable worker, query the production Hey path, and emit an audit."""
    from .review import corpus as load_corpus, reset_database
    started=time.perf_counter(); reset_database(settings); migrate(settings)
    corpus_data=load_corpus(corpus_path); questions=json.loads(Path(questions_path).read_text(encoding='utf-8'))
    ground_truth=json.loads(Path(ground_truth_path).read_text(encoding='utf-8'))
    extractor=extractor or OllamaExtractor(settings); growth=[]
    db=connect(settings); stamp=_now(); import_id=ident('imp')
    try:
        db.execute('INSERT INTO imports VALUES (?,?,?,?,?,?,?,NULL)',(import_id,'processing',len(corpus_data['records']),len(corpus_data['records']),0,stamp,stamp))
        for index,record in enumerate(corpus_data['records']):
            db.execute("INSERT INTO transcripts (id,mode,raw_asr,formatted_text,semantic_processing,created_at,occurred_at,metadata_json) VALUES (?,'dictation',?,?,'queued',?,?,?)",(record['transcript_id'],record['raw_asr'],record['formatted_text'],stamp,record['occurred_at'],json.dumps(record['metadata'],sort_keys=True)))
            db.execute("INSERT INTO jobs (id,transcript_id,kind,state,created_at,import_id) VALUES (?,?,'extract','queued',?,?)",(ident('job'),record['transcript_id'],stamp,import_id))
            db.execute('INSERT INTO import_records VALUES (?,?,?,?,NULL)',(import_id,record['transcript_id'],index,'queued'))
        db.commit()
    finally: db.close()
    for completed in range(1,len(corpus_data['records'])+1):
        asyncio.run(process_one(settings,extractor))
        if completed==1 or completed%sample_every==0 or completed==len(corpus_data['records']):
            db=connect(settings)
            try: growth.append({'records_processed':completed,'database_bytes':Path(settings.database_path).stat().st_size,'tables':_table_sizes(db)})
            finally: db.close()
    db=connect(settings)
    try: db.execute("UPDATE imports SET state='completed',completed_at=? WHERE id=?",(_now(),import_id)); db.commit()
    finally: db.close()
    ingestion=[]; db=connect(settings)
    try:
        for record in corpus_data['records']:
            rid=record['transcript_id']; memories=_ingestion_events(db,rid)
            decisions=[dict(x) for x in db.execute('SELECT candidate_index,gate,outcome,reason_code FROM admission_decisions WHERE transcript_id=? ORDER BY candidate_index',(rid,))]
            t=db.execute('SELECT outcome,semantic_processing FROM transcripts WHERE id=?',(rid,)).fetchone()
            learned=any(event['action'] in {'created','merged','updated','superseded'} for event in memories)
            ignored_reason=None if learned else (decisions[0]['reason_code'] if decisions else t['outcome'])
            ingestion.append({'record_id':rid,'original_input':record,'outcome':t['outcome'],'semantic_processing':t['semantic_processing'],'memory_events':memories,'candidate_decisions':decisions,'nothing_learned_reason':ignored_reason})
    finally: db.close()
    cases=_materialize_cases(questions)
    results=[]
    for case in cases:
        case_start=time.perf_counter(); response=answer_recall(settings,case['question'],None)
        elapsed=round((time.perf_counter()-case_start)*1000,3); db=connect(settings)
        try:
            trace_id=response.get('trace_id'); tr=db.execute('SELECT detail_json FROM decision_traces WHERE id=?',(trace_id,)).fetchone()
            candidates=[]
            for row in db.execute('SELECT * FROM retrieval_candidates WHERE trace_id=? ORDER BY rank',(trace_id,)):
                item=_memory(db,row['memory_id']); item.update({'rank':row['rank'],'legs':json.loads(row['legs_json'])}); candidates.append(item)
            cited_ids={x['memory_id'] for x in response.get('citations',[])}
            retrieved=[x for x in candidates if x['id'] in cited_ids]
            excluded=[{**x,'exclusion_reason':_exclusion_reason(db,trace_id,x)} for x in candidates if x['id'] not in cited_ids]
            provenance=sorted({p for x in retrieved for p in x['provenance']})
            retrieval_ms=response.get('_metrics',{}).get('retrieval_latency_ms',elapsed)
            if tr:
                detail=json.loads(tr['detail_json']); detail['measured_ms']=retrieval_ms
            placeholders=','.join('?' for _ in (case.get('required_provenance') or []))
            has_supersession=True
            if _question_class(case)=='superseded-facts':
                has_supersession=bool(placeholders and db.execute("SELECT 1 FROM memories m JOIN memory_evidence e ON e.memory_id=m.id WHERE e.transcript_id IN ("+placeholders+") AND m.status='superseded' LIMIT 1",tuple(case.get('required_provenance') or [])).fetchone())
            passed,reason=_score(case,response,provenance,has_supersession)
            results.append({'id':case['id'],'class':_question_class(case),'question':case['question'],'expected':case.get('expected_answer') or case.get('expected_behavior'),'actual':response,'abstained':response.get('status')=='abstained','passed':passed,'reason':reason,'retrieval_candidates':candidates,'retrieved_memories':retrieved,'scored_but_excluded':excluded,'provenance_record_ids':provenance,'retrieval_latency_ms':retrieval_ms,'end_to_end_latency_ms':elapsed,'model_usage':[],'cost_usd':0.0})
        finally: db.close()
    usage=list(getattr(extractor,'calls',[])); by_model={}
    for call in usage:
        model=call.get('model','unknown'); bucket=by_model.setdefault(model,{'calls':0,'prompt_tokens':0,'completion_tokens':0,'cost_usd':0.0}); bucket['calls']+=1; bucket['prompt_tokens']+=call.get('prompt_tokens',0); bucket['completion_tokens']+=call.get('completion_tokens',0); bucket['cost_usd']+=call.get('cost_usd',0.0)
    totals={'prompt_tokens':sum(x.get('prompt_tokens',0) for x in usage),'completion_tokens':sum(x.get('completion_tokens',0) for x in usage),'cost_usd':sum(x.get('cost_usd',0) for x in usage),'by_model':by_model}
    by_class={}
    for name in ('distributed-recovery','superseded-facts','demonstrated-preferences','episodic-retrieval','unanswerable'):
        subset=[x for x in results if x['class']==name]; by_class[name]={'passed':sum(x['passed'] for x in subset),'total':len(subset),'pass_rate':round(sum(x['passed'] for x in subset)/len(subset),4) if subset else None}
    unanswerable=[x for x in results if x['class']=='unanswerable']
    report={'schema_version':'1.0','configuration':{'seed':settings.random_seed,'database_path':settings.database_path,'corpus':corpus_path,'questions':questions_path,'ground_truth':ground_truth_path,'extraction_model':settings.extraction_model,'embedding_model':settings.embedding_model},'ground_truth':ground_truth,'ingestion':ingestion,'database_growth':growth,'questions':results,'summary':{'passed':sum(x['passed'] for x in results),'total':len(results),'pass_rate':round(sum(x['passed'] for x in results)/len(results),4) if results else 0,'by_class':by_class,'unanswerable':{'correct_refusals':sum(x['passed'] for x in unanswerable),'fabrications':sum(not x['passed'] for x in unanswerable)},'latency_ms':{'retrieval':{'p50':_percentile([x['retrieval_latency_ms'] for x in results],.5),'p95':_percentile([x['retrieval_latency_ms'] for x in results],.95)},'end_to_end':{'p50':_percentile([x['end_to_end_latency_ms'] for x in results],.5),'p95':_percentile([x['end_to_end_latency_ms'] for x in results],.95)}}},'model_calls':usage,'total_model_usage':totals,'total_cost_usd':totals['cost_usd'],'elapsed_ms':round((time.perf_counter()-started)*1000,3)}
    output=Path(output_dir); output.mkdir(parents=True,exist_ok=True); (output/'results.json').write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding='utf-8')
    lines=['# Kivi complete-pipeline evaluation','',f"**Overall: {report['summary']['passed']}/{report['summary']['total']} ({report['summary']['pass_rate']:.1%})**",'', '## Pass rate by class','']
    for name,value in by_class.items(): lines.append(f"- {name}: {value['passed']}/{value['total']}"+(f" ({value['pass_rate']:.1%})" if value['pass_rate'] is not None else ' (no cases)'))
    lines += ['',f"Unanswerable: **{report['summary']['unanswerable']['correct_refusals']} correct refusals; {report['summary']['unanswerable']['fabrications']} fabrications**",'',f"Latency: retrieval p50/p95 {report['summary']['latency_ms']['retrieval']['p50']}/{report['summary']['latency_ms']['retrieval']['p95']} ms; end-to-end p50/p95 {report['summary']['latency_ms']['end_to_end']['p50']}/{report['summary']['latency_ms']['end_to_end']['p95']} ms.",'',f"Model usage: {totals['prompt_tokens']} tokens in, {totals['completion_tokens']} tokens out; total cost ${totals['cost_usd']:.6f}.",'','## Failures (full)','']
    failures=[x for x in results if not x['passed']]
    if not failures: lines.append('None.')
    for x in failures: lines += [f"### {x['id']} — {x['class']}",'',f"Question: {x['question']}",'',f"Expected: `{json.dumps(x['expected'],ensure_ascii=False)}`",'',f"Actual: `{json.dumps(x['actual'],ensure_ascii=False)}`",'',f"Reason: **{x['reason']}**",'',f"Retrieved memories: `{json.dumps(x['retrieved_memories'],ensure_ascii=False)}`",'',f"Scored but excluded: `{json.dumps(x['scored_but_excluded'],ensure_ascii=False)}`",'']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report
