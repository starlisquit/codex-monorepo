import base64,json,urllib.parse
from runtime import *
e=Evidence('apps');wait_contracts();v=values();wait_release('litellm','ai');wait_release('sonarqube','quality')
master=v['litellm-auth']['master-key'];headers={'Authorization':'Bearer '+master}
with Forward('ai','service/litellm',4000,14000) as llm:
 status,_=llm.request('/models',statuses=(401,));assert status==401
 _,models=llm.request('/models',headers=headers);assert any(x['id']=='validation-model' for x in models['data'])
 _,response=llm.request('/chat/completions',{'model':'validation-model','messages':[{'role':'user','content':'credential-delivery-test'}]},headers=headers)
 assert response['choices'][0]['message']['content']=='proxy-route-verified'
 e.record('litellm_master_key_and_provider_credentials',{'unauthorized_http':401,'authenticated_models':True,'authenticated_upstream_fixture_request':True})
with Forward('quality','service/sonarqube-sonarqube',9000,19000) as sonar:
 wait('SonarQube UP',lambda:sonar.request('/api/system/status')[1].get('status')=='UP',600)
 status,_=sonar.request('/api/system/health',statuses=(401,403));assert status in [401,403]
 _,health=sonar.request('/api/system/health',headers={'X-Sonar-Passcode':v['sonarqube-monitoring']['passcode']});assert 'health' in health
 e.record('sonarqube_monitoring_passcode',{'without_passcode_rejected':True,'with_passcode_authenticated':True})
 admin={'Authorization':'Basic '+base64.b64encode(b'admin:admin').decode(),'Content-Type':'application/x-www-form-urlencoded'}
 _,valid=sonar.request('/api/authentication/validate',headers=admin);assert valid['valid']
 payload=urllib.parse.urlencode({'project':'eso-credential-verification','name':'ESO Credential Verification'}).encode()
 _,project=sonar.request('/api/projects/create',payload,admin);assert project['project']['key']=='eso-credential-verification'
 _,projects=sonar.request('/api/projects/search?projects=eso-credential-verification',headers=admin);assert projects['components'][0]['key']=='eso-credential-verification'
 e.record('sonarqube_database_password_and_database_round_trip',{'project_created_and_read':True,'database_mode':'external PostgreSQL fixture, no CNPG ownership'})
pg=pod('quality','app=sonarqube-postgresql');out=k('-n','quality','exec',pg['metadata']['name'],'--','sh','-ec','PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U sonarqube -d sonarqube -Atc "SELECT count(*) FROM projects"')
assert int(out.strip())>=1;e.record('postgresql_independent_persisted_project_check')
e.finish()
