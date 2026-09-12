import asyncio, hashlib, json, re, time, uuid
from datetime import datetime, timedelta, timezone
import httpx
from .storage import connect, trace

def ident(prefix): return f"{prefix}_{uuid.uuid4().hex}"
def now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
class ExtractionError(RuntimeError): pass

class OllamaExtractor:
    """The production extractor: bad/unavailable output fails rather than being made up."""
    def __init__(self, settings):
        self.settings=settings
        self.calls=[]
    async def extract(self, text):
        prompt=("Extract atomic eligible work memories only. Return one JSON object with a memories array; every item has "
          "type(entity|preference|episode), name, relation, value, basis(stated|observed|hypothesis). "
          "Use preference/observed only for a writing or work pattern demonstrated by the text; do not label a decision, request, schedule, or assignment as a preference. "
          "Use entity or episode/stated for directly asserted work facts. Return an empty memories array if none. Do not infer or include private/third-party facts. Text: "+text)
        try:
            item_schema={"type":"object","properties":{"type":{"type":"string","enum":["entity","preference","episode"]},"name":{"type":"string"},"relation":{"type":"string"},"value":{"type":"string"},"basis":{"type":"string","enum":["stated","observed","hypothesis"]}},"required":["type","name","relation","value","basis"],"additionalProperties":False}
            schema={"type":"object","properties":{"memories":{"type":"array","items":item_schema}},"required":["memories"],"additionalProperties":False}
            async with httpx.AsyncClient(timeout=30) as client:
                r=await client.post(self.settings.ollama_url+"/api/generate",json={"model":self.settings.extraction_model,"prompt":prompt,"format":schema,"stream":False,"options":{"temperature":0,"seed":self.settings.random_seed}})
                r.raise_for_status(); payload=r.json(); value=json.loads(payload["response"]); value=value.get('memories') if isinstance(value,dict) else value
                self.calls.append({"model":self.settings.extraction_model,"prompt_tokens":int(payload.get("prompt_eval_count",0)),"completion_tokens":int(payload.get("eval_count",0)),"duration_ns":int(payload.get("total_duration",0)),"cost_usd":0.0})
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc: raise ExtractionError("OLLAMA_EXTRACTION_FAILED") from exc
        if not isinstance(value,list): raise ExtractionError("OLLAMA_EXTRACTION_INVALID")
        return value

def _candidates(value):
    if value=={"none":True}: return []
    if isinstance(value,dict) and set(value)=={"name","relation","value"}: return [{**value,"type":"entity","basis":"stated"}]
    if not isinstance(value,list): raise ExtractionError("OLLAMA_EXTRACTION_INVALID")
    return value
def _reason(c):
    if not isinstance(c,dict) or set(c)!={"type","name","relation","value","basis"}: return "INVALID_SCHEMA"
    if c['type'] not in {'entity','preference','episode'} or c['basis'] not in {'stated','observed','hypothesis'}: return "INVALID_TYPE"
    if not all(isinstance(c[k],str) and c[k].strip() for k in ('name','relation','value')): return "INCOMPLETE"
    text=' '.join(c[k].lower() for k in ('name','relation','value'))
    if any(x in text for x in ('health','hospital','diagnosis','religion','politics','salary','family')): return 'EXCLUDED_CATEGORY'
    if any(x in text for x in ('mother','father','she is','he is','they are')): return 'THIRD_PARTY_CHARACTERISATION'
    return None

