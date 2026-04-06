#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 4: Crafting Tool + DRINK verb + consumables

Adds:
  1. DRINK verb on $player (#6) — alias to eat
  2. $basic_craft_tool prototype — carry it, type 'craft' to see recipes
  3. 'craft' verb on $basic_craft_tool:
       2x native fiber/plant fiber  → ration bar
       1x native fiber + any water  → water canteen
       2x ore/mineral               → inert metal
  4. Give starting players the basic crafting tool on spawn
  5. Test run: give wizard a tool + fibers, craft a ration bar, eat it

Run: python3 phase4_craft.py
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777
PLAYER = 6    # $player


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(4)
    time.sleep(0.5)
    s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8)
    s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.35)  # don't read longer than wait+1s
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.65):
    return send(s, f'; {expr}', wait=wait)


def program_verb(s, obj_expr, verbname, code_lines, obj_label=None):
    label = obj_label or obj_expr
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
        print(f'  CODE ERROR {label}:{verbname}:')
        print(result[:600])
        return False
    print(f'  OK: {label}:{verbname}')
    return True


def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}')
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CRAFT verb code for $basic_craft_tool
# ─────────────────────────────────────────────────────────────────────────────

CRAFT_CODE = [
    '"Basic Crafting Tool: process raw materials into useful items.";',
    '"Usage: craft [recipe name] | craft (shows recipes)";',
    'p = player;',
    # collect args into a target string
    'tgt = "";',
    'for w in (args)',
    '  tgt = (tgt == "") ? w | (tgt + " " + w);',
    'endfor',

    # --- show recipes ---
    'if (tgt == "" || tgt == "list" || tgt == "help")',
    '  p:tell("=== BASIC CRAFTING TOOL — RECIPES ===");',
    '  p:tell("  ration bar     — 2x fiber");',
    '  p:tell("  water canteen  — 1x fiber + 1x raw water");',
    '  p:tell("  inert metal    — 2x ore/mineral");',
    '  p:tell("  crude wire     — 1x ore + 1x salvage");',
    '  p:tell("Usage: craft <recipe>");',
    '  return;',
    'endif',

    # --- helper: find items in inventory matching keyword ---
    # We inline the search for each recipe below

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

    'p:tell("Unknown recipe: \'" + tgt + "\'");',
    'p:tell("Type \'craft\' to see available recipes.");',
]


