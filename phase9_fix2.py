#!/usr/bin/env python3
"""Fix enter verb (prefer player-owned portal) + rerun colony_test."""
import socket, time, re

HOST = 'localhost'; PORT = 7777
PLAYER = 6

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
        print(f'  ERROR: {repr(out[:150])}'); return False
    old = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 15 == 14: print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR:\n{result[:400]}'); return False
    print(f'  OK: {obj_expr}:{verbname}'); return True

# Fixed enter verb: prefer valid portal owned by player
ENTER_VERB_FIXED = [
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

# Fixed colony_test: always clean portals at start
COLONY_TEST_FIXED = [
    '"Test sector center craft + placement.";',
    'player:tell("=== COLONY_TEST BEGIN ===");',
    '"Always clean up portals and stale colony at start";',
    'for itm in (player.location.contents)',
    '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
    '    player:tell("  Removing stale portal: " + itm.name);',
    '    recycle(itm);',
    '  endif',
    'endfor',
    'if (valid(player.w_colony))',
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
    '  player:tell("  Cleared old colony.");',
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
    'player:tell("  w_colony now: " + tostr(player.w_colony) + " valid=" + tostr(valid(player.w_colony)));',
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
]

COLONY_VERB_FIXED = [
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

def main():
    s = connect()

    print('=== Fix colony verb ===')
    program_verb(s, f'#{PLAYER}', 'colony', COLONY_VERB_FIXED)

    print('\n=== Fix enter verb ===')
    program_verb(s, f'#{PLAYER}', 'enter', ENTER_VERB_FIXED)

    print('\n=== Fix colony_test verb ===')
    program_verb(s, f'#{PLAYER}', 'colony_test', COLONY_TEST_FIXED)

    print('\n=== Run colony_test ===')
    out = send(s, 'colony_test', wait=20.0)
    print(out.strip())

    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('Done.')

if __name__ == '__main__':
    main()
