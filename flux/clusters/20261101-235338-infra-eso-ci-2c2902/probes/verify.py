import json,re,urllib.parse,urllib.request
from pathlib import Path
from runtime import *
e=Evidence('ci');wait_contracts();v=values();state=json.loads((Path.home()/'gitlab-state.json').read_text());token=v['renovate-credentials']['RENOVATE_TOKEN'];pid=state['project_id']
def api(path):
 req=urllib.request.Request('https://gitlab.com/api/v4/'+path,headers={'PRIVATE-TOKEN':token})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
wait_release('gitlab-runner','ci');wait_release('renovate','ci')
runner=wait('runner online',lambda:(x if (x:=api('runners/'+str(state['runner_id'])))['status']=='online' else False),300)
e.record('runner_authenticated_online',{'runner_id':state['runner_id'],'status':runner['status']})
def pipeline_ready():
 entries=api(f'projects/{pid}/pipelines?ref=infra-eso-validation-20261101')
 return entries[0] if entries and entries[0]['status']=='success' else False
pipeline=wait('real GitLab pipeline',pipeline_ready,600)
jobs=api(f'projects/{pid}/pipelines/{pipeline["id"]}/jobs');assert len(jobs)==1 and jobs[0]['status']=='success' and jobs[0]['runner']['id']==state['runner_id']
e.record('real_kubernetes_executor_job',{'pipeline_id':pipeline['id'],'job_id':jobs[0]['id'],'runner_id':jobs[0]['runner']['id'],'status':'success'})
p=pod('ci','app=gitlab-runner');cfg=k('-n','ci','exec',p['metadata']['name'],'--','cat','/home/gitlab-runner/.gitlab-runner/config.toml')
assert re.search(r'concurrent\s*=\s*5',cfg) and re.search(r'limit\s*=\s*5',cfg);e.record('effective_concurrency_defaults',{'concurrent':5,'runner_limit':5})
k('-n','ci','create','job','renovate-eso-validation','--from=cronjob/renovate')
wait('Renovate completed',lambda:get('job','renovate-eso-validation','ci').get('status',{}).get('succeeded')==1,900)
log=k('-n','ci','logs','job/renovate-eso-validation');(FOLDER/'renovate-private.log').write_text(log)
assert 'Repository finished' in log and ('depCount' in log or 'packageFiles' in log or 'Package files' in log)
e.record('renovate_authenticated_dry_run',{'job':'renovate-eso-validation','completed':True,'repository_finished':True,'extraction_summary_present':True,'github_lookup_warning':'GitHub' in log or 'github.com' in log})
e.finish()
