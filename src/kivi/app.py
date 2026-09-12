import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from .config import Settings
from .services import OllamaExtractor, answer_recall, drain, disclose, ident, now, permission, retrieve, memory_action, sweep_lifecycle
from .storage import connect, migrate, trace
from .evaluation import create_run as create_evaluation_run, run as run_evaluation, report as evaluation_report
class DictationIn(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True); raw_asr:str=Field(min_length=1); formatted_text:str=Field(min_length=1)
class HeyIn(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True); text:str=Field(min_length=1); context:str|None=None; idempotency_key:str|None=None
class PermissionIn(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True); mode:str=Field(pattern='^(anbu|koottu)$')
class ImportRecord(BaseModel):
    model_config=ConfigDict(extra='forbid')
    transcript_id:str=Field(min_length=1); raw_asr:str=Field(min_length=1); formatted_text:str=Field(min_length=1); occurred_at:str=Field(min_length=1); metadata:dict
class ImportIn(BaseModel):
    model_config=ConfigDict(extra='forbid'); records:list[ImportRecord]=Field(min_length=1,max_length=1000)
class MemoryActionIn(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    action:str=Field(pattern='^(confirm|correct|demote|forget|pin|unpin)$'); expected_version:int=Field(ge=0); idempotency_key:str=Field(min_length=1); value:str|None=None
class EvaluationIn(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    case_set:str=Field(pattern='^[a-z0-9_-]+$')
def create_app(settings=None, extractor=None):
    settings=settings or Settings(); extractor=extractor or OllamaExtractor(settings)
    @asynccontextmanager
    async def life(app): migrate(settings); yield
    app=FastAPI(lifespan=life); root=Path(__file__).parent/'web'; templates=Jinja2Templates(directory=str(root/'templates')); app.mount('/static',StaticFiles(directory=str(root/'static')),name='static')
    @app.post('/v1/dictations',status_code=202)
    async def dictation(item:DictationIn):
        transcript_id=ident('trn'); job_id=ident('job'); stamp=now(); db=connect(settings)
        try:
            db.execute('BEGIN IMMEDIATE'); db.execute("INSERT INTO transcripts (id,mode,raw_asr,formatted_text,written_response,semantic_processing,created_at,occurred_at,metadata_json) VALUES (?, 'dictation', ?, ?, ?, 'semantic_processing', ?, ?, '{}')",(transcript_id,item.raw_asr,item.formatted_text,item.formatted_text,stamp,stamp)); db.execute("INSERT OR REPLACE INTO transcript_fts(transcript_id,formatted_text) VALUES (?,?)",(transcript_id,item.formatted_text)); db.execute("INSERT INTO jobs (id,transcript_id,kind,state,created_at) VALUES (?, ?, 'extract_entity', 'queued', ?)",(job_id,transcript_id,stamp)); trace(db,ident('trace'),transcript_id,None,'dictation','accepted',{'semantic_processing':True},stamp); db.commit()
        finally: db.close()
        asyncio.create_task(drain(settings,extractor)); return {'mode':'dictation','transcript_id':transcript_id,'written_response':item.formatted_text,'semantic_processing':'semantic_processing','job_id':job_id}
    @app.get('/v1/permissions')
    def get_permission(): return {'mode':permission(settings)}
    @app.put('/v1/permissions')
    def set_permission(item:PermissionIn):
        db=connect(settings)
        try: db.execute("UPDATE permissions SET mode=?,updated_at=? WHERE singleton=1",(item.mode,now())); db.commit()
        finally: db.close()
        return {'mode':item.mode}
    @app.post('/v1/hey-kivi')
    async def hey(item:HeyIn):
        transcript_id=ident('trn'); stamp=now(); db=connect(settings)
        try: db.execute("INSERT INTO transcripts (id,mode,raw_asr,formatted_text,written_response,semantic_processing,created_at,occurred_at,metadata_json) VALUES (?, 'hey_kivi', ?, ?, NULL, 'complete', ?, ?, '{}')",(transcript_id,item.text,item.text,stamp,stamp)); db.commit()
        finally: db.close()
        sweep_lifecycle(settings); lower=item.text.lower(); mode=permission(settings); invite_daari=any(x in lower for x in ('why ','insight','think i keep'))
        if any(x in lower for x in ('web search','live web','google ')):
            trace_id=ident('trace'); db=connect(settings)
            try: trace(db,trace_id,transcript_id,None,'routing','unsupported',{'reason':'UNSUPPORTED_TOOL'},now()); db.commit()
            finally: db.close()
            return {'mode':'hey_kivi','transcript_id':transcript_id,'selected_tool':None,'status':'unsupported','reason':'UNSUPPORTED_TOOL','answer':[], 'trace_id':trace_id,'citations':[]}
        tool='schedule_reschedule' if any(x in lower for x in ('schedule','reschedule','move to')) else ('draft_reply' if any(x in lower for x in ('draft','reply','write ')) else 'recall_search')
        if tool == 'recall_search':
            return answer_recall(settings,item.text,transcript_id)
        trace_id,candidates,vector_failure=retrieve(settings,transcript_id,item.text)
        used,withheld,hypotheses=disclose(settings,transcript_id,candidates,mode,invite_daari)
        if tool=='schedule_reschedule':
            import re
            match=re.search(r'\b(\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z)\b',item.text)
            event_memory=next((x for x in used if x['kind']=='episode'),None)
            if not match or not event_memory or not item.idempotency_key:
                return {'mode':'hey_kivi','transcript_id':transcript_id,'selected_tool':tool,'status':'abstained','reason':'MISSING_TIME_OR_GROUNDED_EVENT','trace_id':trace_id,'citations':[]}
            db=connect(settings)
            try:
                old=db.execute('SELECT id FROM internal_events WHERE idempotency_key=?',(item.idempotency_key,)).fetchone(); event_id=old['id'] if old else ident('evt')
                if not old: db.execute('INSERT INTO internal_events VALUES (?,?,?,?,?,?)',(event_id,event_memory['id'],match.group(1),item.idempotency_key,'scheduled',now())); db.commit()
            finally: db.close()
            return {'mode':'hey_kivi','transcript_id':transcript_id,'selected_tool':tool,'status':'completed','event_id':event_id,'external_side_effects':'none','trace_id':trace_id,'citations':[{'memory_id':event_memory['id'],'transcript_id':event_memory['transcript_id']}]}
        if not used:
            return {'mode':'hey_kivi','transcript_id':transcript_id,'tool':tool,'selected_tool':tool,'status':'abstained','reason':'NO_GROUNDED_MATCH','search_failure':vector_failure,'near_misses':[],'trace_id':trace_id,'citations':[],'answer':["I don't have a matching stated memory."]}
        if tool=='draft_reply':
            stated=[x for x in used if x['basis']=='stated']
            return {'mode':'hey_kivi','transcript_id':transcript_id,'selected_tool':tool,'status':'completed','draft':'\n'.join(f"{x['name']} {x['relation']} {x['value']}" for x in stated),'trace_id':trace_id,'citations':[{'memory_id':x['id'],'transcript_id':x['transcript_id']} for x in stated],'withheld_observations':len(withheld)}
        answer=[f"{x['name']} {x['relation']} {x['value']}" if x['basis']=='stated' else f"Kivi noticed: {x['name']} {x['relation']} {x['value']}" for x in used]
        if hypotheses: answer += [f"Could it be that {x['name']} {x['relation']} {x['value']}?" for x in hypotheses]
        return {'mode':'hey_kivi','transcript_id':transcript_id,'tool':tool,'selected_tool':tool,'status':'completed','answer':answer,'trace_id':trace_id,'citations':[{'memory_id':x['id'],'transcript_id':x['transcript_id']} for x in used],'withheld_observations':len(withheld),'permission':mode}
    @app.post('/v1/imports',status_code=202)
    async def create_import(payload:ImportIn):
        import_id=ident('imp'); stamp=now(); db=connect(settings); errors=[]; accepted=[]; replayed=[]
        try:
            db.execute('BEGIN IMMEDIATE')
            for i,record in enumerate(payload.records):
                if not isinstance(record.metadata,dict) or not record.metadata.get('source'):
                    errors.append({'index':i,'transcript_id':record.transcript_id,'code':'INVALID_METADATA'}); continue
                old=db.execute('SELECT raw_asr,formatted_text FROM transcripts WHERE id=?',(record.transcript_id,)).fetchone()
                if old:
                    if old['raw_asr']!=record.raw_asr or old['formatted_text']!=record.formatted_text: raise HTTPException(409,'CONTENT_CONFLICT')
                    replayed.append((i,record))
                    continue
                accepted.append((i,record))
            db.execute('INSERT INTO imports VALUES (?,?,?,?,?,?,NULL,NULL)',(import_id,'queued',len(payload.records),len(accepted),len(errors),stamp))
            for i,record in accepted:
                db.execute("INSERT INTO transcripts (id,mode,raw_asr,formatted_text,semantic_processing,created_at,occurred_at,metadata_json) VALUES (?,'dictation',?,?, 'queued',?,?,?)",(record.transcript_id,record.raw_asr,record.formatted_text,stamp,record.occurred_at,__import__('json').dumps(record.metadata,sort_keys=True))); db.execute("INSERT OR REPLACE INTO transcript_fts(transcript_id,formatted_text) VALUES (?,?)",(record.transcript_id,record.formatted_text))
                db.execute("INSERT INTO jobs (id,transcript_id,kind,state,created_at,import_id) VALUES (?,?,'extract','queued',?,?)",(ident('job'),record.transcript_id,stamp,import_id)); db.execute('INSERT INTO import_records VALUES (?,?,?,?,NULL)',(import_id,record.transcript_id,i,'queued'))
            for i,record in replayed: db.execute('INSERT INTO import_records VALUES (?,?,?,?,NULL)',(import_id,record.transcript_id,i,'replayed'))
            for e in errors: db.execute('INSERT INTO import_records VALUES (?,?,?,?,?)',(import_id,e['transcript_id'],e['index'],'rejected',e['code']))
            db.commit()
        finally: db.close()
        asyncio.create_task(drain(settings,extractor)); return {'import_id':import_id,'state':'queued','submitted':len(payload.records),'accepted':len(accepted),'replayed':len(replayed),'rejected':len(errors),'record_errors':errors,'status_url':'/v1/imports/'+import_id,'created_at':stamp}
    @app.get('/v1/imports/{import_id}')
    def import_status(import_id:str):
        db=connect(settings)
        try:
            imp=db.execute('SELECT * FROM imports WHERE id=?',(import_id,)).fetchone()
            if not imp: raise HTTPException(404,'IMPORT_NOT_FOUND')
            records=[dict(x) for x in db.execute('SELECT * FROM import_records WHERE import_id=? ORDER BY record_index',(import_id,))]; active=sum(x['state'] in ('queued','processing','retrying') for x in records)
            return {'import_id':import_id,'state':'completed' if not active else 'processing','complete':not active,'counts':{'submitted':imp['submitted'],'accepted':imp['accepted'],'replayed':sum(x['state']=='replayed' for x in records),'rejected':imp['rejected'],'processed':sum(x['state']=='processed' for x in records),'quarantined':sum(x['state']=='quarantined' for x in records),'queued':sum(x['state']=='queued' for x in records),'processing':sum(x['state']=='processing' for x in records),'retrying':sum(x['state']=='retrying' for x in records)},'records':records}
        finally: db.close()
    @app.get('/v1/jobs/{job_id}')
    def job(job_id:str):
        db=connect(settings); row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone(); db.close()
        if not row: raise HTTPException(404,'JOB_NOT_FOUND')
        return dict(row)
    @app.get('/v1/inspect/{transcript_id}')
    def inspect(transcript_id:str):
        db=connect(settings); t=db.execute('SELECT * FROM transcripts WHERE id=?',(transcript_id,)).fetchone(); traces=db.execute('SELECT * FROM decision_traces WHERE transcript_id=? ORDER BY created_at',(transcript_id,)).fetchall(); mem=db.execute('SELECT * FROM memories WHERE transcript_id=?',(transcript_id,)).fetchall(); db.close()
        if not t: raise HTTPException(404,'TRANSCRIPT_NOT_FOUND')
        return {'transcript':dict(t),'memories':[dict(x) for x in mem],'why':[dict(x) for x in traces]}
    @app.get('/v1/memories')
    def memories():
        sweep_lifecycle(settings); db=connect(settings)
        try:
            rows=[dict(x) for x in db.execute("""
                SELECT m.*, COUNT(DISTINCT e.transcript_id) AS evidence_count,
                       COALESCE(MAX(t.occurred_at), m.created_at) AS last_seen_at
                FROM memories m
                LEFT JOIN memory_evidence e ON e.memory_id=m.id
                LEFT JOIN transcripts t ON t.id=e.transcript_id
                WHERE m.status='active'
                GROUP BY m.id
                ORDER BY m.pinned DESC, last_seen_at DESC, m.created_at DESC
            """)]
            for row in rows: row['version']=db.execute('SELECT COALESCE(MAX(version),0) FROM memory_versions WHERE memory_id=?',(row['id'],)).fetchone()[0]
            return {'groups':{basis:[x for x in rows if x['basis']==basis] for basis in ('stated','observed','hypothesis')}}
        finally: db.close()
    @app.get('/v1/memories/{memory_id}')
    def memory_detail(memory_id:str):
        db=connect(settings)
        try:
            mem=db.execute("SELECT * FROM memories WHERE id=? AND status!='suppressed'",(memory_id,)).fetchone()
            if not mem: raise HTTPException(404,'MEMORY_NOT_FOUND')
            provenance=[dict(x) for x in db.execute('SELECT t.id,t.occurred_at,t.formatted_text FROM memory_evidence e JOIN transcripts t ON t.id=e.transcript_id WHERE e.memory_id=?',(memory_id,))]
            history=[dict(x) for x in db.execute('SELECT * FROM memory_versions WHERE memory_id=? ORDER BY version',(memory_id,))]
            return {'memory':dict(mem),'provenance':provenance,'history':history,'version':history[-1]['version'] if history else 0}
        finally: db.close()
    @app.post('/v1/memories/{memory_id}/actions')
    def action(memory_id:str,item:MemoryActionIn):
        try: return memory_action(settings,memory_id,item.action,item.expected_version,item.idempotency_key,item.value)
        except KeyError: raise HTTPException(404,'MEMORY_NOT_FOUND')
        except ValueError as exc:
            if str(exc)=='CORRECTION_VALUE_REQUIRED': raise HTTPException(422,str(exc))
            raise HTTPException(409,str(exc))
    @app.get('/v1/why/{trace_id}')
    def why(trace_id:str):
        db=connect(settings)
        try:
            trace_row=db.execute('SELECT * FROM decision_traces WHERE id=?',(trace_id,)).fetchone()
            if not trace_row: raise HTTPException(404,'TRACE_NOT_FOUND')
            candidates=[dict(x) for x in db.execute('SELECT * FROM retrieval_candidates WHERE trace_id=? ORDER BY rank',(trace_id,))]
            stages=[dict(x) for x in db.execute('SELECT * FROM decision_traces WHERE transcript_id=? ORDER BY created_at',(trace_row['transcript_id'],))]
            return {'trace':dict(trace_row),'candidates':candidates,'stages':stages}
        finally: db.close()
    @app.post('/v1/evaluations', status_code=202)
    def evaluation(item:EvaluationIn):
        try: run_id=create_evaluation_run(settings,item.case_set)
        except ValueError as exc: raise HTTPException(422,str(exc))
        return {'run_id':run_id,'state':'queued','status_url':f'/v1/evaluations/{run_id}'}
    @app.get('/v1/evaluations/{run_id}')
    def evaluation_status(run_id:str, wait:bool=False):
        try:
            current=evaluation_report(settings,run_id)
            if wait and current['state']=='queued': run_evaluation(settings,run_id); current=evaluation_report(settings,run_id)
            return current
        except KeyError: raise HTTPException(404,'EVALUATION_NOT_FOUND')
    @app.get('/',response_class=HTMLResponse)
    def dictation_page(request:Request): return templates.TemplateResponse(request,'dictation.html',{'page':'dictation'})
    @app.get('/hey',response_class=HTMLResponse)
    def hey_page(request:Request): return templates.TemplateResponse(request,'hey.html',{'page':'hey'})
    @app.get('/memory',response_class=HTMLResponse)
    def memory_page(request:Request): return templates.TemplateResponse(request,'inspect.html',{'page':'memory'})
    @app.get('/inspect',response_class=HTMLResponse)
    def inspect_page(request:Request): return templates.TemplateResponse(request,'inspect.html',{'page':'memory'})
    return app
app=create_app()
