"""Exercise real conversion/scraping, namespace isolation and Pod replacement."""
import copy,datetime,json,subprocess,time,urllib.request,urllib.parse
from pathlib import Path

def kube(*args):return subprocess.check_output(['kubectl',*args],text=True)
def get(kind,name,ns):return json.loads(kube('get',kind,name,'-n',ns,'-o','json'))
def query(q):return json.load(urllib.request.urlopen('http://127.0.0.1:18428/api/v1/query?query='+urllib.parse.quote(q),timeout=10))['data']['result']
def targets():
 alltargets=json.load(urllib.request.urlopen('http://127.0.0.1:18429/api/v1/targets',timeout=10))['data']['activeTargets']
 return [{'labels':t['labels'],'pool':t['scrapePool'],'url':t['scrapeUrl'],'health':t['health'],'error':t['lastError'],'last_scrape':t['lastScrape']} for t in alltargets if '/applications/' in t['scrapePool']]
def wait(fn,timeout=180):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(2)
 raise RuntimeError('Timed out waiting for scrape condition')
def patch(kind,name,ns,payload):return kube('patch',kind,name,'-n',ns,'--type=merge','-p',json.dumps(payload))
def healthy():
 t=targets();return t if len(t)==2 and all(x['health']=='up' and not x['error'] for x in t) else None
before=wait(healthy);assert {x['labels']['namespace'] for x in before}=={'applications'}
initial=query('template_probe{pod=~"'+('|'.join(t['labels']['pod'] for t in before))+'"}');assert len(initial)==2 and {x['metric']['app'] for x in initial}=={'api','worker'}
decoys=[]
for app in ['api','worker']:
 d=get('deployment',app+'-application','applications');spec=copy.deepcopy(d['spec']['template']['spec']);spec['restartPolicy']='Never';spec['containers'][0]['env']=[{'name':'APP_ID','value':'decoy-'+app}]
 decoys.append({'apiVersion':'v1','kind':'Pod','metadata':{'name':'metrics-decoy-'+app,'namespace':'default','labels':{'app.kubernetes.io/name':app}},'spec':spec})
decoys.append({'apiVersion':'v1','kind':'Service','metadata':{'name':'metrics-decoy-api','namespace':'default','labels':{'app.kubernetes.io/name':'api','app.kubernetes.io/component':'metrics'}},'spec':{'selector':{'app.kubernetes.io/name':'api'},'ports':[{'name':'metrics','port':8081,'targetPort':'metrics'}]}})
subprocess.run(['kubectl','apply','-f','-'],input=json.dumps({'apiVersion':'v1','kind':'List','items':decoys}),text=True,check=True)
kube('wait','--for=condition=Ready','pod/metrics-decoy-api','pod/metrics-decoy-worker','-n','default','--timeout=45s')
time.sleep(35);assert query('template_probe{app=~"decoy-.*"}')==[];assert len(wait(healthy))==2
# Freeze just this disposable workload's reconciliation during a negative selector test.
patch('kustomization','api','flux-system',{'spec':{'suspend':True}})
try:
 patch('servicemonitor','api-application','applications',{'spec':{'selector':{'matchLabels':{'app.kubernetes.io/name':'worker'}}}})
 def missing_target():
  now=targets();return now if len(now)==1 and now[0]['pool'].startswith('podScrape/') else None
 missing=wait(missing_target)
 assert missing[0]['health']=='up'
finally:
 patch('servicemonitor','api-application','applications',{'spec':{'selector':{'matchLabels':{'app.kubernetes.io/name':'api'}}}})
 patch('kustomization','api','flux-system',{'spec':{'suspend':False}})
restored=wait(healthy);oldpods={x['labels']['pod'] for x in restored}
kube('rollout','restart','deployment/api-application','deployment/worker-application','-n','applications')
for app in ['api','worker']:kube('rollout','status','deployment/'+app+'-application','-n','applications','--timeout=90s')
def replaced_targets():
 now=healthy();return now if now and all(x['labels']['pod'] not in oldpods for x in now) else None
after=wait(replaced_targets)
podregex='|'.join(x['labels']['pod'] for x in after)
def current_metrics():
 now=query('template_probe{pod=~"'+podregex+'"}');return now if len(now)==2 else None
current=wait(current_metrics)
assert {m['metric']['app'] for m in current}=={'api','worker'} and all(m['value'][1]=='1' for m in current)
assert query('template_probe{app=~"decoy-.*"}')==[]
evidence={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'initial_targets':before,'initial_metrics':initial,'cross_namespace_decoys_scraped':False,'broken_selector_failed_closed':True,'worker_remained_up_during_negative_test':True,'restored_targets':restored,'after_rollout_targets':after,'after_rollout_metrics':current,'decoy_resources':[{'kind':d['kind'],'name':d['metadata']['name'],'namespace':'default'} for d in decoys]}
Path('/tmp/monitor-runtime-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps({'passed':True,'monitor_types':['ServiceMonitor','PodMonitor'],'active_application_targets':len(after),'namespace_isolation':True,'negative_selector_test':True,'pod_replacement':True}),flush=True)
