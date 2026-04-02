#!/usr/bin/env python3
"""
Wayfar 1444 - Phase 2 Expansion

Adds:
  - Resource gathering nodes (ore, fiber, water) in wilderness rooms
  - Fabricator with crafting recipes in workshop
  - Spaceport Alpha (reachable via UP from Landing Zone)
  - Xeris Prime: second planet (icy mining world)
  - Inter-planet travel via colony transport

Run with server live:  python3 expand_wayfar.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777


# ---------------------------------------------------------------------------
# Connection / transport helpers
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
    text = out.decode('utf-8', errors='replace')
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


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


# ---------------------------------------------------------------------------
# World-building helpers
# ---------------------------------------------------------------------------

def recycle(s, num):
    """Recycle an object, sending 'yes' to confirm if prompted."""
    send(s, f'@recycle #{num}', wait=0.6)
    send(s, 'yes', wait=0.5)


def cleanup_objects(s, obj_nums):
    """Recycle a list of object numbers (ignores invalid ones)."""
    for n in obj_nums:
        out = ev(s, f'player:tell(valid(#{n}) ? {moo_str("yes")} + #{n}.name | {moo_str("no")})', wait=0.3)
        if 'yes' in out:
            recycle(s, n)
            print(f'  recycled #{n}')


def dig_room(s, direction, name, from_num):
    goto(s, from_num)
    out = send(s, f'@dig {direction} to {name}', wait=1.0)
    created = re.search(r"Created '.*?#(\d+)", out)
    if created:
        return int(created.group(1))
    nums = re.findall(r'#(\d+)', out)
    for n in nums:
        n = int(n)
        if n != from_num and n > 50:
            return n
    print(f'  WARN @dig {direction} to {name}: {repr(out[:200])}')
    return None


def dig_unlinked(s, name):
    """Create a room not linked to any existing room."""
    out = send(s, f'@dig {moo_str(name)}', wait=1.0)
    # @dig with just a name moves wizard there and prints object number
    nums = re.findall(r'#(\d+)', out)
    created = re.search(r"Created '.*?#(\d+)", out)
    if created:
        return int(created.group(1))
    for n in nums:
        n = int(n)
        if n > 50:
            return n
    print(f'  WARN @dig unlinked {name}: {repr(out[:200])}')
    return None


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
    """Add a new property with initial value (wizard add_property)."""
    return ev(s,
        f'add_property(#{obj}, {moo_str(prop)}, {value_moo}, {{player, "rc"}})',
        wait=0.4)


def add_verb(s, obj, verbname, args='this none none'):
    out = send(s, f'@verb #{obj}:{verbname} {args}', wait=0.5)
    return out


def program_verb(s, obj, verbname, code_lines):
    """Enter @program mode and type verb code line by line."""
    out = send(s, f'@program #{obj}:{verbname}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  WARN entering @program #{obj}:{verbname}: {repr(out[:120])}')
    # In @program mode the MOO doesn't send per-line responses, so use a short
    # timeout to avoid 3s wait per line (which makes 100-line verbs take 5 min).
    s.settimeout(0.25)
    for line in code_lines:
        send(s, line, wait=0.04)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    # Only flag real compile errors (e.g. "3 error(s)")
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
    return out


# ---------------------------------------------------------------------------
# Discover room numbers by navigating from known anchor
# ---------------------------------------------------------------------------
LZ = 159


def discover_rooms(s):
    print('\n=== Discovering room layout ===')
    rooms = {'lz': LZ}

    goto(s, LZ)

    send(s, 'north', wait=0.4)
    rooms['hub'] = here(s)

    send(s, 'west', wait=0.4)
    rooms['medbay'] = here(s)
    send(s, 'east', wait=0.4)   # back to hub

    send(s, 'east', wait=0.4)
    rooms['workshop'] = here(s)
    send(s, 'west', wait=0.4)   # back to hub

    send(s, 'north', wait=0.4)
    rooms['storage'] = here(s)

    goto(s, LZ)
    send(s, 'east', wait=0.4)
    rooms['eastern_flats'] = here(s)

    goto(s, LZ)
    send(s, 'south', wait=0.4)
    rooms['southern_ridge'] = here(s)

    goto(s, LZ)
    send(s, 'west', wait=0.4)
    rooms['western_scrublands'] = here(s)

    goto(s, LZ)

    for k, v in rooms.items():
        print(f'  {k}: #{v}')

    return rooms


# ---------------------------------------------------------------------------
# Resource gathering nodes
# ---------------------------------------------------------------------------

GATHER_VERB = [
    '"Gather resources from this deposit.";',
    'if (this.count <= 0)',
    '  player:tell("The " + this.name + " is depleted. Come back later.");',
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


def create_resource_node(s, room, name, aliases, desc,
                         verb_list, yield_name, yield_aliases, yield_desc,
                         count=12):
    """Create a resource-gathering node object and wire up its verbs."""
    alias_str = ','.join(aliases)
    num = create_item(s, f'"{name}:{alias_str}"', room)
    if not num:
        print(f'  FATAL could not create node: {name}')
        return None

    describe(s, num, desc)

    init_prop(s, num, 'yield_name',    moo_str(yield_name))
    init_prop(s, num, 'yield_aliases', moo_list_str(yield_aliases))
    init_prop(s, num, 'yield_desc',    moo_str(yield_desc))
    init_prop(s, num, 'count',         str(count))
    init_prop(s, num, 'max_count',     str(count))

    primary = verb_list[0]
    add_verb(s, num, primary, 'this none none')
    program_verb(s, num, primary, GATHER_VERB)

    # Alias verbs all delegate to primary
    for alias_verb in verb_list[1:]:
        add_verb(s, num, alias_verb, 'this none none')
        program_verb(s, num, alias_verb, [f'this:{primary}();'])

    print(f'  #{num}: {name} -> #{room}  ({count}x {yield_name})')
    return num


def setup_resource_nodes(s, rooms):
    print('\n=== Setting up resource gathering nodes ===')

    # Ore deposit — Eastern Flats
    create_resource_node(
        s, rooms['eastern_flats'],
        name='ore deposit',
        aliases=['ore', 'deposit', 'vein', 'rock', 'mineral'],
        desc=(
            'A jutting formation of alien mineral ore, threaded with iridescent blue veins '
            'that catch the light. The surface ore can be broken off with basic tools. '
            'Type \'mine deposit\' or \'gather deposit\' to collect samples.'
        ),
        verb_list=['mine', 'gather', 'harvest'],
        yield_name='ore sample',
        yield_aliases=['ore', 'sample', 'mineral', 'rock'],
        yield_desc=(
            'A rough chunk of alien mineral ore, dark and heavy, threaded with veins of '
            'an iridescent blue compound. The scanner identifies it as high-grade ferrite '
            'alloy with trace xenolithic inclusions. Raw material for fabrication.'
        ),
        count=15,
    )

    # Fiber patch — Western Scrublands
    create_resource_node(
        s, rooms['western_scrublands'],
        name='scrub patch',
        aliases=['scrub', 'patch', 'plants', 'stalks', 'vegetation', 'fiber'],
        desc=(
            'A dense cluster of alien scrub vegetation: fibrous stalks topped with '
            'spore-releasing pods. The fibers are surprisingly tough and useful for crafting. '
            'Type \'harvest patch\' or \'gather patch\' to collect material.'
        ),
        verb_list=['harvest', 'gather', 'pick'],
        yield_name='alien plant fiber',
        yield_aliases=['fiber', 'plant', 'stalk', 'vegetation'],
        yield_desc=(
            'A bundle of tough fibrous stalks harvested from the scrublands. '
            'Pale and slightly waxy, surprisingly strong. '
            'Useful as binding material or crude insulation. Smells faintly of ammonia.'
        ),
        count=15,
    )

    # Water spring — Southern Ridge
    create_resource_node(
        s, rooms['southern_ridge'],
        name='water spring',
        aliases=['spring', 'water', 'pool', 'seep', 'runoff'],
        desc=(
            'A small seep of water collecting in a natural depression in the rock. '
            'The liquid appears clear but should be filtered before drinking. '
            'Type \'collect spring\' or \'gather spring\' to fill a container.'
        ),
        verb_list=['collect', 'gather', 'fill'],
        yield_name='raw water',
        yield_aliases=['water', 'liquid', 'fluid', 'h2o'],
        yield_desc=(
            'A sealed container of raw water collected from a surface spring. '
            'Needs filtration before it is safe to drink, but useful for crafting '
            'and colony supply.'
        ),
        count=20,
    )


# ---------------------------------------------------------------------------
# Fabricator crafting system
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
    '  recycle(found[1]);',
    '  recycle(found[2]);',
    '  result = create($thing);',
    '  result.name = "metal plate";',
    '  result.aliases = {"plate", "metal"};',
    '  result.description = "A flat panel of smelted alien ore, processed by the fabricator. Used in colony construction and repairs.";',
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
    '  result.description = "Braided alien plant fiber. Surprisingly strong. Useful for climbing, binding, and light construction.";',
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
    '  recycle(ore_item);',
    '  recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "water filter";',
    '  result.aliases = {"filter", "purifier"};',
    '  result.description = "An improvised filtration unit of compressed ore mesh and fiber matting. Purifies raw water for safe drinking.";',
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
    '  recycle(plate_item);',
    '  recycle(fiber_item);',
    '  result = create($thing);',
    '  result.name = "structural panel";',
    '  result.aliases = {"panel", "structural", "strut"};',
    '  result.description = "A reinforced composite panel of smelted ore and woven fiber. Used in colony structure construction.";',
    '  move(result, player);',
    '  player:tell("The fabricator assembles a structural panel.");',
    '  return;',
    'endif',
    '"--- purified water ---";',
    'if (index(tgt, "purified") || (index(tgt, "water") && index(tgt, "purif")))',
    '  water_item = 0; filter_item = 0;',
    '  for item in (player.contents)',
    '    if (!water_item && (item.name == "raw water" || ("water" in item.aliases && index(item.name, "raw"))))',
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
    '  result.description = "Filtered and purified water, safe to drink. Colony standard. Tastes of nothing, which is exactly right.";',
    '  move(result, player);',
    '  player:tell("The filter removes contaminants. You now have purified water.");',
    '  return;',
    'endif',
    'player:tell("Unknown recipe: " + tgt);',
    'player:tell("Type \'craft\' for available recipes.");',
]


def setup_fabricator(s, workshop_num):
    print(f'\n=== Setting up fabricator in #{workshop_num} ===')

    num = create_item(s, '"fabricator unit:fabricator,fab,maker,machine"', workshop_num)
    if not num:
        print('  FATAL could not create fabricator')
        return None

    describe(s, num, (
        'A robust automated fabricator unit, roughly the size of a wardrobe. '
        'Touch screens along the front panel display schematics and resource inventories. '
        'The unit can process raw materials into usable colony equipment. '
        'Type \'craft\' to see what it can make, or \'craft <item>\' to fabricate something.'
    ))

    # Two verb forms: one for plain "craft", one for "craft <item>"
    add_verb(s, num, 'craft', 'none none none')
    program_verb(s, num, 'craft', CRAFT_VERB)

    add_verb(s, num, 'craft', 'any none none')
    program_verb(s, num, 'craft', CRAFT_VERB)

    print(f'  #{num}: fabricator unit -> #{workshop_num}')
    return num


# ---------------------------------------------------------------------------
# Spaceport and inter-planetary travel
# ---------------------------------------------------------------------------

TRAVEL_VERB = [
    '"Travel to another colony or planet via the launch pad.";',
    '"Usage: travel [destination name or number]";',
    'if (args == {})',
    '  player:tell("=== COLONY TRANSPORT SYSTEM ===");',
    '  player:tell("Available destinations:");',
    '  i = 1;',
    '  for d in (this.destinations)',
    '    player:tell("  " + tostr(i) + ". " + d[1] + " - " + d[2]);',
    '    i = i + 1;',
    '  endfor',
    '  player:tell("Usage: travel <name or number>");',
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
    'dest = 0;',
    'n = toint(tgt);',
    'if (n > 0 && n <= length(this.destinations))',
    '  dest = this.destinations[n];',
    'else',
    '  for d in (this.destinations)',
    '    if (index(d[1], tgt))',
    '      dest = d;',
    '      break;',
    '    endif',
    '  endfor',
    'endif',
    'if (!dest)',
    '  player:tell("Unknown destination: " + tgt);',
    '  player:tell("Type \'travel\' for available destinations.");',
    '  return;',
    'endif',
    'dest_room = dest[3];',
    'if (!valid(dest_room))',
    '  player:tell("That destination is currently unavailable.");',
    '  return;',
    'endif',
    'player:tell("You board the colony transport and strap in. The engines ignite with a roar.");',
    'player.location:announce(player.name + " boards the colony transport and lifts off.", player);',
    'move(player, dest_room);',
    'player:tell("After a brutal transit burn, you arrive at " + dest[1] + ".");',
    'player.location:announce(player.name + " arrives on the colony transport.", player);',
]


def build_spaceport(s, lz_num):
    print(f'\n=== Building Spaceport Alpha (up from #{lz_num}) ===')

    spaceport = dig_room(s, 'up', 'Spaceport Alpha', lz_num)
    if not spaceport:
        print('  FATAL could not create Spaceport Alpha')
        return None, None

    describe(s, spaceport, (
        'A bare-bones launch facility carved from the plateau rock. '
        'A single hardened landing pad dominates the center, blast-scored from dozens of burns. '
        'Fuel lines and umbilical connectors snake across the floor. '
        'A battered colony transport sits on the pad, its hull patched with mismatched alloys. '
        'Through the transparent dome overhead, the stars are sharp and merciless. '
        'Available destinations are displayed on the departure board. '
        'The landing zone lies below.'
    ))

    # Launch pad object
    pad = create_item(s, '"launch pad:pad,launchpad,transport,ship,shuttle,board"', spaceport)
    if not pad:
        print('  FATAL could not create launch pad')
        return spaceport, None

    describe(s, pad, (
        'The colony transport rests on a blast-scarred launch pad. '
        'It is a blunt, utilitarian vessel: all fuel tanks and cargo capacity, '
        'with just enough crew space for a handful of colonists. '
        'Destinations are pre-programmed for known colony sites. '
        'Type \'travel\' to see where it can take you, or \'travel <destination>\'.'
    ))

    add_verb(s, pad, 'travel', 'none none none')
    add_verb(s, pad, 'travel', 'any none none')

    print(f'  Spaceport Alpha: #{spaceport}')
    print(f'  Launch pad: #{pad}')
    return spaceport, pad


def build_xeris_prime(s):
    """Build Xeris Prime: an icy mining world with two explorable areas."""
    print('\n=== Building Xeris Prime (second planet) ===')

    xeris_lz = dig_unlinked(s, 'Xeris Prime - Landing Pad')
    if not xeris_lz:
        print('  FATAL could not create Xeris Prime landing pad')
        return None

    goto(s, xeris_lz)   # move wizard there so @dig works from it

    describe(s, xeris_lz, (
        'The Xeris Prime landing pad is a permafrost shelf reinforced with embedded heat coils. '
        'Without them, the ground would buckle and swallow anything left on the surface. '
        'Temperature: -67C. Atmospheric pressure: 0.3 standard. '
        'The sky is a violet-black, striated with cirrus clouds of frozen ammonia. '
        'Jagged ice formations ring the perimeter. '
        'Ice caverns lie to the north. The frozen expanse stretches to the south.'
    ))
    print(f'  Xeris Prime - Landing Pad: #{xeris_lz}')

    # Ice Caverns (north)
    xeris_caverns = dig_room(s, 'north', 'Ice Caverns', xeris_lz)
    if xeris_caverns:
        describe(s, xeris_caverns, (
            'Vast caverns carved by ancient geothermal activity, now locked in permanent ice. '
            'The walls glitter with embedded xenocrystal formations: pale blue, semi-translucent, '
            'pulsing with a faint inner light. The silence is absolute except for the '
            'occasional crack of thermal stress deep in the rock. '
            'Valuable minerals are everywhere if you have the tools to extract them. '
            'The landing pad lies south.'
        ))
        print(f'  Ice Caverns: #{xeris_caverns}')

        create_resource_node(
            s, xeris_caverns,
            name='xenocrystal formation',
            aliases=['xenocrystal', 'crystal', 'formation', 'vein', 'xeno'],
            desc=(
                'A cluster of xenocrystal formations jutting from the cavern wall. '
                'Pale blue, semi-translucent, and pulsing with bioluminescent energy. '
                'High-value material used in advanced colony tech. '
                'Type \'mine formation\' to extract fragments.'
            ),
            verb_list=['mine', 'gather', 'extract'],
            yield_name='xenocrystal',
            yield_aliases=['xenocrystal', 'crystal', 'xeno', 'mineral'],
            yield_desc=(
                'A fragment of xenocrystal, cold and pale blue. '
                'The mineral pulsates faintly in your hand. '
                'Extremely valuable — used in advanced colony electronics and medical devices.'
            ),
            count=8,
        )

    # Frozen Expanse (south)
    xeris_expanse = dig_room(s, 'south', 'Frozen Expanse', xeris_lz)
    if xeris_expanse:
        describe(s, xeris_expanse, (
            'A vast plain of cracked permafrost stretching to the horizon. '
            'Ruins of an earlier colonial attempt are visible here: '
            'collapsed hab-domes, solar panels shattered by meteorite impacts, '
            'equipment frozen solid in the ice. '
            'In the far distance, something large moves across the ice. '
            'The landing pad lies north.'
        ))
        print(f'  Frozen Expanse: #{xeris_expanse}')

        create_resource_node(
            s, xeris_expanse,
            name='frozen salvage',
            aliases=['salvage', 'wreck', 'debris', 'equipment', 'ruins', 'scrap'],
            desc=(
                'Wreckage from the original Xeris colonial expedition, frozen in place. '
                'Some components are still identifiable beneath the ice. '
                'Type \'salvage wreck\' to dig out parts.'
            ),
            verb_list=['salvage', 'dig', 'recover', 'gather'],
            yield_name='salvaged components',
            yield_aliases=['salvage', 'components', 'parts', 'scrap'],
            yield_desc=(
                'A handful of frozen machine components recovered from old colonial wreckage. '
                'Corroded but potentially functional. '
                'Could be repurposed at a colony workshop.'
            ),
            count=12,
        )

    return xeris_lz


def setup_launchpad_destinations(s, pad_num, kepler_lz, xeris_lz):
    """Program the travel verb and set destinations on the launch pad."""
    print(f'\n=== Configuring launch pad #{pad_num} ===')

    # Build MOO list: {{name, desc, #room}, ...}
    dest_moo = (
        '{'
        + '{' + moo_str('Kepler-7 Colony')
        + ', ' + moo_str('Temperate starting world — your first colony')
        + ', #' + str(kepler_lz) + '}'
        + ', '
        + '{' + moo_str('Xeris Prime')
        + ', ' + moo_str('Icy mining world, rich in xenocrystals')
        + ', #' + str(xeris_lz) + '}'
        + '}'
    )

    init_prop(s, pad_num, 'destinations', dest_moo)

    # Program both verb forms (none none none and any none none)
    program_verb(s, pad_num, 'travel', TRAVEL_VERB)
    # Second verb (any none none) was added; program it by re-entering @program
    # In HellCore, @program targets the first matching verb by name unless ambiguous.
    # We need to get both. Use @list to check.
    out = ev(s, f'for v in (verbs(#{pad_num})): player:tell(tostr(verbnum(#{pad_num}, v)) + " " + v); endfor', wait=0.5)
    print(f'  Verbs on pad: {repr(out.strip()[:120])}')

    print(f'  Destinations: Kepler-7 Colony (#{kepler_lz}), Xeris Prime (#{xeris_lz})')


# ---------------------------------------------------------------------------
# Update LZ description to mention spaceport
# ---------------------------------------------------------------------------

def update_lz(s):
    describe(s, LZ, (
        'The colony landing zone is a wide, scorched plateau of alien rock. '
        'The transport that brought you here is already gone, leaving only a faint '
        'contrail against the amber sky. Crates of standard-issue supplies are stacked '
        'near a prefab shelter. A battered sign reads: COLONY WAYPOINT DELTA-7. '
        'Wilderness stretches to the east, south, and west. '
        'A well-worn path leads north toward the colony hub. '
        'A ladder leads up to the colony spaceport.'
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Wayfar 1444 - Phase 2 Expansion')
    print('=' * 60)

    s = connect()

    # Clean up objects from any previous failed run (#401 and above)
    print('\n=== Cleaning up previous run objects ===')
    cleanup_objects(s, range(401, 450))

    rooms = discover_rooms(s)

    setup_resource_nodes(s, rooms)
    fab = setup_fabricator(s, rooms['workshop'])
    spaceport, pad = build_spaceport(s, rooms['lz'])
    xeris_lz = build_xeris_prime(s)

    if pad and xeris_lz:
        setup_launchpad_destinations(s, pad, rooms['lz'], xeris_lz)

    update_lz(s)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Phase 2 complete ===')
    print('New features:')
    print('  mine deposit      - ore in Eastern Flats')
    print('  harvest patch     - fiber in Western Scrublands')
    print('  collect spring    - water in Southern Ridge')
    print('  craft <item>      - at fabricator in Workshop')
    print('  go up             - from LZ to Spaceport Alpha')
    print('  travel <planet>   - at launch pad in Spaceport')
    print('  Xeris Prime       - icy second planet with xenocrystals + salvage')
