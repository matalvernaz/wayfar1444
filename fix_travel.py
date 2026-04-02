#!/usr/bin/env python3
"""
Fix script for expand_wayfar.py issues:
  1. Remove duplicate resource nodes left by pre-cleanup runs
  2. Replace broken 'travel' verb (clashes with HellCore built-in) with 'launch'
     placed on the spaceport ROOM so free-text destinations work
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5)
    s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7)
    s.recv(65536)
    return s


def send(s, cmd, wait=0.65):
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


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def program_verb(s, obj, verbname, code_lines):
    out = send(s, f'@program #{obj}:{verbname}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  WARN @program #{obj}:{verbname}: {repr(out[:120])}')
    s.settimeout(0.25)
    for line in code_lines:
        send(s, line, wait=0.04)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
    return out


# ---------------------------------------------------------------------------
# Known room/object numbers
# ---------------------------------------------------------------------------
SPACEPORT   = 405
LAUNCH_PAD  = 408
KEPLER_LZ   = 159
XERIS_LZ    = 409

E_FLATS     = 380
W_SCRUB     = 386
S_RIDGE     = 383

# Objects from pre-cleanup runs that ended up in wilderness rooms
STALE_NODES = [197, 397, 399]   # extra ore deposits in E_FLATS
# We'll do a broader scan too


# ---------------------------------------------------------------------------
# 1. Clean duplicate resource nodes
# ---------------------------------------------------------------------------

def get_contents(s, room):
    """Return list of (num, name) for objects in room (excludes exits)."""
    count_out = ev(s, f'player:tell(tostr(length(#{room}.contents)))', wait=0.4)
    m = re.search(r'(\d+)', count_out)
    if not m:
        return []
    n = int(m.group(1))
    items = []
    for i in range(1, n + 1):
        out = ev(s, f'x = #{room}.contents[{i}]; player:tell(tostr(x) + " " + x.name)', wait=0.3)
        m2 = re.search(r'#(\d+)\s+(.+)', out)
        if m2:
            items.append((int(m2.group(1)), m2.group(2).strip()))
    return items


def recycle_obj(s, num):
    send(s, f'@recycle #{num}', wait=0.6)
    send(s, 'yes', wait=0.5)


def clean_duplicates(s):
    print('\n=== Cleaning duplicate resource nodes ===')

    rooms = {
        'eastern_flats':    (E_FLATS,  'ore deposit'),
        'western_scrublands':(W_SCRUB, 'scrub patch'),
        'southern_ridge':   (S_RIDGE,  'water spring'),
    }

    for label, (room, target_name) in rooms.items():
        items = get_contents(s, room)
        found = [(n, nm) for n, nm in items if target_name in nm]
        print(f'  {label}: {len(found)} "{target_name}" node(s)')
        if len(found) > 1:
            # Keep the highest-numbered one (most recent from expand script)
            keep = max(found, key=lambda x: x[0])
            for n, nm in found:
                if n != keep[0]:
                    recycle_obj(s, n)
                    print(f'    recycled #{n} ({nm})')
            print(f'    kept #{keep[0]}')


# ---------------------------------------------------------------------------
# 2. Replace travel verb with launch on the spaceport ROOM
# ---------------------------------------------------------------------------

# Putting 'launch' on the room means it catches "launch <free-text>" even
# when the destination string doesn't resolve to any in-scope object.
# dobjstr will hold whatever the player typed.

LAUNCH_VERB = [
    '"Launch the colony transport to another world.";',
    '"Usage: launch [destination name or number]";',
    'if (dobjstr == "")',
    '  player:tell("=== COLONY TRANSPORT SYSTEM ===");',
    '  player:tell("Available destinations:");',
    '  pad = 0;',
    '  for x in (player.location.contents)',
    '    if (x.name == "launch pad")',
    '      pad = x;',
    '    endif',
    '  endfor',
    '  if (!pad)',
    '    player:tell("No launch pad found in this room.");',
    '    return;',
    '  endif',
    '  i = 1;',
    '  for d in (pad.destinations)',
    '    player:tell("  " + tostr(i) + ". " + d[1] + " - " + d[2]);',
    '    i = i + 1;',
    '  endfor',
    '  player:tell("Usage: launch <name or number>");',
    '  return;',
    'endif',
    'pad = 0;',
    'for x in (player.location.contents)',
    '  if (x.name == "launch pad")',
    '    pad = x;',
    '  endif',
    'endfor',
    'if (!pad)',
    '  player:tell("There is no launch pad here.");',
    '  return;',
    'endif',
    'tgt = dobjstr;',
    'dest = 0;',
    'n = toint(tgt);',
    'if (n > 0 && n <= length(pad.destinations))',
    '  dest = pad.destinations[n];',
    'else',
    '  for d in (pad.destinations)',
    '    if (index(d[1], tgt))',
    '      dest = d;',
    '      break;',
    '    endif',
    '  endfor',
    'endif',
    'if (!dest)',
    '  player:tell("Unknown destination: " + tgt);',
    '  player:tell("Type \'launch\' to see available destinations.");',
    '  return;',
    'endif',
    'dest_room = dest[3];',
    'if (!valid(dest_room))',
    '  player:tell("That destination is currently unavailable.");',
    '  return;',
    'endif',
    'player:tell("You board the colony transport and strap in. Engines ignite.");',
    'player.location:announce(player.name + " boards the colony transport and lifts off.", player);',
    'move(player, dest_room);',
    'player:tell("After a brutal transit burn, you arrive at " + dest[1] + ".");',
    'player.location:announce(player.name + " arrives on the colony transport.", player);',
]

# Also put the 'launch' verb on the Xeris Prime landing pad room so players
# can travel BACK from Xeris.
XERIS_LZ_RETURN = [
    '"Launch back to Kepler-7 Colony.";',
    '"Usage: launch [destination]";',
    'if (dobjstr == "" || index(dobjstr, "kepler") || index(dobjstr, "colony") || index(dobjstr, "1"))',
    f'  player:tell("You board the supply shuttle. Engines burn hot through the atmosphere.");',
    f'  player.location:announce(player.name + " boards the shuttle and lifts off.", player);',
    f'  move(player, #{KEPLER_LZ});',
    f'  player:tell("After a cold transit burn, you arrive at Kepler-7 Colony.");',
    f'  player.location:announce(player.name + " arrives on the shuttle.", player);',
    '  return;',
    'endif',
    'player:tell("From Xeris Prime you can only launch back to the Kepler-7 Colony.");',
    'player:tell("Type \'launch\' or \'launch colony\'.");',
]


def setup_launch_verb(s):
    print(f'\n=== Setting up launch verb on spaceport room #{SPACEPORT} ===')

    # Remove any old travel verbs from the launch pad object
    out = send(s, f'@rmverb #{LAUNCH_PAD}:travel', wait=0.6)
    send(s, 'yes', wait=0.4)   # confirm if asked
    print(f'  removed travel verb from #{LAUNCH_PAD}: {repr(out.strip()[:60])}')

    # Add launch verb to the ROOM (none none none = no-arg menu)
    send(s, f'@verb #{SPACEPORT}:launch none none none', wait=0.5)
    program_verb(s, SPACEPORT, 'launch', LAUNCH_VERB)
    print(f'  added launch (none none none) to #{SPACEPORT}')

    # Add launch verb to the ROOM (any none none = "launch <destination>")
    send(s, f'@verb #{SPACEPORT}:launch any none none', wait=0.5)
    program_verb(s, SPACEPORT, 'launch', LAUNCH_VERB)
    print(f'  added launch (any none none) to #{SPACEPORT}')

    # Add launch verb to Xeris Prime landing pad room so players can return
    send(s, f'@verb #{XERIS_LZ}:launch none none none', wait=0.5)
    program_verb(s, XERIS_LZ, 'launch', XERIS_LZ_RETURN)
    send(s, f'@verb #{XERIS_LZ}:launch any none none', wait=0.5)
    program_verb(s, XERIS_LZ, 'launch', XERIS_LZ_RETURN)
    print(f'  added launch return verb to #{XERIS_LZ} (Xeris Prime)')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 - Travel Fix')
    print('=' * 60)

    s = connect()

    clean_duplicates(s)
    setup_launch_verb(s)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\nDone. Players can now:')
    print('  launch          - show destination menu from Spaceport Alpha')
    print('  launch xeris    - fly to Xeris Prime')
    print('  launch 1        - fly to destination 1 (Kepler-7 Colony)')
    print('  launch          - return from Xeris Prime')
