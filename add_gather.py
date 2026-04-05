#!/usr/bin/env python3
"""
add_gather.py — Add gather verb to $wroom (#452) with any none none.

In HellCore, 'this none none' verbs on room-contained objects don't
match for free-text player input. The fix is a room-level verb with
'any none none' that looks up nodes by name/alias.

Also adds a 'gather' verb to Impact Site Zero (#459, a plain room)
so it works there too.
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777
WROOM = 452
LZ    = 459  # Impact Site Zero (non-wroom parent)


GATHER_VERB = [
    '"Gather resources - inline mining logic.";',
    'nodelist = {};',
    'for itm in (player.location.contents)',
    '  if (itm != player)',
    '    if (itm.is_node == 1)',
    '      nodelist = listappend(nodelist, itm);',
    '    endif',
    '  endif',
    'endfor',
    'if (dobjstr == "" || dobjstr == "list")',
    '  if (length(nodelist) == 0)',
    '    player:tell("Nothing to gather here.");',
    '    return;',
    '  endif',
    '  player:tell("Resources:");',
    '  for rn in (nodelist)',
    '    player:tell("  " + rn.name + " (" + tostr(rn.count) + " left)");',
    '  endfor',
    '  return;',
    'endif',
    '"Find node and mine inline";',
    'mined = 0;',
    'for rn in (nodelist)',
    '  if (index(rn.name, dobjstr))',
    '    if (rn.count <= 0)',
    '      player:tell("The " + rn.name + " is depleted.");',
    '      mined = 1;',
    '      break;',
    '    endif',
    '    itm = create($thing);',
    '    itm.name = rn.yield_name;',
    '    itm.description = rn.yield_desc;',
    '    move(itm, player);',
    '    rn.count = rn.count - 1;',
    '    player:tell("You gather some " + itm.name + ". [" + tostr(rn.count) + "/" + tostr(rn.max_count) + " remaining]");',
    '    player.location:announce(player.name + " gathers some resources.", player);',
    '    mined = 1;',
    '    break;',
    '  endif',
    'endfor',
    'if (!mined)',
    '  player:tell("No matching resource for: " + dobjstr);',
    'endif',
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


def add_and_program(s, obj, verbname, args, code_lines):
    """Delete any existing verb, add fresh, then program."""
    # Check if verb exists on THIS object (not parents)
    verbs_out = ev(s, f'player:tell(tostr(verbs(#{obj})))', wait=0.4)
    # verbs() returns a list; check if verbname is in it
    # The tell shows the raw list representation
    verb_check = ev(s, f'player:tell({repr(verbname)} in verbs(#{obj}) ? "yes" | "no")', wait=0.4)
    if 'yes' in verb_check:
        # Find index and delete
        idx_out = ev(s, f'player:tell(tostr(verb_info(#{obj}, {repr(verbname)})))', wait=0.4)
        # Use listindex to find position
        pos_out = ev(s, f'idx = 0; for i in [1..length(verbs(#{obj}))]; if (verbs(#{obj})[i] == {repr(verbname)}); idx = i; break; endif; endfor; player:tell(tostr(idx))', wait=0.5)
        m = re.search(r'(\d+)\r\n=> 0', pos_out)
        if m:
            idx = int(m.group(1))
            if idx > 0:
                ev(s, f'delete_verb(#{obj}, {idx})', wait=0.3)
                print(f'  Deleted existing #{obj}:{verbname} at index {idx}')

    # Add verb
    send(s, f'@verb #{obj}:{verbname} {args}', wait=0.4)

    # Program it
    out = send(s, f'@program #{obj}:{verbname}', wait=0.6)
    if 'programming' not in out.lower():
        print(f'  WARN @program #{obj}:{verbname}: {repr(out[:120])}')
        return False
    s.settimeout(0.15)
    for line in code_lines:
        send(s, line, wait=0.03)
    s.settimeout(0.5)
    out = send(s, '.', wait=1.5)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
        return False
    return True


if __name__ == '__main__':
    print('Wayfar 1444 — Add gather verb to $wroom')
    print('=' * 60)

    s = connect()

    ok = add_and_program(s, WROOM, 'gather', 'any none none', GATHER_VERB)
    print(f'  #{WROOM}:gather: {"OK" if ok else "FAIL"}')

    ok = add_and_program(s, LZ, 'gather', 'any none none', GATHER_VERB)
    print(f'  #{LZ}:gather: {"OK" if ok else "FAIL"}')

    # --- Test ---
    print('\n=== Testing gather ===')
    # Move to LZ
    send(s, f'@go #{LZ}', wait=0.5)

    # Spawn a test ore node
    out = ev(s, 'n = create($ore_node); n.count = $ore_node.max_count; move(n, player.location); player:tell(tostr(n))')
    m = re.search(r'#(\d+)', out)
    if m:
        nnum = int(m.group(1))
        print(f'  Spawned ore node #{nnum}')

        out1 = send(s, 'gather', wait=0.5)
        print(f'  gather (list):\n    {out1.strip()[:120]}')

        out2 = send(s, 'gather ore', wait=0.5)
        print(f'  gather ore: {out2.strip()[:100]}')

        out3 = send(s, 'gather mineral', wait=0.5)
        print(f'  gather mineral: {out3.strip()[:100]}')

        # Clean up
        ev(s, f'recycle(#{nnum})', 0.3)
        print(f'  Recycled #{nnum}')

    # --- Save ---
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(out.strip()[:80])

    s.sendall(b'QUIT\r\n')
    s.close()
    print('\nDone.')
