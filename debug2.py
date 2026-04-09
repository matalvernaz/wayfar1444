#!/usr/bin/env python3
"""Very minimal: check wizard inventory state."""

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


def main():
    s = connect()
    print('connected')

    # Raw inventory check
    out = send(s, 'i', wait=1.0)
    print(f'i command:\n{out.strip()[-300:]}')

    # Check wizard's w_hp
    out = send(s, '; player:tell("w_hp=" + tostr(#361.w_hp))', wait=0.7)
    print(f'w_hp check: {out.strip()[-60:]}')

    # Simple get/drop test - drop something from the room itself
    out = send(s, 'look', wait=1.0)
    print(f'look:\n{out.strip()[-400:]}')

    # Try typing 'inventory' command
    out = send(s, 'inventory', wait=1.0)
    print(f'inventory:\n{out.strip()[-200:]}')

    # Check if wizard is actually connected properly
    out = send(s, '; player:tell("I am " + player.name + " #" + tostr(player))', wait=0.7)
    print(f'who am i: {out.strip()[-60:]}')

    # Try creating an item and checking where it lands
    out = send(s, '; x = create($thing); x.name = "probe"; player:tell("x=" + tostr(x) + " in=" + tostr(x.location))', wait=1.0)
    print(f'create probe: {out.strip()[-100:]}')

    # Use 'get' to check if probe is findable
    out = send(s, 'get probe', wait=0.8)
    print(f'get probe: {out.strip()[-100:]}')

    # Check inventory after
    out = send(s, 'i', wait=1.0)
    print(f'i after get:\n{out.strip()[-200:]}')

    # Check player.contents directly
    out = send(s, '; n = length(player.contents); player:tell("items in inv: " + tostr(n))', wait=0.7)
    print(f'inv count: {out.strip()[-60:]}')

    s.close()


if __name__ == '__main__':
    main()