async def process_one(settings, extractor):
    db=connect(settings)
    row=db.execute("SELECT j.id job_id,j.attempts,j.import_id,t.id,t.formatted_text FROM jobs j JOIN transcripts t ON t.id=j.transcript_id WHERE j.state IN ('queued','retrying') ORDER BY COALESCE(t.occurred_at,t.created_at),j.created_at,j.id LIMIT 1").fetchone()
    if not row: db.close(); return False
    db.execute('BEGIN IMMEDIATE'); db.execute("UPDATE jobs SET state='processing',attempts=attempts+1,lease_until=? WHERE id=?",((datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),row['job_id'])); db.commit()
    try:
        candidates=_candidates(await extractor.extract(row['formatted_text'])); db.execute('BEGIN IMMEDIATE'); admitted=dropped=0
        for i,c in enumerate(candidates):
            reason=_reason(c)
            if reason:
                db.execute("INSERT INTO admission_decisions VALUES (?,?,?,?,?,?,?)",(ident('adm'),row['id'],i,'ordered_admission','dropped',reason,now())); dropped+=1; continue
            old=db.execute("SELECT * FROM memories WHERE name=? AND relation=? AND value=?",(c['name'].strip(),c['relation'].strip(),c['value'].strip())).fetchone()
            if old:
                db.execute("INSERT OR IGNORE INTO memory_evidence VALUES (?,?)",(old['id'],row['id']))
                db.execute("INSERT INTO admission_decisions VALUES (?,?,?,?,?,?,?)",(ident('adm'),row['id'],i,'consolidation','duplicate','EXACT_SEMANTIC_KEY',now())); continue
            replacement_words=(' now ',' changed ',' moved ',' replace',' instead',' stopped',' from ')
            explicit_replacement=any(word in (' '+row['formatted_text'].lower()+' ') for word in replacement_words)
            displaced=db.execute("SELECT * FROM memories WHERE status='active' AND name=? AND relation=? AND value<>?",(c['name'].strip(),c['relation'].strip(),c['value'].strip())).fetchall() if explicit_replacement else []
            mid=ident('mem'); db.execute("INSERT INTO memories (id,kind,name,relation,value,transcript_id,created_at,basis) VALUES (?,?,?,?,?,?,?,?)",(mid,c['type'],c['name'].strip(),c['relation'].strip(),c['value'].strip(),row['id'],now(),c['basis']))
            db.execute("INSERT INTO memory_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",(ident('ver'),mid,0,c['type'],c['name'].strip(),c['relation'].strip(),c['value'].strip(),c['basis'],'active','admitted',now()))
            db.execute("INSERT INTO memory_evidence VALUES (?,?)",(mid,row['id'])); db.execute("INSERT INTO memory_fts VALUES (?,?,?,?)",(mid,c['name'].strip(),c['relation'].strip(),c['value'].strip()))
            db.execute("INSERT OR IGNORE INTO entity_links VALUES (?,?)",(mid,c['name'].strip())); db.execute("INSERT OR REPLACE INTO projections VALUES (?,NULL,'pending',NULL)",(mid,))
            db.execute("INSERT INTO admission_decisions VALUES (?,?,?,?,?,?,?)",(ident('adm'),row['id'],i,'ordered_admission','admitted',None,now())); trace(db,ident('trace'),row['id'],mid,'extraction','admitted',{'type':c['type'],'basis':c['basis']},now()); admitted+=1
            for prior in displaced:
                db.execute("UPDATE memories SET status='superseded' WHERE id=?",(prior['id'],))
                version=_version(db,prior['id'])+1
                db.execute("INSERT INTO memory_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",(ident('ver'),prior['id'],version,prior['kind'],prior['name'],prior['relation'],prior['value'],prior['basis'],'superseded','superseded',now()))
                trace(db,ident('trace'),row['id'],prior['id'],'consolidation','superseded',{'replacement_memory_id':mid,'reason':'EXPLICIT_REPLACEMENT_LANGUAGE'},now())
        outcome='no_candidates' if not candidates else ('all_dropped' if not admitted else ('partial_success' if dropped else 'stored_candidates'))
        db.execute("INSERT OR REPLACE INTO transcript_fts(transcript_id,formatted_text) VALUES (?,?)",(row['id'],row['formatted_text']))
        db.execute("UPDATE transcripts SET outcome=?,semantic_processing='complete' WHERE id=?",(outcome,row['id'])); db.execute("UPDATE jobs SET state='completed',completed_at=?,lease_until=NULL WHERE id=?",(now(),row['job_id']))
        if row['import_id']: db.execute("UPDATE import_records SET state='processed' WHERE import_id=? AND transcript_id=?",(row['import_id'],row['id']))
        db.commit()
    except ExtractionError as exc:
        db.execute('BEGIN IMMEDIATE'); terminal=(not row['import_id']) or row['attempts']+1>=settings.extraction_retry_cap; state=('quarantined' if terminal and row['import_id'] else ('failed' if terminal else 'retrying'))
        db.execute("UPDATE jobs SET state=?,error_code=?,completed_at=?,lease_until=NULL WHERE id=?",(state,str(exc),now() if terminal else None,row['job_id']))
        db.execute("UPDATE transcripts SET outcome=?,semantic_processing=? WHERE id=?",('quarantined' if terminal else None,state,row['id']))
        if row['import_id']: db.execute("UPDATE import_records SET state=?,error_code=? WHERE import_id=? AND transcript_id=?",(state,str(exc),row['import_id'],row['id']))
        db.commit()
    finally: db.close()
    return True
