#!/usr/bin/env python3
"""Debug: check w_colony state after navigation."""
import socket, time, re

HOST = 'localhost'; PORT = 7777
PLAYER = 6

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n'); time.sleep(0.8); s.recv(65536)
    return s

def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''; deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.7): return send(s, '; ' + e, wait)

def main():
    s = connect()

    # Check current state
    print('=== Debug w_colony state ===')
    out = ev(s, 'player:tell("w_colony prop? " + tostr("w_colony" in properties(player)))', wait=0.7)
    print(out.strip()[-60:])
    out = ev(s, 'player:tell("w_colony = " + tostr(player.w_colony))', wait=0.7)
    print(out.strip()[-60:])
    out = ev(s, 'player:tell("valid? " + tostr(valid(player.w_colony)))', wait=0.7)
    print(out.strip()[-60:])

    # Check if there's still a colony from previous test
    out = ev(s, 'player:tell("loc = " + player.location.name)', wait=0.7)
    print(out.strip()[-60:])

    # Create a fresh sector center and check step by step
    print('\n=== Fresh colony setup ===')
    # Clear old
    ev(s, 'if (valid(player.w_colony)) old = player.w_colony; player.w_colony = $nothing; recycle(old); endif', wait=1.0)
    # Remove old portals
    ev(s, 'for itm in (player.location.contents) if (is_a(itm, $building) && "sc_plaza" in properties(itm)) recycle(itm); endif endfor', wait=1.0)

    # Give materials and craft
    ev(s, 'm1 = create($thing); m1.name = "inert metal"; move(m1, player)', wait=0.5)
    ev(s, 'm2 = create($thing); m2.name = "inert metal"; move(m2, player)', wait=0.5)
    ev(s, 'w1 = create($thing); w1.name = "crude wire"; move(w1, player)', wait=0.5)
    ev(s, 'w2 = create($thing); w2.name = "crude wire"; move(w2, player)', wait=0.5)
    out = send(s, 'craft sector center', wait=2.0)
    print(f'craft: {out.strip()[-80:]}')

    out = send(s, 'place sector center', wait=5.0)
    print(f'place: {out.strip()[-120:]}')

    out = ev(s, 'player:tell("AFTER_PLACE w_colony=" + tostr(player.w_colony))', wait=0.7)
    print(out.strip()[-80:])

    # Navigate out
    out = send(s, 'out', wait=1.5)
    print(f'out: {out.strip()[-80:]}')

    out = ev(s, 'player:tell("AFTER_OUT w_colony=" + tostr(player.w_colony))', wait=0.7)
    print(out.strip()[-80:])

    out = ev(s, 'player:tell("valid=" + tostr(valid(player.w_colony)))', wait=0.7)
    print(out.strip()[-40:])

    # Now colony teleport
    out = send(s, 'colony', wait=2.0)
    print(f'colony: {out.strip()[-80:]}')

    s.close()
    print('Done.')

if __name__ == '__main__':
    main()
