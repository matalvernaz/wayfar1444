#!/usr/bin/env python3
"""
Wayfar 1444 - Full World Rebuild (Procedural Architecture)

Tears down the hand-crafted rooms and builds the authentic architecture:

  $wroom     - wilderness room archetype (inherits $room, has ANSI map look)
  $ore_node  - ore deposit prototype
  $fiber_node- fiber patch prototype
  $water_spring - water spring prototype
  $salvage_pile - salvage debris prototype
  $kepler7   - first planet object
  $ods       - on-demand room spawner (coordinate-based)

Player movement uses coordinates, not exits.  Rooms are spawned lazily
by $ods and recycled when empty.  World is driven by perlin_2d().

Run with server live:  python3 rebuild_world.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777


# ---------------------------------------------------------------------------
# Transport helpers
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


def fast_send(s, cmd, wait=0.12):
    """Like send() but with a short socket timeout for bulk single-response ops."""
    old = s.gettimeout()
    s.settimeout(0.4)
    result = send(s, cmd, wait)
    s.settimeout(old)
    return result


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def goto(s, obj_num):
    send(s, f'@go #{obj_num}', wait=0.5)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def moo_list_str(lst):
    return '{' + ', '.join(moo_str(x) for x in lst) + '}'


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
    return ev(s, f'#{obj}.{prop} = {value_moo}', wait=0.3)


def add_verb(s, obj, verbname, args='this none none'):
    return send(s, f'@verb #{obj}:{verbname} {args}', wait=0.5)


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


def recycle(s, num):
    """Recycle via MOO built-in (no confirmation prompt needed)."""
    ev(s, f'recycle(#{num})', wait=0.08)


def obj_valid(s, num):
    out = ev(s, f'player:tell(valid(#{num}) ? "yes" | "no")', wait=0.08)
    return 'yes' in out


def fast_cleanup(s, start, end, skip_set):
    """Batch recycle using a single MOO task per 50-object chunk to avoid
    task-tick limits and minimise round-trips."""
    print(f'  Recycling #{start}-#{end} in 50-object batches ...')
    # Reduce socket timeout during bulk ops so recv loop exits quickly
    old_timeout = s.gettimeout()
    s.settimeout(0.5)
    count = 0
    nums = [n for n in range(start, end + 1) if n not in skip_set]
    # Process in batches of 20 (stay well under MOO task tick limits)
    batch_size = 20
    for i in range(0, len(nums), batch_size):
        batch = nums[i:i + batch_size]
        # Build a MOO snippet that recycles each valid object in the batch
        lines = [f'if (valid(#{n})) recycle(#{n}); endif' for n in batch]
        snippet = ' '.join(lines) + ' player:tell("batch_done");'
        out = ev(s, snippet, wait=0.6)
        count += len(batch)
        if 'batch_done' not in out:
            print(f'  WARN batch {i//batch_size + 1} may have hit task limit: {repr(out[:80])}')
    s.settimeout(old_timeout)
    print(f'  Cleanup done ({len(nums)} objects processed)')


def get_obj_num(s, expr):
    """Evaluate a MOO expression that returns an object and get its number."""
    out = ev(s, f'player:tell(tostr({expr}))', wait=0.4)
    m = re.search(r'#(\d+)', out)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Phase 0 — Recycle old custom objects
# ---------------------------------------------------------------------------

WIZARD_NUM = 361  # from @shutdown message


def cleanup_old_world(s, start=155, end=500):
    """Recycle all valid objects in range, skipping wizard."""
    print(f'\n=== Cleaning up objects #{start}-#{end} ===')
    count = 0
    for n in range(start, end + 1):
        if n == WIZARD_NUM:
            continue
        if obj_valid(s, n):
            recycle(s, n)
            count += 1
    print(f'  Recycled {count} objects')


# ---------------------------------------------------------------------------
# Phase 1 — Wilderness room archetype ($wroom)
# ---------------------------------------------------------------------------

# Biome data: 5 types indexed 0-4 (matched to perlin_2d output range)
# Based on actual Wayfar 1444 wiki biomes
BIOME_NAMES = [
    'Mountain',
    'Forest',
    'Desert',
    'Jungle',
    'Volcanic',
]

BIOME_DESCS = [
    'Jagged peaks and exposed rock faces rise around you. Mineral veins glint in the cliff walls. The air is thin and cold.',
    'Towering alien trees form a dense canopy overhead. Fibrous undergrowth crunches underfoot. The air is thick with spores.',
    'Endless dunes of amber sand stretch to the horizon. Half-buried wreckage and ancient ruins poke through the surface.',
    'Dense tropical vegetation chokes every surface. Moisture drips from broad alien leaves. Hidden water sources trickle nearby.',
    'The ground radiates heat. Sulphur vents hiss between cracked basalt slabs. Energy readings spike on your scanner.',
]

# ANSI colour codes and map chars for each biome (3-char cells)
# chr(27) is used inside MOO code at runtime
BIOME_COLORS_MOO = [
    'esc+"[37m"',   # 0 Mountain  — white (rock/snow)
    'esc+"[32m"',   # 1 Forest    — green
    'esc+"[33m"',   # 2 Desert    — yellow (sand)
    'esc+"[36m"',   # 3 Jungle    — cyan (tropical)
    'esc+"[31m"',   # 4 Volcanic  — red
]

BIOME_CHARS = [' ^ ', ' T ', ' . ', ' % ', ' ~ ']

# MOO list literals for embedding in verb code
BIOME_NAMES_MOO = moo_list_str(BIOME_NAMES)
BIOME_DESCS_MOO = moo_list_str(BIOME_DESCS)
BIOME_CHARS_MOO = moo_list_str(BIOME_CHARS)


LOOK_SELF_VERB = [
    '"Render wilderness room: ANSI 7x5 map + biome description.";',
    'rx = this.x;',
    'ry = this.y;',
    'planet = this.planet;',
    'esc = chr(27);',
    'reset = esc + "[0m";',
    'bold  = esc + "[1m";',
    'bcolor = {esc+"[37m", esc+"[32m", esc+"[33m", esc+"[36m", esc+"[31m"};',
    'bchar  = {" ^ ", " T ", " . ", " % ", " ~ "};',
    'pcell  = " " + esc + "[36m@" + reset + " ";',
    '"draw 7-wide x 5-tall map (dy 2..-2, dx -3..3)";',
    'dy = 2;',
    'while (dy >= -2)',
    '  row = "";',
    '  dx = -3;',
    '  while (dx <= 3)',
    '    if (dx == 0 && dy == 0)',
    '      row = row + pcell;',
    '    else',
    '      b = perlin_2d(rx+dx, ry+dy, 1.0, 1.5, 5, 1);',
    '      if (b < 0) b = 0; elseif (b > 4) b = 4; endif',
    '      row = row + bcolor[b+1] + bchar[b+1] + reset;',
    '    endif',
    '    dx = dx + 1;',
    '  endwhile',
    '  player:tell(row);',
    '  dy = dy - 1;',
    'endwhile',
    'player:tell("");',
    '"Room name and coordinates";',
    'bnames = planet.biome_names;',
    'bdescs = planet.biome_descs;',
    'b = this.biome;',
    'if (b < 0) b = 0; elseif (b > 4) b = 4; endif',
    'player:tell(bold + this.name + reset + "  (" + tostr(rx) + ", " + tostr(ry) + ")  [" + planet.name + "]");',
    'player:tell(bdescs[b+1]);',
    '"List visible contents";',
    'items = {};',
    'for obj in (this.contents)',
    '  if (obj != player)',
    '    items = listappend(items, obj.name);',
    '  endif',
    'endfor',
    'if (length(items) > 0)',
    '  player:tell("");',
    '  listing = items[1];',
    '  idx = 2;',
    '  while (idx <= length(items))',
    '    listing = listing + ", " + items[idx];',
    '    idx = idx + 1;',
    '  endwhile',
    '  player:tell("You see here: " + listing);',
    'endif',
    'player:tell("");',
    'player:tell("Exits: n  s  e  w");',
]

LOOK_VERB_WROOM = [
    '"Look at current room — dispatches to look_self.";',
    'this:look_self();',
]


def setup_wroom(s, room_class):
    """Create the wilderness room archetype and program its verbs."""
    print(f'\n=== Creating $wroom wilderness archetype ===')

    # Use MOO create() directly — @create doesn't accept #N parent syntax
    out = ev(s, 'r = create($room); r.name = "Wilderness Archetype"; player:tell(tostr(r))', wait=1.0)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  FATAL: {repr(out[:200])}')
        return None
    wroom = int(m.group(1))
    print(f'  $wroom = #{wroom}')

    # Core properties all spawned rooms will have
    init_prop(s, wroom, 'x',      '0')
    init_prop(s, wroom, 'y',      '0')
    init_prop(s, wroom, 'planet', '#-1')
    init_prop(s, wroom, 'biome',  '0')

    # look_self: this none none — the main renderer
    add_verb(s, wroom, 'look_self', 'this none none')
    program_verb(s, wroom, 'look_self', LOOK_SELF_VERB)

    # look / l: none none none — player-facing, calls look_self
    add_verb(s, wroom, 'look', 'none none none')
    program_verb(s, wroom, 'look', LOOK_VERB_WROOM)
    add_verb(s, wroom, 'l', 'none none none')
    program_verb(s, wroom, 'l', LOOK_VERB_WROOM)

    # Register globally
    ev(s, f'#0.wroom = #{wroom}', wait=0.4)
    print(f'  #0.wroom = #{wroom}')
    return wroom


# ---------------------------------------------------------------------------
# Phase 2 — Resource node prototypes
# ---------------------------------------------------------------------------

GATHER_VERB_CODE = [
    '"Gather resources from this deposit.";',
    'if (this.count <= 0)',
    '  player:tell("The " + this.name + " is depleted.");',
    '  return;',
    'endif',
    'item = create($thing);',
    'item.name = this.yield_name;',
    'item.aliases = this.yield_aliases;',
    'item.description = this.yield_desc;',
    'move(item, player);',
    'this.count = this.count - 1;',
    'player:tell("You gather some " + item.name + ". [" + tostr(this.count) + "/" + tostr(this.max_count) + " remaining]");',
    'player.location:announce(player.name + " gathers some resources.", player);',
]


def create_resource_prototype(s, thing_class, name, aliases_str, desc,
                              yield_name, yield_aliases, yield_desc,
                              verbs, count=12):
    """Create a $thing child that serves as the prototype for a resource node."""
    aliases_moo = moo_list_str([a.strip() for a in aliases_str.split(',')])
    out = ev(s,
        f'r = create($thing); r.name = {moo_str(name)}; r.aliases = {aliases_moo}; '
        f'player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  FATAL create prototype {name}: {repr(out[:200])}')
        return None
    num = int(m.group(1))

    describe(s, num, desc)

    init_prop(s, num, 'yield_name',    moo_str(yield_name))
    init_prop(s, num, 'yield_aliases', moo_list_str(yield_aliases))
    init_prop(s, num, 'yield_desc',    moo_str(yield_desc))
    init_prop(s, num, 'count',         str(count))
    init_prop(s, num, 'max_count',     str(count))

    primary = verbs[0]
    add_verb(s, num, primary, 'this none none')
    program_verb(s, num, primary, GATHER_VERB_CODE)
    for alias_verb in verbs[1:]:
        add_verb(s, num, alias_verb, 'this none none')
        program_verb(s, num, alias_verb, [f'this:{primary}();'])

    print(f'  #{num}: {name} prototype')
    return num


def setup_resource_prototypes(s, thing_class):
    print(f'\n=== Creating resource node prototypes ===')

    ore = create_resource_prototype(
        s, thing_class,
        name='ore deposit', aliases_str='ore,deposit,vein,mineral,rock',
        desc='A jutting formation of alien mineral ore threaded with iridescent blue veins. Type \'mine deposit\' to collect samples.',
        yield_name='ore sample',
        yield_aliases=['ore', 'sample', 'mineral'],
        yield_desc='A rough chunk of alien mineral ore. Dark and heavy, threaded with an iridescent blue compound. Raw material for fabrication.',
        verbs=['mine', 'gather', 'harvest'],
        count=15,
    )

    fiber = create_resource_prototype(
        s, thing_class,
        name='fiber patch', aliases_str='fiber,patch,plants,stalks,vegetation',
        desc='A dense cluster of alien scrub vegetation; fibrous stalks topped with spore-releasing pods. Type \'harvest patch\' to collect material.',
        yield_name='alien plant fiber',
        yield_aliases=['fiber', 'plant', 'stalk'],
        yield_desc='A bundle of tough fibrous stalks. Pale, waxy, surprisingly strong. Smells faintly of ammonia.',
        verbs=['harvest', 'gather', 'pick'],
        count=15,
    )

    water = create_resource_prototype(
        s, thing_class,
        name='water seep', aliases_str='water,seep,spring,pool',
        desc='A small seep of clear liquid collecting in a depression. Filter before drinking. Type \'collect seep\' to fill a container.',
        yield_name='raw water',
        yield_aliases=['water', 'liquid', 'fluid'],
        yield_desc='Collected raw water. Needs filtering before it is safe to drink.',
        verbs=['collect', 'gather', 'fill'],
        count=20,
    )

    salvage = create_resource_prototype(
        s, thing_class,
        name='salvage debris', aliases_str='salvage,debris,wreck,scrap,equipment',
        desc='Wreckage of unknown origin, half-buried. Some components may still be usable. Type \'salvage debris\' to dig out parts.',
        yield_name='salvaged components',
        yield_aliases=['salvage', 'components', 'parts', 'scrap'],
        yield_desc='Corroded machine components recovered from debris. Potentially functional if cleaned up.',
        verbs=['salvage', 'dig', 'recover'],
        count=8,
    )

    prototypes = {
        'ore': ore, 'fiber': fiber, 'water': water, 'salvage': salvage
    }
    # Register globally
    for name, num in prototypes.items():
        if num:
            ev(s, f'#0.{name}_node = #{num}', wait=0.3)
            print(f'  #0.{name}_node = #{num}')

    return prototypes


# ---------------------------------------------------------------------------
# Phase 3 — Planet object
# ---------------------------------------------------------------------------

def setup_planet(s, thing_class):
    print(f'\n=== Creating Kepler-7 planet object ===')

    out = ev(s,
        'r = create($thing); r.name = "Kepler-7"; '
        'r.aliases = {"kepler", "planet", "k7"}; player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  FATAL: {repr(out[:200])}')
        return None
    num = int(m.group(1))

    describe(s, num, (
        'Kepler-7: a temperate colony world, breathable atmosphere, '
        'surface gravity 0.94g. Designated for colonization by the '
        'Colonial Development Authority. Status: active.'
    ))

    init_prop(s, num, 'name',        moo_str('Kepler-7'))
    init_prop(s, num, 'biome_names', BIOME_NAMES_MOO)
    init_prop(s, num, 'biome_descs', BIOME_DESCS_MOO)
    init_prop(s, num, 'biome_chars', BIOME_CHARS_MOO)

    ev(s, f'#0.kepler7 = #{num}', wait=0.3)
    print(f'  #{num}: Kepler-7  (#0.kepler7)')
    return num


# ---------------------------------------------------------------------------
# Phase 4 — On-demand spawn ($ods)
# ---------------------------------------------------------------------------

ODS_SPAWN_ROOM = [
    '"Spawn or retrieve a wilderness room at (planet, x, y).";',
    '"Usage: $ods:spawn_room(planet_obj, x_int, y_int) -> room";',
    '{planet, x, y} = args;',
    'set_task_perms(this.owner);',
    '"Build property key: strip # from planet ref so name is a valid identifier";',
    'pkey = strsub(tostr(planet), "#", "p");',
    '"Encode negative coords: replace - with m (minus)";',
    'xkey = strsub(tostr(x), "-", "m");',
    'ykey = strsub(tostr(y), "-", "m");',
    'prop = "r" + pkey + "_x" + xkey + "_y" + ykey;',
    '"Check if room already exists";',
    'if (prop in properties(this))',
    '  r = this.(prop);',
    '  if (valid(r)) return r; endif',
    'endif',
    '"Create new wilderness room";',
    'r = create($wroom);',
    'r.x = x;',
    'r.y = y;',
    'r.planet = planet;',
    'b = perlin_2d(x, y, 1.0, 1.5, 5, 1);',
    'if (b < 0) b = 0; elseif (b > 4) b = 4; endif',
    'r.biome = b;',
    'bnames = planet.biome_names;',
    'r.name = bnames[b+1];',
    '"Store the room";',
    'add_property(this, prop, r, {player, "rc"});',
    '"Possibly spawn a resource node";',
    'this:populate(r, planet);',
    'return r;',
]

ODS_POPULATE = [
    '"Possibly spawn a resource node in room based on biome + coords.";',
    '{room, planet} = args;',
    'set_task_perms(this.owner);',
    'x = room.x; y = room.y;',
    'b = room.biome;',
    '"Use offset perlin call for resources (decorrelated from biome)";',
    'roll = perlin_2d(x*7+13, y*5+7, 2.0, 2.0, 10, 1);',
    '"roll range 0-9; spawn resource if roll >= 7 (30%)";',
    'if (roll < 7) return; endif',
    '"Select node prototype by biome";',
    '"  0=Mountain -> ore (mineral veins)";',
    '"  1=Forest   -> fiber (alien plant matter)";',
    '"  2=Desert   -> salvage (buried ruins/wreckage)";',
    '"  3=Jungle   -> water (hidden springs) + fiber";',
    '"  4=Volcanic -> ore (geothermal mineral deposits)";',
    'proto = 0;',
    'if (b == 0)',
    '  proto = $ore_node;',
    'elseif (b == 1)',
    '  proto = $fiber_node;',
    'elseif (b == 2)',
    '  proto = $salvage_pile;',
    'elseif (b == 3)',
    '  if (roll > 8)',
    '    proto = $fiber_node;',
    '  else',
    '    proto = $water_node;',
    '  endif',
    'elseif (b == 4)',
    '  proto = $ore_node;',
    'endif',
    'if (!valid(proto)) return; endif',
    'node = create(proto);',
    '"Reset count to parent default";',
    'node.count = proto.max_count;',
    'move(node, room);',
]

ODS_CLEAN = [
    '"Recycle empty wilderness rooms to save memory.";',
    'set_task_perms(this.owner);',
    'for prop in (properties(this))',
    '  "Our room props all start with r (e.g. rp415_x0_y0)";',
    '  if (length(prop) > 1 && prop[1] == "r" && prop[2] == "p")',
    '    r = this.(prop);',
    '    if (valid(r) && length(r.contents) == 0)',
    '      recycle(r);',
    '    endif',
    '  endif',
    'endfor',
]


def setup_ods(s, thing_class):
    print(f'\n=== Creating $ods on-demand room spawner ===')

    out = ev(s,
        'r = create($thing); r.name = "on-demand spawn"; '
        'r.aliases = {"ods", "spawner"}; player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  FATAL: {repr(out[:200])}')
        return None
    num = int(m.group(1))

    describe(s, num, 'Internal object: manages on-demand wilderness room spawning.')

    add_verb(s, num, 'spawn_room', 'this none none')
    program_verb(s, num, 'spawn_room', ODS_SPAWN_ROOM)

    add_verb(s, num, 'populate', 'this none none')
    program_verb(s, num, 'populate', ODS_POPULATE)

    add_verb(s, num, 'clean', 'this none none')
    program_verb(s, num, 'clean', ODS_CLEAN)

    ev(s, f'#0.ods = #{num}', wait=0.3)
    print(f'  #{num}: $ods  (#0.ods)')
    return num


# ---------------------------------------------------------------------------
# Phase 5 — Player movement verbs (coordinate-based)
# ---------------------------------------------------------------------------

def make_move_verb(direction, dx, dy, from_dir, to_dir):
    """Generate movement verb code for a given direction."""
    return [
        f'"Move {direction} by adjusting coordinates.";',
        '"Check we are in a wilderness room (child of $wroom)";',
        'if (parent(player.location) != $wroom)',
        '  player:tell("You cannot go that way.");',
        '  return;',
        'endif',
        f'nx = player.location.x + ({dx});',
        f'ny = player.location.y + ({dy});',
        'planet = player.location.planet;',
        'dest = $ods:spawn_room(planet, nx, ny);',
        'if (!valid(dest))',
        '  player:tell("The way is blocked.");',
        '  return;',
        'endif',
        f'player.location:announce(player.name + " heads {direction}.", player);',
        'move(player, dest);',
        f'player.location:announce(player.name + " arrives from the {from_dir}.", player);',
        'player.location:look_self();',
    ]


def setup_movement(s, player_class):
    print(f'\n=== Adding coordinate movement verbs to $player #{player_class} ===')

    dirs = [
        ('north', 0,  1, 'south',  'n'),
        ('south', 0, -1, 'north',  's'),
        ('east',  1,  0, 'west',   'e'),
        ('west', -1,  0, 'east',   'w'),
    ]

    for direction, dx, dy, from_dir, abbrev in dirs:
        add_verb(s, player_class, direction, 'none none none')
        program_verb(s, player_class, direction, make_move_verb(direction, dx, dy, from_dir, direction))
        add_verb(s, player_class, abbrev, 'none none none')
        program_verb(s, player_class, abbrev, [f'this:{direction}();'])
        print(f'  {direction} / {abbrev}  (dx={dx}, dy={dy})')


# ---------------------------------------------------------------------------
# Phase 6 — Examine verb on $thing (self-documenting objects)
# ---------------------------------------------------------------------------

EXAMINE_VERB = [
    '"Examine an object — shows description and available commands.";',
    'player:tell(this.name);',
    'player:tell(this.description);',
    '"Build verb list";',
    'vlist = {};',
    'for v in (verbs(this))',
    '  if (v[1] != "_")',
    '    vlist = listappend(vlist, v);',
    '  endif',
    'endfor',
    'if (length(vlist) > 0)',
    '  player:tell("");',
    '  line = "Commands: " + vlist[1];',
    '  i = 2;',
    '  while (i <= length(vlist))',
    '    line = line + "  " + vlist[i];',
    '    i = i + 1;',
    '  endwhile',
    '  player:tell(line);',
    'endif',
]


def setup_examine(s, thing_class):
    print(f'\n=== Adding examine verb to $thing #{thing_class} ===')
    add_verb(s, thing_class, 'examine', 'this none none')
    program_verb(s, thing_class, 'examine', EXAMINE_VERB)
    add_verb(s, thing_class, 'ex', 'this none none')
    program_verb(s, thing_class, 'ex', ['this:examine();'])
    print(f'  examine / ex on #{thing_class}')


# ---------------------------------------------------------------------------
# Phase 7 — Chatnet / chat on $player
# ---------------------------------------------------------------------------

CHATNET_VERB = [
    '"Toggle or check the colony communication relay.";',
    'if (dobjstr == "" || dobjstr == "status")',
    '  if (player.chatnet_on)',
    '    player:tell("[CHATNET] Relay active.");',
    '  else',
    '    player:tell("[CHATNET] Relay offline. Type \'chatnet on\' to activate.");',
    '  endif',
    '  return;',
    'endif',
    'if (index(dobjstr, "on"))',
    '  player.chatnet_on = 1;',
    '  player:tell("[CHATNET] Colony relay activated.");',
    'elseif (index(dobjstr, "off"))',
    '  player.chatnet_on = 0;',
    '  player:tell("[CHATNET] Colony relay deactivated.");',
    'else',
    '  player:tell("[CHATNET] Usage: chatnet on  |  chatnet off  |  chatnet");',
    'endif',
]

CHAT_VERB = [
    '"Broadcast a message over the colony communication relay.";',
    '"Usage: chat <message>";',
    'if (dobjstr == "")',
    '  player:tell("[CHATNET] Usage: chat <message>");',
    '  return;',
    'endif',
    'if (!player.chatnet_on)',
    '  player:tell("[CHATNET] Your relay is offline. Type \'chatnet on\' first.");',
    '  return;',
    'endif',
    'msg = "[CHATNET] " + player.name + ": " + dobjstr;',
    'for p in (connected_players())',
    '  if (p.chatnet_on)',
    '    p:tell(msg);',
    '  endif',
    'endfor',
]


def setup_chatnet(s, player_class):
    print(f'\n=== Adding chatnet/chat to $player #{player_class} ===')

    # chatnet_on property on $player
    out = ev(s, f'player:tell(tostr(#{player_class}.chatnet_on))', wait=0.3)
    if 'Property not found' in out or out.strip() == '':
        init_prop(s, player_class, 'chatnet_on', '0')
        print(f'  Added .chatnet_on to #{player_class}')

    add_verb(s, player_class, 'chatnet', 'any none none')
    program_verb(s, player_class, 'chatnet', CHATNET_VERB)

    add_verb(s, player_class, 'chat', 'any none none')
    program_verb(s, player_class, 'chat', CHAT_VERB)
    print(f'  chatnet / chat added')


# ---------------------------------------------------------------------------
# Phase 8 — Starting crash site room + survival kit
# ---------------------------------------------------------------------------

CRASH_SITE_LOOK = [
    '"Override look for the crash site — shows special description first time.";',
    'rx = this.x; ry = this.y; planet = this.planet;',
    'esc = chr(27); reset = esc + "[0m"; bold = esc + "[1m";',
    'bcolor = {esc+"[37m", esc+"[32m", esc+"[33m", esc+"[36m", esc+"[31m"};',
    'bchar  = {" ^ ", " T ", " . ", " % ", " ~ "};',
    'pcell  = " " + esc + "[36m@" + reset + " ";',
    'dy = 2;',
    'while (dy >= -2)',
    '  row = "";',
    '  dx = -3;',
    '  while (dx <= 3)',
    '    if (dx == 0 && dy == 0)',
    '      row = row + pcell;',
    '    else',
    '      b = perlin_2d(rx+dx, ry+dy, 1.0, 1.5, 5, 1);',
    '      if (b < 0) b = 0; elseif (b > 4) b = 4; endif',
    '      row = row + bcolor[b+1] + bchar[b+1] + reset;',
    '    endif',
    '    dx = dx + 1;',
    '  endwhile',
    '  player:tell(row);',
    '  dy = dy - 1;',
    'endwhile',
    'player:tell("");',
    'player:tell(bold + "Impact Site Zero" + reset + "  (0, 0)  [Kepler-7]");',
    'player:tell("Your escape pod hit at terminal velocity, carving a blackened crater in the mineral flats.");',
    'player:tell("The hull is twisted open like a tin can. The emergency beacon is transmitting.");',
    'player:tell("You have atmosphere — barely. Whatever you need, you will have to build it.");',
    '"List visible contents";',
    'items = {};',
    'for obj in (this.contents)',
    '  if (obj != player)',
    '    items = listappend(items, obj.name);',
    '  endif',
    'endfor',
    'if (length(items) > 0)',
    '  player:tell("");',
    '  listing = items[1]; idx = 2;',
    '  while (idx <= length(items))',
    '    listing = listing + ", " + items[idx]; idx = idx + 1;',
    '  endwhile',
    '  player:tell("You see here: " + listing);',
    'endif',
    'player:tell("");',
    'player:tell("Exits: n  s  e  w");',
]


def parse_name_spec(name_spec):
    """Parse '"Name:alias1,alias2"' into (name_str, aliases_moo_list)."""
    raw = name_spec.strip('"\'')
    if ':' in raw:
        nm, aliaspart = raw.split(':', 1)
        aliases = moo_list_str([a.strip() for a in aliaspart.split(',')])
    else:
        nm = raw
        aliases = '{}'
    return nm, aliases


def create_item_in(s, name_spec, room):
    nm, aliases = parse_name_spec(name_spec)
    out = ev(s,
        f'r = create($thing); r.name = {moo_str(nm)}; r.aliases = {aliases}; '
        f'move(r, #{room}); player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if m:
        return int(m.group(1))
    print(f'  WARN create_item_in {nm}: {repr(out[:200])}')
    return None


def setup_crash_site(s, wroom, planet, thing_class):
    print(f'\n=== Creating crash site at (0,0) ===')

    out = ev(s,
        f'r = create(#{wroom}); r.name = "Impact Site Zero"; '
        f'r.aliases = {{"crash", "site", "zero", "pod", "crater"}}; player:tell(tostr(r))',
        wait=0.8)
    m = re.search(r'#(\d+)', out)
    if not m:
        print(f'  FATAL: {repr(out[:200])}')
        return None
    site = int(m.group(1))

    # Set coordinates and planet
    set_prop(s, site, 'x',      '0')
    set_prop(s, site, 'y',      '0')
    set_prop(s, site, 'planet', f'#{planet}')
    set_prop(s, site, 'biome',  '0')

    # Override look_self with crash-site-specific description
    add_verb(s, site, 'look_self', 'this none none')
    program_verb(s, site, 'look_self', CRASH_SITE_LOOK)

    # Register in $ods so spawn_room(planet,0,0) returns this room.
    # Key formula mirrors ODS_SPAWN_ROOM: "r" + planet# stripped + "_x0_y0"
    pkey = str(planet)   # planet is already an int (no # prefix)
    ods_prop = f'rp{pkey}_x0_y0'
    ev(s, f'add_property($ods, {moo_str(ods_prop)}, #{site}, {{player, "rc"}})', wait=0.5)

    print(f'  #{site}: Impact Site Zero — registered as (0,0) on #{planet}')

    # Move wizard there
    goto(s, site)
    print(f'  Wizard moved to #{site}')

    # Create survival kit
    print(f'  Creating starting survival items...')

    kit = create_item_in(s, '"survival kit:kit,crate,pack,supplies,emergency"', site)
    if kit:
        describe(s, kit, (
            'A cracked emergency survival kit from your escape pod. '
            'Dented but sealed. Stamped on the lid: CDA STANDARD ISSUE. '
            'Type \'open kit\' or \'search kit\' to see what survived the impact.'
        ))
        # Multi-tool
        tool = create_item_in(s, '"multi-tool:tool,multitool,knife,scanner"', site)
        if tool:
            describe(s, tool, (
                'A standard-issue colonial multi-tool. Folding utility blade, '
                'basic mineral scanner, and a deployable cutting edge for harvesting. '
                'Type \'scan\' while holding it to check local resources.'
            ))
            send(s, f'@move #{tool} to #{kit}', wait=0.4)

        # 2 ration bars
        for i in range(2):
            r = create_item_in(s, '"ration bar:ration,bar,food,edible"', site)
            if r:
                describe(s, r, 'A dense compressed food bar. Tastes of nothing. Calories are calories.')
                send(s, f'@move #{r} to #{kit}', wait=0.4)

        # Empty canteen
        canteen = create_item_in(s, '"empty canteen:canteen,container,bottle"', site)
        if canteen:
            describe(s, canteen, 'A durable metal canteen, currently empty. Fill it at a water source.')
            send(s, f'@move #{canteen} to #{kit}', wait=0.4)

    # Also create the emergency beacon as atmosphere
    beacon = create_item_in(s, '"emergency beacon:beacon,signal,transmitter"', site)
    if beacon:
        describe(s, beacon, (
            'A short-range emergency distress beacon, transmitting on colony frequencies. '
            'The battery indicator shows three days of power remaining. '
            'Someone might come. Or they might not.'
        ))

    return site


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 - Full World Rebuild')
    print('=' * 60)

    s = connect()

    # Find core object numbers
    room_class  = get_obj_num(s, '$room')
    player_class = get_obj_num(s, '$player')
    thing_class = get_obj_num(s, '$thing')
    wizard_loc  = get_obj_num(s, 'player.location')

    print(f'$room   = #{room_class}')
    print(f'$player = #{player_class}')
    print(f'$thing  = #{thing_class}')
    print(f'Wizard loc = #{wizard_loc}')

    # Phase 0: recycle all old custom objects
    safe_skip = {WIZARD_NUM, room_class, player_class, thing_class}
    print(f'\n=== Cleaning up old world (skipping {safe_skip}) ===')
    fast_cleanup(s, 155, 500, safe_skip)

    # Phase 1-8: build the new world
    wroom    = setup_wroom(s, room_class)
    protos   = setup_resource_prototypes(s, thing_class)
    planet   = setup_planet(s, thing_class)
    ods      = setup_ods(s, thing_class)

    setup_movement(s, player_class)
    setup_examine(s, thing_class)
    setup_chatnet(s, player_class)

    site = setup_crash_site(s, wroom, planet, thing_class)

    # Teleport wizard to the crash site for a test look
    if site:
        goto(s, site)
        print(f'\n=== Test look from crash site ===')
        out = send(s, 'look', wait=2.0)
        print(out[:600])

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Rebuild complete ===')
    print('The world:')
    print('  $wroom        — wilderness room archetype with ANSI map')
    print('  $ore_node     — ore deposit prototype (mine/gather/harvest)')
    print('  $fiber_node   — fiber patch prototype (harvest/gather/pick)')
    print('  $water_spring — water seep prototype (collect/gather/fill)')
    print('  $salvage_pile — salvage debris prototype (salvage/dig/recover)')
    print('  $kepler7      — Kepler-7 planet object')
    print('  $ods          — on-demand room spawner')
    print('  (0,0) Kepler-7 — Impact Site Zero (crash site)')
    print()
    print('Player commands:')
    print('  n s e w       — coordinate movement + ANSI map')
    print('  look / l      — re-render current room')
    print('  examine <obj> — show description + verb list')
    print('  chatnet on/off— toggle colony relay')
    print('  chat <msg>    — broadcast to colony relay')
