from __future__ import annotations
from pathlib import Path
from decimal import Decimal,InvalidOperation
import hashlib,json,sqlite3,time,urllib.request,urllib.error,re,platform
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
PROMPTS={
 'direct':'Solve the problem. Give only the final numerical answer in the format #### NUMBER.',
 'reasoned':'Solve the problem step by step. End with the final numerical answer in the format #### NUMBER.'}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def extract(text):
    """Strict final-line delimiter. Never guess from numbers in reasoning."""
    match=re.search(r'(?:^|\n)\s*####\s*([$]?-?[\d,]+(?:\.\d+)?)\s*$',text)
    if not match:return None
    try:return str(Decimal(match[1].replace(',','').replace('$','')).normalize())
    except InvalidOperation:return None
def request(url,body=None,timeout=120):
    raw=None if body is None else json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json'}),timeout=timeout) as r:return json.load(r)
def model_digest(base,model):
    for row in request(base+'/api/tags')['models']:
        if row['name']==model:return row['digest']
    raise ValueError('Model not installed; run ollama pull '+model)
def dataset(path,count,seed):
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    ids=np.random.default_rng(seed).choice(len(rows),count,replace=False).tolist()
    return [{'id':i,'question':rows[i]['question'],'target':extract(rows[i]['answer'])} for i in sorted(ids)]
