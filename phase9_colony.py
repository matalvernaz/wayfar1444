#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 9: Per-Player Colony (Redesign D)

Adds:
  1. Sector center kit recipe (2x inert metal + 2x crude wire)
  2. place sector center — spawns 3-room complex for the placing player:
       Plaza (entrance), Governor's Office (east), Factorium (south)
     Rooms are wired with exit properties; portal building stays in wilderness
  3. out verb on $player — exit rooms via out_exit property
  4. enter verb on $player — enter a sector center building
  5. colony verb on $player — teleport to your sector center
  6. labor verb — earn 10 cr in factorium (1h cooldown)
  7. w_colony property on $player
  8. Governor's Office: colony command shows population + buildings
     (initial stub — full colony management in later phase)

Run with server live: python3 phase9_colony.py
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')

HOST = 'localhost'
PORT = 7777
PLAYER = 6
BUILDING_PROTO = 117   # $building
BCT_NUM = 592          # $basic_craft_tool


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, e, wait=0.7):
    return send(s, '; ' + e, wait)


def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj_expr}:{verbname}: {repr(out[:150])}')
        return False
    old_to = s.gettimeout()
    s.settimeout(0.3)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.06)
        if i % 15 == 14:
            print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old_to)
    result = send(s, '.', wait=3.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR {obj_expr}:{verbname}:')
        print(result[:600])
        return False
    print(f'  OK: {obj_expr}:{verbname}')
    return True


def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}')


# ─────────────────────────────────────────────────────────────────────────────
# place_sc verb — spawns 3-room sector center complex
# Called from updated place verb when kit contains "sector center"
# ─────────────────────────────────────────────────────────────────────────────

