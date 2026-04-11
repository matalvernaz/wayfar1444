#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 39: Playtest Fixes

Fixes from wizard playtest session:
  1. u/d shortcuts — wildcard verbs u*p and d*own on $player
  2. Shuttle east exit — remove east_exit so only exit/out works
  3. Biome descriptions — richer, more atmospheric per biome
  4. Empty-name inventory junk — clean up and prevent display

Run with server live: python3 phase39_playtest_fixes.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''; deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR entering @program: {repr(out[:150])}', flush=True)
        return False
    old = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 20 == 19:
            print(f'    ... {i+1}/{len(code_lines)}', flush=True)
    s.settimeout(old)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR:\n{result[:600]}', flush=True)
        return False
    print(f'  OK: {obj_expr}:{verbname}', flush=True)
    return True


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


PLAYER = 6
SH = 1702   # Shuttle Interior
JN = 1703   # Junction
WROOM = 452  # Wilderness room archetype


s = connect()
print('Connected.', flush=True)

# =========================================================================
# Fix 1: u/d shortcuts — wildcard verbs on $player
# =========================================================================
print('\n=== Fix 1: u*p and d*own wildcard verbs ===', flush=True)

# Remove old up/down verbs
send(s, f'@rmverb #{PLAYER}:up', wait=0.5)
send(s, f'@rmverb #{PLAYER}:down', wait=0.5)

# Add wildcarded up verb
send(s, f'@verb #{PLAYER}:"u*p" none none none', wait=0.6)
program_verb(s, f'#{PLAYER}', 'up', [
    '"Move up — supports room exit.";',
    'try',
    '  dest = player.location.up_exit;',
    '  if (valid(dest))',
    '    player.location:announce(player.name + " heads up.", player);',
    '    move(player, dest);',
    '    player.location:announce(player.name + " arrives from below.", player);',
    '    return;',
    '  endif',
    'except e (ANY)',
    'endtry',
    'player:tell("You cannot go that way.");',
])

# Add wildcarded down verb
send(s, f'@verb #{PLAYER}:"d*own" none none none', wait=0.6)
program_verb(s, f'#{PLAYER}', 'down', [
    '"Move down — supports room exit.";',
    'try',
    '  dest = player.location.down_exit;',
    '  if (valid(dest))',
    '    player.location:announce(player.name + " heads down.", player);',
    '    move(player, dest);',
    '    player.location:announce(player.name + " arrives from above.", player);',
    '    return;',
    '  endif',
    'except e (ANY)',
    'endtry',
    'player:tell("You cannot go that way.");',
])

# =========================================================================
# Fix 2: Shuttle room — remove east_exit, keep only exit/out
# =========================================================================
print('\n=== Fix 2: Remove shuttle east_exit ===', flush=True)
ev(s, f'delete_property(#{SH}, "east_exit")', wait=0.5)
print(f'  Removed east_exit from #{SH}', flush=True)

# Verify out_exit still exists
out = ev(s, f'player:tell(tostr(#{SH}.out_exit))', wait=0.4)
print(f'  Shuttle out_exit: {out.strip()[:60]}', flush=True)

# Also add "out" verb alias on shuttle if not present
send(s, f'@rmverb #{SH}:out', wait=0.3)
send(s, f'@verb #{SH}:"out" none none none', wait=0.6)
program_verb(s, f'#{SH}', 'out', [
    'player:tell("You duck through the hatch and step onto the station.");',
    f'move(player, #{JN});',
])

# Update shuttle look_self to not mention east
print('  Updating shuttle look_self...', flush=True)
program_verb(s, f'#{SH}', 'look_self', [
    'player:tell("");',
    f'player:tell("  " + #{SH}.name);',
    'player:tell("");',
    f'player:tell(#{SH}.description);',
    'player:tell("");',
    'player:tell("  Type EXIT or OUT to disembark.");',
    'player:tell("");',
])

