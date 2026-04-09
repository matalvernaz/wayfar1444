#!/usr/bin/env python3
"""Debug move() and craft."""

import socket, time, re

def connect():
    s = socket.socket()
    s.connect(('localhost', 7777))
    s.settimeout(3)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, e, wait=0.7):
    return send(s, '; ' + e, wait)


def main():
    s = connect()
    print('=== Minimal move test ===')

    # Test 1: create then inspect in same statement
    out = ev(s, 'r = create($thing); r.name = "test item"; player:tell("r=" + tostr(r) + " r.loc=" + tostr(r.location))', wait=1.0)
    print(f'create result: {out.strip()[-100:]}')

    # Test 2: move in same statement and check
    out = ev(s, 'r = create($thing); r.name = "t2"; m = move(r, player); player:tell("r=" + tostr(r) + " loc=" + tostr(r.location) + " m=" + tostr(m))', wait=1.0)
    print(f'move test: {out.strip()[-150:]}')

    # Test 3: check player.contents
    out = ev(s, 'player:tell("inv cnt=" + tostr(length(player.contents)))', wait=0.7)
    print(f'inventory count: {out.strip()[-50:]}')

    # Test 4: check player.contents items
    out = ev(s, 'for x in (player.contents); player:tell(tostr(x) + " " + x.name); endfor', wait=1.0)
    print(f'inventory items:\n{out.strip()[-300:]}')

    # Test 5: What does get work on?
    print('\n=== Test: get item ===')
    out = ev(s, 'r = create($thing); r.name = "pickup test"; move(r, player.location); player:tell("r in room=" + tostr(r.location))', wait=1.0)
    print(f'create in room: {out.strip()[-100:]}')
    out = send(s, 'get pickup test', wait=1.0)
    print(f'get command: {out.strip()[-100:]}')
    out = ev(s, 'player:tell("inv=" + tostr(length(player.contents)))', wait=0.7)
    print(f'inv after get: {out.strip()[-50:]}')

    # Test 6: direct inventory check via @property
    print('\n=== Direct property check ===')
    out = ev(s, 'player:tell(tostr(player.contents))', wait=1.0)
    print(f'player.contents: {out.strip()[-200:]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
