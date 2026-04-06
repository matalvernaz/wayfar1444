#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 5: Building System

Adds:
  1. $building prototype — placed structures that persist in a room
  2. pre-fab shelter kit recipe in the craft verb (1x inert metal + 2x fiber)
  3. 'place <kit>' verb on $player — deploy a kit at current coordinates
  4. 'buildings' verb on $player — list structures in current room

Craft chain:
  gather ore x2 → craft inert metal
  gather fiber x2 + inert metal → craft pre-fab shelter kit
  (in wilderness room) place shelter → pre-fab shelter appears in room

Run with server live: python3 phase5_buildings.py
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')

HOST = 'localhost'
PORT = 7777
PLAYER = 6
BCT_NUM = 592   # $basic_craft_tool


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
# CRAFT verb — extended with pre-fab shelter kit recipe
# ─────────────────────────────────────────────────────────────────────────────

CRAFT_RECIPE_PREFAB = [
    # === PRE-FAB SHELTER KIT ===
    'if (index(tgt, "shelter") || index(tgt, "prefab") || index(tgt, "pre-fab") || index(tgt, "pre") || index(tgt, "kit"))',
    '  found_m = {}; found_f = {};',
    '  for itm in (p.contents)',
    '    n = itm.name;',
    '    if (length(found_m) == 0 && (index(n, "inert metal") || index(n, "metal ingot")))',
    '      found_m = listappend(found_m, itm);',
    '    endif',
    '    if (length(found_f) < 2 && (index(n, "fiber") || index(n, "plant")))',
    '      found_f = listappend(found_f, itm);',
    '    endif',
    '  endfor',
    '  if (length(found_m) == 0)',
    '    p:tell("Need 1x inert metal. (craft inert metal from 2x ore first)");',
    '    return;',
    '  endif',
    '  if (length(found_f) < 2)',
    '    p:tell("Need 2x fiber. Have: " + tostr(length(found_f)));',
    '    return;',
    '  endif',
    '  recycle(found_m[1]); recycle(found_f[1]); recycle(found_f[2]);',
    '  r = create($thing);',
    '  r.name = "pre-fab shelter kit";',
    '  r.description = "A collapsed alloy-frame shelter with fiber insulation panels. Type \'place shelter\' to deploy it.";',
    '  move(r, p);',
    '  p:tell("You assemble the metal frame and fiber panels into a pre-fab shelter kit. [+shelter kit]");',
    '  return;',
    'endif',
]

