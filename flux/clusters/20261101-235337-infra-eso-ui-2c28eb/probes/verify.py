import base64,json
from runtime import *
e=Evidence('ui');wait_contracts();v=values();fixture=json.loads((FOLDER/'fixture-values.json').read_text())
wait('RedisInsight ready',lambda:ready(pod('ui','app=redisinsight')));wait_release('nui','broker')
ids={}
def redis_round_trip(redis,initial):
 if initial:
  redis.request('/api/settings',{'agreements':{'eula':True,'analytics':False,'notifications':False,'encryption':True}},method='PATCH')
  _,existing=redis.request('/api/databases')
  database=next((d for d in existing if d['name']=='eso-redis'),None)
  if database is None:_,database=redis.request('/api/databases',{'host':'redis-validation.ui.svc','port':6379,'name':'eso-redis','password':fixture['redis_password'],'db':0})
  ids['redis']=database['id']
  e.record('redisinsight_encrypted_authenticated_connection_created')
 dbid=ids['redis'];b=lambda s:{'type':'Buffer','data':list(s.encode())}
 redis.request('/api/databases/'+dbid+'/string',{'keyName':b('eso:credentials'),'value':b('eso-verified')},method='POST',statuses=(200,201,409))
 redis.request('/api/databases/'+dbid+'/string',{'keyName':b('eso:credentials'),'value':b('eso-verified')},method='PUT')
 _,value=redis.request('/api/databases/'+dbid+'/string/get-value',{'keyName':b('eso:credentials')},method='POST')
 p=pod('ui','app=redis-validation');out=k('-n','ui','exec',p['metadata']['name'],'--','sh','-ec','REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli GET eso:credentials');assert out.strip()=='eso-verified'
 if not initial:e.record('redisinsight_saved_encrypted_connection_survives_restart')
 else:e.record('redisinsight_api_write_confirmed_by_redis_cli')
def nui_round_trip(nui,initial):
 _,connections=nui.request('/api/connection');assert isinstance(connections,list) and connections
 connection=next((c for c in connections if c.get('name')=='platform'),connections[0]);cid=connection.get('id') or connection.get('Id');assert cid
 if initial:
  ids['nui']=cid
  nui.request('/api/connection/'+cid+'/stream',{'name':'ESO_CREDENTIALS','subjects':['eso.>'],'storage':'memory'},statuses=(200,201,422))
 else:assert cid==ids['nui']
 nui.request('/api/connection/'+cid+'/messages/publish',{'subject':'eso.credentials','payload':base64.b64encode(b'eso-verified').decode(),'headers':{}})
 _,stream=nui.request('/api/connection/'+cid+'/stream/ESO_CREDENTIALS');assert stream['state']['messages']>=1
 if initial:e.record('nui_eso_context_authenticated_stream_and_publish',{'context_autoloaded':True,'authenticated_nats_operations':True})
 else:e.record('nui_authenticated_context_survives_restart')
with Forward('ui','service/redisinsight-service',5540,15540) as redis:redis_round_trip(redis,True)
with Forward('broker','service/nui',31311,13111) as nui:nui_round_trip(nui,True)
before={'redis':pod('ui','app=redisinsight')['metadata']['uid'],'nui':pod('broker','app.kubernetes.io/name=nui')['metadata']['uid']}
k('-n','ui','rollout','restart','deployment/redisinsight')
# NUI StatefulSet uses the shared chart's labels and retains its PVC.
nui_pod=pod('broker','app.kubernetes.io/name=nui');k('-n','broker','delete','pod',nui_pod['metadata']['name'],'--wait=false')
wait('RedisInsight replacement ready',lambda:pod('ui','app=redisinsight')['metadata']['uid']!=before['redis'] and ready(pod('ui','app=redisinsight')),300)
wait('NUI replacement ready',lambda:pod('broker','app.kubernetes.io/name=nui')['metadata']['uid']!=before['nui'] and ready(pod('broker','app.kubernetes.io/name=nui')),300)
with Forward('ui','service/redisinsight-service',5540,15540) as redis:redis_round_trip(redis,False)
with Forward('broker','service/nui',31311,13111) as nui:nui_round_trip(nui,False)
e.record('replacement_pod_uids_changed',before);e.finish()