def main():
    s = connect()

    # ─── 1. DRINK verb on $player ────────────────────────────────────────────
    print('\n=== DRINK verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"drink"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'drink', [
        '"Alias for eat — consume a liquid from inventory.";',
        'this:eat(args);',
    ], obj_label='$player')

    # ─── 2. Create $basic_craft_tool prototype ───────────────────────────────
    print('\n=== $basic_craft_tool prototype ===')

    # Check if it already exists as a proper $thing (not a player/room)
    out = ev(s, 'player:tell(tostr($basic_craft_tool))', wait=0.6)
    m = re.search(r'#(\d+)', out)
    bct_num = None
    if m:
        cand = int(m.group(1))
        # Validate: must be valid, not a player, not a room, parent must be $thing
        ok = ev(s, f'player:tell(valid(#{cand}) ? "yes" | "no")', wait=0.5)
        if 'yes' in ok:
            # Check it's a $thing child, not $player
            is_player = ev(s, f'player:tell(is_a(#{cand}, $player) ? "yes" | "no")', wait=0.5)
            if 'yes' not in is_player:
                bct_num = cand
                print(f'  $basic_craft_tool already exists as #{bct_num}')
            else:
                print(f'  WARNING: $basic_craft_tool points to #{cand} which is a player — will recreate')
                ev(s, f'$basic_craft_tool = $nothing', wait=0.5)

    if bct_num is None:
        # Create as child of $thing
        out = ev(s, 'bct = create($thing); player:tell(tostr(bct)); bct.name = "basic crafting tool"; bct.description = "A portable fabrication unit — press, compress, smelt. Produces simple goods from raw materials. Type \'craft\' to see recipes.";', wait=1.0)
        m = re.search(r'#(\d+)', out)
        if m:
            bct_num = int(m.group(1))
            print(f'  Created $basic_craft_tool as #{bct_num}')
            # Register as $basic_craft_tool
            ev(s, f'$basic_craft_tool = #{bct_num}', wait=0.5)
            # Confirm
            out2 = ev(s, 'player:tell(tostr($basic_craft_tool))', wait=0.5)
            print(f'  $basic_craft_tool = {out2.strip()[-20:]}')
        else:
            print(f'  ERROR creating bct: {out.strip()[:200]}')
            s.close()
            return

    bct = f'#{bct_num}'
    # Store bct_num in a MOO var so CRAFT verb on player can reference it
    # The craft verb on $player will check for $basic_craft_tool in inventory

    # ─── 3. Add CRAFT verb to $player ────────────────────────────────────────
    # Craft verb lives on $player; requires $basic_craft_tool in inventory
    print(f'\n=== craft verb on $player (requires {bct} in inventory) ===')
    add_verb(s, f'#{PLAYER}', 'craft', 'any none none')
    # Prepend tool check to CRAFT_CODE
    craft_with_tool_check = [
        '"Craft items using a basic crafting tool from inventory.";',
        'tool = 0;',
        'for itm in (player.contents)',
        f'  if (is_a(itm, #{bct_num}))',
        '    tool = itm; break;',
        '  endif',
        'endfor',
        'if (!tool)',
        '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
        '  return;',
        'endif',
    ] + CRAFT_CODE
    program_verb(s, f'#{PLAYER}', 'craft', craft_with_tool_check, obj_label='$player')

    # ─── 4. Make wizard-player own a basic crafting tool ─────────────────────
    print('\n=== Equip wizard with basic crafting tool ===')
    out = ev(s, f'has_bct = 0; for itm in (player.contents); if (is_a(itm, #{bct_num})); has_bct = 1; break; endif; endfor; player:tell(tostr(has_bct))', wait=0.8)
    if '1' in out.split('=>')[-1][:10]:
        print('  Wizard already has a basic crafting tool.')
    else:
        out = ev(s, f'new_bct = create(#{bct_num}); move(new_bct, player)', wait=0.7)
        print(f'  Created and moved basic crafting tool to wizard')

    # Also verify/fix eat verb (check verb_info)
    print('\n=== Checking eat verb ===')
    vi = ev(s, 'player:tell(tostr(verb_info(#6, "eat")))', wait=0.6)
    print(f'  eat verb_info: {vi.strip()[-60:]}')

    # ─── 5. End-to-end test ──────────────────────────────────────────────────
    print('\n=== End-to-end test: craft ration bar + eat it ===')
    ev(s, '#361.w_hp = 50; #361.w_hp_max = 100')
    ev(s, 'f1 = create($thing); f1.name = "native fiber"; move(f1, player)')
    ev(s, 'f2 = create($thing); f2.name = "native fiber"; move(f2, player)')
    print('  Created 2x native fiber in wizard inventory')

    out = send(s, 'craft ration bar', wait=1.2)
    print(f'  craft ration bar => {out.strip()[-120:]}')

    out = send(s, 'eat ration', wait=1.2)
    print(f'  eat ration => {out.strip()[-200:]}')

    hp = ev(s, '#361.w_hp').strip()[-20:]
    nour = ev(s, '#361.w_nourished').strip()[-30:]
    print(f'  w_hp: {hp} (expect 55)')
    print(f'  w_nourished set: {"yes" if "=>" in nour else "no"} [{nour}]')

    print('\n--- drink test ---')
    ev(s, 'f3 = create($thing); f3.name = "native fiber"; move(f3, player)')
    ev(s, 'w1 = create($thing); w1.name = "raw water sample"; move(w1, player)')
    out = send(s, 'craft water canteen', wait=1.2)
    print(f'  craft water canteen => {out.strip()[-120:]}')
    out = send(s, 'drink canteen', wait=1.2)
    print(f'  drink canteen => {out.strip()[-120:]}')

    # ─── 6. Save DB ──────────────────────────────────────────────────────────
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=3.0)
    print(out.strip()[:80])

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