# Full craft verb: tool check + all recipes
CRAFT_FULL = [
    '"Craft items using a basic crafting tool from inventory.";',
    'p = player;',
    'tool = 0;',
    f'for itm in (player.contents)',
    f'  if (is_a(itm, #{BCT_NUM}))',
    '    tool = itm;',
    '    break;',
    '  endif',
    'endfor',
    'if (tool == 0)',
    '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
    '  return;',
    'endif',
    '"--- build target string from args ---";',
    'tgt = "";',
    'for w in (args)',
    '  tgt = (tgt == "") ? w | (tgt + " " + w);',
    'endfor',
    'if (typeof(dobjstr) == STR && dobjstr != "")',
    '  tgt = dobjstr;',
    'endif',
    '"--- show recipes ---";',
    'if (tgt == "" || tgt == "list" || tgt == "help")',
    '  p:tell("=== BASIC CRAFTING TOOL — RECIPES ===");',
    '  p:tell("  ration bar        — 2x fiber");',
    '  p:tell("  water canteen     — 1x fiber + 1x raw water");',
    '  p:tell("  inert metal       — 2x ore/mineral");',
    '  p:tell("  crude wire        — 1x ore + 1x salvage");',
    '  p:tell("  pre-fab shelter kit — 1x inert metal + 2x fiber");',
    '  p:tell("Usage: craft <recipe name>");',
    '  return;',
    'endif',

    # === RATION BAR ===
    'if (index(tgt, "ration") || index(tgt, "food") || index(tgt, "bar"))',
    '  found = {};',
    '  for itm in (p.contents)',
    '    if (length(found) < 2)',
    '      n = itm.name;',
    '      if (index(n, "fiber") || index(n, "plant"))',
    '        found = listappend(found, itm);',
    '      endif',
    '    endif',
    '  endfor',
    '  if (length(found) < 2)',
    '    p:tell("Need 2x fiber/plant material. Have: " + tostr(length(found)));',
    '    return;',
    '  endif',
    '  recycle(found[1]); recycle(found[2]);',
    '  r = create($thing);',
    '  r.name = "ration bar";',
    '  r.description = "A compressed brick of processed plant fiber. Tastes like cardboard. Calories are calories.";',
    '  move(r, p);',
    '  p:tell("You press the fibers into a dense ration bar. [+food item]");',
    '  p.location:announce(p.name + " uses a crafting tool.", p);',
    '  return;',
    'endif',

    # === WATER CANTEEN ===
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
    '    p:tell("Need 1x fiber (to make the canteen body).");',
    '    return;',
    '  endif',
    '  if (length(found_w) == 0)',
    '    p:tell("Need 1x water sample (raw water, water sample).");',
    '    return;',
    '  endif',
    '  recycle(found_f[1]); recycle(found_w[1]);',
    '  r = create($thing);',
    '  r.name = "water canteen";',
    '  r.description = "A rough fiber-bound canteen containing filtered drinking water.";',
    '  move(r, p);',
    '  p:tell("You weave fiber around the water sample into a sealed canteen. [+drink item]");',
    '  return;',
    'endif',

    # === INERT METAL ===
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
    '  r = create($thing);',
    '  r.name = "inert metal";',
    '  r.description = "Smelted alien ore, shaped into a rough ingot. Foundation of all construction.";',
    '  move(r, p);',
    '  p:tell("You smelt the ore samples into an inert metal ingot. [+inert metal]");',
    '  return;',
    'endif',

    # === CRUDE WIRE ===
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
    '  r = create($thing);',
    '  r.name = "crude wire";',
    '  r.description = "Rough conductive wire pulled from salvage and refined ore. Used in basic electronics.";',
    '  move(r, p);',
    '  p:tell("You draw ore through salvage frames into crude wire. [+crude wire]");',
    '  return;',
    'endif',

] + CRAFT_RECIPE_PREFAB + [
    'p:tell("Unknown recipe: \'" + tgt + "\'");',
    'p:tell("Type \'craft\' to see available recipes.");',
]


# ─────────────────────────────────────────────────────────────────────────────
# PLACE verb — deploy a building kit at current location
# ─────────────────────────────────────────────────────────────────────────────

