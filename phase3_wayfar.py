#!/usr/bin/env python3
"""
Wayfar 1444 - Phase 3

Adds:
  - Player survival stats: hunger / health / stamina on $player
  - 'vitals' command to check stats
  - 'eat' / 'drink' verbs (consume food/water items)
  - 'ration bar' craftable recipe (2 fiber -> food)
  - Heartbeat object: decays stats for all connected players every 5 min
  - Building system: 'build <structure>' in LZ / wilderness rooms
      hab dome    - 3 structural panels
      generator   - 2 ore samples + 2 metal plates
      med station - 2 structural panels + 1 water filter
  - 2 NPCs in Colony Hub: Sergeant Vera + Doc Harlan
      talk <npc> for contextual dialogue

Run with server live:  python3 phase3_wayfar.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

# Known room numbers from Phase 2
LZ      = 159
HUB     = 157
WORKSHOP = 374

# ---------------------------------------------------------------------------
# Transport helpers (identical pattern to expand_wayfar.py)
# ---------------------------------------------------------------------------

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


def goto(s, obj_num):
    send(s, f'@go #{obj_num}', wait=0.5)


def here(s):
    out = ev(s, 'player:tell(tostr(player.location))', wait=0.35)
    m = re.search(r'#(\d+)', out)
    return int(m.group(1)) if m else None


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def moo_list_str(lst):
    return '{' + ', '.join(moo_str(x) for x in lst) + '}'


def create_item(s, name_spec, in_room):
    out = send(s, f'@create $thing named {name_spec}', wait=0.8)
    m = re.search(r'object number #(\d+)', out)
    if m:
        num = int(m.group(1))
        send(s, f'@move #{num} to #{in_room}', wait=0.5)
        return num
    print(f'  WARN @create {name_spec}: {repr(out[:200])}')
    return None


def describe(s, num, text):
    out = send(s, f'@describe #{num} as {moo_str(text)}', wait=0.6)
    if 'Description set' not in out:
        print(f'  WARN describe #{num}: {repr(out[:100])}')


def rename(s, num, name):
    send(s, f'@rename #{num} to {moo_str(name)}', wait=0.5)


def init_prop(s, obj, prop, value_moo):
    return ev(s,
        f'add_property(#{obj}, {moo_str(prop)}, {value_moo}, {{player, "rc"}})',
        wait=0.4)


def set_prop(s, obj, prop, value_moo):
    return ev(s, f'#{obj}.{prop} = {value_moo}', wait=0.35)


def add_verb(s, obj, verbname, args='this none none'):
    return send(s, f'@verb #{obj}:{verbname} {args}', wait=0.5)


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


def recycle(s, num):
    send(s, f'@recycle #{num}', wait=0.6)
    send(s, 'yes', wait=0.5)


def cleanup_objects(s, obj_nums):
    for n in obj_nums:
        out = ev(s, f'player:tell(valid(#{n}) ? {moo_str("yes")} + #{n}.name | {moo_str("no")})', wait=0.3)
        if 'yes' in out:
            recycle(s, n)
            print(f'  recycled #{n}')


# ---------------------------------------------------------------------------
# 1.  Player stats on $player
# ---------------------------------------------------------------------------

VITALS_VERB = [
    '"Show the player their current survival stats.";',
    'h = player.hunger;',
    'hp = player.health;',
    'st = player.stamina;',
    '"--- hunger label ---";',
    'if (h > 70)',
    '  hlabel = "GOOD";',
    'elseif (h > 40)',
    '  hlabel = "FAIR";',
    'elseif (h > 20)',
    '  hlabel = "LOW";',
    'else',
    '  hlabel = "CRITICAL";',
    'endif',
    '"--- health label ---";',
    'if (hp > 70)',
    '  hplabel = "GOOD";',
    'elseif (hp > 40)',
    '  hplabel = "FAIR";',
    'elseif (hp > 20)',
    '  hplabel = "LOW";',
    'else',
    '  hplabel = "CRITICAL";',
    'endif',
    '"--- stamina label ---";',
    'if (st > 70)',
    '  stlabel = "HIGH";',
    'elseif (st > 40)',
    '  stlabel = "FAIR";',
    'elseif (st > 20)',
    '  stlabel = "LOW";',
    'else',
    '  stlabel = "EXHAUSTED";',
    'endif',
    'player:tell("=== VITALS ===");',
    'player:tell("  Hunger  : " + tostr(h) + "/100  [" + hlabel + "]");',
    'player:tell("  Health  : " + tostr(hp) + "/100  [" + hplabel + "]");',
    'player:tell("  Stamina : " + tostr(st) + "/100  [" + stlabel + "]");',
    'if (h <= 0)',
    '  player:tell("  ** You are starving. Find food immediately. **");',
    'endif',
    'if (hp <= 20)',
    '  player:tell("  ** You are critically injured. Rest or find the Med Bay. **");',
    'endif',
]

EAT_VERB = [
    '"Eat or drink a food item from your inventory.";',
    '"Usage: eat <item>";',
    'if (dobjstr == "")',
    '  player:tell("Eat what? (Type \'inventory\' to see what you are carrying.)");',
    '  return;',
    'endif',
    'found = 0;',
    'for item in (player.contents)',
    '  if (index(item.name, dobjstr) || (dobjstr in item.aliases))',
    '    found = item;',
    '    break;',
    '  endif',
    'endfor',
    'if (!found)',
    '  player:tell("You are not carrying a \'" + dobjstr + "\'.");',
    '  return;',
    'endif',
    'if (!("edible" in found.aliases) && !("food" in found.aliases) && !("drink" in found.aliases))',
    '  player:tell("You cannot eat that.");',
    '  return;',
    'endif',
    '"--- determine nourishment value ---";',
    'nourish = 0;',
    'heal = 0;',
    'if ("ration" in found.aliases)',
    '  nourish = 35;',
    '  heal = 5;',
    'elseif ("purified" in found.aliases || "water" in found.aliases)',
    '  nourish = 20;',
    '  heal = 3;',
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
    'player:tell("You consume the " + found.name + ". Hunger: " + tostr(player.hunger) + "/100");',
    'player.location:announce(player.name + " eats something.", player);',
]

DRINK_VERB = [
    '"Alias of eat for liquids.";',
    'this:eat(args);',
]

REST_VERB = [
    '"Rest to recover stamina.";',
    '"Usage: rest";',
    'if (player.stamina >= 100)',
    '  player:tell("You feel fully rested already.");',
    '  return;',
    'endif',
    'recover = 25;',
    'new_st = player.stamina + recover;',
    'if (new_st > 100)',
    '  new_st = 100;',
    'endif',
    'player.stamina = new_st;',
    'player:tell("You rest for a while. Stamina: " + tostr(player.stamina) + "/100");',
    'player.location:announce(player.name + " sits down to rest.", player);',
]


def setup_player_stats(s):
    print('\n=== Setting up player stats on $player ===')

    # Find $player object number
    out = ev(s, 'player:tell(tostr($player))', wait=0.4)
    m = re.search(r'#(\d+)', out)
    player_class = int(m.group(1)) if m else 2
    print(f'  $player is #{player_class}')

    # Add properties (skip if already exist — re-running script)
    for prop, default in [('hunger', '100'), ('health', '100'), ('stamina', '100')]:
        out = ev(s, f'player:tell(tostr(#{player_class}.{prop}))', wait=0.3)
        if 'Property not found' in out or 'E_PROPNF' in out or out.strip() == '':
            init_prop(s, player_class, prop, default)
            print(f'  Added .{prop} = {default} to #{player_class}')
        else:
            print(f'  .{prop} already exists on #{player_class}, skipping')

    # Add vitals verb
    add_verb(s, player_class, 'vitals', 'none none none')
    program_verb(s, player_class, 'vitals', VITALS_VERB)
    print('  vitals verb added')

    # Add eat verb (any none none for free-text dobj)
    add_verb(s, player_class, 'eat', 'any none none')
    program_verb(s, player_class, 'eat', EAT_VERB)
    print('  eat verb added')

    # Add drink as alias
    add_verb(s, player_class, 'drink', 'any none none')
    program_verb(s, player_class, 'drink', DRINK_VERB)
    print('  drink verb added')

    # Add rest verb
    add_verb(s, player_class, 'rest', 'none none none')
    program_verb(s, player_class, 'rest', REST_VERB)
    print('  rest verb added')

    return player_class


# ---------------------------------------------------------------------------
# 2.  Heartbeat decay object
# ---------------------------------------------------------------------------

HEARTBEAT_TICK = [
    '"Decay survival stats for all connected players. Re-schedules itself.";',
    'set_task_perms(this.owner);',
    'for p in (connected_players())',
    '  "--- hunger decay ---";',
    '  nh = p.hunger - 4;',
    '  if (nh < 0)',
    '    nh = 0;',
    '  endif',
    '  p.hunger = nh;',
    '  "--- stamina recovers slightly if hunger is ok, otherwise falls ---";',
    '  if (p.hunger > 30)',
    '    ns = p.stamina + 2;',
    '    if (ns > 100)',
    '      ns = 100;',
    '    endif',
    '  else',
    '    ns = p.stamina - 3;',
    '    if (ns < 0)',
    '      ns = 0;',
    '    endif',
    '  endif',
    '  p.stamina = ns;',
    '  "--- health falls when starving ---";',
    '  if (p.hunger == 0)',
    '    nhp = p.health - 5;',
    '    if (nhp < 0)',
    '      nhp = 0;',
    '    endif',
    '    p.health = nhp;',
    '    p:tell("[SURVIVAL] You are starving. Find food.");',
    '  elseif (p.hunger < 20)',
    '    p:tell("[SURVIVAL] Warning: hunger low (" + tostr(p.hunger) + "/100).");',
    '  endif',
    'endfor',
    '"--- NPC idle chatter ---";',
    'this:npc_idle();',
    '"--- re-schedule in 300 seconds (5 min) ---";',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

HEARTBEAT_START = [
    '"Start the survival heartbeat loop.";',
    'player:tell("Survival monitor starting (5-minute decay cycle).");',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

# NPC idle lines are set as a property, indexed per NPC
HEARTBEAT_NPC_IDLE = [
    '"Fire random idle chatter for NPCs in hub.";',
    'for npc in (this.npcs)',
    '  if (!valid(npc))',
    '    break;',
    '  endif',
    '  lines = npc.idle_lines;',
    '  if (length(lines) == 0)',
    '    break;',
    '  endif',
    '  idx = random(length(lines));',
    '  npc.location:announce(npc.name + " says, \\"" + lines[idx] + "\\"");',
    'endfor',
]


def setup_heartbeat(s, hub_num):
    print(f'\n=== Setting up heartbeat object in #{hub_num} ===')

    num = create_item(s, '"survival monitor:heartbeat,monitor,hb"', hub_num)
    if not num:
        print('  FATAL could not create heartbeat object')
        return None

    describe(s, num, (
        'A wall-mounted colony systems monitor. Status indicators show power, '
        'atmospheric readings, and colonist biometrics. It hums quietly.'
    ))

    # npcs list property (filled later by setup_npcs)
    init_prop(s, num, 'npcs', '{}')

    add_verb(s, num, 'tick', 'this none none')
    program_verb(s, num, 'tick', HEARTBEAT_TICK)

    add_verb(s, num, 'start', 'this none none')
    program_verb(s, num, 'start', HEARTBEAT_START)

    add_verb(s, num, 'npc_idle', 'this none none')
    program_verb(s, num, 'npc_idle', HEARTBEAT_NPC_IDLE)

    print(f'  #{num}: survival monitor -> #{hub_num}')
    return num


# ---------------------------------------------------------------------------
# 3.  Building system — build verb on wilderness/LZ rooms
# ---------------------------------------------------------------------------

BUILD_VERB = [
    '"Construct a colony structure from materials in your inventory.";',
    '"Usage: build <structure name> | build (list)";',
    'if (dobjstr == "" || dobjstr == "list")',
    '  player:tell("=== COLONY CONSTRUCTION ===");',
    '  player:tell("  hab dome    - 3 structural panels");',
    '  player:tell("  generator   - 2 ore samples + 2 metal plates");',
    '  player:tell("  med station - 2 structural panels + 1 water filter");',
    '  player:tell("Usage: build <structure>");',
    '  return;',
    'endif',
    'tgt = dobjstr;',
    '"--- HAB DOME ---";',
    'if (index(tgt, "hab") || index(tgt, "dome") || index(tgt, "shelter"))',
    '  panels = {};',
    '  for item in (player.contents)',
    '    if (length(panels) < 3)',
    '      if (item.name == "structural panel" || ("panel" in item.aliases))',
    '        panels = listappend(panels, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(panels) < 3)',
    '    player:tell("Need 3 structural panels. You have: " + tostr(length(panels)));',
    '    return;',
    '  endif',
    '  for p in (panels)',
    '    recycle(p);',
    '  endfor',
    '  dome = create($thing);',
    '  dome.name = "hab dome";',
    '  dome.aliases = {"hab", "dome", "shelter", "habitat"};',
    '  dome.description = "A collapsible pressurized hab dome assembled from structural panels. "',
    '    + "Just large enough for two colonists. The interior smells of recycled air. "',
    '    + "Sleeping here will restore stamina more effectively. Type \'enter dome\' to rest inside.";',
    '  move(dome, player.location);',
    '  player:tell("You assemble the structural panels into a hab dome. It pressurizes with a hiss.");',
    '  player.location:announce(player.name + " constructs a hab dome.", player);',
    '  return;',
    'endif',
    '"--- GENERATOR ---";',
    'if (index(tgt, "generator") || index(tgt, "power") || index(tgt, "gen"))',
    '  ores = {}; plates = {};',
    '  for item in (player.contents)',
    '    if (length(ores) < 2)',
    '      if (index(item.name, "ore") || ("ore" in item.aliases))',
    '        ores = listappend(ores, item);',
    '      endif',
    '    endif',
    '    if (length(plates) < 2)',
    '      if (item.name == "metal plate" || ("plate" in item.aliases))',
    '        plates = listappend(plates, item);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(ores) < 2)',
    '    player:tell("Need 2 ore samples. You have: " + tostr(length(ores)));',
    '    return;',
    '  endif',
    '  if (length(plates) < 2)',
    '    player:tell("Need 2 metal plates. You have: " + tostr(length(plates)));',
    '    return;',
    '  endif',
    '  recycle(ores[1]); recycle(ores[2]);',
    '  recycle(plates[1]); recycle(plates[2]);',
    '  gen = create($thing);',
    '  gen.name = "power generator";',
    '  gen.aliases = {"generator", "power", "gen"};',
    '  gen.description = "A compact ore-fueled power generator bolted to the ground. "',
    '    + "It hums steadily, feeding power to nearby colony systems. "',
    '    + "Colony output is improved while this is running.";',
    '  move(gen, player.location);',
    '  player:tell("You assemble and start the power generator. It rumbles to life.");',
    '  player.location:announce(player.name + " installs a power generator.", player);',
    '  return;',
    'endif',
    '"--- MED STATION ---";',
    'if (index(tgt, "med") || index(tgt, "station") || index(tgt, "infirmary"))',
    '  panels = {}; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (length(panels) < 2)',
    '      if (item.name == "structural panel" || ("panel" in item.aliases))',
    '        panels = listappend(panels, item);',
    '      endif',
    '    endif',
    '    if (!filter_item)',
    '      if (item.name == "water filter" || ("filter" in item.aliases))',
    '        filter_item = item;',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(panels) < 2)',
    '    player:tell("Need 2 structural panels. You have: " + tostr(length(panels)));',
    '    return;',
    '  endif',
    '  if (!filter_item)',
    '    player:tell("Need 1 water filter.");',
    '    return;',
    '  endif',
    '  recycle(panels[1]); recycle(panels[2]);',
    '  recycle(filter_item);',
    '  med = create($thing);',
    '  med.name = "med station";',
    '  med.aliases = {"med", "station", "medical", "infirmary"};',
    '  med.description = "A field-erected medical station: folding cot, basic surgical kit, "',
    '    + "and a purification unit repurposed as a sterile-water source. "',
    '    + "Type \'treat\' here to restore health.";',
    '  move(med, player.location);',
    '  player:tell("You construct a field med station. The filtration unit is now handling sterile supply.");',
    '  player.location:announce(player.name + " erects a med station.", player);',
    '  return;',
    'endif',
    'player:tell("Unknown structure: " + tgt);',
    'player:tell("Type \'build\' for available structures.");',
]

TREAT_VERB = [
    '"Use a med station in the room to restore health.";',
    'med = 0;',
    'for item in (player.location.contents)',
    '  if (item.name == "med station" || ("med" in item.aliases))',
    '    med = item;',
    '    break;',
    '  endif',
    'endfor',
    'if (!med)',
    '  player:tell("There is no med station here.");',
    '  return;',
    'endif',
    'new_hp = player.health + 30;',
    'if (new_hp > 100)',
    '  new_hp = 100;',
    'endif',
    'player.health = new_hp;',
    'player:tell("The med station patches your wounds. Health: " + tostr(player.health) + "/100");',
    'player.location:announce(player.name + " uses the med station.", player);',
]


def setup_building_system(s, player_class):
    """Add build verb to $player (any none none) + treat verb."""
    print('\n=== Setting up building system ===')

    add_verb(s, player_class, 'build', 'any none none')
    program_verb(s, player_class, 'build', BUILD_VERB)
    print('  build verb added to $player')

    add_verb(s, player_class, 'treat', 'none none none')
    program_verb(s, player_class, 'treat', TREAT_VERB)
    print('  treat verb added to $player')


# ---------------------------------------------------------------------------
# 4.  Update crafting: add ration bar recipe + aliases on purified water
# ---------------------------------------------------------------------------

# We re-program the craft verb on the room (#374) to add ration bar.
# Re-use the existing pattern: any none none on room.

CRAFT_VERB_V2 = [
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
    '      if (index(item.name, "ore") || ("ore" in item.aliases))',
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
    '  recycle(found[1]); recycle(found[2]); recycle(found[3]);',
    '  result = create($thing);',
    '  result.name = "rope";',
    '  result.aliases = {"rope", "cord", "line"};',
    '  result.description = "Braided alien plant fiber. Surprisingly strong.";',
    '  move(result, player);',
    '  player:tell("The fabricator weaves the fibers into a length of rope.");',
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
    '  recycle(ore_item); recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "water filter";',
    '  result.aliases = {"filter", "purifier"};',
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
    '  recycle(plate_item); recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "structural panel";',
    '  result.aliases = {"panel", "structural", "strut"};',
    '  result.description = "A reinforced composite panel for colony construction.";',
    '  move(result, player);',
    '  player:tell("The fabricator assembles a structural panel.");',
    '  return;',
    'endif',
    '"--- purified water ---";',
    'if (index(tgt, "purified") || (index(tgt, "water") && index(tgt, "purif")))',
    '  water_item = 0; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (!water_item && (item.name == "raw water" || index(item.name, "raw")))',
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
    '  recycle(water_item); recycle(filter_item);',
    '  result = create($thing);',
    '  result.name = "purified water";',
    '  result.aliases = {"water", "drink", "purified", "edible"};',
    '  result.description = "Filtered colony-standard water, safe to drink.";',
    '  move(result, player);',
    '  player:tell("The filter removes contaminants. You now have purified water.");',
    '  return;',
    'endif',
    '"--- ration bar ---";',
    'if (index(tgt, "ration") || index(tgt, "food") || index(tgt, "bar"))',
    '  found = {};',
    '  for item in (player.contents)',
    '    if (length(found) < 2)',
    '      if (index(item.name, "fiber") || ("fiber" in item.aliases))',
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
    '  result.aliases = {"ration", "bar", "food", "edible"};',
    '  result.description = "A compressed block of processed alien plant fiber, dried and formed into a dense bar. "',
    '    + "Tastes like cardboard with a faint ammonia aftertaste. Calories are calories.";',
    '  move(result, player);',
    '  player:tell("The fabricator compresses the fibers into a ration bar.");',
    '  return;',
    'endif',
    'player:tell("Unknown recipe: " + tgt);',
    'player:tell("Type \'craft\' for available recipes.");',
]


def update_crafting(s, workshop_num):
    """Re-program the craft verb on the fabricator object in the workshop."""
    print(f'\n=== Updating crafting recipes in #{workshop_num} ===')

    # Find the fabricator object number
    out = ev(s, (
        'for item in (#' + str(workshop_num) + '.contents):'
        '  if (index(item.name, "fabricator")): player:tell(tostr(item)); break; endif;'
        'endfor'
    ), wait=0.5)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  WARN could not find fabricator in #{workshop_num}')
        return

    fab_num = int(m.group(1))
    print(f'  Fabricator is #{fab_num}')

    # Re-program the first craft verb (any none none)
    # In HellCore @program targets the first verb matching the name.
    # The any-none-none form was the second added, but both were named 'craft'.
    # We'll just re-program whichever one @program hits.
    program_verb(s, fab_num, 'craft', CRAFT_VERB_V2)
    print(f'  craft verb updated on #{fab_num}')


# ---------------------------------------------------------------------------
# 5.  NPCs — Sergeant Vera + Doc Harlan in Colony Hub
# ---------------------------------------------------------------------------

VERA_LINES = [
    "Keep your eyes open out there. We're not alone on this rock.",
    "Resource discipline wins colonies. Waste nothing.",
    "I've seen three colonies fail. This one won't.",
    "The Xeris operation lost twenty-two people. We don't talk about why.",
    "Don't trust a clean scanner reading. They lie.",
    "Morning patrol found tracks. Not human.",
    "You sleeping enough? Stamina collapse kills faster than anything out here.",
]

HARLAN_LINES = [
    "Drink your water. Dehydration is the quiet killer.",
    "I'm running low on filter components. Bring me what you find.",
    "That cough going around isn't anything. Probably.",
    "Hunger below twenty and your cognition starts to go. Watch for it.",
    "I used to practice on Earth. Colony medicine is... creative.",
    "The xenocrystals have unusual bioelectric properties. I'm still testing.",
    "Sleep matters. The body repairs itself. So does the mind.",
]

TALK_VERB = [
    '"Talk to this NPC.";',
    '"Usage: talk <npc name>";',
    'lines = this.talk_lines;',
    'if (length(lines) == 0)',
    '  player:tell(this.name + " has nothing to say.");',
    '  return;',
    'endif',
    'idx = random(length(lines));',
    'player:tell(this.name + " says, \\"" + lines[idx] + "\\"");',
    'player.location:announce(player.name + " speaks with " + this.name + ".", player);',
]

LOOK_VERB = [
    '"Look at or examine this NPC.";',
    'player:tell(this.name);',
    'player:tell(this.description);',
    'player:tell("Type \'talk " + this.name + "\' to speak with them.");',
]


def create_npc(s, room, name, aliases, desc, talk_lines):
    alias_str = ','.join(aliases)
    num = create_item(s, f'"{name}:{alias_str}"', room)
    if not num:
        print(f'  FATAL could not create NPC: {name}')
        return None

    describe(s, num, desc)

    # Talk lines as a property
    lines_moo = moo_list_str(talk_lines)
    init_prop(s, num, 'talk_lines', lines_moo)

    # Idle lines (same lines, NPC will randomly announce one)
    init_prop(s, num, 'idle_lines', moo_list_str(talk_lines[:4]))

    add_verb(s, num, 'talk', 'this none none')
    program_verb(s, num, 'talk', TALK_VERB)

    add_verb(s, num, 'look', 'this none none')
    program_verb(s, num, 'look', LOOK_VERB)

    print(f'  #{num}: {name} -> #{room}')
    return num


def setup_npcs(s, hub_num, heartbeat_num):
    print(f'\n=== Creating NPCs in #{hub_num} ===')

    vera = create_npc(
        s, hub_num,
        name='Sergeant Vera',
        aliases=['vera', 'sergeant', 'sgt', 'soldier'],
        desc=(
            'Sergeant Vera is built like a bulkhead: short, broad-shouldered, '
            'and seemingly impervious to cold. Her standard-issue colony uniform '
            'is immaculate despite everything. A deep scar runs from her left ear '
            'to her jawline — she has never explained it. '
            'She watches the room with the fixed attention of someone waiting for trouble.'
        ),
        talk_lines=VERA_LINES,
    )

    harlan = create_npc(
        s, hub_num,
        name='Doc Harlan',
        aliases=['harlan', 'doc', 'doctor', 'medic'],
        desc=(
            'Doc Harlan is tall and thin, permanently stooped as though always '
            'about to lean over a patient. His lab coat is layered over colony '
            'thermals and covered in pockets, all of them full. '
            'He wears reading lenses pushed up on his forehead. '
            'He moves with quiet precision and speaks the same way.'
        ),
        talk_lines=HARLAN_LINES,
    )

    # Register NPCs with the heartbeat
    if vera and harlan and heartbeat_num:
        ev(s, f'#{heartbeat_num}.npcs = {{#{vera}, #{harlan}}}', wait=0.4)
        print(f'  NPCs registered on heartbeat #{heartbeat_num}')

    return vera, harlan


# ---------------------------------------------------------------------------
# 6.  Start heartbeat
# ---------------------------------------------------------------------------

def start_heartbeat(s, heartbeat_num):
    print(f'\n=== Starting heartbeat #{heartbeat_num} ===')
    goto(s, HUB)
    out = send(s, f'start #{heartbeat_num}', wait=1.5)
    print(f'  {out.strip()[:80]}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 - Phase 3')
    print('=' * 60)

    s = connect()

    # Clean up any objects from a previous Phase 3 run
    # Phase 2 ended around #417; Phase 3 objects start around #418
    print('\n=== Cleaning up previous Phase 3 objects (if any) ===')
    cleanup_objects(s, range(418, 470))

    player_class = setup_player_stats(s)
    heartbeat = setup_heartbeat(s, HUB)
    setup_building_system(s, player_class)
    update_crafting(s, WORKSHOP)
    vera, harlan = setup_npcs(s, HUB, heartbeat)

    if heartbeat:
        start_heartbeat(s, heartbeat)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Phase 3 complete ===')
    print('New features:')
    print('  vitals            - check hunger / health / stamina')
    print('  eat <item>        - consume edible items')
    print('  drink <item>      - alias for eat')
    print('  rest              - recover stamina')
    print('  treat             - use a nearby med station to heal')
    print('  build <structure> - construct hab dome / generator / med station')
    print('  craft ration bar  - 2 fibers -> edible ration bar')
    print('  talk vera/harlan  - speak to colony NPCs in Hub')
    print('  Heartbeat: stats decay every 5 minutes for connected players')
