#!/usr/bin/env python3
"""
Wayfar 1444 world setup script.

Key HellCore commands discovered:
  @dig <cardinal-dir> to <room-name-or-#obj>  -- creates room + bidirectional exits
  @dig <room-name>                             -- creates unlinked room, moves wizard there
  @create $thing named "name:alias,alias"     -- creates item in wizard inventory
  @describe #obj as "text"                    -- sets description
  @rename #obj to "name"                      -- renames object
  @move #obj to #room                         -- moves object to room
  @recycle #obj                               -- deletes object
  @dump-database                              -- saves DB to disk
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
    except:
        pass
    text = out.decode('utf-8', errors='replace')
    # Strip ANSI codes for clean output
    clean = re.sub(r'\x1b\[[0-9;]*m', '', text)
    return clean


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def goto(s, obj_num):
    send(s, f'@go #{obj_num}', wait=0.5)


def moo_str(text):
    """Escape for MOO string literal."""
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def dig_room(s, direction, name, from_num):
    """
    Dig a new room from from_num in the given direction.
    Returns new room number, or None on failure.
    """
    goto(s, from_num)
    out = send(s, f'@dig {direction} to {name}', wait=1.0)
    # Output: "Created '#NNN' destination room." and "@dug..." are both possible
    # Also: "Created '#NNN'" in the output
    m = re.search(r"'([^']+)' destination room|@dug\s+\S+\s+\(#(\d+)\)|#(\d+)", out)
    # Actually look for object numbers more carefully
    nums = re.findall(r'#(\d+)', out)
    # The destination room number is usually mentioned as "Created '#NNN'"
    created = re.search(r"Created '.*?#(\d+)", out)
    if created:
        return int(created.group(1))
    # Fallback: check all mentioned numbers except known ones
    for n in nums:
        n = int(n)
        if n != from_num and n > 50:
            return n
    print(f'  WARN @dig {direction} to {name}: {repr(out[:200])}')
    return None


def create_item(s, name_spec, in_room):
    """
    Create a $thing. name_spec: "display name:alias,alias"
    Returns object number.
    """
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


def recycle(s, num):
    out = send(s, f'@recycle #{num}', wait=0.7)
    if 'recycled' not in out.lower():
        print(f'  WARN recycle #{num}: {repr(out[:100])}')


# ---------------------------------------------------------------------------
# Step 1: Clean up test objects from earlier sessions
# ---------------------------------------------------------------------------
def cleanup(s):
    print('\n=== Cleaning up test objects ===')
    # Bad room created with wrong @dig syntax
    for obj in [160, 197, 206, 346, 362]:
        out = ev(s, f'player:tell("valid=" + tostr(valid(#{obj})) + " name=" + (valid(#{obj}) ? #{obj}.name | "n/a"))', wait=0.3)
        print(f'  #{obj}: {out.strip()[:60]}')
        if 'valid=1' in out:
            recycle(s, obj)
            print(f'    recycled #{obj}')


# ---------------------------------------------------------------------------
# Step 2: Describe Landing Zone (already exists as #159)
# ---------------------------------------------------------------------------
LZ = 159

def setup_lz(s):
    print(f'\n=== Landing Zone (#{LZ}) ===')
    rename(s, LZ, 'Landing Zone Delta-7')
    describe(s, LZ, (
        'The colony landing zone is a wide, scorched plateau of alien rock. '
        'The transport that brought you here is already gone, leaving only a faint '
        'contrail against the amber sky. Crates of standard-issue supplies are stacked '
        'near a prefab shelter. A battered sign reads: COLONY WAYPOINT DELTA-7. '
        'Wilderness stretches to the east, south, and west. '
        'A well-worn path leads north toward the colony hub.'
    ))
    print('  Done.')


# ---------------------------------------------------------------------------
# Step 3: Build colony rooms north of LZ
# ---------------------------------------------------------------------------
def build_colony(s):
    print('\n=== Building colony rooms ===')
    rooms = {}

    # Hub (north of LZ)
    n = dig_room(s, 'north', 'Colony Hub', LZ)
    if not n:
        print('  FATAL: could not create Colony Hub')
        return rooms
    rooms['hub'] = n
    print(f'  Colony Hub: #{n}')
    describe(s, n, (
        'The colony hub is a pressurized dome roughly thirty meters across. '
        'Modular hab-units ring the interior wall. A public terminal at the center '
        'displays colony status: POPULATION 1, FOOD 14 DAYS, POWER NOMINAL. '
        'Corridors branch east to the workshop, west to the medbay, and north to storage. '
        'The landing zone lies south through a heavy airlock.'
    ))

    # Med Bay (west of hub)
    n = dig_room(s, 'west', 'Medical Bay', rooms['hub'])
    if n:
        rooms['medbay'] = n
        print(f'  Medical Bay: #{n}')
        describe(s, n, (
            'A compact but well-organized medical bay. Autodoc units line one wall, '
            'each capable of diagnosing and treating common injuries and alien pathogens. '
            'A cabinet of pharmaceuticals is secured behind a combination lock. '
            'A faded poster lists symptoms of Stage 1 through Stage 4 xenobiological exposure. '
            'The colony hub lies to the east.'
        ))

    # Workshop (east of hub)
    n = dig_room(s, 'east', 'Colony Workshop', rooms['hub'])
    if n:
        rooms['workshop'] = n
        print(f'  Colony Workshop: #{n}')
        describe(s, n, (
            'The workshop smells of metal shavings and scorched polymer. '
            'Workbenches covered in tools and half-finished components fill the room. '
            'A fabricator unit hums in the corner, ready to manufacture items from raw materials. '
            'Schematics are pinned to every vertical surface. '
            'The colony hub lies to the west.'
        ))

    # Storage (north of hub)
    n = dig_room(s, 'north', 'Colony Storage', rooms['hub'])
    if n:
        rooms['storage'] = n
        print(f'  Colony Storage: #{n}')
        describe(s, n, (
            'Rows of industrial shelving hold the colony material reserves. '
            'Bins are labeled in marker: ORE, POLYMER, CIRCUIT BOARD, WIRE, FOOD RATION, WATER. '
            'A manifest terminal near the door tracks current inventory levels. '
            'The colony hub lies to the south.'
        ))

    return rooms


# ---------------------------------------------------------------------------
# Step 4: Build wilderness rooms around LZ
# ---------------------------------------------------------------------------
def build_wilderness(s):
    print('\n=== Building wilderness rooms ===')
    rooms = {}

    data = [
        ('east',  'Eastern Flats', (
            'The terrain here flattens into a wide plain of compacted alien soil. '
            'Skeletal formations of crystalline mineral jut from the ground at odd angles, '
            'catching the sunlight and scattering it in prismatic patterns. '
            'Tracks of some large creature cross the plain; the creature itself is gone. '
            'The landing zone lies to the west.'
        )),
        ('south', 'Southern Ridge', (
            'A ridge of jagged stone rises here, offering a vantage point over the terrain. '
            'From here you can see the landing zone to the north, and in the far distance, '
            'the wreckage of an older colony attempt: prefab walls collapsed, solar panels shattered. '
            'A cautionary tale written in rust and silence. '
            'The landing zone lies to the north.'
        )),
        ('west',  'Western Scrublands', (
            'Dense alien vegetation crowds the path here: waist-high, fibrous stalks topped with '
            'spore-releasing pods that burst if brushed. '
            'The air is thick with organic compounds. Something moves in the scrub, '
            'quick and low, gone before you can see it clearly. '
            'Foraging here might yield useful plant matter. '
            'The landing zone lies to the east.'
        )),
    ]

    for direction, name, desc in data:
        n = dig_room(s, direction, name, LZ)
        if n:
            key = name.lower().replace(' ', '_')
            rooms[key] = n
            print(f'  {name}: #{n}')
            describe(s, n, desc)

    return rooms


# ---------------------------------------------------------------------------
# Step 5: Create items
# ---------------------------------------------------------------------------
ITEMS = [
    # (name_spec, room_key, description)
    (
        'emergency ration pack:ration,rations,food,pack',
        'lz',
        'A vacuum-sealed pack of compressed nutrients. Not appealing, but calorie-dense enough '
        'to keep a colonist operational for a full standard day. '
        'Label reads: COLONY AUTHORITY STANDARD RATION, MFG DATE REDACTED.'
    ),
    (
        'water canteen:canteen,water',
        'lz',
        'A durable polymer canteen with an integrated filtration nozzle. '
        'Filled with treated water from the colony purification system. '
        'Essential equipment for any surface excursion.'
    ),
    (
        'colony multitool:multitool,tool,knife',
        'lz',
        'A heavy-duty folding multi-tool with seventeen configurations: blade, pry bar, '
        'wire stripper, circuit probe, sample extractor, and more. '
        'Standard issue for all colonists. Handle worn smooth from use.'
    ),
    (
        'survey scanner:scanner,scan',
        'workshop',
        'A handheld device that analyzes surrounding terrain for mineral deposits, '
        'organic matter, and structural anomalies. Display cracked but functional. '
        'Battery life approximately 6 hours per charge.'
    ),
    (
        'med-patch:patch,medpatch,med',
        'medbay',
        'An adhesive medical patch impregnated with broad-spectrum pharmaceuticals. '
        'Apply to skin to treat minor wounds, toxins, and Stage 1 infections. Single use. '
        'Additional patches can be synthesized at the medical bay.'
    ),
    (
        'ore sample:ore,sample,rock',
        'eastern_flats',
        'A rough chunk of alien mineral ore, dark and heavy, threaded with veins of '
        'an iridescent blue compound. The scanner identifies it as high-grade ferrite alloy '
        'with trace xenolithic inclusions. Raw material for fabrication.'
    ),
    (
        'alien plant fiber:fiber,plant,stalk',
        'western_scrublands',
        'A bundle of tough fibrous stalks harvested from the scrublands. '
        'Pale and slightly waxy, surprisingly strong. '
        'Useful as binding material or crude insulation. Smells faintly of ammonia.'
    ),
    (
        'colony manifest:manifest,document,charter',
        'hub',
        'A laminated sheet listing the original colony charter and supply manifest. '
        'Most resource numbers have already been crossed out and updated by hand. '
        'At the bottom someone has written: WE WILL SURVIVE THIS.'
    ),
]

# #190 is the ration pack created during testing - we can repurpose it
EXISTING_ITEMS = {190: ('emergency ration pack', LZ)}


def build_items(s, all_rooms):
    print('\n=== Creating items ===')

    # Repurpose the test ration pack (#190)
    describe(s, 190, (
        'A vacuum-sealed pack of compressed nutrients. Not appealing, but calorie-dense enough '
        'to keep a colonist operational for a full standard day. '
        'Label reads: COLONY AUTHORITY STANDARD RATION, MFG DATE REDACTED.'
    ))
    rename(s, 190, 'emergency ration pack')
    ev(s, '#190.aliases = {"ration", "rations", "food", "pack"}')
    send(s, f'@move #190 to #{LZ}', wait=0.5)
    print(f'  Repurposed #190: emergency ration pack -> #{LZ}')

    # Room lookup
    room_map = {'lz': LZ}
    room_map.update(all_rooms)

    for spec, room_key, desc in ITEMS:
        if spec.startswith('emergency ration'):
            continue  # already handled above
        room_num = room_map.get(room_key)
        if room_num is None:
            print(f'  SKIP (no room {room_key}): {spec.split(":")[0]}')
            continue
        num = create_item(s, spec, room_num)
        if num:
            describe(s, num, desc)
            print(f'  #{num}: {spec.split(":")[0]} -> #{room_num}')


# ---------------------------------------------------------------------------
# Step 6: Welcome screen
# ---------------------------------------------------------------------------
def set_welcome(s):
    print('\n=== Welcome screen ===')
    lines = [
        '',
        '      :::       :::  :::     :::   ::: :::::::::: :::     ::::::::: ',
        '      :+:       :+::+: :+:  :+:   :+: :+:        :+:    :+:    :+: ',
        '      +:+       +:+      +:+ +:+  +:+ +:+        +:+    +:+    +:+  ',
        '      +#+  +:+  +#++#++:++#++  +#++:+ :#::+::#   +#+    +#++:++#++  ',
        '      +#+ +#+#+ +#++#+    +#+  +#+    +#+        +#+    +#+    +#+  ',
        '       #+#+# #+#+# #+#    #+#  #+#    #+#        #+#    #+#    #+#  ',
        '        ###   ###  ###    ###  ###    ########## ###### #########   ',
        '',
        '                    [ W A Y F A R   1 4 4 4 ]                      ',
        '             sci-fi survival & colonization moo  |  est. 2010       ',
        '',
    ]
    moo_list = '{' + ', '.join(moo_str(l) for l in lines) + '}'
    ev(s, f'$login.welcome_message = {moo_list}')

    quotes = [
        ('You are a colonist. The planet does not care if you survive.',       'Wayfar 1444'),
        ('The stars are indifferent. The colony is not.',                      'Unknown colonist'),
        ('Survival is not a right. It is a skill.',                            'Frontier doctrine'),
        ('Build or die. There is no third option.',                            'Colony charter'),
        ('Every piece of ore you pull from this rock is a vote for tomorrow.', 'Colony overseer'),
        ('The wilderness does not yield. You take what you can, while you can.','Survey log, Year 1'),
    ]
    moo_quotes = (
        '{'
        + ', '.join(
            '{{' + moo_str(q) + '}, ' + moo_str(attr) + '}'
            for q, attr in quotes
        )
        + '}'
    )
    ev(s, f'$login.quotes = {moo_quotes}')
    print('  Done.')


# ---------------------------------------------------------------------------
# Step 7: Set player start location
# ---------------------------------------------------------------------------
def set_start(s):
    print(f'\n=== Player start location -> #{LZ} ===')
    # Try known properties
    ev(s, f'$login.start_room = #{LZ}')
    # Also set default home for new players via player class
    ev(s, f'$player_class.home = #{LZ}')
    out = ev(s, f'player:tell("start_room=" + tostr($login.start_room))')
    print(f'  {out.strip()[:80]}')


# ---------------------------------------------------------------------------
# Step 8: Wizard room
# ---------------------------------------------------------------------------
def setup_wizard_room(s):
    print('\n=== Wizard room (Colony Command, #339) ===')
    rename(s, 339, 'Colony Command')
    describe(s, 339, (
        'The nerve center of colony administrative operations. '
        'Banks of terminals line the walls, showing real-time surface sensor feeds. '
        'A holographic display in the center projects a topographic map of the terrain. '
        'The air carries the tang of recycled atmosphere and machine oil.'
    ))
    print('  Done.')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('Wayfar 1444 Setup')
    print('=' * 60)

    s = connect()

    cleanup(s)
    setup_lz(s)
    setup_wizard_room(s)
    set_welcome(s)

    colony_rooms = build_colony(s)
    wild_rooms   = build_wilderness(s)

    all_rooms = {}
    all_rooms.update(colony_rooms)
    all_rooms.update(wild_rooms)

    build_items(s, all_rooms)
    set_start(s)

    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.0)
    print(f'  {out.strip()[:80]}')

    s.sendall(b'QUIT\r\n')
    s.close()

    print('\n=== Done ===')
    print(f'Connect: telnet localhost {PORT}')
    print('Login:   connect wizard')
    print('\nRooms built:')
    print(f'  #159: Landing Zone Delta-7')
    print(f'  #339: Colony Command (wizard)')
    for k, v in all_rooms.items():
        print(f'  #{v}: {k}')
