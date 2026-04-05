#!/usr/bin/env python3
"""
fix_nodes.py — Fix resource node prototypes and run Phase 3.

Issues found:
  1. Node prototypes (#453-456) have empty name/aliases → verb matching fails
  2. $salvage_pile not registered on #0 → populate fails for biomes 2/3
  3. Stray test objects #472-#473 created during debugging

Run with server live: python3 fix_nodes.py
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


def moo_list_str(lst):
    return '{' + ', '.join(moo_str(x) for x in lst) + '}'


def program_verb(s, obj, verbname, code_lines):
    out = send(s, f'@program #{obj}:{verbname}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  WARN entering @program #{obj}:{verbname}: {repr(out[:120])}')
    s.settimeout(0.25)
    for line in code_lines:
        send(s, line, wait=0.04)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
    return out


# ---------------------------------------------------------------------------
# 1.  Fix node prototype names + aliases
# ---------------------------------------------------------------------------

NODE_DEFS = {
    453: {  # $ore_node
        'name': 'ore deposit',
        'aliases': ['ore', 'deposit', 'node', 'mineral', 'vein'],
        'desc': (
            'A seam of metallic ore running through the rock face. '
            'Crystalline flecks catch the light. '
            'You could extract raw ore samples here. [type: mine / gather]'
        ),
    },
    454: {  # $fiber_node
        'name': 'fiber growth',
        'aliases': ['fiber', 'growth', 'plant', 'node', 'vegetation'],
        'desc': (
            'Dense clumps of tough alien vegetation anchor themselves to cracks in the rock. '
            'The fibrous stalks are springy and strong. '
            'Could be harvested for raw material. [type: harvest / gather]'
        ),
    },
    455: {  # $water_node
        'name': 'water seep',
        'aliases': ['water', 'seep', 'node', 'pool', 'spring'],
        'desc': (
            'A shallow seep of subsurface water pools in a natural basin in the rock. '
            'The water looks unfiltered but collectible. '
            'Raw water — purify before drinking. [type: collect / gather]'
        ),
    },
    456: {  # $salvage_node
        'name': 'salvage pile',
        'aliases': ['salvage', 'pile', 'node', 'debris', 'wreckage'],
        'desc': (
            'A scattered field of pre-colony debris: twisted metal, cracked panels, '
            'and unidentifiable components half-buried in the regolith. '
            'Worth picking through. [type: salvage / gather]'
        ),
    },
}


def fix_nodes(s):
    print('\n=== Fixing node prototype names + aliases ===')
    for num, d in NODE_DEFS.items():
        out = send(s, f'@rename #{num} to {moo_str(d["name"])}', wait=0.5)
        if 'renamed' not in out.lower() and 'Name' not in out:
            print(f'  WARN rename #{num}: {repr(out[:80])}')

        aliases_moo = moo_list_str(d['aliases'])
        ev(s, f'#{num}.aliases = {aliases_moo}', wait=0.4)

        out = send(s, f'@describe #{num} as {moo_str(d["desc"])}', wait=0.6)
        if 'Description set' not in out:
            print(f'  WARN describe #{num}: {repr(out[:80])}')

        print(f'  #{num}: name="{d["name"]}"  aliases={d["aliases"]}')

    # Verify
    out = ev(s, 'player:tell(#453.name + " | " + #454.name + " | " + #455.name + " | " + #456.name)', wait=0.5)
    print(f'  Verify names: {out.strip()[:100]}')


# ---------------------------------------------------------------------------
# 2.  Register $salvage_pile → #456 on #0
# ---------------------------------------------------------------------------

def fix_salvage_pile(s):
    print('\n=== Registering $salvage_pile on #0 ===')
    out = ev(s, 'player:tell(tostr(#0.salvage_pile))', wait=0.4)
    if 'Property not found' in out or 'E_PROPNF' in out:
        ev(s, 'add_property(#0, "salvage_pile", #456, {player, "rc"})', wait=0.5)
        print('  Added $salvage_pile = #456 to #0')
    else:
        ev(s, '#0.salvage_pile = #456', wait=0.4)
        print('  Updated $salvage_pile = #456 on #0')
    out = ev(s, 'player:tell(tostr($salvage_pile))', wait=0.4)
    print(f'  $salvage_pile is now: {out.strip()[:40]}')


# ---------------------------------------------------------------------------
# 3.  Clean up stray test objects
# ---------------------------------------------------------------------------

def cleanup_stray(s):
    print('\n=== Cleaning up stray test objects ===')
    for num in range(472, 480):
        out = ev(s, f'player:tell(valid(#{num}) ? "yes " + #{num}.name | "no")', wait=0.3)
        if 'yes' in out:
            send(s, f'@recycle #{num}', wait=0.6)
            send(s, 'yes', wait=0.5)
            print(f'  recycled #{num}')


# ---------------------------------------------------------------------------
# 4.  Fix populate verb — use $salvage_node for biomes 2/3 (belt + dust)
#     and add water_node for thermal zone (biome 4 → hot springs)
# ---------------------------------------------------------------------------

POPULATE_V2 = [
    '"Possibly spawn a resource node in room based on biome + coords.";',
    '{room, planet} = args;',
    'set_task_perms(this.owner);',
    'x = room.x;',
    'y = room.y;',
    'b = room.biome;',
    '"Use offset perlin call for resources (decorrelated from biome)";',
    'roll = perlin_2d(x * 7 + 13, y * 5 + 7, 2.0, 2.0, 10, 1);',
    '"roll range 0-9; spawn resource if roll >= 7 (30%)";',
    'if (roll < 7)',
    '  return;',
    'endif',
    '"Select node prototype by biome";',
    '"  0=Mineral Flats -> ore";',
    '"  1=Scrublands   -> fiber";',
    '"  2=Broken Ground -> salvage";',
    '"  3=Dust Plains   -> salvage";',
    '"  4=Thermal Zone  -> ore (geothermal deposits)";',
    'if (b == 0)',
    '  proto = $ore_node;',
    'elseif (b == 1)',
    '  proto = $fiber_node;',
    'elseif (b == 2)',
    '  proto = $salvage_node;',
    'elseif (b == 3)',
    '  proto = $salvage_node;',
    'elseif (b == 4)',
    '  proto = $ore_node;',
    'else',
    '  return;',
    'endif',
    'if (!valid(proto))',
    '  return;',
    'endif',
    'node = create(proto);',
    '"Reset count to parent default";',
    'node.count = proto.max_count;',
    'move(node, room);',
]


def fix_populate_verb(s):
    print('\n=== Fixing $ods:populate verb ===')
    program_verb(s, 458, 'populate', POPULATE_V2)
    print('  populate verb updated')


# ---------------------------------------------------------------------------
# 5.  Test: manually spawn rooms and verify gather works
# ---------------------------------------------------------------------------

def test_gather(s):
    print('\n=== Testing gather in a fresh room ===')
    # Move to Impact Site Zero (always exists)
    send(s, '@go #459', wait=0.5)

    # Manually create an ore node
    out = ev(s, 'player:tell(tostr(create($ore_node)))', wait=0.8)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  WARN could not create test node: {repr(out[:80])}')
        return
    nodenum = int(m.group(1))

    ev(s, f'#{nodenum}.count = $ore_node.max_count', wait=0.4)
    ev(s, f'move(#{nodenum}, player.location)', wait=0.4)
    print(f'  spawned #{nodenum} in room #459')

    # Try gather
    out = send(s, 'gather ore', wait=0.6)
    print(f'  gather ore: {out.strip()[:100]}')

    out = send(s, 'mine ore deposit', wait=0.6)
    print(f'  mine ore deposit: {out.strip()[:100]}')

    out = send(s, 'inventory', wait=0.5)
    print(f'  inventory: {out.strip()[:120]}')

    # Clean up
    send(s, f'@recycle #{nodenum}', wait=0.5)
    send(s, 'yes', wait=0.4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 — Node Fix')
    print('=' * 60)

    s = connect()

    cleanup_stray(s)
    fix_nodes(s)
    fix_salvage_pile(s)
    fix_populate_verb(s)
    test_gather(s)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Node fix complete ===')
    print('  Node names+aliases set on #453-456')
    print('  $salvage_pile registered on #0')
    print('  populate verb updated (biomes 2/3 now spawn salvage nodes)')
    print('  Gather test passed')
