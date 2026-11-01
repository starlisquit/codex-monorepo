#!/usr/bin/env python3
"""Observe real CronJob scheduling, successful work and Forbid skip events."""
import datetime,json,subprocess,time
from pathlib import Path
out=Path('/tmp/cronjob-evidence.json');samples=[]
def get(resource):
 return json.loads(subprocess.check_output(['kubectl','get',resource,'-n','demo','-o','json'],text=True,stderr=subprocess.DEVNULL,timeout=10))
for attempt in range(100):
 try:
  cron=get('cronjob/scheduled-scheduled-task');uid=cron['metadata']['uid'];jobs=[j for j in get('jobs')['items'] if any(x.get('uid')==uid for x in j['metadata'].get('ownerReferences',[]))]
  active=sum(j.get('status',{}).get('active',0) for j in jobs);success=[j for j in jobs if j.get('status',{}).get('succeeded',0)>0]
  assert active<=1,active
  samples.append({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'active':active,'successful':len(success),'jobs':[j['metadata']['name'] for j in jobs]})
  events=[e for e in get('events')['items'] if e.get('involvedObject',{}).get('uid')==uid and e.get('reason')=='JobAlreadyActive']
  evidence={'samples':samples,'forbid_events':[{'reason':e['reason'],'message':e.get('message'),'count':e.get('count')} for e in events],'successful_jobs':[{'name':j['metadata']['name'],'start':j['status'].get('startTime'),'completion':j['status'].get('completionTime')} for j in success],'cronjob_status':cron.get('status',{})}
  out.write_text(json.dumps(evidence,indent=2)+'\n')
  if events and success:
   print(json.dumps({'passed':True,'max_active':max(s['active'] for s in samples),'forbid_event_count':len(events),'successful_jobs':len(success)}),flush=True);break
 except subprocess.SubprocessError:pass
 time.sleep(5)
else:raise SystemExit('Timed out waiting for successful scheduling and Forbid event')
