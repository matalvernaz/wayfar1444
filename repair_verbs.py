#!/usr/bin/env python3
"""
repair_verbs.py — Re-program unprogrammed player verbs.

The phase3 script ran multiple times; @program always targets the FIRST verb
with that name. This left earlier copies programmed and later copies as dupes.
We deleted the wrong set. This script re-programs the surviving (currently
unprogrammed) verbs without adding new duplicates.

Also adds status verb (shows coords + biome + vitals summary).
"""

import socket, time, re, sys
sys.path.insert(0, '.')
# Import verb code from phase3_wayfar
from phase3_wayfar import (
    VITALS_VERB, EAT_VERB, DRINK_VERB, REST_VERB,
    BUILD_VERB, TREAT_VERB,
)

HOST = 'localhost'
PORT = 7777

PLAYER = 6   # $player

STATUS_VERB = [
    '"Show coordinates, biome, and vitals summary.";',
    'loc = player.location;',
    'if (parent(loc) != $wroom)',
    '  player:tell("You are not in the wilderness.");',
    '  player:tell("  Location: " + loc.name);',
    '  return;',
    'endif',
    'x = loc.x;',
    'y = loc.y;',
    'bnames = {"Mineral Flats", "Scrublands", "Broken Ground", "Dust Plains", "Thermal Zone"};',
    'b = loc.biome;',
    'if (b < 0)',
    '  b = 0;',
    'elseif (b > 4)',
    '  b = 4;',
    'endif',
    'player:tell("=== STATUS ===");',
    'player:tell("  Coords : (" + tostr(x) + ", " + tostr(y) + ")");',
    'player:tell("  Biome  : " + bnames[b + 1]);',
    'player:tell("  Hunger : " + tostr(player.hunger) + "/100");',
    'player:tell("  Health : " + tostr(player.health) + "/100");',
    'player:tell("  Stamina: " + tostr(player.stamina) + "/100");',
    '"Show any nodes in the room";',
    'for item in (loc.contents)',
    '  if (item != player && ("node" in item.aliases))',
    '    player:tell("  Resource: " + item.name + " [" + tostr(item.count) + "/" + tostr(item.max_count) + "]");',
    '  endif',
    'endfor',
]


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(0.5)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    return s


def send(s, cmd, wait=0.4):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.4):
    return send(s, f'; {expr}', wait)


def program_verb(s, obj, verbname, code_lines):
    """Program the FIRST verb named verbname on obj (HellCore @program behavior)."""
    out = send(s, f'@program #{obj}:{verbname}', wait=0.6)
    if 'programming' not in out.lower():
        print(f'  WARN entering @program #{obj}:{verbname}: {repr(out[:120])}')
    s.settimeout(0.15)
    for line in code_lines:
        send(s, line, wait=0.03)
    s.settimeout(0.5)
    out = send(s, '.', wait=1.5)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
        return False
    return True


def add_verb_if_missing(s, obj, verbname, args='none none none'):
    """Add a verb only if none with that name exists on obj."""
    out = ev(s, f'player:tell(verbname in verbs(#{obj}) ? "yes" | "no")',
             wait=0.3)
    # verbname in list check
    out2 = send(s, f'@list #{obj}:{verbname}', wait=0.4)
    if 'No such verb' in out2 or 'E_VERBNF' in out2:
        send(s, f'@verb #{obj}:{verbname} {args}', wait=0.4)
        print(f'  Added @verb #{obj}:{verbname} {args}')
    else:
        print(f'  #{obj}:{verbname} already exists, programming in place')


if __name__ == '__main__':
    print('Wayfar 1444 — Verb Repair')
    print('=' * 60)

    s = connect()

    # --- Re-program player verbs (no add_verb — targets existing first verb) ---
    print('\n=== Re-programming $player (#6) verbs ===')

    for verbname, code, args in [
        ('vitals', VITALS_VERB, 'none none none'),
        ('eat',    EAT_VERB,    'any none none'),
        ('drink',  DRINK_VERB,  'any none none'),
        ('rest',   REST_VERB,   'none none none'),
        ('build',  BUILD_VERB,  'any none none'),
        ('treat',  TREAT_VERB,  'none none none'),
    ]:
        # Check if verb exists; if not add it first
        out = send(s, f'@list #{PLAYER}:{verbname}', wait=0.4)
        if 'not been programmed' in out or 'programming' in out.lower():
            # Verb exists but unprogrammed — just program it
            ok = program_verb(s, PLAYER, verbname, code)
            status = 'OK' if ok else 'FAIL'
            print(f'  {verbname}: {status}')
        elif 'No such verb' in out or 'E_VERBNF' in out:
            # Verb doesn't exist — add then program
            send(s, f'@verb #{PLAYER}:{verbname} {args}', wait=0.4)
            ok = program_verb(s, PLAYER, verbname, code)
            status = 'OK (added)' if ok else 'FAIL'
            print(f'  {verbname}: {status}')
        else:
            # Already programmed — re-program anyway to get latest code
            ok = program_verb(s, PLAYER, verbname, code)
            status = 'OK (updated)' if ok else 'FAIL'
            print(f'  {verbname}: {status}')

    # --- Status verb ---
    out = send(s, f'@list #{PLAYER}:status', wait=0.4)
    if 'No such verb' in out or 'E_VERBNF' in out:
        send(s, f'@verb #{PLAYER}:status none none none', wait=0.4)
        print('  Added status verb')
    ok = program_verb(s, PLAYER, 'status', STATUS_VERB)
    print(f'  status: {"OK" if ok else "FAIL"}')

    # --- Quick test ---
    print('\n=== Quick test ===')
    out = send(s, 'vitals', wait=0.5)
    print('vitals:\n', out[:300])
    out = send(s, 'status', wait=0.5)
    print('status:\n', out[:300])

    # --- Save ---
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(out.strip()[:80])

    s.sendall(b'QUIT\r\n')
    s.close()
    print('\nDone.')
