import base64,copy,datetime as dt,hashlib,hmac,json,urllib.request,urllib.error,xml.etree.ElementTree as ET
from runtime import *
e=Evidence('data');wait_contracts();v=values();fixture=json.loads((FOLDER/'fixture-values.json').read_text())
wait('S3 fixture ready',lambda:ready(pod('velero','app=s3-fixture')))
with Forward('velero','service/s3-fixture',9000,19090) as s3:
 def s3call(method,path):
  now=dt.datetime.now(dt.timezone.utc);stamp=now.strftime('%Y%m%dT%H%M%SZ');date=now.strftime('%Y%m%d');host='127.0.0.1:19090';payload=hashlib.sha256(b'').hexdigest();headers=f'host:{host}\nx-amz-content-sha256:{payload}\nx-amz-date:{stamp}\n';signed='host;x-amz-content-sha256;x-amz-date';canonical=method+'\n'+path+'\n\n'+headers+'\n'+signed+'\n'+payload;scope=date+'/us-east-1/s3/aws4_request';string='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
  key=('AWS4'+fixture['s3_secret_key']).encode()
  for part in [date,'us-east-1','s3','aws4_request']:key=hmac.new(key,part.encode(),hashlib.sha256).digest()
  sig=hmac.new(key,string.encode(),hashlib.sha256).hexdigest();auth='AWS4-HMAC-SHA256 Credential='+fixture['s3_access_key']+'/'+scope+', SignedHeaders='+signed+', Signature='+sig
  return s3.request(path,data=b'' if method=='PUT' else None,headers={'x-amz-content-sha256':payload,'x-amz-date':stamp,'Authorization':auth},method=method,statuses=(200,204))
 s3call('PUT','/velero-validation');e.record('local_authenticated_s3_bucket_created')
 wait_release('velero','velero')
 wait('Velero BSL available',lambda:get('backupstoragelocation','default','velero').get('status',{}).get('phase')=='Available',300)
 e.record('velero_consumes_eso_cloud_credentials',{'bsl':'default','phase':'Available','backend':'authenticated local SeaweedFS S3 fixture'})
 objects=[{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'velero-credential-check'}},{'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'credential-check','namespace':'velero-credential-check'},'data':{'status':'verified'}},{'apiVersion':'velero.io/v1','kind':'Backup','metadata':{'name':'eso-credential-backup','namespace':'velero'},'spec':{'includedNamespaces':['velero-credential-check'],'snapshotVolumes':False,'ttl':'1h0m0s'}}]
 result=subprocess.run(['kubectl','apply','-f','-'],input=json.dumps({'apiVersion':'v1','kind':'List','items':objects}),capture_output=True,text=True,timeout=25);assert result.returncode==0
 backup=wait('Velero backup completed',lambda:(x if (x:=get('backup','eso-credential-backup','velero')).get('status',{}).get('phase')=='Completed' else False),300)
 assert backup['status'].get('errors',0)==0
 _,xml=s3call('GET','/velero-validation');assert 'eso-credential-backup' in xml
 k('-n','velero-credential-check','delete','configmap','credential-check')
 restore={'apiVersion':'velero.io/v1','kind':'Restore','metadata':{'name':'eso-credential-restore','namespace':'velero'},'spec':{'backupName':'eso-credential-backup','restorePVs':False}}
 result=subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(restore),capture_output=True,text=True,timeout=20);assert result.returncode==0
 wait('Velero restore complete',lambda:get('restore','eso-credential-restore','velero').get('status',{}).get('phase')=='Completed',300)
 assert get('configmap','credential-check','velero-credential-check')['data']['status']=='verified'
 e.record('velero_real_object_backup_and_restore',{'backup':'Completed','restore':'Completed','restored_configmap':'verified','objects_observed_in_bucket':True})
wait_release('clickhouse-operator','databases')
wait('ClickHouse Ready',lambda:ready(get('clickhousecluster','clickhouse','databases')),600)
items=json.loads(k('-n','databases','get','pods','-o','json'))['items'];ch=next(p for p in items if any('clickhouse-server' in c['image'] for c in p['spec']['containers']))
password=v['clickhouse-auth']['password'];name=ch['metadata']['name']
def sql(query,password=password,check=True):return command(['kubectl','-n','databases','exec',name,'--','clickhouse-client','--password',password,'--query',query],check)
assert sql('SELECT 1','definitely-wrong',False).returncode!=0
assert sql('SELECT 1').stdout.strip()=='1'
sql('CREATE DATABASE IF NOT EXISTS eso_validation');sql('CREATE TABLE IF NOT EXISTS eso_validation.credentials (status String) ENGINE=MergeTree ORDER BY tuple()');sql("INSERT INTO eso_validation.credentials VALUES ('verified')")
assert sql('SELECT status FROM eso_validation.credentials LIMIT 1').stdout.strip()=='verified'
e.record('clickhouse_password_authentication_and_sql_round_trip',{'wrong_password_rejected':True,'eso_password_accepted':True,'write_and_read':True})
e.finish()
