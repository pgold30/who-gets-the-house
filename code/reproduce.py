"""Versioned offline analysis-to-paper master. Original raw build is separate."""
import os,sys,subprocess,json,time,platform,hashlib,datetime,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['MPLCONFIGDIR']=str(ROOT/'tmp/matplotlib')
OUT=ROOT/'results';OUT.mkdir(exist_ok=True);LOG=OUT/'stage_logs';LOG.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'release':'WGTH-2026-09-10-JHE-S1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'scope':'Supplied archived inputs and preserved public extracts to current paper; original full raw-to-panel build not executed.','source_sha256':{str(p.relative_to(ROOT)):sha(p) for folder in ['code','inputs'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)},'stages':[]}
manifest['mode']='from-results' if '--from-results' in sys.argv else 'full-analysis'
start=time.monotonic()
programs=['parse_rates.py','analyze_repeat_sales.py','analyze_coop_audit.py','analyze_notches.py','additional_checks.py','notch_sample_checks.py','property_comparison.py','make_review_queues.py','check_reform_design.py','build_exhibits.py','build_targeted_supplement.py','build_support_documents.py']
if '--from-results' in sys.argv:
    programs=['build_exhibits.py','build_targeted_supplement.py','build_support_documents.py']
try:
    for name in programs:
        t=time.monotonic();print('RUN',name,flush=True)
        with (LOG/(name+'.log')).open('w') as f:subprocess.run([sys.executable,str(ROOT/'code'/name)],cwd=ROOT,env=os.environ,stdout=f,stderr=subprocess.STDOUT,check=True)
        elapsed=time.monotonic()-t;manifest['stages'].append({'program':name,'seconds':elapsed,'status':'passed'});print('PASS',name,round(elapsed,2),'seconds',flush=True)
    tectonic=shutil.which('tectonic')
    if not tectonic:raise RuntimeError('Install Tectonic to compile paper/paper.tex; numerical analysis completed.')
    t=time.monotonic()
    with (LOG/'tectonic.log').open('w') as f:subprocess.run([tectonic,str(ROOT/'paper/paper.tex')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    manifest['stages'].append({'program':'tectonic paper/paper.tex','seconds':time.monotonic()-t,'status':'passed'})
    with (LOG/'submission_documents.log').open('w') as f:subprocess.run([sys.executable,str(ROOT/'code/build_submission_documents.py')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    manifest['stages'].append({'program':'build_submission_documents.py','status':'passed'})
    manifest['status']='passed'
except Exception as e:
    manifest['status']='failed';manifest['error']=repr(e);raise
finally:
    manifest['seconds_total']=time.monotonic()-start;manifest['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
print('PASS consolidated build; consult run_manifest.json for full-analysis versus from-results mode.',flush=True)