async def drain(settings,extractor):
    while await process_one(settings,extractor): await asyncio.sleep(0)
def _terms(question):
    stop={'who','what','when','where','why','did','does','the','and','for','about','my','is','on','to','a'}
    words=[x.lower() for x in re.findall(r'[A-Za-z0-9]+',question)]
    if 'about' in words: words=words[words.index('about')+1:]
    return [x for x in words if len(x)>1 and x not in stop]

def _vector_score(left, right):
    if not isinstance(left,list) or not isinstance(right,list) or len(left)!=len(right) or not left: return None
    dot=sum(a*b for a,b in zip(left,right)); mag=(sum(a*a for a in left)*sum(b*b for b in right))**.5
    return dot/mag if mag else None

def retrieve(settings, transcript_id, question):
    """Retrieve before disclosure. An unavailable vector leg is recorded, never invented."""
    terms=_terms(question); db=connect(settings); trace_id=ident('trace')
    try:
        history_intent=any(x in question.lower() for x in ('old ','previous','replaced','superseded','before','earlier'))
        statuses="('active','superseded')" if history_intent else "('active')"
        lexical={} if not terms else {r['id']: -r['score'] for r in db.execute("SELECT m.id,bm25(memory_fts) score FROM memory_fts f JOIN memories m ON m.id=f.memory_id WHERE memory_fts MATCH ? AND m.status IN "+statuses,(' OR '.join(terms),))}
        query_vector=None; vector_failure='EMBEDDING_UNAVAILABLE'
        # Query vectors are supplied only by a real caller/model integration; do not synthesize them.
        semantic={}
        entity_ids=set()
        if terms:
            placeholders=','.join('?' for _ in terms)
            entity_ids={r['memory_id'] for r in db.execute("SELECT DISTINCT e2.memory_id FROM entity_links e1 JOIN entity_links e2 ON e1.entity_name=e2.entity_name WHERE lower(e1.entity_name) IN ("+placeholders+")",terms)}
        ids=set(lexical)|set(semantic)|entity_ids
        rows={r['id']:dict(r) for r in db.execute("SELECT * FROM memories WHERE status IN "+statuses)}
        ranked=[]
        for mid in ids:
            row=rows.get(mid)
            if not row: continue
            score=lexical.get(mid,0)*100+semantic.get(mid,0)*10+(1 if mid in entity_ids else 0)
            ranked.append((score, row, {'fts':mid in lexical,'embedding':mid in semantic,'one_hop':mid in entity_ids}))
        ranked.sort(key=lambda x:(-x[0], -x[1]['pinned'], {'stated':2,'observed':1,'hypothesis':0}[x[1]['basis']], x[1]['created_at'], x[1]['id']))
        detail={'query_terms':len(terms),'vector_leg':vector_failure,'candidate_count':len(ranked)}
        trace(db,trace_id,transcript_id,None,'retrieval','found' if ranked else 'not_found',detail,now())
        for rank,(_,row,legs) in enumerate(ranked,1): db.execute("INSERT INTO retrieval_candidates VALUES (?,?,?,?,?)",(trace_id,row['id'],rank,'retrieved',json.dumps(legs,sort_keys=True)))
        db.commit()
        return trace_id,[x[1] for x in ranked],vector_failure
    finally: db.close()

