#!/usr/bin/env python3
"""
fix_colony.py — Post-setup fixes for Colony Hub

Issues:
  1. Hub 'east'/'west' verbs shadowed by $player movement verbs
     Fix: replace with 'workshop' (hub→workshop) and 'hub' (workshop→hub)
  2. Colony Hub/Workshop look_self crashes (inherits broken generic room verb)
     Fix: add custom look_self to both rooms
  3. Wizard's health/hunger/stamina may have wrong values
     Fix: reset them on the player class and on wizard directly
  4. 'talk vera' not working — verify talk verb args and aliases

Run with server live: python3 fix_colony.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777
HUB      = 504
WORKSHOP = 505
VERA     = 508
HARLAN   = 509
PLAYER   = 6  # $player class


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(0.5)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8)
    try: s.recv(65536)
    except: pass
    return s


def send(s, cmd, wait=0.4):
    try:
        s.sendall((cmd + '\r\n').encode())
    except Exception as e:
        print(f'  [send error] {e}')
        return ''
    time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.4):
    return send(s, f'; {expr}', wait=wait)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def add_verb(s, obj, verbname, args='this none none'):
    return send(s, f'@verb #{obj}:{verbname} {args}', wait=0.3)


def program_verb(s, obj, verbname, code_lines):
    out = send(s, f'@program #{obj}:{verbname}', wait=0.5)
    if 'programming' not in out.lower():
        print(f'  WARN @program #{obj}:{verbname}: {repr(out[:100])}')
    s.settimeout(0.05)
    for line in code_lines:
        send(s, line, wait=0.02)
    s.settimeout(0.5)
    out = send(s, '.', wait=1.5)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:300])}')
    return out


def delete_verb_if_exists(s, obj, verbname):
    """Remove a named verb from obj if present."""
    out = ev(s, f'player:tell(tostr(verb_info(#{obj}, {moo_str(verbname)})))', wait=0.4)
    if 'Verb not found' in out or 'E_VERBNF' in out or 'error' in out.lower():
        return  # Not there, nothing to do
    # Get verb index and delete
    out = ev(s, f'player:tell(tostr(verb_index(#{obj}, {moo_str(verbname)})))', wait=0.4)
    m = re.search(r'\d+', out)
    if m:
        idx = m.group(0)
        ev(s, f'delete_verb(#{obj}, {idx})', wait=0.4)
        print(f'  removed {verbname} from #{obj}')


# ---------------------------------------------------------------------------
# 1. Fix hub/workshop exits
# ---------------------------------------------------------------------------

HUB_LOOK = [
    '"Show Colony Hub description.";',
    'player:tell("Colony Hub");',
    'player:tell(this.description);',
    'player:tell("");',
    'player:tell("Exits: workshop  outside");',
    '"--- contents ---";',
    'for item in (this.contents)',
    '  if (item != player)',
    '    player:tell("  " + item.name);',
    '  endif',
    'endfor',
]

WORKSHOP_LOOK = [
    '"Show Workshop description.";',
    'player:tell("Workshop");',
    'player:tell(this.description);',
    'player:tell("");',
    'player:tell("Exits: hub");',
    '"--- contents ---";',
    'for item in (this.contents)',
    '  if (item != player)',
    '    player:tell("  " + item.name);',
    '  endif',
    'endfor',
]


def fix_exits(s):
    print('\n=== Fixing Hub/Workshop exits ===')

    # Remove shadow-prone east/west verbs from hub and workshop
    delete_verb_if_exists(s, HUB, 'east')
    delete_verb_if_exists(s, WORKSHOP, 'west')

    # Hub: 'workshop' → goes to workshop, 'look'/'look_self' → custom desc
    add_verb(s, HUB, 'workshop', 'none none none')
    program_verb(s, HUB, 'workshop', [
        '"Go to the fabrication workshop.";',
        f'player:tell("You head into the workshop.");',
        f'player.location:announce(player.name + " heads into the workshop.", player);',
        f'move(player, #{WORKSHOP});',
        f'player.location:announce(player.name + " arrives from the hub.", player);',
    ])
    print(f'  workshop verb added to #{HUB}')

    add_verb(s, HUB, 'look_self', 'this none none')
    program_verb(s, HUB, 'look_self', HUB_LOOK)
    print(f'  look_self added to #{HUB}')

    # Workshop: 'hub' → goes to hub, 'look'/'look_self' → custom desc
    add_verb(s, WORKSHOP, 'hub', 'none none none')
    program_verb(s, WORKSHOP, 'hub', [
        '"Go back to the colony hub.";',
        f'player:tell("You head back into the colony hub.");',
        f'player.location:announce(player.name + " heads back to the hub.", player);',
        f'move(player, #{HUB});',
        f'player.location:announce(player.name + " arrives from the workshop.", player);',
    ])
    print(f'  hub verb added to #{WORKSHOP}')

    add_verb(s, WORKSHOP, 'look_self', 'this none none')
    program_verb(s, WORKSHOP, 'look_self', WORKSHOP_LOOK)
    print(f'  look_self added to #{WORKSHOP}')

    # Also add 'look' aliases since players often type 'look'
    for room in [HUB, WORKSHOP]:
        add_verb(s, room, 'look', 'none none none')
        program_verb(s, room, 'look', [
            f'"Alias for look_self.";',
            f'this:look_self({{}});',
        ])
    print(f'  look verb added to #{HUB} and #{WORKSHOP}')


# ---------------------------------------------------------------------------
# 2. Fix player stats defaults (reset $player class defaults and wizard values)
# ---------------------------------------------------------------------------

def fix_stats(s):
    print('\n=== Fixing player survival stats ===')

    # Get wizard object number
    out = ev(s, 'player:tell(tostr(player))', wait=0.4)
    m = re.search(r'#(\d+)', out)
    wizard = int(m.group(1)) if m else 361
    print(f'  Wizard is #{wizard}')

    # Reset $player class defaults
    for prop, val in [('hunger', '100'), ('health', '100'), ('stamina', '100')]:
        ev(s, f'#{PLAYER}.{prop} = {val}', wait=0.3)
        print(f'  #{PLAYER}.{prop} = {val}')

    # Reset wizard's own values (clear their personal overrides by setting to defaults)
    for prop, val in [('hunger', '100'), ('health', '100'), ('stamina', '100')]:
        ev(s, f'#{wizard}.{prop} = {val}', wait=0.3)
        print(f'  #{wizard}.{prop} = {val}')

    # Verify
    out = ev(s, 'player:tell("hunger=" + tostr(player.hunger) + " health=" + tostr(player.health) + " stamina=" + tostr(player.stamina))', wait=0.4)
    print(f'  Verify: {out.strip()[:80]}')


# ---------------------------------------------------------------------------
# 3. Fix talk verb — ensure it's 'this none none' and test aliases
# ---------------------------------------------------------------------------

def fix_talk(s):
    print('\n=== Checking talk verb + NPC aliases ===')

    for npc_num, npc_name in [(VERA, 'Vera'), (HARLAN, 'Harlan')]:
        # Check aliases
        out = ev(s, f'player:tell(tostr(#{npc_num}.aliases))', wait=0.4)
        print(f'  #{npc_num} {npc_name} aliases: {out.strip()[:80]}')

        # Check talk verb args
        out = ev(s, f'player:tell(tostr(verb_info(#{npc_num}, "talk")))', wait=0.4)
        print(f'  #{npc_num} talk verb_info: {out.strip()[:80]}')


# ---------------------------------------------------------------------------
# 4. Update $player movement verbs to support room exit properties
# ---------------------------------------------------------------------------

# Updated movement verb template — checks room.X_exit before blocking
def make_move_verb(dx, dy, direction, from_dir):
    return [
        f'"Move {direction} — supports room exit or wilderness movement.";',
        '"--- check for a room exit property first ---";',
        f'exit_prop = "{direction}_exit";',
        f'if (parent(player.location) != $wroom)',
        f'  if (exit_prop in properties(player.location))',
        f'    dest = player.location.(exit_prop);',
        f'    if (valid(dest))',
        f'      player.location:announce(player.name + " heads {direction}.", player);',
        f'      move(player, dest);',
        f'      player.location:announce(player.name + " arrives from the {from_dir}.", player);',
        f'      return;',
        f'    endif',
        f'  endif',
        f'  player:tell("You cannot go that way.");',
        f'  return;',
        f'endif',
        f'nx = player.location.x + {dx};',
        f'ny = player.location.y + {dy};',
        f'planet = player.location.planet;',
        f'dest = $ods:spawn_room(planet, nx, ny);',
        f'if (!valid(dest))',
        f'  player:tell("The way is blocked.");',
        f'  return;',
        f'endif',
        f'player.location:announce(player.name + " heads {direction}.", player);',
        f'move(player, dest);',
        f'player.location:announce(player.name + " arrives from the {from_dir}.", player);',
    ]


DIRECTIONS = [
    # (dx, dy, verb_names, dir_str, from_dir)
    (0,  1,  ['north', 'n'], 'north', 'south'),
    (0, -1,  ['south', 's'], 'south', 'north'),
    (1,  0,  ['east',  'e'], 'east',  'west'),
    (-1, 0,  ['west',  'w'], 'west',  'east'),
]


def update_movement_verbs(s):
    print('\n=== Updating $player movement verbs for room exit support ===')

    for dx, dy, names, direction, from_dir in DIRECTIONS:
        code = make_move_verb(dx, dy, direction, from_dir)
        for name in names:
            program_verb(s, PLAYER, name, code)
            print(f'  #{PLAYER}:{name} updated')


# ---------------------------------------------------------------------------
# 5. Add exit properties to hub/workshop for east/west movement
# ---------------------------------------------------------------------------

def add_exit_props(s):
    print('\n=== Adding exit properties to hub and workshop ===')

    # Hub: east_exit → workshop
    out = ev(s, f'player:tell(tostr(#{HUB}.east_exit))', wait=0.4)
    if 'Property not found' in out or 'E_PROPNF' in out:
        ev(s, f'add_property(#{HUB}, "east_exit", #{WORKSHOP}, {{player, "rc"}})', wait=0.4)
    else:
        ev(s, f'#{HUB}.east_exit = #{WORKSHOP}', wait=0.3)
    print(f'  #{HUB}.east_exit = #{WORKSHOP}')

    # Workshop: west_exit → hub
    out = ev(s, f'player:tell(tostr(#{WORKSHOP}.west_exit))', wait=0.4)
    if 'Property not found' in out or 'E_PROPNF' in out:
        ev(s, f'add_property(#{WORKSHOP}, "west_exit", #{HUB}, {{player, "rc"}})', wait=0.4)
    else:
        ev(s, f'#{WORKSHOP}.west_exit = #{HUB}', wait=0.3)
    print(f'  #{WORKSHOP}.west_exit = #{HUB}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 — Colony Fix')
    print('=' * 60)

    s = connect()

    fix_exits(s)
    fix_stats(s)
    fix_talk(s)
    update_movement_verbs(s)
    add_exit_props(s)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Colony fix complete ===')
    print('  Hub exits: workshop → Workshop, outside → surface, east (via exit prop)')
    print('  Workshop exits: hub → Hub, west (via exit prop)')
    print('  $player movement verbs now check room exit properties')
    print('  Player stats reset to correct values')
