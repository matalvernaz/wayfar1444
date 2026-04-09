#!/usr/bin/env python3
"""Get full tick verb and start verb."""
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

def send(s, cmd, wait=1.0):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

s = connect()

print('=== #545:tick ===')
print(send(s, '@list #545:tick', wait=1.5))

print('=== #545:start ===')
print(send(s, '@list #545:start', wait=1.0))

s.close()