PLACE_SC_VERB = [
    '"Spawn 3-room sector center complex for the player. Called by place verb.";',
    'p = player;',
    'loc = p.location;',
    '"Check: already have one";',
    'if (valid(p.w_colony))',
    '  p:tell("You already have a sector center. (Type \'colony\' to return to it.)");',
    '  return;',
    'endif',
    'p:tell("Assembling sector center... this may take a moment.");',
    '"Create 3 rooms as children of $sc_room (custom look_self, no area() call)";',
    'plaza = create($sc_room);',
    'gov = create($sc_room);',
    'fact = create($sc_room);',
    '"Set names";',
    'plaza.name = p.name + "\'s Sector Center — Central Plaza";',
    'gov.name = p.name + "\'s Sector Center — Governor\'s Office";',
    'fact.name = p.name + "\'s Sector Center — Factorium";',
    '"Set descriptions";',
    'plaza.description = "The central hub of " + p.name + "\'s colonial outpost. A resource locker stands against one wall. The Governor\'s Office is to the east; the Factorium lies to the south.";',
    'gov.description = "A spartan office with a flickering holographic display. Colony management functions are available here.";',
    'fact.description = "A cavernous work hall. A labor coordinator terminal glows on the far wall. Hard work earns credits here.";',
    '"Add exit properties to plaza";',
    'add_property(plaza, "east_exit", $nothing, {p, "rw"});',
    'add_property(plaza, "south_exit", $nothing, {p, "rw"});',
    'add_property(plaza, "out_exit", $nothing, {p, "rw"});',
    'add_property(plaza, "sc_owner", $nothing, {p, "rw"});',
    '"Add exit properties to gov office";',
    'add_property(gov, "west_exit", $nothing, {p, "rw"});',
    'add_property(gov, "sc_owner", $nothing, {p, "rw"});',
    '"Add exit properties to factorium";',
    'add_property(fact, "north_exit", $nothing, {p, "rw"});',
    'add_property(fact, "sc_owner", $nothing, {p, "rw"});',
    'add_property(fact, "labor_cd", 0, {p, "rw"});',
    '"Wire exits";',
    'plaza.east_exit = gov;',
    'plaza.south_exit = fact;',
    'plaza.out_exit = loc;',
    'gov.west_exit = plaza;',
    'fact.north_exit = plaza;',
    '"Set owners";',
    'plaza.sc_owner = p; gov.sc_owner = p; fact.sc_owner = p;',
    '"Store in player";',
    'p.w_colony = plaza;',
    '"Create portal building in wilderness room";',
    'portal = create($building);',
    'portal.name = p.name + "\'s sector center";',
    'portal.description = "A compact prefab administrative complex. Type \'enter sector center\' to go inside.";',
    'portal.b_type = "sector center";',
    'portal.b_owner = p;',
    'portal.b_hp = 2500; portal.b_hp_max = 2500;',
    'portal.b_x = (("x" in properties(loc)) ? loc.x | 0);',
    'portal.b_y = (("y" in properties(loc)) ? loc.y | 0);',
    'add_property(portal, "sc_plaza", $nothing, {p, "rw"});',
    'portal.sc_plaza = plaza;',
    'move(portal, loc);',
    '"Move player to plaza";',
    'move(p, plaza);',
    'p:tell("The sector center snaps into place. You stand in the central plaza.");',
    'p:tell("  east  — Governor\'s Office");',
    'p:tell("  south — Factorium (earn credits via \'labor\')");',
    'p:tell("  out   — Return to wilderness");',
    'loc:announce(p.name + " erects a sector center here.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# Updated place verb — routes sector center kits to place_sc
# ─────────────────────────────────────────────────────────────────────────────

PLACE_VERB_V2 = [
    '"Deploy a building kit at current location. Usage: place <kit name>.";',
    'p = player;',
    'query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (query == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      query = query == "" ? w | query + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (query == "")',
    '  p:tell("Place what? (e.g. place shelter / place sector center)");',
    '  return;',
    'endif',
    '"Find kit matching query";',
    'kit = 0;',
    'for itm in (p.contents)',
    '  nm = "";',
    '  try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '  if (index(nm, query) && index(nm, "kit"))',
    '    kit = itm; break;',
    '  endif',
    'endfor',
    'if (kit == 0)',
    '  p:tell("You\'re not carrying a \'" + query + "\' kit.");',
    '  return;',
    'endif',
    '"Route sector center kits to place_sc";',
    'if (index(kit.name, "sector center"))',
    '  recycle(kit);',
    '  this:place_sc();',
    '  return;',
    'endif',
    '"Normal building placement";',
    'loc = p.location;',
    'kn = kit.name;',
    'bname = strsub(kn, " kit", "");',
    'b = create($building);',
    'b.name = bname;',
    'b.description = kit.description;',
    'b.b_owner = p;',
    'b.b_type = bname;',
    'b.b_hp = 100; b.b_hp_max = 100;',
    'b.b_x = (("x" in properties(loc)) ? loc.x | 0);',
    'b.b_y = (("y" in properties(loc)) ? loc.y | 0);',
    'move(b, loc);',
    'recycle(kit);',
    'p:tell("You unfold and anchor the " + bname + " to the ground. [building placed]");',
    'loc:announce(p.name + " constructs a " + bname + " here.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# out verb — exit non-wilderness rooms via out_exit property
# ─────────────────────────────────────────────────────────────────────────────

OUT_VERB = [
    '"Exit current room (sector center, buildings, etc.) via out_exit.";',
    'loc = player.location;',
    'if (parent(loc) == $wroom)',
    '  player:tell("You are already in the wilderness.");',
    '  return;',
    'endif',
    'if ("out_exit" in properties(loc))',
    '  dest = loc.out_exit;',
    '  if (valid(dest))',
    '    loc:announce(player.name + " heads outside.", player);',
    '    move(player, dest);',
    '    player.location:announce(player.name + " steps out of a building.", player);',
    '    return;',
    '  endif',
    'endif',
    'player:tell("There\'s no exit that way.");',
]


# ─────────────────────────────────────────────────────────────────────────────
# enter verb — enter a sector center or other building
# ─────────────────────────────────────────────────────────────────────────────

ENTER_VERB = [
    '"Enter a building in the current room. Usage: enter sector center (or just: enter)";',
    'p = player;',
    'query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (query == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      query = query == "" ? w | query + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    '"Search room contents for enterable buildings — prefer player-owned valid portal";',
    'target = 0;',
    'for itm in (p.location.contents)',
    '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
    '    if (query == "" || index(itm.name, query))',
    '      if (!valid(itm.sc_plaza))',
    '        "Skip portals with recycled interior";',
    '      elseif (target == 0)',
    '        target = itm;',
    '      elseif ("b_owner" in properties(itm) && itm.b_owner == p)',
    '        "Prefer the one we own";',
    '        target = itm;',
    '      endif',
    '    endif',
    '  endif',
    'endfor',
    'if (target == 0)',
    '  p:tell("Nothing to enter here.");',
    '  return;',
    'endif',
    'dest = target.sc_plaza;',
    'if (!valid(dest))',
    '  p:tell("The building interior is inaccessible.");',
    '  return;',
    'endif',
    'p.location:announce(p.name + " enters " + target.name + ".", p);',
    'move(p, dest);',
    'p.location:announce(p.name + " arrives.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# colony verb — teleport to your sector center
# ─────────────────────────────────────────────────────────────────────────────

COLONY_VERB = [
    '"Teleport to your sector center, or show colony status if already inside.";',
    'p = player;',
    'if (!valid(p.w_colony))',
    '  p:tell("You have not established a colony yet.");',
    '  p:tell("Craft a sector center kit (2x inert metal + 2x crude wire) and use \'place sector center\'.");',
    '  return;',
    'endif',
    'if (p.location == p.w_colony)',
    '  "Already here — show colony summary";',
    '  p:tell("=== COLONY: " + p.w_colony.name + " ===");',
    '  buildings_here = {};',
    '  for itm in (p.location.contents)',
    '    if (is_a(itm, $building))',
    '      buildings_here = listappend(buildings_here, itm);',
    '    endif',
    '  endfor',
    '  if (buildings_here == {})',
    '    p:tell("No structures in this room.");',
    '  else',
    '    for b in (buildings_here)',
    '      p:tell("  [" + b.b_type + "] HP: " + tostr(b.b_hp) + "/" + tostr(b.b_hp_max));',
    '    endfor',
    '  endif',
    'else',
    '  move(p, p.w_colony);',
    '  p:tell("You return to your sector center.");',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# labor verb — earn credits in the factorium (1h cooldown)
# ─────────────────────────────────────────────────────────────────────────────

LABOR_VERB = [
    '"Perform manual labor in the factorium for credits. 1-hour cooldown.";',
    'p = player;',
    'loc = p.location;',
    '"Must be in a factorium room";',
    'if (!("labor_cd" in properties(loc)))',
    '  p:tell("There\'s no labor work available here.");',
    '  p:tell("(Find a Factorium — the south room of a sector center.)");',
    '  return;',
    'endif',
    'now = time();',
    'if (loc.labor_cd > now)',
    '  mins = (loc.labor_cd - now) / 60;',
    '  p:tell("The labor coordinator is on break. (Available in " + tostr(mins) + " min)");',
    '  return;',
    'endif',
    'loc.labor_cd = now + 3600;',
    'earn = 10;',
    'p.w_credits = p.w_credits + earn;',
    'p:tell("You spend an hour on the factorium floor. [+" + tostr(earn) + " cr]");',
    'p:tell("Balance: " + tostr(p.w_credits) + " cr");',
    'loc:announce(p.name + " works the floor.", p);',
]


def main():
    s = connect()

    # ── 1. Add w_colony property to $player ───────────────────────────────────
    print('=== Add w_colony to $player ===')
    out = ev(s, 'player:tell("w_colony" in properties($player))', wait=0.7)
    if '1' in out.strip()[-10:]:
        print('  w_colony already exists')
    else:
        out = ev(s, 'add_property($player, "w_colony", $nothing, {player, "rw"})', wait=0.8)
        print(f'  add_property: {out.strip()[-40:]}')

    # ── 2. place_sc sub-verb ──────────────────────────────────────────────────
    print('\n=== place_sc verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"place_sc"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'place_sc', PLACE_SC_VERB)

    # ── 3. Update place verb ──────────────────────────────────────────────────
    print('\n=== Update place verb on $player ===')
    program_verb(s, f'#{PLAYER}', 'place', PLACE_VERB_V2)

    # ── 4. out verb ───────────────────────────────────────────────────────────
    print('\n=== out verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"out exit"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'out', OUT_VERB)

    # ── 5. enter verb ─────────────────────────────────────────────────────────
    print('\n=== enter verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"enter"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'enter', ENTER_VERB)

    # ── 6. colony verb ────────────────────────────────────────────────────────
    print('\n=== colony verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"colony"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'colony', COLONY_VERB)

    # ── 7. labor verb ─────────────────────────────────────────────────────────
    print('\n=== labor verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"labor"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'labor', LABOR_VERB)

    # ── 8. Add sector center kit recipe to craft verb ─────────────────────────
    # We need to read existing craft verb and append the recipe
    # Instead, we'll reprogram it with the recipe appended inline
    print('\n=== Add sector center kit recipe to craft verb ===')
    # Append just the sector center kit recipe to craft verb
    # We push a brand new craft verb that includes all existing recipes + sc kit
    SC_RECIPE = [
        '"=== SECTOR CENTER KIT ===";',
        'if (index(tgt, "sector") || index(tgt, "center") || index(tgt, "sc kit"))',
        '  found_m = {}; found_w = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_m) < 2 && index(n, "inert metal"))',
        '      found_m = listappend(found_m, itm);',
        '    endif',
        '    if (length(found_w) < 2 && index(n, "crude wire"))',
        '      found_w = listappend(found_w, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_m) < 2)',
        '    p:tell("Need 2x inert metal. Have: " + tostr(length(found_m)));',
        '    return;',
        '  endif',
        '  if (length(found_w) < 2)',
        '    p:tell("Need 2x crude wire. Have: " + tostr(length(found_w)));',
        '    return;',
        '  endif',
        '  recycle(found_m[1]); recycle(found_m[2]);',
        '  recycle(found_w[1]); recycle(found_w[2]);',
        '  r = create($thing); r.name = "sector center kit";',
        '  r.description = "A compressed prefab colony administration complex. Deploy with: place sector center";',
        '  move(r, p);',
        '  p:tell("You assemble the components into a sector center kit. [+sector center kit]");',
        '  return;',
        'endif',
    ]

    # Full craft verb with all recipes including sector center kit
    craft_full = [
        '"Craft items using a basic crafting tool from inventory.";',
        'p = player;',
        'tool = 0;',
        'for itm in (player.contents)',
        f'  if (is_a(itm, #{BCT_NUM}))',
        '    tool = itm; break;',
        '  endif',
        'endfor',
        'if (tool == 0)',
        '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
        '  return;',
        'endif',
        'tgt = "";',
        'for w in (args)',
        '  tgt = (tgt == "") ? w | (tgt + " " + w);',
        'endfor',
        'if (typeof(dobjstr) == STR && dobjstr != "")',
        '  tgt = dobjstr;',
        'endif',
        'if (tgt == "" || tgt == "list" || tgt == "help")',
        '  p:tell("=== BASIC CRAFTING TOOL — RECIPES ===");',
        '  p:tell("  ration bar           — 2x fiber");',
        '  p:tell("  water canteen        — 1x fiber + 1x raw water");',
        '  p:tell("  inert metal          — 2x ore/mineral");',
        '  p:tell("  crude wire           — 1x ore + 1x salvage");',
        '  p:tell("  pre-fab shelter kit  — 1x inert metal + 2x fiber");',
        '  p:tell("  sector center kit    — 2x inert metal + 2x crude wire");',
        '  p:tell("Usage: craft <recipe name>");',
        '  return;',
        'endif',
        # RATION BAR
        'if (index(tgt, "ration") || index(tgt, "food") || index(tgt, "bar"))',
        '  found = {};',
        '  for itm in (p.contents)',
        '    if (length(found) < 2 && (index(itm.name, "fiber") || index(itm.name, "plant")))',
        '      found = listappend(found, itm);',
        '    endif',
        '  endfor',
        '  if (length(found) < 2)',
        '    p:tell("Need 2x fiber. Have: " + tostr(length(found)));',
        '    return;',
        '  endif',
        '  recycle(found[1]); recycle(found[2]);',
        '  r = create($thing); r.name = "ration bar";',
        '  r.description = "A compressed brick of processed plant fiber.";',
        '  move(r, p);',
        '  p:tell("You press the fibers into a dense ration bar. [+food item]");',
        '  p.location:announce(p.name + " uses a crafting tool.", p);',
        '  return;',
        'endif',
        # WATER CANTEEN
        'if (index(tgt, "water") || index(tgt, "canteen"))',
        '  found_f = {}; found_w = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_f) == 0 && (index(n, "fiber") || index(n, "plant")))',
        '      found_f = listappend(found_f, itm);',
        '    endif',
        '    if (length(found_w) == 0 && (index(n, "water") || index(n, "liquid")))',
        '      found_w = listappend(found_w, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_f) == 0)',
        '    p:tell("Need 1x fiber.");',
        '    return;',
        '  endif',
        '  if (length(found_w) == 0)',
        '    p:tell("Need 1x water sample.");',
        '    return;',
        '  endif',
        '  recycle(found_f[1]); recycle(found_w[1]);',
        '  r = create($thing); r.name = "water canteen";',
        '  r.description = "A rough fiber-bound canteen containing filtered drinking water.";',
        '  move(r, p);',
        '  p:tell("You weave fiber around the water sample into a sealed canteen. [+drink item]");',
        '  return;',
        'endif',
        # INERT METAL
        'if (index(tgt, "inert") || index(tgt, "metal"))',
        '  found = {};',
        '  for itm in (p.contents)',
        '    if (length(found) < 2)',
        '      n = itm.name;',
        '      if (index(n, "ore") || index(n, "mineral") || index(n, "rock") || index(n, "stone"))',
        '        found = listappend(found, itm);',
        '      endif',
        '    endif',
        '  endfor',
        '  if (length(found) < 2)',
        '    p:tell("Need 2x ore/mineral. Have: " + tostr(length(found)));',
        '    return;',
        '  endif',
        '  recycle(found[1]); recycle(found[2]);',
        '  r = create($thing); r.name = "inert metal";',
        '  r.description = "Smelted alien ore, shaped into a rough ingot. Foundation of all construction.";',
        '  move(r, p);',
        '  p:tell("You smelt the ore samples into an inert metal ingot. [+inert metal]");',
        '  return;',
        'endif',
        # CRUDE WIRE
        'if (index(tgt, "wire") || index(tgt, "crude"))',
        '  found_o = {}; found_s = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_o) == 0 && (index(n, "ore") || index(n, "mineral")))',
        '      found_o = listappend(found_o, itm);',
        '    endif',
        '    if (length(found_s) == 0 && (index(n, "salvage") || index(n, "scrap") || index(n, "wreckage")))',
        '      found_s = listappend(found_s, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_o) == 0)',
        '    p:tell("Need 1x ore/mineral.");',
        '    return;',
        '  endif',
        '  if (length(found_s) == 0)',
        '    p:tell("Need 1x salvage/scrap.");',
        '    return;',
        '  endif',
        '  recycle(found_o[1]); recycle(found_s[1]);',
        '  r = create($thing); r.name = "crude wire";',
        '  r.description = "Rough conductive wire pulled from salvage and ore.";',
        '  move(r, p);',
        '  p:tell("You draw ore through salvage frames into crude wire. [+crude wire]");',
        '  return;',
        'endif',
        # PRE-FAB SHELTER KIT
        'if (index(tgt, "shelter") || index(tgt, "prefab") || index(tgt, "pre"))',
        '  found_m = {}; found_f = {};',
        '  for itm in (p.contents)',
        '    n = itm.name;',
        '    if (length(found_m) == 0 && index(n, "inert metal"))',
        '      found_m = listappend(found_m, itm);',
        '    endif',
        '    if (length(found_f) < 2 && (index(n, "fiber") || index(n, "plant")))',
        '      found_f = listappend(found_f, itm);',
        '    endif',
        '  endfor',
        '  if (length(found_m) == 0)',
        '    p:tell("Need 1x inert metal.");',
        '    return;',
        '  endif',
        '  if (length(found_f) < 2)',
        '    p:tell("Need 2x fiber. Have: " + tostr(length(found_f)));',
        '    return;',
        '  endif',
        '  recycle(found_m[1]); recycle(found_f[1]); recycle(found_f[2]);',
        '  r = create($thing); r.name = "pre-fab shelter kit";',
        '  r.description = "A collapsed alloy-frame shelter with fiber panels. Type \'place shelter\' to deploy.";',
        '  move(r, p);',
        '  p:tell("You assemble metal frame and fiber panels into a pre-fab shelter kit. [+shelter kit]");',
        '  return;',
        'endif',
    ] + SC_RECIPE + [
        'p:tell("Unknown recipe: \'" + tgt + "\'");',
        'p:tell("Type \'craft\' to see available recipes.");',
    ]
    program_verb(s, f'#{PLAYER}', 'craft', craft_full)

    # ── 9. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test sector center ===')
    add_verb(s, f'#{PLAYER}', '"colony_test"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'colony_test', [
        '"Test sector center craft + placement.";',
        'player:tell("=== COLONY_TEST BEGIN ===");',
        '"Clear existing colony if any";',
        'if ("w_colony" in properties(player) && valid(player.w_colony))',
        '  old_plaza = player.w_colony;',
        '  if ("east_exit" in properties(old_plaza))',
        '    old_gov = old_plaza.east_exit;',
        '    if (valid(old_gov)) recycle(old_gov); endif',
        '  endif',
        '  if ("south_exit" in properties(old_plaza))',
        '    old_fact = old_plaza.south_exit;',
        '    if (valid(old_fact)) recycle(old_fact); endif',
        '  endif',
        '  recycle(old_plaza);',
        '  player.w_colony = $nothing;',
        '  "remove any portal buildings";',
        '  for itm in (player.location.contents)',
        '    if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
        '      recycle(itm);',
        '    endif',
        '  endfor',
        '  player:tell("  Cleared old sector center.");',
        'endif',
        '"Give materials";',
        'm1 = create($thing); m1.name = "inert metal"; move(m1, player);',
        'm2 = create($thing); m2.name = "inert metal"; move(m2, player);',
        'w1 = create($thing); w1.name = "crude wire"; move(w1, player);',
        'w2 = create($thing); w2.name = "crude wire"; move(w2, player);',
        '"Craft sector center kit";',
        'this:craft("sector", "center");',
        'kit_found = 0;',
        'for itm in (player.contents)',
        '  if (index(itm.name, "sector center"))',
        '    kit_found = 1;',
        '    player:tell("  Kit in inv: " + itm.name);',
        '  endif',
        'endfor',
        'if (kit_found == 0)',
        '  player:tell("  ERROR: sector center kit not crafted!");',
        '  return;',
        'endif',
        '"Place it";',
        'this:place("sector", "center");',
        'player:tell("  Current location: " + player.location.name);',
        'player:tell("  w_colony: " + tostr(player.w_colony));',
        '"Test east (governor\'s office)";',
        'this:e();',
        'player:tell("  Gov office: " + player.location.name);',
        'this:w();',
        '"Test south (factorium)";',
        'this:s();',
        'player:tell("  Factorium: " + player.location.name);',
        '"Test labor";',
        'player.w_credits = 0;',
        'this:labor();',
        'player:tell("  After labor: " + tostr(player.w_credits) + " cr (expect 10)");',
        '"Test out";',
        'this:n();',
        'this:out();',
        'player:tell("  After out: " + player.location.name);',
        '"Test colony teleport";',
        'this:colony();',
        'player:tell("  After colony: " + player.location.name);',
        '"Test enter";',
        'this:out();',
        'this:enter("sector center");',
        'player:tell("  After enter: " + player.location.name);',
        '"Cleanup";',
        'old_plaza2 = player.w_colony;',
        'this:out();',
        'if (valid(old_plaza2))',
        '  old_gov2 = old_plaza2.east_exit;',
        '  old_fact2 = old_plaza2.south_exit;',
        '  if (valid(old_gov2)) recycle(old_gov2); endif',
        '  if (valid(old_fact2)) recycle(old_fact2); endif',
        '  recycle(old_plaza2);',
        '  player.w_colony = $nothing;',
        'endif',
        'for itm in (player.location.contents)',
        '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
        '    recycle(itm);',
        '  endif',
        'endfor',
        'player:tell("=== COLONY_TEST END ===");',
    ])

    out = send(s, 'colony_test', wait=15.0)
    print(out.strip())

    # ── 10. Save ──────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
