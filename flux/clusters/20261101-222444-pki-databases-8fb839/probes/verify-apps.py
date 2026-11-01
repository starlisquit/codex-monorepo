"""Application DB round trips; secrets remain in an owner-only disposable lab file."""
import base64,json,os,secrets,subprocess,sys,urllib.request,urllib.parse
from pathlib import Path
os.umask(0o077);statefile=Path('/home/laborant/.config/pki-validation/apps.json');statefile.parent.mkdir(parents=True,exist_ok=True)
state=json.loads(statefile.read_text()) if statefile.exists() else {}
def api(base,path,token=None,data=None,basic=None,form=False):
 body=(urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()) if data is not None else None
 headers={}
 if token:headers['Authorization']='Bearer '+token
 if basic:headers['Authorization']='Basic '+base64.b64encode(basic.encode()).decode()
 if body is not None:headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
 with urllib.request.urlopen(urllib.request.Request(base+path,data=body,headers=headers),timeout=30) as r:
  content=r.read();return json.loads(content) if content else None
secret=json.loads(subprocess.check_output(['kubectl','get','secret','litellm-auth','-n','ai','-o','json']))['data'];master=base64.b64decode(secret['master-key']).decode()
readiness=api('http://127.0.0.1:14000','/health/readiness',token=master)
if 'virtual_key' not in state:
 response=api('http://127.0.0.1:14000','/key/generate',token=master,data={'models':['validation-model'],'duration':'1h','key_alias':'central-pki-validation'});state['virtual_key']=response['key'];statefile.write_text(json.dumps(state));statefile.chmod(0o600)
chat=api('http://127.0.0.1:14000','/v1/chat/completions',token=state['virtual_key'],data={'model':'validation-model','messages':[{'role':'user','content':'verify centralized database PKI'}]});assert chat['choices'][0]['message']['content']=='proxy-route-verified'
status=api('http://127.0.0.1:19000','/api/system/status');assert status['status']=='UP',status
if 'sonar_password' not in state:
 password=secrets.token_urlsafe(24)+"Aa1!";api('http://127.0.0.1:19000','/api/users/change_password',basic='admin:admin',data={'login':'admin','previousPassword':'admin','password':password},form=True);state['sonar_password']=password;statefile.write_text(json.dumps(state));statefile.chmod(0o600)
basic='admin:'+state['sonar_password'];valid=api('http://127.0.0.1:19000','/api/authentication/validate',basic=basic);assert valid['valid']
projects=api('http://127.0.0.1:19000','/api/projects/search?projects=central-pki-validation',basic=basic)
if not projects['components']:
 assert len(sys.argv)<2 or sys.argv[1]!='after', 'Project disappeared after renewal/failover'
 api('http://127.0.0.1:19000','/api/projects/create',basic=basic,data={'project':'central-pki-validation','name':'Central PKI verification'},form=True)
 projects=api('http://127.0.0.1:19000','/api/projects/search?projects=central-pki-validation',basic=basic)
assert len(projects['components'])==1
print(json.dumps({'litellm_readiness':readiness,'litellm_model_reply':chat['choices'][0]['message']['content'],'virtual_key_persisted':True,'sonarqube_status':status['status'],'sonarqube_version':status['version'],'sonarqube_project':projects['components'][0]['key'],'sonarqube_login_valid':valid['valid']}))
