import concurrent.futures, http.server, json, socket, ssl, threading
from pathlib import Path
import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
class HTTP(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'http:primitive-runtime-ok\n')
 def log_message(self,*args): pass
def echo(port,tls=False,udp=False):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if udp else socket.SOCK_STREAM);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('0.0.0.0',port))
 if udp:
  while True:
   data,peer=s.recvfrom(1024);s.sendto(b'udp:'+data,peer)
 else:
  s.listen()
  ctx=None
  if tls:
   ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain('/tls/tls.crt','/tls/tls.key')
  while True:
   c,_=s.accept()
   try:
    c.settimeout(5)
    if ctx:c=ctx.wrap_socket(c,server_side=True)
    data=c.recv(1024);c.sendall((b'tls:' if tls else b'tcp:')+data)
   except (ssl.SSLError,TimeoutError,OSError):pass
   finally:c.close()
for args in [(5432,False,False),(8443,True,False),(5353,False,True)]:threading.Thread(target=echo,args=args,daemon=True).start()
s=grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=2));h=health.HealthServicer();h.set('primitive-runtime',health_pb2.HealthCheckResponse.SERVING);health_pb2_grpc.add_HealthServicer_to_server(h,s);s.add_insecure_port('[::]:50051');s.start()
print(json.dumps({'ready_protocols':['HTTP','gRPC','TLS','TCP','UDP']}),flush=True)
http.server.ThreadingHTTPServer(('0.0.0.0',8080),HTTP).serve_forever()