def permission(settings):
    db=connect(settings)
    try: return db.execute("SELECT mode FROM permissions WHERE singleton=1").fetchone()['mode']
    finally: db.close()

def sweep_lifecycle(settings):
    """Expiry is a durable state change; stated and pinned memory are never swept."""
    db=connect(settings); stamp=now()
    try:
        db.execute('BEGIN IMMEDIATE')
        # Deliberately conservative, documented windows: observations 90 days; hypotheses 30 days.
        db.execute("UPDATE memories SET status='suppressed' WHERE status='active' AND pinned=0 AND basis='observed' AND created_at < datetime('now','-90 days')")
        db.execute("UPDATE memories SET status='suppressed' WHERE status='active' AND pinned=0 AND basis='hypothesis' AND created_at < datetime('now','-30 days')")
        db.commit()
    finally: db.close()

def _version(db, memory_id):
    row=db.execute('SELECT MAX(version) v FROM memory_versions WHERE memory_id=?',(memory_id,)).fetchone()
    return 0 if row['v'] is None else row['v']

def memory_action(settings, memory_id, action, expected_version, idempotency_key, value=None):
    db=connect(settings); stamp=now()
    try:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT * FROM memory_actions WHERE idempotency_key=?',(idempotency_key,)).fetchone()
        if old:
            result=json.loads(old['detail_json']); db.commit(); return result
        memory=db.execute("SELECT * FROM memories WHERE id=? AND status!='suppressed'",(memory_id,)).fetchone()
        if not memory: raise KeyError('MEMORY_NOT_FOUND')
        version=_version(db,memory_id)
        if expected_version!=version: raise ValueError('VERSION_CONFLICT')
        if action=='confirm':
            if memory['basis']!='observed': raise ValueError('CONFIRM_REQUIRES_OBSERVED')
            db.execute("UPDATE memories SET basis='stated' WHERE id=?",(memory_id,))
        elif action=='correct':
            if not value or not value.strip(): raise ValueError('CORRECTION_VALUE_REQUIRED')
            db.execute("UPDATE memories SET value=?,status='active' WHERE id=?",(value.strip(),memory_id))
            db.execute("DELETE FROM memory_fts WHERE memory_id=?",(memory_id,)); db.execute("INSERT INTO memory_fts VALUES (?,?,?,?)",(memory_id,memory['name'],memory['relation'],value.strip()))
            db.execute("INSERT OR REPLACE INTO suppressions VALUES (?,?,?,?)",(ident('sup'),memory_id,'CORRECTED_OLD_BELIEF',stamp))
        elif action=='demote': db.execute("UPDATE memories SET status='suppressed' WHERE id=?",(memory_id,)); db.execute("INSERT OR REPLACE INTO suppressions VALUES (?,?,?,?)",(ident('sup'),memory_id,'DEMOTED',stamp))
        elif action=='forget':
            db.execute("UPDATE memories SET status='suppressed' WHERE id=?",(memory_id,)); db.execute("DELETE FROM memory_fts WHERE memory_id=?",(memory_id,)); db.execute("INSERT OR REPLACE INTO suppressions VALUES (?,?,?,?)",(ident('sup'),memory_id,'FORGOTTEN',stamp)); db.execute("INSERT OR REPLACE INTO memory_tombstones VALUES (?,?)",(memory_id,stamp))
        elif action=='pin': db.execute("UPDATE memories SET pinned=1 WHERE id=?",(memory_id,))
        elif action=='unpin': db.execute("UPDATE memories SET pinned=0 WHERE id=?",(memory_id,))
        else: raise ValueError('UNSUPPORTED_ACTION')
        after=db.execute('SELECT * FROM memories WHERE id=?',(memory_id,)).fetchone()
        next_version=version+1
        db.execute("INSERT INTO memory_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",(ident('ver'),memory_id,next_version,after['kind'],after['name'],after['relation'],after['value'],after['basis'],after['status'],action,stamp))
        receipt={'receipt_id':ident('act'),'memory':dict(after),'version':next_version,'action':action}
        db.execute("INSERT INTO memory_actions VALUES (?,?,?,?,?,?,?)",(receipt['receipt_id'],memory_id,action,idempotency_key,expected_version,json.dumps(receipt,sort_keys=True),stamp))
        trace(db,ident('trace'),after['transcript_id'],memory_id,'memory_action',action,{'version':version,'idempotency_key':idempotency_key},stamp)
        db.commit(); return receipt
    except:
        db.rollback(); raise
    finally: db.close()

