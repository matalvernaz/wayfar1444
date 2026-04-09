#!/usr/bin/env python3
"""Quick debug checks via socket."""
import socket, time, re

HOST = 'localhost'; PORT = 7777

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(2)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n'); time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    return s

def send(s, cmd, wait=0.5):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.5): return send(s, '; ' + e, wait)

s = connect()

print(ev(s, 'player:tell("w_colony=" + tostr(player.w_colony))'))
print(ev(s, 'player:tell("valid=" + tostr(valid(player.w_colony)))'))
print(ev(s, 'player:tell("loc=" + player.location.name)'))

s.close()