PLACE_VERB = [
    '"Deploy a building kit at current coordinates.";',
    '"Usage: place <kit name> (e.g. place shelter)";',
    'p = player;',
    '"Build query from dobjstr or args";',
    'query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (query == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      query = query == "" ? w | query + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (query == "")',
    '  p:tell("Place what? (e.g. place shelter)");',
    '  p:tell("Type \'i\' to see your inventory.");',
    '  return;',
    'endif',
    '"Find a kit matching query";',
    'kit = 0;',
    'for itm in (p.contents)',
    '  nm = "";',
    '  try',
    '    nm = tostr(itm.name);',
    '  except e (ANY)',
    '    nm = "";',
    '  endtry',
    '  if (index(nm, query) && index(nm, "kit"))',
    '    kit = itm;',
    '    break;',
    '  endif',
    'endfor',
    'if (kit == 0)',
    '  p:tell("You\'re not carrying a \'" + query + "\' kit.");',
    '  return;',
    'endif',
    'loc = p.location;',
    'if (!valid(loc))',
    '  p:tell("You can\'t place buildings here.");',
    '  return;',
    'endif',
    '"Derive building name: strip trailing \' kit\' using strsub";',
    'kn = kit.name;',
    'bname = strsub(kn, " kit", "");',
    '"Create building object as child of $building";',
    'b = create($building);',
    'b.name = bname;',
    'b.description = kit.description;',
    'b.b_owner = p;',
    'b.b_type = bname;',
    'b.b_hp = 100;',
    'b.b_hp_max = 100;',
    '"Store coords if room has them";',
    'b.b_x = (("x" in properties(loc)) ? loc.x | 0);',
    'b.b_y = (("y" in properties(loc)) ? loc.y | 0);',
    'move(b, loc);',
    'recycle(kit);',
    'p:tell("You unfold and anchor the " + bname + " to the ground. [building placed]");',
    'loc:announce(p.name + " constructs a " + bname + " here.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# BUILDINGS verb — list structures in current room
# ─────────────────────────────────────────────────────────────────────────────

BUILDINGS_VERB = [
    '"List all buildings placed in the current room.";',
    'p = player;',
    'loc = p.location;',
    'found = {};',
    'for itm in (loc.contents)',
    '  if (is_a(itm, $building))',
    '    found = listappend(found, itm);',
    '  endif',
    'endfor',
    'if (found == {})',
    '  p:tell("No structures have been built here.");',
    '  return;',
    'endif',
    'p:tell("=== STRUCTURES AT THIS LOCATION ===");',
    'for b in (found)',
    '  owner = valid(b.b_owner) ? b.b_owner.name | "unknown";',
    '  hpstr = tostr(b.b_hp) + "/" + tostr(b.b_hp_max);',
    '  p:tell("  [" + b.b_type + "]  HP: " + hpstr + "  Owner: " + owner);',
    'endfor',
]


# ─────────────────────────────────────────────────────────────────────────────
# $building look_self
# ─────────────────────────────────────────────────────────────────────────────

BUILDING_LOOK = [
    '"Show building details when examined.";',
    'p = player;',
    'owner = valid(this.b_owner) ? this.b_owner.name | "unknown";',
    'hpstr = tostr(this.b_hp) + "/" + tostr(this.b_hp_max);',
    'p:tell("--- " + this.name + " ---");',
    'p:tell("Type: " + this.b_type + "   HP: " + hpstr + "   Owner: " + owner);',
    'if (this.description != "")',
    '  p:tell(this.description);',
    'endif',
    'coords = "(" + tostr(this.b_x) + ", " + tostr(this.b_y) + ")";',
    'p:tell("Coordinates: " + coords);',
]


def main():
    s = connect()

    # ── 1. Create $building prototype ─────────────────────────────────────────
    print('=== Create $building prototype ===')
    out = ev(s, 'player:tell(tostr($building))', wait=0.6)
    m = re.search(r'#(\d+)', out)
    bld_num = None
    if m:
        cand = int(m.group(1))
        ok = ev(s, f'player:tell(valid(#{cand}) ? "yes" | "no")', wait=0.5)
        if 'yes' in ok:
            is_player = ev(s, f'player:tell(is_a(#{cand}, $player) ? "yes" | "no")', wait=0.5)
            if 'yes' not in is_player:
                bld_num = cand
                print(f'  $building already exists as #{bld_num}')

    if bld_num is None:
        out = ev(s,
            'b = create($thing); '
            'b.name = "building"; '
            'b.b_type = "unknown"; '
            'b.b_owner = 0; '
            'b.b_hp = 100; '
            'b.b_hp_max = 100; '
            'b.b_x = 0; '
            'b.b_y = 0; '
            'player:tell(tostr(b));',
            wait=1.0)
        m = re.search(r'#(\d+)', out)
        if not m:
            print(f'  ERROR creating $building: {out.strip()[:200]}')
            s.close()
            return
        bld_num = int(m.group(1))
        print(f'  Created $building as #{bld_num}')
        ev(s, f'$building = #{bld_num}', wait=0.5)
        out2 = ev(s, 'player:tell(tostr($building))', wait=0.5)
        print(f'  $building = {out2.strip()[-20:]}')

    # Add look_self verb to $building
    add_verb(s, f'#{bld_num}', '"look_self"', 'none none none')
    program_verb(s, f'#{bld_num}', 'look_self', BUILDING_LOOK)

    # ── 2. Update craft verb on $player (#6) ──────────────────────────────────
    print(f'\n=== Update craft verb on #{PLAYER} ===')
    program_verb(s, f'#{PLAYER}', 'craft', CRAFT_FULL)

    # ── 3. Add place verb ──────────────────────────────────────────────────────
    print(f'\n=== Add place verb on #{PLAYER} ===')
    add_verb(s, f'#{PLAYER}', '"place"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'place', PLACE_VERB)

    # ── 4. Add buildings verb ─────────────────────────────────────────────────
    print(f'\n=== Add buildings verb on #{PLAYER} ===')
    add_verb(s, f'#{PLAYER}', '"buildings"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'buildings', BUILDINGS_VERB)

    # ── 5. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test: building system ===')

    # Update wf_test to include building test
    program_verb(s, f'#{PLAYER}', 'wf_test', [
        '"Full craft/eat/drink/build test.";',
        'player:tell("=== WF_TEST BEGIN ===");',
        'player.w_hp = 50; player.w_hp_max = 100;',
        '"clean up test items (keep BCT)";',
        'for itm in (player.contents)',
        f'  if (!is_a(itm, #{BCT_NUM}))',
        '    recycle(itm);',
        '  endif',
        'endfor',
        '"ensure one BCT";',
        f'bct_found = 0;',
        'for itm in (player.contents)',
        f'  if (is_a(itm, #{BCT_NUM}))',
        '    bct_found = 1;',
        '  endif',
        'endfor',
        'if (bct_found == 0)',
        f'  t = create(#{BCT_NUM}); move(t, player);',
        '  player:tell("  Gave basic crafting tool.");',
        'endif',
        '"--- craft ration bar ---";',
        'f1 = create($thing); f1.name = "native fiber"; move(f1, player);',
        'f2 = create($thing); f2.name = "native fiber"; move(f2, player);',
        'this:craft("ration", "bar");',
        'this:eat("ration bar");',
        'player:tell("  eat: w_hp=" + tostr(player.w_hp) + " (expect 55)");',
        '"--- craft water canteen ---";',
        'f3 = create($thing); f3.name = "native fiber"; move(f3, player);',
        'w1 = create($thing); w1.name = "raw water sample"; move(w1, player);',
        'this:craft("water", "canteen");',
        'this:drink("canteen");',
        'player:tell("  drink: w_hp=" + tostr(player.w_hp) + " (expect 58+)");',
        '"--- craft pre-fab shelter kit ---";',
        'o1 = create($thing); o1.name = "ore chunk"; move(o1, player);',
        'o2 = create($thing); o2.name = "ore chunk"; move(o2, player);',
        'f4 = create($thing); f4.name = "native fiber"; move(f4, player);',
        'f5 = create($thing); f5.name = "native fiber"; move(f5, player);',
        'this:craft("inert", "metal");',
        'player:tell("  after craft inert metal: inv=" + tostr(length(player.contents)));',
        'this:craft("pre-fab", "shelter");',
        'kit_found = 0;',
        'for itm in (player.contents)',
        '  if (index(itm.name, "shelter"))',
        '    kit_found = 1;',
        '    player:tell("  shelter kit in inv: " + itm.name);',
        '  endif',
        'endfor',
        'if (kit_found == 0)',
        '  player:tell("  ERROR: shelter kit not found in inventory!");',
        'endif',
        '"--- place shelter ---";',
        'this:place("shelter");',
        '"--- list buildings ---";',
        'this:buildings();',
        '"--- cleanup buildings placed by test ---";',
        'for itm in (player.location.contents)',
        f'  if (is_a(itm, $building))',
        '    recycle(itm);',
        '  endif',
        'endfor',
        'player:tell("=== WF_TEST END ===");',
    ])

    out = send(s, 'wf_test', wait=8.0)
    print(f'wf_test:\n{out.strip()}')

    # ── 6. Save ───────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
