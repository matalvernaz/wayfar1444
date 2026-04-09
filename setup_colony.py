#!/usr/bin/env python3
"""
setup_colony.py — Colony Hub + Phase 3 Setup

Builds the Colony Hub structure off Impact Site Zero (#459), then installs
all Phase 3 features: player survival stats, heartbeat decay, building system,
crafting update, and NPCs.

Layout:
  Impact Site Zero (#459)  -- hub/outside verbs --> Colony Hub
  Colony Hub                -- east/west -->         Workshop

Run with server live: python3 setup_colony.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

# Impact Site Zero — always exists, is the anchor
CRASH_SITE = 459


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(0.5)
    time.sleep(0.5)
    try: s.recv(65536)
    except Exception: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8)
    try: s.recv(65536)
    except Exception: pass
    return s


def send(s, cmd, wait=0.3):
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
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.4):
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


def parse_name_spec(name_spec):
    """Parse '"name:alias,alias"' into (name_str, aliases_moo)."""
    name_spec = name_spec.strip('"')
    if ':' in name_spec:
        nm, alias_str = name_spec.split(':', 1)
        aliases = [a.strip() for a in alias_str.split(',')]
    else:
        nm, aliases = name_spec, []
    return nm, '{' + ', '.join(moo_str(a) for a in aliases) + '}'


def create_item(s, name_spec, in_room):
    """Create a $thing with name/aliases and move it to in_room."""
    nm, aliases_moo = parse_name_spec(name_spec)
    out = ev(s,
        f'r = create($thing); r.name = {moo_str(nm)}; r.aliases = {aliases_moo}; '
        f'move(r, #{in_room}); player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if m:
        return int(m.group(1))
    print(f'  WARN create_item {nm}: {repr(out[:200])}')
    return None


def describe(s, num, text):
    ev(s, f'#{num}.description = {moo_str(text)}', wait=0.5)


def rename(s, num, name):
    ev(s, f'#{num}.name = {moo_str(name)}', wait=0.4)


def init_prop(s, obj, prop, value_moo):
    return ev(s,
        f'add_property(#{obj}, {moo_str(prop)}, {value_moo}, {{player, "rc"}})',
        wait=0.4)


def set_prop(s, obj, prop, value_moo):
    return ev(s, f'#{obj}.{prop} = {value_moo}', wait=0.35)


def add_verb(s, obj, verbname, args='this none none'):
    return send(s, f'@verb #{obj}:{verbname} {args}', wait=0.3)


def program_verb(s, obj, verbname, code_lines):
    out = send(s, f'@program #{obj}:{verbname}', wait=0.5)
    if 'programming' not in out.lower():
        print(f'  WARN entering @program #{obj}:{verbname}: {repr(out[:120])}')
    # Tight timeout while streaming lines — server sends nothing until final '.'
    s.settimeout(0.05)
    for line in code_lines:
        send(s, line, wait=0.02)
    s.settimeout(0.5)
    out = send(s, '.', wait=1.5)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
    return out


def recycle_obj(s, num):
    ev(s, f'recycle(#{num})', wait=0.6)


def cleanup_objects(s, obj_nums):
    """Recycle a batch of objects using a single MOO task to avoid timing issues."""
    nums = list(obj_nums)
    batch_size = 10
    recycled = 0
    for i in range(0, len(nums), batch_size):
        batch = nums[i:i + batch_size]
        # Build single MOO statement to check and recycle all in batch
        checks = ' '.join(
            f'if (valid(#{n})) recycle(#{n}); endif' for n in batch
        )
        out = ev(s, checks + ' player:tell("batch_ok")', wait=1.5)
        # Count from tell confirmation
        if 'batch_ok' in out:
            recycled += len(batch)
        else:
            print(f'  WARN cleanup batch {i//batch_size+1}: {repr(out[:80])}')
    print(f'  Cleaned up range (batch mode)')


def make_room(s, name, desc):
    """Create an unlinked room and set name + description."""
    out = ev(s, f'r = create($room); r.name = {moo_str(name)}; player:tell(tostr(r))', wait=1.0)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  WARN create room {name}: {repr(out[:200])}')
        return None
    num = int(m.group(1))
    ev(s, f'#{num}.description = {moo_str(desc)}', wait=0.5)
    return num


def add_dir_verb(s, from_room, verb_name, to_room, msg_leave, msg_arrive):
    """Add a directional movement verb on from_room that moves player to to_room."""
    add_verb(s, from_room, verb_name, 'none none none')
    program_verb(s, from_room, verb_name, [
        f'"Move {verb_name} to #{to_room}.";',
        f'player.location:announce(player.name + " {msg_leave}.", player);',
        f'move(player, #{to_room});',
        f'player.location:announce(player.name + " {msg_arrive}.", player);',
    ])


# ---------------------------------------------------------------------------
# 1.  Build Colony Hub + Workshop
# ---------------------------------------------------------------------------

def build_colony_hub(s):
    print('\n=== Building Colony Hub ===')

    hub = make_room(s,
        'Colony Hub',
        "The colony command centre assembled from the escape pod's integrated shelter kit. "
        "A row of repurposed navigation terminals line one wall, running colony management software. "
        "The air recycler hums. A door to the east leads to the fabrication workshop. "
        "Type 'outside' to return to the surface."
    )
    if not hub:
        print('  FATAL could not create Colony Hub')
        return None, None
    print(f'  Colony Hub: #{hub}')

    workshop = make_room(s,
        'Workshop',
        "The fabrication bay: a cluttered space of salvaged equipment, cabling, and material bins. "
        "The fabricator unit dominates the centre of the room, its interface panel glowing. "
        "A door to the west leads back to the hub."
    )
    if not workshop:
        print('  WARN could not create Workshop')
    else:
        # Link hub <-> workshop with east/west verbs
        add_dir_verb(s, hub, 'east', workshop, 'heads to the workshop', 'arrives from the hub')
        add_dir_verb(s, workshop, 'west', hub, 'heads to the hub', 'arrives from the workshop')
        print(f'  Workshop: #{workshop} (east of Hub)')

    return hub, workshop


# ---------------------------------------------------------------------------
# 2.  Add hub/outside verbs to crash site and hub
# ---------------------------------------------------------------------------

HUB_ENTER_VERB = [
    '"Enter the colony hub from the crash site.";',
    'player:tell("You push through the shelter module airlock into the colony hub.");',
    'player.location:announce(player.name + " enters the colony hub.", player);',
]

HUB_EXIT_VERB = [
    '"Exit the colony hub back to the crash site.";',
    'player:tell("You step back through the airlock to the surface.");',
    'player.location:announce(player.name + " exits to the surface.", player);',
]


def setup_hub_verbs(s, hub, workshop):
    print('\n=== Linking Hub to Impact Site Zero ===')

    # Add 'hub' verb on crash site → hub
    add_verb(s, CRASH_SITE, 'hub', 'none none none')
    program_verb(s, CRASH_SITE, 'hub',
        HUB_ENTER_VERB + [f'move(player, #{hub});'])
    print(f'  hub verb on #{CRASH_SITE} → #{hub}')

    # Add 'outside'/'out' verbs on hub → crash site
    add_verb(s, hub, 'outside', 'none none none')
    program_verb(s, hub, 'outside',
        HUB_EXIT_VERB + [f'move(player, #{CRASH_SITE});'])

    add_verb(s, hub, 'out', 'none none none')
    program_verb(s, hub, 'out', [
        '"Alias for outside.";',
        'this:outside({});',
    ])
    print(f'  outside/out verbs on #{hub} → #{CRASH_SITE}')

    # Store hub reference on crash site
    out = ev(s, f'player:tell(tostr(#{CRASH_SITE}.hub_room))', wait=0.3)
    if 'Property not found' in out or 'E_PROPNF' in out:
        init_prop(s, CRASH_SITE, 'hub_room', f'#{hub}')
    else:
        set_prop(s, CRASH_SITE, 'hub_room', f'#{hub}')


# ---------------------------------------------------------------------------
# 3.  Fabricator in Workshop
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
    'if (index(tgt, "purified") || index(tgt, "water"))',
    '  water_item = 0; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (!water_item && (index(item.name, "raw water") || index(item.name, "raw")))',
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
    '  player:tell("The filter removes contaminants. You have purified water.");',
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
    '  result.description = "A compressed block of processed alien plant fiber. '
    'Tastes like cardboard with a faint ammonia aftertaste. Calories are calories.";',
    '  move(result, player);',
    '  player:tell("The fabricator compresses the fibers into a ration bar.");',
    '  return;',
    'endif',
    'player:tell("Unknown recipe: " + tgt);',
    'player:tell("Type \'craft\' for available recipes.");',
]


def setup_fabricator(s, workshop):
    print(f'\n=== Setting up fabricator in #{workshop} ===')
    goto(s, workshop)

    num = create_item(s, '"fabricator unit:fabricator,fab,maker,machine"', workshop)
    if not num:
        print('  FATAL could not create fabricator')
        return None

    describe(s, num, (
        'A colony-issue fabrication unit roughly the size of a refrigerator, '
        'its casing scratched and stickered over with colony manifest tags. '
        'The interface panel glows amber. A small hopper accepts raw materials; '
        'a tray below collects finished output. Type \'craft\' to see recipes.'
    ))

    add_verb(s, num, 'craft', 'any none none')
    program_verb(s, num, 'craft', CRAFT_VERB)

    # Add look verb
    add_verb(s, num, 'look', 'this none none')
    program_verb(s, num, 'look', [
        '"Examine the fabricator.";',
        'player:tell(this.name);',
        'player:tell(this.description);',
        'player:tell("Type \'craft\' to see recipes.");',
    ])

    print(f'  #{num}: fabricator unit → #{workshop}')
    return num


# ---------------------------------------------------------------------------
# 4.  Player survival stats
# ---------------------------------------------------------------------------

VITALS_VERB = [
    '"Show the player their current survival stats.";',
    'h = player.hunger;',
    'hp = player.health;',
    'st = player.stamina;',
    'if (h > 70)',
    '  hlabel = "GOOD";',
    'elseif (h > 40)',
    '  hlabel = "FAIR";',
    'elseif (h > 20)',
    '  hlabel = "LOW";',
    'else',
    '  hlabel = "CRITICAL";',
    'endif',
    'if (hp > 70)',
    '  hplabel = "GOOD";',
    'elseif (hp > 40)',
    '  hplabel = "FAIR";',
    'elseif (hp > 20)',
    '  hplabel = "LOW";',
    'else',
    '  hplabel = "CRITICAL";',
    'endif',
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
    '  player:tell("  ** Critical health. Rest or find the med station. **");',
    'endif',
]

EAT_VERB = [
    '"Consume a food or drink item.";',
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

REST_VERB = [
    '"Rest to recover stamina.";',
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

STATUS_VERB = [
    '"Show player status including location and biome.";',
    'this:vitals({});',
    '"--- location ---";',
    'if (valid(player.location))',
    '  player:tell("  Location: " + player.location.name);',
    '  if (player.location.x != 0 || player.location.y != 0)',
    '    player:tell("  Coords  : (" + tostr(player.location.x) + ", " + tostr(player.location.y) + ")");',
    '  endif',
    'endif',
]


def setup_player_stats(s):
    print('\n=== Setting up player stats on $player ===')

    out = ev(s, 'player:tell(tostr($player))', wait=0.4)
    m = re.search(r'#(\d+)', out)
    player_class = int(m.group(1)) if m else 6
    print(f'  $player is #{player_class}')

    for prop, default in [('hunger', '100'), ('health', '100'), ('stamina', '100')]:
        out = ev(s, f'player:tell(tostr(#{player_class}.{prop}))', wait=0.3)
        if 'Property not found' in out or 'E_PROPNF' in out:
            init_prop(s, player_class, prop, default)
            print(f'  Added .{prop} = {default}')
        else:
            print(f'  .{prop} already exists, skipping')

    for verbname, args, code in [
        ('vitals', 'none none none', VITALS_VERB),
        ('eat',    'any none none',  EAT_VERB),
        ('drink',  'any none none',  ['"Alias of eat for liquids.";', 'this:eat(args);']),
        ('rest',   'none none none', REST_VERB),
        ('status', 'none none none', STATUS_VERB),
    ]:
        add_verb(s, player_class, verbname, args)
        program_verb(s, player_class, verbname, code)
        print(f'  {verbname} verb added')

    return player_class


# ---------------------------------------------------------------------------
# 5.  Heartbeat decay object
# ---------------------------------------------------------------------------

HEARTBEAT_TICK = [
    '"Decay survival stats for connected players. Re-schedules itself.";',
    'set_task_perms(this.owner);',
    'for p in (connected_players())',
    '  nh = p.hunger - 4;',
    '  if (nh < 0)',
    '    nh = 0;',
    '  endif',
    '  p.hunger = nh;',
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
    '  if (p.health <= 0)',
    '    p.health = 1;',
    '    p.hunger = 50;',
    '    p.stamina = 50;',
    f'   move(p, #{CRASH_SITE});',
    '    p:tell("[DEATH] You collapse. Colony emergency protocol moves you to the crash site.");',
    '  endif',
    'endfor',
    'this:npc_idle();',
    '"--- re-schedule in 300 seconds (5 min) ---";',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

HEARTBEAT_NPC_IDLE = [
    '"Fire random idle chatter for registered NPCs.";',
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


def setup_heartbeat(s, hub):
    print(f'\n=== Setting up heartbeat in #{hub} ===')

    num = create_item(s, '"survival monitor:heartbeat,monitor,hb"', hub)
    if not num:
        print('  FATAL could not create heartbeat object')
        return None

    describe(s, num, (
        'A wall-mounted colony systems monitor. Status indicators show power, '
        'atmospheric readings, and colonist biometrics. It hums quietly.'
    ))

    init_prop(s, num, 'npcs', '{}')

    add_verb(s, num, 'tick', 'this none none')
    program_verb(s, num, 'tick', HEARTBEAT_TICK)

    add_verb(s, num, 'start', 'this none none')
    program_verb(s, num, 'start', [
        '"Start the survival heartbeat loop.";',
        'player:tell("Survival monitor starting (5-minute decay cycle).");',
        'fork (300)',
        '  this:tick();',
        'endfork',
    ])

    add_verb(s, num, 'npc_idle', 'this none none')
    program_verb(s, num, 'npc_idle', HEARTBEAT_NPC_IDLE)

    print(f'  #{num}: survival monitor → #{hub}')
    return num


# ---------------------------------------------------------------------------
# 6.  Building system on $player
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
    '    + "Just large enough for two colonists. The interior smells of recycled air.";',
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
    '  gen.description = "A compact ore-fueled power generator. It hums steadily, '
    'feeding power to nearby colony systems.";',
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
    '  med.description = "A field-erected medical station with a cot, basic surgical kit, '
    'and purification unit. Type \'treat\' to restore health.";',
    '  move(med, player.location);',
    '  player:tell("You construct a field med station.");',
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
    '  if ("med" in item.aliases)',
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
    print('\n=== Setting up building system ===')
    add_verb(s, player_class, 'build', 'any none none')
    program_verb(s, player_class, 'build', BUILD_VERB)
    add_verb(s, player_class, 'treat', 'none none none')
    program_verb(s, player_class, 'treat', TREAT_VERB)
    print('  build + treat verbs added to $player')


# ---------------------------------------------------------------------------
# 7.  NPCs in Colony Hub
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
    'lines = this.talk_lines;',
    'if (length(lines) == 0)',
    '  player:tell(this.name + " has nothing to say.");',
    '  return;',
    'endif',
    'idx = random(length(lines));',
    'player:tell(this.name + " says, \\"" + lines[idx] + "\\"");',
    'player.location:announce(player.name + " speaks with " + this.name + ".", player);',
]

NPC_LOOK_VERB = [
    '"Examine this NPC.";',
    'player:tell(this.name);',
    'player:tell(this.description);',
    'player:tell("Type \'talk " + this.name + "\' to speak with them.");',
]


def create_npc(s, room, name, aliases, desc, talk_lines):
    alias_str = ','.join(aliases)
    num = create_item(s, f'"{name}:{alias_str}"', room)
    if not num:
        return None

    describe(s, num, desc)
    lines_moo = moo_list_str(talk_lines)
    init_prop(s, num, 'talk_lines', lines_moo)
    init_prop(s, num, 'idle_lines', moo_list_str(talk_lines[:4]))

    add_verb(s, num, 'talk', 'this none none')
    program_verb(s, num, 'talk', TALK_VERB)
    add_verb(s, num, 'look', 'this none none')
    program_verb(s, num, 'look', NPC_LOOK_VERB)

    print(f'  #{num}: {name} → #{room}')
    return num


def setup_npcs(s, hub, heartbeat):
    print(f'\n=== Creating NPCs in #{hub} ===')

    vera = create_npc(
        s, hub,
        name='Sergeant Vera',
        aliases=['vera', 'sergeant', 'sgt', 'soldier'],
        desc=(
            'Sergeant Vera is built like a bulkhead: short, broad-shouldered, '
            'and seemingly impervious to cold. Her standard-issue colony uniform '
            'is immaculate despite everything. A deep scar runs from her left ear '
            'to her jawline. She watches the room with the fixed attention of someone '
            'waiting for trouble.'
        ),
        talk_lines=VERA_LINES,
    )

    harlan = create_npc(
        s, hub,
        name='Doc Harlan',
        aliases=['harlan', 'doc', 'doctor', 'medic'],
        desc=(
            'Doc Harlan is tall and thin, permanently stooped as though always '
            'about to lean over a patient. His lab coat is layered over colony '
            'thermals and covered in pockets, all of them full. '
            'He moves with quiet precision and speaks the same way.'
        ),
        talk_lines=HARLAN_LINES,
    )

    if vera and harlan and heartbeat:
        ev(s, f'#{heartbeat}.npcs = {{#{vera}, #{harlan}}}', wait=0.4)
        print(f'  NPCs registered on heartbeat #{heartbeat}')

    return vera, harlan


# ---------------------------------------------------------------------------
# 8.  Start heartbeat
# ---------------------------------------------------------------------------

def start_heartbeat(s, hub, heartbeat):
    print(f'\n=== Starting heartbeat #{heartbeat} ===')
    goto(s, hub)
    out = send(s, f'start #{heartbeat}', wait=1.5)
    print(f'  {out.strip()[:80]}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 — Colony Hub + Phase 3 Setup')
    print('=' * 60)

    s = connect()

    # Clean up any previous colony objects (phase3 range was 418-470,
    # now we start fresh from 476 onwards)
    print('\n=== Cleaning up previous colony objects (476-530) ===')
    cleanup_objects(s, range(476, 531))

    hub, workshop = build_colony_hub(s)
    if not hub:
        print('FATAL: could not build Colony Hub. Aborting.')
        s.close()
        exit(1)

    setup_hub_verbs(s, hub, workshop)

    if workshop:
        setup_fabricator(s, workshop)

    player_class = setup_player_stats(s)
    heartbeat = setup_heartbeat(s, hub)
    setup_building_system(s, player_class)
    vera, harlan = setup_npcs(s, hub, heartbeat)

    if heartbeat:
        start_heartbeat(s, hub, heartbeat)

    # Store hub/workshop globals on #0
    out = ev(s, 'player:tell(tostr(#0.colony_hub))', wait=0.3)
    if 'Property not found' in out or 'E_PROPNF' in out:
        ev(s, f'add_property(#0, "colony_hub", #{hub}, {{player, "rc"}})', wait=0.4)
    else:
        ev(s, f'#0.colony_hub = #{hub}', wait=0.4)

    if workshop:
        out = ev(s, 'player:tell(tostr(#0.colony_workshop))', wait=0.3)
        if 'Property not found' in out or 'E_PROPNF' in out:
            ev(s, f'add_property(#0, "colony_workshop", #{workshop}, {{player, "rc"}})', wait=0.4)
        else:
            ev(s, f'#0.colony_workshop = #{workshop}', wait=0.4)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Colony + Phase 3 Setup Complete ===')
    print(f'  Colony Hub  : #{hub}')
    print(f'  Workshop    : #{workshop}')
    print('  From Impact Site Zero, type "hub" to enter the colony.')
    print('  New player commands: vitals, eat, drink, rest, status')
    print('  Building: build <dome|generator|med station>')
    print('  Crafting: craft <recipe> (in Workshop)')
    print('  NPCs: talk vera / talk harlan (in Hub)')
    print('  Heartbeat: stats decay every 5 minutes')