# =========================================================================
# Fix 3: Biome descriptions — richer atmosphere
# =========================================================================
print('\n=== Fix 3: Atmospheric biome descriptions ===', flush=True)

# New biome descriptions — longer, more evocative, end naturally so
# resource node descriptions flow seamlessly after them
NEW_BIOME_DESCS = [
    # 0 - Mountain
    (
        'Jagged peaks and exposed rock faces rise around you, the stone '
        'scarred by ancient tectonic violence. Wind keens through narrow '
        'passes. Mineral veins glint in the cliff walls where erosion has '
        'stripped the surface bare. The air is thin and bitterly cold.'
    ),
    # 1 - Forest
    (
        'Towering alien trees form a dense canopy overhead, their trunks '
        'wider than hab-modules. Fibrous undergrowth crunches underfoot. '
        'Shafts of pale light filter through gaps in the foliage, catching '
        'drifting clouds of spores. Something calls in the distance — not '
        'quite a bird.'
    ),
    # 2 - Desert
    (
        'Endless dunes of amber sand stretch to the horizon under a sky '
        'bleached almost white by the twin suns. The heat shimmers off the '
        'ground in visible waves. Half-buried wreckage and ancient ruins '
        'poke through the surface, slowly being swallowed by the sand.'
    ),
    # 3 - Jungle
    (
        'Dense tropical vegetation chokes every surface in a riot of alien '
        'green. Moisture drips from broad leaves the size of solar panels. '
        'The air is heavy, hot, and alive with the drone of unseen insects. '
        'Thick roots snake across the ground and hidden water trickles nearby.'
    ),
    # 4 - Underwater
    (
        'Shallow alien waters lap against your suit, warm and faintly '
        'luminescent. Bioluminescent organisms pulse beneath the surface '
        'in slow, rhythmic waves. The ground is soft silt that clouds with '
        'every step. Strange fronds sway in currents you cannot feel.'
    ),
    # 5 - Fungal Zone
    (
        'WARNING: Fungal zone. Towering alien mushrooms rise from the earth '
        'like bloated pillars, their caps weeping a milky fluid. Clouds of '
        'spores drift in thick curtains. The air is acrid and sweet in a way '
        'that makes your suit filters cycle hard. Diseases are likely.'
    ),
    # 6 - Volcanic
    (
        'WARNING: Volcanic zone. The ground radiates searing heat through '
        'your boot soles. Sulphur vents hiss and spit between cracked '
        'basalt slabs. Rivers of cooling magma glow dull orange in the '
        'crevasses. Energy readings spike across the board. Move quickly.'
    ),
]

# Build MOO list literal
desc_list_moo = '{' + ', '.join(moo_str(d) for d in NEW_BIOME_DESCS) + '}'

# Update on planet object (Kepler-7 = #0.kepler7)
out = ev(s, 'player:tell(tostr(#0.kepler7))', wait=0.4)
kepler_num = re.search(r'#(\d+)', out)
if kepler_num:
    kepler_num = kepler_num.group(1)
    ev(s, f'#{kepler_num}.biome_descs = {desc_list_moo}', wait=0.8)
    print(f'  Updated biome_descs on #{kepler_num} (Kepler-7)', flush=True)
else:
    print('  WARN: Could not find Kepler-7 planet object', flush=True)

# Also check for any other active planets
out = ev(s, 'try for p in (#0.active_planets) player:tell(tostr(p) + " " + p.name); endfor except e (ANY) player:tell("no active_planets"); endtry', wait=0.8)
print(f'  Active planets: {out.strip()[:200]}', flush=True)

# =========================================================================
# Fix 4: Clean up empty-name objects from wizard inventory
# =========================================================================
print('\n=== Fix 4: Clean up empty-name junk ===', flush=True)

# Count and recycle empty-name items from wizard's inventory
out = ev(s, '''
count = 0;
for obj in (player.contents)
  if (obj.name == "")
    recycle(obj);
    count = count + 1;
  endif
endfor
player:tell("Recycled " + tostr(count) + " empty-name objects");
'''.replace('\n', ' '), wait=2.0)
print(f'  {out.strip()[:200]}', flush=True)

