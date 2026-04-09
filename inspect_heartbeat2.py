#!/usr/bin/env python3
"""Inspect heartbeat object #545 verbs and how it ticks."""
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

# List all verbs on #545
print(send(s, '@verbs #545', wait=1.0)[:500])

# List all verbs on #545 with details
print(send(s, '@list #545:tick', wait=1.0)[:800])
print(send(s, '@list #545:beat', wait=1.0)[:800])

# What calls #545? Check if it has a scheduled task
print(ev(s, 'player:tell(tostr(queued_tasks()))', wait=1.0).strip()[-400:])

# Check #545 properties directly
print(send(s, '@examine #545', wait=1.0)[:600])

s.close()
