#!/usr/bin/env python3
"""Exercise actual API authorization using short-lived ServiceAccount tokens."""
import base64,json,ssl,subprocess,urllib.request,urllib.error

def kubectl(*args):return subprocess.check_output(['kubectl',*args],text=True)
config=json.loads(kubectl('config','view','--raw','--minify','-o','json'))['clusters'][0]['cluster']
ctx=ssl.create_default_context(cadata=base64.b64decode(config['certificate-authority-data']).decode())
backend=json.loads(kubectl('get','pods','-n','demo','-l','app.kubernetes.io/name=application','-o','json'))['items'][0]['metadata']['name']
results=[]
for identity in ['baseline','namespace-reader','cluster-reader']:
 token=kubectl('create','token',identity+'-application','-n','demo','--duration=10m').strip()
 cases=[('list-own-pods','/api/v1/namespaces/demo/pods?limit=1',200 if identity!='baseline' else 403),('get-own-pod','/api/v1/namespaces/demo/pods/'+backend,200 if identity!='baseline' else 403),('watch-own-pods','/api/v1/namespaces/demo/pods?watch=true&timeoutSeconds=1',200 if identity!='baseline' else 403),('list-other-pods','/api/v1/namespaces/proxy/pods?limit=1',200 if identity=='cluster-reader' else 403),('list-all-pods','/api/v1/pods?limit=1',200 if identity=='cluster-reader' else 403),('read-secrets','/api/v1/namespaces/demo/secrets?limit=1',403),('create-pod','/api/v1/namespaces/demo/pods?dryRun=All',403)]
 for name,path,expected in cases:
  body=json.dumps({'apiVersion':'v1','kind':'Pod','metadata':{'name':'rbac-denied-probe'},'spec':{'containers':[{'name':'probe','image':'busybox:1.37.0'}]}}).encode() if name=='create-pod' else None
  req=urllib.request.Request(config['server'].rstrip('/')+path,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,context=ctx,timeout=10) as r:code=r.status;r.read()
  except urllib.error.HTTPError as e:code=e.code;e.read()
  results.append({'identity':identity,'test':name,'status':code,'expected':expected});assert code==expected,(identity,name,code,expected)
print(json.dumps({'results':results,'assertions_passed':len(results)},sort_keys=True))
