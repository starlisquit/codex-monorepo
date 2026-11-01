"""Run verified SQL against the DB services with app credentials kept in memory."""
import base64,json,subprocess

def get(kind,name,ns):return json.loads(subprocess.check_output(['kubectl','get',kind,name,'-n',ns,'-o','json']))
results=[]
for ns,name,user in [('ai','litellm-db','litellm'),('quality','sonarqube-postgresql','sonarqube')]:
 cluster=get('cluster',name,ns);pod=cluster['status']['currentPrimary'];secret=get('secret',name+'-app',ns)['data'];password=base64.b64decode(secret['password']).decode();ca=get('configmap','platform-ca',ns)['data']['ca.crt'];host=name+'-rw.'+ns+'.svc.cluster.local'
 script='''IFS= read -r PGPASSWORD; export PGPASSWORD
psql "host='''+host+' user='+user+' dbname='+user+''' sslmode=verify-full sslrootcert=/controller/certificates/server-ca.crt" -X -v ON_ERROR_STOP=1 -At <<'SQL'
CREATE TABLE IF NOT EXISTS central_pki_validation (id integer PRIMARY KEY, value text);
INSERT INTO central_pki_validation VALUES (1, 'central-ca-verified') ON CONFLICT (id) DO NOTHING;
SELECT value FROM central_pki_validation WHERE id=1;
SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT count(*) FROM pg_stat_replication;
SQL
'''
 proc=subprocess.run(['kubectl','exec','-i','-n',ns,pod,'-c','postgres','--','sh','-ec',script],input=password+'\n'+base64.b64encode(ca.encode()).decode()+'\n',text=True,capture_output=True)
 assert proc.returncode==0,proc.stderr
 assert 'central-ca-verified' in proc.stdout and 't|TLSv1.3' in proc.stdout,proc.stdout
 results.append({'namespace':ns,'cluster':name,'primary':pod,'sql':proc.stdout.strip(),'ready_instances':cluster['status'].get('readyInstances'),'desired_instances':cluster['spec']['instances']})
print(json.dumps(results))
