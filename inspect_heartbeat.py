#!/usr/bin/env python3
"""Inspect heartbeat object #545 and $npc_worker if exists."""
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

def send(s, cmd, wait=0.8):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.8): return send(s, '; ' + e, wait)

s = connect()

# Check heartbeat #545
print('=== Heartbeat #545 ===')
print(ev(s, 'player:tell(#545.name)', wait=0.5).strip()[-60:])
print(ev(s, 'player:tell(tostr(verbs(#545)))', wait=0.5).strip()[-200:])
print(ev(s, 'player:tell(tostr(properties(#545)))', wait=0.5).strip()[-200:])

# Get _beat verb code
print('\n=== #545:_beat verb ===')
out = send(s, '@list #545:_beat', wait=1.5)
print(out[:1200])

# Check connected_players builtin
print('\n=== connected_players ===')
print(ev(s, 'player:tell(tostr(connected_players()))', wait=0.5).strip()[-80:])

# Check if $npc_worker exists
print('\n=== $npc_worker ===')
print(ev(s, 'player:tell(tostr($npc_worker))', wait=0.5).strip()[-50:])

s.close()