# Also fix inventory verb to skip empty-name items gracefully
print('  Updating inventory verb to handle empty names...', flush=True)
program_verb(s, f'#{PLAYER}', 'inventory', [
    '"Show inventory with stacked counts.";',
    'p = player;',
    'if (length(p.contents) == 0)',
    '  p:tell("You are empty-handed.");',
    '  return;',
    'endif',
    '"Count items by name";',
    'names = {};',
    'counts = {};',
    'for itm in (p.contents)',
    '  nm = itm.name;',
    '  if (nm == "")',
    '    nm = "(unknown object)";',
    '  endif',
    '  found = 0;',
    '  for i in [1..length(names)]',
    '    if (names[i] == nm)',
    '      counts = listset(counts, counts[i] + 1, i);',
    '      found = 1;',
    '    endif',
    '  endfor',
    '  if (!found)',
    '    names = listappend(names, nm);',
    '    counts = listappend(counts, 1);',
    '  endif',
    'endfor',
    'p:tell("You are carrying:");',
    'for i in [1..length(names)]',
    '  if (counts[i] > 1)',
    '    p:tell("  " + tostr(counts[i]) + "x " + names[i]);',
    '  else',
    '    p:tell("  " + names[i]);',
    '  endif',
    'endfor',
])

# =========================================================================
# Fix Junction exits display to show up direction
# =========================================================================
print('\n=== Fix Junction look_self to show up exit ===', flush=True)
program_verb(s, f'#{JN}', 'look_self', [
    'player:tell("");',
    f'player:tell("  " + #{JN}.name);',
    'player:tell("");',
    f'player:tell(#{JN}.description);',
    'player:tell("");',
    'for obj in (this.contents)',
    '  if (obj != player && is_player(obj))',
    '    player:tell("  " + obj.name + " is here.");',
    '  endif',
    'endfor',
    'player:tell("  Exits: north, south, east, west, up");',
    'player:tell("");',
])

# Fix Obs Deck look_self to show down exit
print('\n=== Fix Obs Deck look_self to show down exit ===', flush=True)

# Check if Obs Deck has look_self
out = send(s, '@list #3840:look_self', wait=1.0)
if 'programming' in out.lower() or 'That object' in out:
    send(s, '@verb #3840:"look_self" none none none', wait=0.6)

program_verb(s, '#3840', 'look_self', [
    'player:tell("");',
    '  player:tell("  " + this.name);',
    'player:tell("");',
    '  player:tell(this.description);',
    'player:tell("");',
    'for obj in (this.contents)',
    '  if (obj != player && is_player(obj))',
    '    player:tell("  " + obj.name + " is here.");',
    '  endif',
    'endfor',
    'player:tell("  Exits: down");',
    'player:tell("");',
])

# Fix Lobby look_self to show south exit
print('\n=== Fix Lobby exits ===', flush=True)
program_verb(s, '#1704', 'look_self', [
    'player:tell("");',
    f'player:tell("  " + #1704.name);',
    'player:tell("");',
    f'player:tell(#1704.description);',
    'player:tell("");',
    'player:tell("  [TERMINALS]");',
    'player:tell("  BACKGROUND <1-6>  -- register your colonial file");',
    'player:tell("  DISPATCH          -- deploy to the planet surface");',
    'player:tell("");',
    'player:tell("  Exits: west, south");',
    'player:tell("");',
])

# =========================================================================
# Save
# =========================================================================
print('\n=== Saving database ===', flush=True)
send(s, '@dump-database', wait=3.0)
s.close()
print('\nDone. Fixes applied:', flush=True)
print('  1. u/d shortcuts now work (wildcard u*p, d*own)', flush=True)
print('  2. Shuttle only exits via exit/out (no east)', flush=True)
print('  3. Biome descriptions more atmospheric', flush=True)
print('  4. Empty-name inventory items cleaned up', flush=True)
