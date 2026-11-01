"""TLS trust/identity probes. Config and results contain no signing/private keys."""
import hashlib,json,socket,ssl,struct,sys
CA='/ca/ca.crt';root=ssl._ssl._test_decode_cert(CA)
fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(open(CA).read())).hexdigest()
def connect(target,ctx,hostname):
 s=socket.create_connection((target['host'],target['port']),timeout=5)
 if target.get('postgres'):
  s.sendall(struct.pack('!II',8,80877103));assert s.recv(1)==b'S'
 return ctx.wrap_socket(s,server_hostname=hostname)
def context(target,trust=True,client=True):
 ctx=ssl.create_default_context(cafile=CA) if trust else ssl.create_default_context()
 if target.get('client') and client:ctx.load_cert_chain('/client/tls.crt','/client/tls.key')
 return ctx
results=[]
for t in json.loads(sys.argv[1]):
 with connect(t,context(t),t['server_name']) as s:
  peer=s.getpeercert();assert peer['issuer']==root['subject'],(t['name'],'not signed directly by central root')
  result={'name':t['name'],'server_name':t['server_name'],'serial':peer['serialNumber'],'issuer':peer['issuer'],'tls_version':s.version(),'not_after':peer['notAfter']}
 for mode in ['wrong_ca','wrong_hostname']:
  try:
   with connect(t,context(t,trust=mode!='wrong_ca'),'wrong.invalid' if mode=='wrong_hostname' else t['server_name']):pass
   raise AssertionError((t['name'],mode,'was accepted'))
  except ssl.SSLCertVerificationError as error:result[mode]={'rejected':True,'reason':error.verify_message}
 if t.get('mtls'):
  try:
   with connect(t,context(t,client=False),t['server_name']) as s:
    s.sendall(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n');data=s.recv(64)
    if data:raise AssertionError((t['name'],'accepted a client without a certificate'))
   result['missing_client_certificate_rejected']=True
  except (ssl.SSLError,ConnectionResetError):result['missing_client_certificate_rejected']=True
 results.append(result)
print(json.dumps({'root_sha256':fingerprint,'results':results},sort_keys=True))
