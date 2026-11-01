import grpc,json,socket,ssl,sys,urllib.request
from grpc_health.v1 import health_pb2,health_pb2_grpc
host=sys.argv[1];out={}
r=urllib.request.Request('http://'+host+':18080/',headers={'Host':'app.example.com'});out['http']=urllib.request.urlopen(r,timeout=10).read().decode().strip();assert out['http']=='http:primitive-runtime-ok'
with grpc.insecure_channel(host+':15051') as channel:
 r=health_pb2_grpc.HealthStub(channel).Check(health_pb2.HealthCheckRequest(service='primitive-runtime'),timeout=10);out['grpc']=health_pb2.HealthCheckResponse.ServingStatus.Name(r.status);assert out['grpc']=='SERVING'
ctx=ssl.create_default_context(cafile='/tls/tls.crt')
with ctx.wrap_socket(socket.create_connection((host,18443),timeout=10),server_hostname='app.example.com') as s:
 s.sendall(b'primitive-runtime-ok');out['tls']=s.recv(1024).decode();out['tls_version']=s.version();assert out['tls']=='tls:primitive-runtime-ok'
with socket.create_connection((host,15432),timeout=10) as s:
 s.sendall(b'primitive-runtime-ok');out['tcp']=s.recv(1024).decode();assert out['tcp']=='tcp:primitive-runtime-ok'
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(10);s.sendto(b'primitive-runtime-ok',(host,15353));out['udp']=s.recv(1024).decode();assert out['udp']=='udp:primitive-runtime-ok'
print(json.dumps(out,sort_keys=True))