class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,manifest TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS tasks(run TEXT,qid INTEGER,condition TEXT,seed INTEGER,
                question TEXT,target TEXT,status TEXT DEFAULT 'pending',lease REAL DEFAULT 0,
                attempts INTEGER DEFAULT 0,response TEXT,error TEXT,latency REAL,tokens INTEGER,
                PRIMARY KEY(run,qid,condition,seed));
            ''')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row;db.execute('PRAGMA journal_mode=WAL');return db
    def initialize(self,manifest,questions):
        run=digest(manifest)[:20]
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO runs VALUES(?,?)',(run,canonical(manifest)))
            for q in questions:
                for condition in manifest['conditions']:
                    for seed in manifest['seeds']:
                        db.execute('INSERT OR IGNORE INTO tasks(run,qid,condition,seed,question,target) VALUES(?,?,?,?,?,?)',(run,q['id'],condition,seed,q['question'],q['target']))
        return run
    def claim(self,run,lease_seconds=180):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE tasks SET status='pending' WHERE run=? AND status='running' AND lease<?",(run,time.time()))
            row=db.execute("SELECT * FROM tasks WHERE run=? AND status='pending' ORDER BY qid,condition,seed LIMIT 1",(run,)).fetchone()
            if row is None:return None
            db.execute("UPDATE tasks SET status='running',lease=?,attempts=attempts+1 WHERE run=? AND qid=? AND condition=? AND seed=?",(time.time()+lease_seconds,run,row['qid'],row['condition'],row['seed']))
            claimed=dict(row);claimed['attempts']+=1
            return claimed
    def finish(self,row,response=None,error=None,latency=0,tokens=0):
        with self.connect() as db:
            cursor=db.execute("UPDATE tasks SET status=?,response=?,error=?,latency=?,tokens=?,lease=0 WHERE run=? AND qid=? AND condition=? AND seed=? AND status='running' AND attempts=?",
                ('failed' if error else 'completed',response,error,latency,tokens,row['run'],row['qid'],row['condition'],row['seed'],row['attempts']))
            if cursor.rowcount!=1:raise RuntimeError('Stale task lease: result rejected')
    def rows(self,run):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM tasks WHERE run=? ORDER BY qid,condition,seed',(run,))]
    def manifest(self,run):
        with self.connect() as db:
            row=db.execute('SELECT manifest FROM runs WHERE id=?',(run,)).fetchone()
            if row is None:raise ValueError('Unknown run')
            return json.loads(row[0])
def run_tasks(store,run,adapter=None):
    manifest=store.manifest(run)
    if adapter is None and model_digest(manifest['base_url'],manifest['model'])!=manifest['model_digest']:
        raise ValueError('Installed model digest changed; create a new run')
    while row:=store.claim(run,manifest.get('timeout',120)+60):
        started=time.perf_counter()
        try:
            if adapter:
                result=adapter(row)
            else:
                prompt=PROMPTS[row['condition']]+'\n\n'+row['question']
                result=request(manifest['base_url']+'/api/generate',{'model':manifest['model'],'prompt':prompt,'stream':False,'think':manifest['think'],'options':{'seed':row['seed'],'temperature':manifest['temperature'],'num_predict':manifest['num_predict'],'num_ctx':manifest['num_ctx']}},manifest.get('timeout',120))
            store.finish(row,response=result['response'],latency=time.perf_counter()-started,tokens=result.get('eval_count',0))
        except (urllib.error.URLError,TimeoutError,KeyError) as e:
            store.finish(row,error=type(e).__name__+': '+str(e),latency=time.perf_counter()-started)
        print(f"{row['qid']} {row['condition']} saved",flush=True)
    return make_report(store,run)
def make_report(store,run):
    rows=store.rows(run);manifest=store.manifest(run);summaries={}
    for row in rows:
        row['extracted']=extract(row['response'] or '')
        row['correct']=row['status']=='completed' and row['extracted'] is not None and row['extracted']==row['target']
    for condition in manifest['conditions']:
        subset=[r for r in rows if r['condition']==condition];completed=[r for r in subset if r['status']=='completed']
        summaries[condition]={'scheduled':len(subset),'completed':len(completed),'failed':sum(r['status']=='failed' for r in subset),
            'pending_or_running':sum(r['status'] in ['pending','running'] for r in subset),
            'correct':sum(r['correct'] for r in subset),'task_success':sum(r['correct'] for r in subset)/len(subset),
            'accuracy_on_completed':sum(r['correct'] for r in completed)/len(completed) if completed else None,
            'extraction_failures':sum(r['extracted'] is None for r in completed),
            'p50_seconds':float(np.median([r['latency'] for r in completed])) if completed else None,
            'tokens':sum(r['tokens'] or 0 for r in completed)}
    paired=None
    if len(manifest['conditions'])==2:
        a,b=manifest['conditions'];deltas=[]
        for qid in sorted({r['qid'] for r in rows}):
            left=[r['correct'] for r in rows if r['qid']==qid and r['condition']==a]
            right=[r['correct'] for r in rows if r['qid']==qid and r['condition']==b]
            deltas.append(float(np.mean(right)-np.mean(left)))
        rng=np.random.default_rng(42);values=np.asarray(deltas)
        samples=values[rng.integers(0,len(values),(2000,len(values)))].mean(axis=1)
        paired={'difference':float(values.mean()),'ci95':np.quantile(samples,[.025,.975]).tolist(),'unit':'question','comparison':b+' minus '+a,'n_questions':len(values)}
    report={'run_id':run,'manifest':manifest,'summary':summaries,'paired':paired,'responses':rows,
            'limitations':['Small public benchmark subset; potential training contamination','Single recorded seed per condition unless manifest says otherwise','Token extraction is separate from model correctness','Incomplete tasks count against scheduled task success']}
    folder=ROOT/'reports'/run;folder.mkdir(parents=True,exist_ok=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (folder/'responses.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    (ROOT/'reports'/'latest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
def download():
    source=request('https://api.github.com/repos/openai/grade-school-math/commits/master')['sha']
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    url='https://raw.githubusercontent.com/openai/grade-school-math/'+source+'/grade_school_math/data/test.jsonl'
    raw=urllib.request.urlopen(url).read();(folder/'test.jsonl').write_bytes(raw)
    license_url='https://raw.githubusercontent.com/openai/grade-school-math/'+source+'/LICENSE'
    (folder/'GSM8K-LICENSE.txt').write_bytes(urllib.request.urlopen(license_url).read())
    (folder/'manifest.json').write_text(json.dumps({'url':url,'revision':source,'sha256':hashlib.sha256(raw).hexdigest(),'license':'MIT'},indent=2))
def start(model,count=20,base='http://localhost:11434'):
    path=ROOT/'data'/'test.jsonl';questions=dataset(path,count,42)
    manifest={'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'question_ids':[q['id'] for q in questions],
        'prompts':PROMPTS,'conditions':list(PROMPTS),'seeds':[42],'model':model,'model_digest':model_digest(base,model),
        'base_url':base,'temperature':.6,'num_predict':512,'num_ctx':4096,'think':False,'timeout':120,
        'scorer':'strict-final-line-v1','platform':platform.platform(),'ollama_version':request(base+'/api/version')['version'],
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    store=Store(ROOT/'data'/'runs.sqlite');run=store.initialize(manifest,questions)
    report=run_tasks(store,run);print(json.dumps(report['summary'],indent=2));return report
