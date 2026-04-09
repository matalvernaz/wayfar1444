#!/usr/bin/env python3
"""
fix_food.py — Fix eat verb and craft verb to use name-based detection.

The aliases property cannot be set on $thing children (c flag missing),
so all checks like '"ration" in found.aliases' silently fail.

Fixes:
  1. EAT_VERB on $player (#6):
     - Gate check: index(found.name, "ration") OR index(found.name, "purified water")
     - Nourish/heal: name-based instead of alias-based
  2. CRAFT_VERB on Workshop (#505):
     - Filter detection: index(item.name, "filter") instead of "filter" in item.aliases
     - Also fix ore/fiber checks in structural panel recipe

Also adds a 'drink' verb alias that just calls eat.
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

PLAYER   = 6     # $player
WORKSHOP = 505   # Workshop room (from fix_colony.py)


# ---------------------------------------------------------------------------
# Fixed eat verb — name-based food/drink detection
# ---------------------------------------------------------------------------

EAT_VERB = [
    '"Consume a food or drink item from inventory.";',
    '"Usage: eat <item> / drink <item>";',
    'if (dobjstr == "")',
    '  player:tell("Eat what? (Type \'i\' to see what you carry.)");',
    '  return;',
    'endif',
    'found = 0;',
    'for item in (player.contents)',
    '  if (index(item.name, dobjstr))',
    '    found = item;',
    '    break;',
    '  endif',
    'endfor',
    'if (!found)',
    '  player:tell("You are not carrying a \'" + dobjstr + "\'.");',
    '  return;',
    'endif',
    '"--- check if this item is food/drink by name ---";',
    'is_food = 0;',
    'if (index(found.name, "ration"))',
    '  is_food = 1;',
    'elseif (found.name == "purified water" || index(found.name, "purified"))',
    '  is_food = 1;',
    'endif',
    'if (!is_food)',
    '  player:tell("You cannot eat or drink that.");',
    '  return;',
    'endif',
    '"--- determine nourishment ---";',
    'nourish = 0;',
    'heal   = 0;',
    'if (index(found.name, "ration"))',
    '  nourish = 35;',
    '  heal    = 5;',
    'elseif (found.name == "purified water" || index(found.name, "purified"))',
    '  nourish = 20;',
    '  heal    = 3;',
    'else',
    '  nourish = 20;',
    'endif',
    'recycle(found);',
    'new_hunger = player.hunger + nourish;',
    'if (new_hunger > 100)',
    '  new_hunger = 100;',
    'endif',
    'player.hunger = new_hunger;',
    'new_health = player.health + heal;',
    'if (new_health > 100)',
    '  new_health = 100;',
    'endif',
    'player.health = new_health;',
    'player:tell("You consume the " + found.name + ".");',
    'player:tell("  Hunger: " + tostr(player.hunger) + "/100  Health: " + tostr(player.health) + "/100");',
    'player.location:announce(player.name + " eats something.", player);',
]

DRINK_VERB = [
    '"Alias: delegate to eat.";',
    'this:eat(args);',
]


# ---------------------------------------------------------------------------
# Fixed craft verb — name-based ingredient detection throughout
# ---------------------------------------------------------------------------

CRAFT_VERB = [
    '"Craft an item from raw materials in your inventory.";',
    '"Usage: craft [item name]";',
    'if (args == {})',
    '  player:tell("=== FABRICATOR UNIT - RECIPES ===");',
    '  player:tell("  metal plate      - 2 ore samples");',
    '  player:tell("  rope             - 3 alien plant fibers");',
    '  player:tell("  water filter     - 1 ore sample + 1 alien plant fiber");',
    '  player:tell("  structural panel - 1 metal plate + 1 alien plant fiber");',
    '  player:tell("  purified water   - 1 raw water + 1 water filter");',
    '  player:tell("  ration bar       - 2 alien plant fibers (edible)");',
    '  player:tell("Usage: craft <item>");',
    '  return;',
    'endif',
    'tgt = "";',
    'for w in (args)',
    '  if (tgt == "")',
    '    tgt = w;',
    '  else',
    '    tgt = tgt + " " + w;',
    '  endif',
    'endfor',
    '"--- metal plate ---";',
    'if (index(tgt, "metal") || index(tgt, "plate"))',
    '  found = {};',
    '  for item in (player.contents)',
    '    if (length(found) < 2)',
    '      if (index(item.name, "ore"))',
    '        found = listappend(found, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 2)',
    '    player:tell("Need 2 ore samples. You have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]); recycle(found[2]);',
    '  result = create($thing);',
    '  result.name = "metal plate";',
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
    '      if (index(item.name, "fiber"))',
    '        found = listappend(found, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 3)',
    '    player:tell("Need 3 alien plant fibers. You have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]); recycle(found[2]); recycle(found[3]);',
    '  result = create($thing);',
    '  result.name = "rope";',
    '  result.description = "Braided alien plant fiber. Surprisingly strong.";',
    '  move(result, player);',
    '  player:tell("The fabricator weaves the fibers into a length of rope.");',
    '  return;',
    'endif',
    '"--- water filter ---";',
    'if (index(tgt, "filter"))',
    '  ore_item = 0; fiber_item = 0;',
    '  for item in (player.contents)',
    '    if (!ore_item && index(item.name, "ore"))',
    '      ore_item = item;',
    '    elseif (!fiber_item && index(item.name, "fiber"))',
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
    '  recycle(ore_item); recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "water filter";',
    '  result.description = "An improvised filtration unit of compressed ore mesh and fiber matting.";',
    '  move(result, player);',
    '  player:tell("The fabricator produces a water filter unit.");',
    '  return;',
    'endif',
    '"--- structural panel ---";',
    'if (index(tgt, "structural") || index(tgt, "panel"))',
    '  plate_item = 0; fiber_item = 0;',
    '  for item in (player.contents)',
    '    if (!plate_item && item.name == "metal plate")',
    '      plate_item = item;',
    '    elseif (!fiber_item && index(item.name, "fiber"))',
    '      fiber_item = item;',
    '    endif',
    '  endfor',
    '  if (!plate_item)',
    '    player:tell("Need a metal plate. (craft metal plate first)");',
    '    return;',
    '  endif',
    '  if (!fiber_item)',
    '    player:tell("Need an alien plant fiber.");',
    '    return;',
    '  endif',
    '  recycle(plate_item); recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "structural panel";',
    '  result.description = "A reinforced composite panel for colony construction.";',
    '  move(result, player);',
    '  player:tell("The fabricator assembles a structural panel.");',
    '  return;',
    'endif',
    '"--- purified water ---";',
    'if (index(tgt, "purified") || index(tgt, "water"))',
    '  water_item = 0; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (!water_item && index(item.name, "raw water"))',
    '      water_item = item;',
    '    elseif (!filter_item && index(item.name, "filter"))',
    '      filter_item = item;',
    '    endif',
    '  endfor',
    '  if (!water_item)',
    '    player:tell("Need raw water. (gather from a water seep)");',
    '    return;',
    '  endif',
    '  if (!filter_item)',
    '    player:tell("Need a water filter. (craft water filter first)");',
    '    return;',
    '  endif',
    '  recycle(water_item); recycle(filter_item);',
    '  result = create($thing);',
    '  result.name = "purified water";',
    '  result.description = "Filtered colony-standard water, safe to drink.";',
    '  move(result, player);',
    '  player:tell("The filter removes contaminants. You have purified water.");',
    '  return;',
    'endif',
    '"--- ration bar ---";',
    'if (index(tgt, "ration") || index(tgt, "food") || index(tgt, "bar"))',
    '  found = {};',
    '  for item in (player.contents)',
    '    if (length(found) < 2)',
    '      if (index(item.name, "fiber"))',
    '        found = listappend(found, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 2)',
    '    player:tell("Need 2 alien plant fibers. You have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]); recycle(found[2]);',
    '  result = create($thing);',
    '  result.name = "ration bar";',
    '  result.description = "A compressed block of processed alien plant fiber. '
    'Tastes like cardboard with a faint ammonia aftertaste. Calories are calories.";',
    '  move(result, player);',
    '  player:tell("The fabricator compresses the fibers into a ration bar.");',
    '  return;',
    'endif',
    'player:tell("Unknown recipe: " + tgt);',
    'player:tell("Type \'craft\' for available recipes.");',
]


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7)
    try: s.recv(65536)
    except: pass
    return s


def send(s, cmd, wait=0.5):
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


def ev(s, expr, wait=0.5):
    return send(s, f'; {expr}', wait)


def add_and_program(s, obj, verbname, args, code_lines):
    """Delete all copies of verbname on obj, add fresh, program."""
    for _ in range(5):
        pos_out = ev(
            s,
            f'idx = 0; for i in [1..length(verbs(#{obj}))]; '
            f'if (verbs(#{obj})[i] == {repr(verbname)}); idx = i; break; endif; endfor; '
            f'player:tell(tostr(idx))',
            wait=0.6,
        )
        m = re.search(r'(\d+)\r?\n=> 0', pos_out)
        if not m:
            break
        idx = int(m.group(1))
        if idx == 0:
            break
        ev(s, f'delete_verb(#{obj}, {idx})', wait=0.4)
        print(f'  Deleted #{obj}:{verbname} at index {idx}')

    send(s, f'@verb #{obj}:{verbname} {args}', wait=0.5)
    print(f'  Added @verb #{obj}:{verbname} {args}')

    out = send(s, f'@program #{obj}:{verbname}', wait=0.6)
    if 'programming' not in out.lower():
        print(f'  WARN @program: {repr(out[:100])}')
    s.settimeout(0.15)
    for line in code_lines:
        send(s, line, wait=0.03)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:300])}')
        return False
    return True


def check_workshop(s):
    """Return the workshop object number, trying #505 first then scanning."""
    ok = ev(s, f'player:tell(valid(#{WORKSHOP}) ? "yes" | "no")', wait=0.4)
    if 'yes' in ok:
        name = ev(s, f'player:tell(#{WORKSHOP}.name)', wait=0.3)
        print(f'  Workshop #{WORKSHOP}: {name.strip()[:60]}')
        return WORKSHOP

    # Try to find it via #0 global
    out = ev(s, 'player:tell(tostr(#0.colony_workshop))', wait=0.4)
    m = re.search(r'#(\d+)', out)
    if m:
        w = int(m.group(1))
        ok2 = ev(s, f'player:tell(valid(#{w}) ? "yes" | "no")', wait=0.4)
        if 'yes' in ok2:
            print(f'  Workshop via #0.colony_workshop: #{w}')
            return w

    print(f'  WARN: Workshop #{WORKSHOP} is invalid and #0.colony_workshop not found')
    return None


