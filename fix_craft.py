#!/usr/bin/env python3
"""Reprogram craft verb with fixed obj==0 checks (replaces !obj HellCore bug)."""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')
from phase4_craft import CRAFT_CODE

HOST = 'localhost'
PORT = 7777
PLAYER = 6
BCT_NUM = 592


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
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
        print(f'  ERROR @program: {repr(out[:150])}')
        return False
    old_to = s.gettimeout()
    s.settimeout(0.3)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.06)
        if i % 15 == 14:
            print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old_to)
    result = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR: {result[:400]}')
        return False
    print(f'  OK: #{obj_num}:{verbname}')
    return True


def main():
    s = connect()

    craft_code = [
        '"Craft items using a basic crafting tool from inventory.";',
        'tool = 0;',
        'for itm in (player.contents)',
        f'  if (is_a(itm, #{BCT_NUM}))',
        '    tool = itm;',
        '    break;',
        '  endif',
        'endfor',
        'if (tool == 0)',
        '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
        '  return;',
        'endif',
    ] + CRAFT_CODE

    print(f'=== Update craft verb on #{PLAYER} ===')
    program_verb(s, PLAYER, 'craft', craft_code)

    # Full wf_test via verb (proper context for move())
    print('\n=== wf_test (full craft+eat+drink) ===')
    out = send(s, 'wf_test', wait=6.0)
    print(f'wf_test:\n{out.strip()}')

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
