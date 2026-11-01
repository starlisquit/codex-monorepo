"""Test central leaf renewal, replication, failover and application reconnection."""
import datetime,json,subprocess,time
from pathlib import Path
pairs=[('ai','litellm-db'),('quality','sonarqube-postgresql')]
def kube(*args):return subprocess.check_output(['kubectl',*args],text=True)
def get(kind,name,ns):return json.loads(kube('get',kind,*([name] if name else []),'-n',ns,'-o','json'))
def sql():return json.loads(subprocess.check_output(['python3','/home/laborant/verify-sql.py'],text=True))
def apps(after=False):return json.loads(subprocess.check_output(['python3','/home/laborant/verify-apps.py']+(['after'] if after else []),text=True))
def pods():return {p['metadata']['name']:p['metadata']['uid'] for ns,db in pairs for p in get('pods','',ns)['items'] if p['metadata'].get('labels',{}).get('cnpg.io/cluster')==db and p['status']['phase']=='Running'}
targets=[{'name':name,'host':name+'-rw.'+ns+'.svc.cluster.local','port':5432,'server_name':name+'-rw.'+ns+'.svc.cluster.local','postgres':True} for ns,name in pairs]
def tls():return json.loads(kube('exec','-n','ai','pki-probe','--','python','/scripts/verify-tls.py',json.dumps(targets)))
before={'sql':sql(),'apps':apps(),'tls':tls(),'pods':pods()};Path('/tmp/databases-before.json').write_text(json.dumps(before,indent=2)+'\n')
for ns,_ in pairs:subprocess.run(['/home/laborant/cmctl','renew','--all','-n',ns],check=True)
serials={x['name']:x['serial'] for x in before['tls']['results']};end=time.monotonic()+240
while time.monotonic()<end:
 try:
  aftertls=tls()
  if all(x['serial']!=serials[x['name']] for x in aftertls['results']):break
 except subprocess.SubprocessError:pass
 time.sleep(5)
else:raise SystemExit('PostgreSQL did not reload the renewed server certificates')
after_renewal={'sql':sql(),'apps':apps(True),'tls':aftertls,'pods':pods()};assert after_renewal['pods']==before['pods'],'Database restarted during leaf renewal';assert aftertls['root_sha256']==before['tls']['root_sha256']
oldprimaries={db:get('cluster',db,ns)['status']['currentPrimary'] for ns,db in pairs}
for ns,db in pairs:kube('delete','pod',oldprimaries[db],'-n',ns,'--wait=false')
end=time.monotonic()+240
while time.monotonic()<end:
 clusters=[get('cluster',db,ns) for ns,db in pairs]
 if all(c['status'].get('currentPrimary')!=oldprimaries[c['metadata']['name']] and c['status'].get('readyInstances')==2 and any(x['type']=='Ready' and x['status']=='True' for x in c['status'].get('conditions',[])) for c in clusters):break
 time.sleep(3)
else:raise SystemExit('Database failover/replica recovery did not complete')
# Applications can need a few retries to replace old pooled DB connections.
end=time.monotonic()+90
while True:
 try:afterapps=apps(True);break
 except subprocess.SubprocessError:
  if time.monotonic()>end:raise
  time.sleep(3)
after_failover={'sql':sql(),'apps':afterapps,'tls':tls(),'new_primaries':{db:get('cluster',db,ns)['status']['currentPrimary'] for ns,db in pairs}}
for row in after_failover['sql']:assert row['ready_instances']==row['desired_instances']==2
out={'passed':True,'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before':before,'after_renewal':after_renewal,'after_failover':after_failover,'old_primaries':oldprimaries,'hot_reload_without_database_restart':True,'root_unchanged':True};Path('/tmp/databases-runtime-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'clusters':len(pairs),'renewed_serving_serials':True,'hot_reload_without_database_restart':True,'failover':True,'applications_reconnected':True}),flush=True)
