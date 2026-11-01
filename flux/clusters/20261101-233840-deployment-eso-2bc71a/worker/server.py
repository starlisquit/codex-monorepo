import hashlib,http.server,json,os,pathlib,stat
class H(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  try:
   mode=os.environ['DELIVERY_MODE'];extra={}
   if mode=='eso':value=os.environ['APP_PASSWORD']
   else:
    p=pathlib.Path('/vault/secrets/config.json');value=json.loads(p.read_text())['APP_PASSWORD'];s=p.stat();extra={'file_mode':oct(stat.S_IMODE(s.st_mode)),'file_uid':s.st_uid}
   body=json.dumps({'sha256':hashlib.sha256(value.encode()).hexdigest(),'mode':mode,'uid':os.getuid(),**extra}).encode();self.send_response(200)
  except Exception:body=b'{"error":"credential unavailable"}';self.send_response(503)
  self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
http.server.ThreadingHTTPServer(('0.0.0.0',8080),H).serve_forever()