if __name__ == '__main__':
    print('Wayfar 1444 — Fix Food/Craft Chain')
    print('=' * 60)

    s = connect()

    # --- Fix eat verb on $player ---
    print('\n=== Fixing eat verb on $player (#6) ===')
    ok = add_and_program(s, PLAYER, 'eat', 'any none none', EAT_VERB)
    print(f'  eat: {"OK" if ok else "FAIL"}')

    ok = add_and_program(s, PLAYER, 'drink', 'any none none', DRINK_VERB)
    print(f'  drink: {"OK" if ok else "FAIL"}')

    # --- Fix craft verb on Workshop ---
    ws = check_workshop(s)
    if ws:
        print(f'\n=== Fixing craft verb on Workshop (#{ws}) ===')
        ok = add_and_program(s, ws, 'craft', 'any none none', CRAFT_VERB)
        print(f'  craft: {"OK" if ok else "FAIL"}')
    else:
        print('\n  Skipping craft fix — no Workshop found')

    # --- End-to-end test ---
    print('\n=== End-to-end food chain test ===')

    # Give wizard 2 fibers in inventory
    ev(s, 'f1 = create($thing); f1.name = "alien plant fiber"; move(f1, player)', wait=0.4)
    ev(s, 'f2 = create($thing); f2.name = "alien plant fiber"; move(f2, player)', wait=0.4)
    print('  Created 2 alien plant fibers in inventory')

    # Hunger test: set hunger low
    ev(s, 'player.hunger = 10', wait=0.3)
    ev(s, 'player.health = 80', wait=0.3)

    if ws:
        # Go to workshop to craft
        send(s, f'@go #{ws}', wait=0.5)

        # Craft ration bar
        out = send(s, 'craft ration bar', wait=0.8)
        print(f'  craft ration bar: {out.strip()[:120]}')

        # Check inventory
        out2 = send(s, 'i', wait=0.5)
        print(f'  inventory: {out2.strip()[:200]}')

        # Eat the ration bar
        out3 = send(s, 'eat ration', wait=0.6)
        print(f'  eat ration: {out3.strip()[:150]}')
    else:
        # No workshop — test eat directly by creating a ration bar
        ev(s, 'r = create($thing); r.name = "ration bar"; move(r, player)', wait=0.4)
        ev(s, 'player.hunger = 10', wait=0.3)
        out3 = send(s, 'eat ration', wait=0.6)
        print(f'  eat ration (direct): {out3.strip()[:150]}')

    # Check vitals
    out4 = send(s, 'vitals', wait=0.5)
    print(f'  vitals: {out4.strip()[:200]}')

    # --- Save ---
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.5)
    print(out.strip()[:80])

    s.sendall(b'QUIT\r\n')
    s.close()
    print('\nDone.')
