#!/usr/bin/env python3
"""Reprogram craft verb with sector center recipe, then run colony_test."""
import socket, time, re, sys

HOST = 'localhost'; PORT = 7777
PLAYER = 6
BCT_NUM = 592

def connect():
    s = socket.socket(); s.connect((HOST, PORT)); s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n'); time.sleep(0.8); s.recv(65536)
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

def ev(s, e, wait=0.7): return send(s, '; ' + e, wait)

def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR @program: {repr(out[:150])}'); return False
    old_to = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 15 == 14: print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old_to)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR:\n{result[:600]}'); return False
    print(f'  OK: {obj_expr}:{verbname}'); return True

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

def main():
    s = connect()

    print('=== Reprogram craft verb ===')
    ok = program_verb(s, f'#{PLAYER}', 'craft', craft_full)
    if not ok:
        s.close(); return

    print('\n=== Run colony_test ===')
    out = send(s, 'colony_test', wait=20.0)
    print(out.strip())

    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('Done.')

if __name__ == '__main__':
    main()
