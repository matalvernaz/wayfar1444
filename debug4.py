#!/usr/bin/env python3
"""Test gather verb and craft from within actual verb context."""

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


def program_verb(s, obj_num, verbname, code_lines):
    out = send(s, f'@program #{obj_num}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program #{obj_num}:{verbname}: {repr(out[:150])}')
        return False
    old_to = s.gettimeout()
    s.settimeout(0.3)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.06)
    s.settimeout(old_to)
    result = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERRORS: {result[:400]}')
        return False
    print(f'  OK: #{obj_num}:{verbname}')
    return True


def main():
    s = connect()

    # Step 1: Go to a wilderness room (dispatch to get there)
    print('=== Go to wilderness (dispatch) ===')
    out = send(s, 'dispatch', wait=2.0)
    print(f'dispatch: {out.strip()[-200:]}')

    out = ev(s, 'player:tell("loc=" + tostr(player.location) + " " + player.location.name)', wait=0.7)
    print(f'location: {out.strip()[-80:]}')

    # Step 2: Try gather (uses move inside verb)
    print('\n=== gather test ===')
    out = send(s, 'gather', wait=1.0)
    print(f'gather (list): {out.strip()[-300:]}')

    out = send(s, 'gather ore', wait=1.5)
    print(f'gather ore: {out.strip()[-200:]}')

    # Check if item ended up in inventory
    out = ev(s, 'player:tell("inv cnt=" + tostr(length(player.contents)))', wait=0.7)
    print(f'inv count: {out.strip()[-50:]}')

    out = ev(s, 'for x in (player.contents); player:tell(tostr(x) + " " + x.name); endfor', wait=1.0)
    print(f'inventory:\n{out.strip()[-300:]}')

    # Step 3: If gather worked, try craft
    print('\n=== Craft test (if gather worked) ===')
    # Need 2 fibers - gather more
    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber: {out.strip()[-150:]}')
    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber 2: {out.strip()[-150:]}')

    out = send(s, 'craft ration bar', wait=2.0)
    print(f'craft ration bar: {out.strip()[-200:]}')

    out = ev(s, 'for x in (player.contents); player:tell(tostr(x) + " " + x.name); endfor', wait=1.0)
    print(f'inventory after craft:\n{out.strip()[-200:]}')

    # Eat the ration
    out = send(s, 'eat ration', wait=1.5)
    print(f'eat ration: {out.strip()[-200:]}')

    hp = ev(s, 'player:tell("w_hp=" + tostr(player.w_hp))', wait=0.7)
    print(f'w_hp: {hp.strip()[-40:]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
