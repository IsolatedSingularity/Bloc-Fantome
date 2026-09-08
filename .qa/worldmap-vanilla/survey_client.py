import socket,struct,time,zlib
s=socket.create_connection(('127.0.0.1',25585));s.settimeout(1)
def vi(n):
 b=bytearray()
 while True:
  x=n&127;n>>=7;b.append(x|(128 if n else 0))
  if not n:return bytes(b)
def st(t):
 b=t.encode();return vi(len(b))+b
def send(b):s.sendall(vi(len(b))+b)
send(vi(0)+vi(736)+st('localhost')+struct.pack('>H',25585)+vi(2))
send(vi(0)+st('CodexSurvey'))
end=time.time()+90
while time.time()<end:
 try:
  b=s.recv(65536)
  if not b:break
 except socket.timeout:pass
s.close()
