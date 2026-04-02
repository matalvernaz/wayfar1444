#!/usr/bin/env python3
"""
Final verb fix:
  - HellCore 'any none none' matches ALL inputs (even no-arg), 'none none none' never fires
  - Solution: ONE verb per command, 'any none none', check dobjstr == "" for menu
  - Remove duplicate verbs; reprogram craft + launch with correct single-verb pattern
  - Clean up test verbs added during debugging
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

SPACEPORT   = 405
WORKSHOP    = 374
XERIS_LZ    = 409
LZ          = 159


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


def rmverb_all(s, obj, name):
    """Remove ALL verbs with this name from obj."""
    for _ in range(5):
        out = send(s, f'@rmverb #{obj}:{name}', wait=0.6)
        send(s, 'yes', wait=0.4)
        if 'no verb' in out.lower() or 'no such' in out.lower() or 'removed' not in out.lower():
            break


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
# Launch verb (on spaceport room #405) — single any none none
# ---------------------------------------------------------------------------

LAUNCH_VERB = [
    '"Launch the colony transport to another world.";',
    '"Usage: launch [destination name or number]";',
    'pad = #408;',
    'if (!valid(pad))',
    '  player:tell("The launch pad is not operational.");',
    '  return;',
    'endif',
    'if (dobjstr == "")',
    '  player:tell("=== COLONY TRANSPORT SYSTEM ===");',
    '  player:tell("Available destinations:");',
    '  i = 1;',
    '  for d in (pad.destinations)',
    '    player:tell("  " + tostr(i) + ". " + d[1] + " - " + d[2]);',
    '    i = i + 1;',
    '  endfor',
    '  player:tell("Usage: launch <name or number>");',
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
    '  player:tell("Type \'launch\' for available destinations.");',
    '  return;',
    'endif',
    'dest_room = dest[3];',
    'if (!valid(dest_room))',
    '  player:tell("That destination is currently unavailable.");',
    '  return;',
    'endif',
    'player:tell("You board the colony transport and strap in. Engines ignite.");',
    'player.location:announce(player.name + " boards the colony transport.", player);',
    'move(player, dest_room);',
    'player:tell("After a brutal transit burn, you arrive at " + dest[1] + ".");',
    'player.location:announce(player.name + " arrives on the transport.", player);',
]


# ---------------------------------------------------------------------------
# Launch return verb (on Xeris Prime #409)
# ---------------------------------------------------------------------------

XERIS_RETURN = [
    '"Launch back toward Kepler-7 Colony.";',
    f'player:tell("You board the supply shuttle. Engines burn hot through the atmosphere.");',
    f'player.location:announce(player.name + " boards the shuttle and lifts off.", player);',
    f'move(player, #{LZ});',
    f'player:tell("After a cold transit burn, you arrive at Kepler-7 Colony.");',
    f'player.location:announce(player.name + " arrives on the shuttle.", player);',
]


# ---------------------------------------------------------------------------
# Craft verb (on workshop room #374) — single any none none
# ---------------------------------------------------------------------------

CRAFT_VERB = [
    '"Craft an item at the fabricator using materials in your inventory.";',
    '"Usage: craft [item name]";',
    'if (dobjstr == "")',
    '  player:tell("=== FABRICATOR UNIT - RECIPES ===");',
    '  player:tell("  metal plate      - 2 ore samples");',
    '  player:tell("  rope             - 3 alien plant fibers");',
    '  player:tell("  water filter     - 1 ore sample + 1 alien plant fiber");',
    '  player:tell("  structural panel - 1 metal plate + 1 alien plant fiber");',
    '  player:tell("  purified water   - 1 raw water + 1 water filter");',
    '  player:tell("Usage: craft <item>");',
    '  return;',
    'endif',
    'tgt = dobjstr;',
    '"--- metal plate ---";',
    'if (index(tgt, "metal") || index(tgt, "plate"))',
    '  found = {};',
    '  for item in (player.contents)',
    '    if (length(found) < 2)',
    '      if (index(item.name, "ore") || ("ore" in item.aliases))',
    '        found = listappend(found, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 2)',
    '    player:tell("Need 2 ore samples. You have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]);',
    '  recycle(found[2]);',
    '  result = create($thing);',
    '  result.name = "metal plate";',
    '  result.aliases = {"plate", "metal"};',
    '  result.description = "A flat panel of smelted alien ore. Used in colony construction.";',
    '  move(result, player);',
    '  player:tell("The fabricator hums. You produce a metal plate.");',
    '  return;',
    'endif',
    '"--- rope ---";',
    'if (index(tgt, "rope") || index(tgt, "cord"))',
    '  found = {};',
    '  for item in (player.contents)',
    '    if (length(found) < 3)',
    '      if (index(item.name, "fiber") || ("fiber" in item.aliases))',
    '        found = listappend(found, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 3)',
    '    player:tell("Need 3 alien plant fibers. You have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]);',
    '  recycle(found[2]);',
    '  recycle(found[3]);',
    '  result = create($thing);',
    '  result.name = "rope";',
    '  result.aliases = {"rope", "cord", "line"};',
    '  result.description = "Braided alien plant fiber rope. Strong and light.";',
    '  move(result, player);',
    '  player:tell("The fabricator weaves the fibers into rope.");',
    '  return;',
    'endif',
    '"--- water filter ---";',
    'if (index(tgt, "filter"))',
    '  ore_item = 0; fiber_item = 0;',
    '  for item in (player.contents)',
    '    if (!ore_item && (index(item.name, "ore") || ("ore" in item.aliases)))',
    '      ore_item = item;',
    '    elseif (!fiber_item && (index(item.name, "fiber") || ("fiber" in item.aliases)))',
    '      fiber_item = item;',
    '    endif',
    '  endfor',
    '  if (!ore_item)',
    '    player:tell("Need 1 ore sample.");',
    '    return;',
    '  endif',
    '  if (!fiber_item)',
    '    player:tell("Need 1 alien plant fiber.");',
    '    return;',
    '  endif',
    '  recycle(ore_item);',
    '  recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "water filter";',
    '  result.aliases = {"filter", "purifier"};',
    '  result.description = "Ore mesh and fiber filter. Purifies raw water.";',
    '  move(result, player);',
    '  player:tell("The fabricator produces a water filter.");',
    '  return;',
    'endif',
    '"--- structural panel ---";',
    'if (index(tgt, "structural") || index(tgt, "panel"))',
    '  plate_item = 0; fiber_item = 0;',
    '  for item in (player.contents)',
    '    if (!plate_item && item.name == "metal plate")',
    '      plate_item = item;',
    '    elseif (!fiber_item && (index(item.name, "fiber") || ("fiber" in item.aliases)))',
    '      fiber_item = item;',
    '    endif',
    '  endfor',
    '  if (!plate_item)',
    '    player:tell("Need a metal plate.");',
    '    return;',
    '  endif',
    '  if (!fiber_item)',
    '    player:tell("Need an alien plant fiber.");',
    '    return;',
    '  endif',
    '  recycle(plate_item);',
    '  recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "structural panel";',
    '  result.aliases = {"panel", "structural", "strut"};',
    '  result.description = "Reinforced composite panel. Used in building construction.";',
    '  move(result, player);',
    '  player:tell("The fabricator assembles a structural panel.");',
    '  return;',
    'endif',
    '"--- purified water ---";',
    'if (index(tgt, "purif") || (index(tgt, "water") && index(tgt, "filter")))',
    '  water_item = 0; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (!water_item && index(item.name, "raw"))',
    '      water_item = item;',
    '    elseif (!filter_item && ("filter" in item.aliases))',
    '      filter_item = item;',
    '    endif',
    '  endfor',
    '  if (!water_item)',
    '    player:tell("Need raw water.");',
    '    return;',
    '  endif',
    '  if (!filter_item)',
    '    player:tell("Need a water filter.");',
    '    return;',
    '  endif',
    '  recycle(water_item);',
    '  recycle(filter_item);',
    '  result = create($thing);',
    '  result.name = "purified water";',
    '  result.aliases = {"water", "drink", "purified"};',
    '  result.description = "Filtered, safe drinking water. Colony standard.";',
    '  move(result, player);',
    '  player:tell("The filter removes contaminants. You have purified water.");',
    '  return;',
    'endif',
    'player:tell("Unknown recipe: " + tgt);',
    'player:tell("Type \'craft\' for available recipes.");',
]


if __name__ == '__main__':
    print('Wayfar 1444 - Final Verb Fix')
    print('=' * 60)

    s = connect()

    # Remove stale test verbs from LZ room
    print('\n=== Cleaning test verbs from #159 ===')
    rmverb_all(s, LZ, 'testcmd')

    # --- LAUNCH: clean slate, single any none none on spaceport room ---
    print(f'\n=== Launch verb on spaceport #{SPACEPORT} ===')
    rmverb_all(s, SPACEPORT, 'launch')
    send(s, f'@verb #{SPACEPORT}:launch any none none', wait=0.5)
    program_verb(s, SPACEPORT, 'launch', LAUNCH_VERB)
    print(f'  launch (any none none) programmed on #{SPACEPORT}')

    # --- LAUNCH RETURN: clean slate on Xeris ---
    print(f'\n=== Launch return on Xeris #{XERIS_LZ} ===')
    rmverb_all(s, XERIS_LZ, 'launch')
    send(s, f'@verb #{XERIS_LZ}:launch any none none', wait=0.5)
    program_verb(s, XERIS_LZ, 'launch', XERIS_RETURN)
    print(f'  launch return programmed on #{XERIS_LZ}')

    # --- CRAFT: clean slate, single any none none on workshop room ---
    print(f'\n=== Craft verb on workshop #{WORKSHOP} ===')
    rmverb_all(s, WORKSHOP, 'craft')
    send(s, f'@verb #{WORKSHOP}:craft any none none', wait=0.5)
    program_verb(s, WORKSHOP, 'craft', CRAFT_VERB)
    print(f'  craft (any none none) programmed on #{WORKSHOP}')

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\nAll verbs fixed. Commands:')
    print('  launch                  (in Spaceport) - show destinations')
    print('  launch xeris            (in Spaceport) - fly to Xeris Prime')
    print('  launch                  (on Xeris)     - return to colony')
    print('  craft                   (in Workshop)  - show recipes')
    print('  craft metal plate       (in Workshop)  - fabricate item')