def disclose(settings, transcript_id, candidates, mode, invite_daari=False):
    used=[]; withheld=[]; hypotheses=[]
    for row in candidates:
        if row['basis']=='stated': used.append(row)
        elif row['basis']=='observed' and mode=='koottu': used.append(row)
        elif row['basis']=='hypothesis' and invite_daari: hypotheses.append(row)
        else: withheld.append(row)
    db=connect(settings)
    try:
        for row in used: trace(db,ident('trace'),transcript_id,row['id'],'disclosure','used',{'mode':mode},now())
        for row in withheld+hypotheses: trace(db,ident('trace'),transcript_id,row['id'],'disclosure','withheld' if row in withheld else 'daari_question',{'mode':mode},now())
        db.commit()
    finally: db.close()
    return used,withheld,hypotheses

def answer_recall(settings, question, transcript_id=None):
    """Run production recall/disclosure; an evaluator may omit the transcript."""
    sweep_lifecycle(settings); mode=permission(settings)
    invite_daari=any(x in question.lower() for x in ('why ','insight','think i keep'))
    retrieval_started=time.perf_counter(); trace_id,candidates,vector_failure=retrieve(settings,transcript_id,question)
    retrieval_ms=round((time.perf_counter()-retrieval_started)*1000,3)
    lower=question.lower()
    requested=None
    patterns=(r'\b(?:exact|formal|public|final approved|line|root)\s+([a-z][a-z-]*)',r'\bwhich\s+(?:[a-z-]+\s+){0,3}([a-z-]+)\s+was\s+(?:selected|chosen)',r'\bhow much\b.*\b(cost)\b',r'\bwhat did\b.*\bsay about (?:the )?([a-z-]+)')
    for pattern in patterns:
        match=re.search(pattern,lower)
        if match: requested=match.group(1); break
    supporting=candidates
    if requested:
        supporting=[row for row in candidates if requested in ' '.join(str(row[k]).lower() for k in ('name','relation','value'))]
    rejected=[row for row in candidates if row not in supporting]
    db=connect(settings)
    try:
        for row in rejected:
            db.execute("UPDATE retrieval_candidates SET disposition='near_miss' WHERE trace_id=? AND memory_id=?",(trace_id,row['id']))
            trace(db,ident('trace'),transcript_id,row['id'],'support_validation','near_miss',{'missing_facet':requested},now())
        db.commit()
    finally: db.close()
    used,withheld,hypotheses=disclose(settings,transcript_id,supporting,mode,invite_daari)
    if not used:
        return {'mode':'hey_kivi','transcript_id':transcript_id,'tool':'recall_search','selected_tool':'recall_search','status':'abstained','reason':'NO_GROUNDED_MATCH','search_failure':vector_failure,'near_misses':[],'trace_id':trace_id,'citations':[],'answer':["I don't have a matching stated memory."], '_metrics':{'retrieval_latency_ms':retrieval_ms}}
    answer=[f"{x['name']} {x['relation']} {x['value']}" if x['basis']=='stated' else f"Kivi noticed: {x['name']} {x['relation']} {x['value']}" for x in used]
    if hypotheses: answer += [f"Could it be that {x['name']} {x['relation']} {x['value']}?" for x in hypotheses]
    return {'mode':'hey_kivi','transcript_id':transcript_id,'tool':'recall_search','selected_tool':'recall_search','status':'completed','answer':answer,'trace_id':trace_id,'citations':[{'memory_id':x['id'],'transcript_id':x['transcript_id']} for x in used],'withheld_observations':len(withheld),'permission':mode,'_metrics':{'retrieval_latency_ms':retrieval_ms}}
