#!/usr/bin/env python3
"""
Fix eat verb to work programmatically (when called via drink or wf_test).
Also fix #592 (basic_craft_tool) name property.
"""

import socket, time, re, sys
sys.path.insert(0, '/home/matt/wayfar')

HOST = 'localhost'
PORT = 7777
PLAYER = 6


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


def program_verb(s, obj_num, verbname, code_lines):
    out = send(s, f'@program #{obj_num}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program: {repr(out[:150])}')
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
        print(f'  CODE ERROR: {result[:400]}')
        return False
    print(f'  OK: #{obj_num}:{verbname}')
    return True


EAT_VERB = [
    '"Eat food. Grants Nourished effect (+HP, better dice regen).";',
    '"Works via command (eat <item>) or programmatic call (this:eat(args)).";',
    '"--- find the item ---";',
    'found = 0;',
    'if (valid(dobj) && dobj.location == player)',
    '  found = dobj;',
    'else',
    '  "Search by string from dobjstr or args";',
    '  "dobjstr may be 0 in programmatic calls; build query from dobjstr or args";',
    '  query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    '  if (query == "" && args != {})',
    '    for w in (args)',
    '      if (typeof(w) == STR)',
    '        query = query == "" ? w | query + " " + w;',
    '      endif',
    '    endfor',
    '  endif',
    '  if (query == "")',
    '    player:tell("Eat what? (Type i to see inventory)");',
    '    return;',
    '  endif',
    '  for itm in (player.contents)',
    '    nm = "";',
    '    try',
    '      nm = tostr(itm.name);',
    '    except e (ANY)',
    '      nm = "";',
    '    endtry',
    '    if (index(nm, query))',
    '      found = itm;',
    '      break;',
    '    endif',
    '  endfor',
    'endif',
    'if (found == 0)',
    '  player:tell("You are not carrying a \'" + (query != "" ? query | (args != {} ? args[1] | "?")) + "\'.");',
    '  return;',
    'endif',
    '"--- check edibility ---";',
    'fname = "";',
    'try',
    '  fname = tostr(found.name);',
    'except e (ANY)',
    '  fname = "";',
    'endtry',
    'edible = 0;',
    'for kw in ({"berry", "berries", "fungus", "tuber", "soup", "ration", "food", "snack", "fruit", "meat", "pie", "paste", "donut", "slush", "vita", "canteen", "water"})',
    '  if (index(fname, kw))',
    '    edible = 1;',
    '    break;',
    '  endif',
    'endfor',
    'if (!edible && "is_food" in properties(found))',
    '  edible = found.is_food;',
    'endif',
    'if (!edible)',
    '  player:tell("That doesn\'t look edible.");',
    '  return;',
    'endif',
    '"--- apply effects ---";',
    'player.w_nourished = time() + 600;',
    'heal = 5;',
    'if (index(fname, "canteen") || index(fname, "water"))',
    '  heal = 3;',
    'endif',
    'player.w_hp = min(player.w_hp + heal, player.w_hp_max);',
    'recycle(found);',
    'player:tell("You consume the " + fname + ". [+" + tostr(heal) + " HP | Nourished for 10 min]");',
    'player.location:announce(player.name + " eats.", player);',
]


def main():
    s = connect()

    # Fix #592 name
    print('=== Fix #592 (basic_craft_tool) name ===')
    out = ev(s, 'player:tell(valid(#592) ? "valid" | "invalid")')
    print(f'#592 valid: {out.strip()[-40:]}')
    out = ev(s, '#592.name = "basic crafting tool"; #592.description = "A portable fabrication unit. Type craft to see recipes."')
    print(f'set name: {out.strip()[-40:]}')
    out = ev(s, 'player:tell(#592.name)')
    print(f'#592.name: {out.strip()[-50:]}')

    # Update eat verb
    print('\n=== Update eat verb on $player ===')
    program_verb(s, PLAYER, 'eat', EAT_VERB)

    # Update drink verb to use proper args
    print('\n=== Update drink verb ===')
    program_verb(s, PLAYER, 'drink', [
        '"Alias for eat — consume a liquid.";',
        'this:eat(@args);',
    ])

    # Update wf_test with fixed eat/drink test
    print('\n=== Update wf_test ===')
    program_verb(s, PLAYER, 'wf_test', [
        '"Full craft/eat/drink test.";',
        'player:tell("=== WF_TEST BEGIN ===");',
        'player.w_hp = 50; player.w_hp_max = 100;',
        '"--- clean up leftover test items ---";',
        'keep = {};',
        'for itm in (player.contents)',
        '  if (is_a(itm, $basic_craft_tool))',
        '    keep = {@keep, itm};',
        '  else',
        '    recycle(itm);',
        '  endif',
        'endfor',
        '"--- ensure one BCT ---";',
        'if (keep == {})',
        '  t = create($basic_craft_tool); move(t, player);',
        '  player:tell("  Gave basic crafting tool.");',
        'endif',
        '"--- give 2 fibers ---";',
        'f1 = create($thing); f1.name = "native fiber"; move(f1, player);',
        'f2 = create($thing); f2.name = "native fiber"; move(f2, player);',
        'cnt = length(player.contents);',
        'player:tell("  Inventory: " + tostr(cnt) + " items");',
        'for x in (player.contents)',
        '  player:tell("    - " + tostr(x.name));',
        'endfor',
        'player:tell("--- craft ration bar ---");',
        'this:craft("ration", "bar");',
        'cnt2 = length(player.contents);',
        'player:tell("  After craft: " + tostr(cnt2) + " items");',
        'for x in (player.contents)',
        '  player:tell("    - " + tostr(x.name));',
        'endfor',
        'player:tell("--- eat ration bar ---");',
        'this:eat("ration bar");',
        'player:tell("  w_hp: " + tostr(player.w_hp) + " (expect 55)");',
        'player:tell("  nourished: " + tostr(player.w_nourished > time()) + " (expect 1)");',
        '"--- drink canteen test ---";',
        'f3 = create($thing);',
        'f3.name = "native fiber";',
        'move(f3, player);',
        'w1 = create($thing);',
        'w1.name = "raw water sample";',
        'move(w1, player);',
        'player:tell("  Pre-craft inv: " + tostr(length(player.contents)));',
        'for x in (player.contents)',
        '  player:tell("    - " + tostr(x.name));',
        'endfor',
        'this:craft("water", "canteen");',
        'this:drink("canteen");',
        'player:tell("  drink canteen hp: " + tostr(player.w_hp) + " (expect 58+)");',
        'player:tell("=== WF_TEST END ===");',
    ])

    # Add eat_debug verb to trace what eat sees
    print('\n=== Add eat_debug verb ===')
    out = send(s, '@verb #6:eat_debug none none none', wait=0.6)
    program_verb(s, PLAYER, 'eat_debug', [
        '"Debug: create ration bar, then trace eat lookup.";',
        'rb = create($thing); rb.name = "ration bar"; move(rb, player);',
        'player:tell("  rb in inv: " + tostr(rb in player.contents));',
        'player:tell("  rb.name: " + tostr(rb.name));',
        'player:tell("  typeof(rb.name): " + tostr(typeof(rb.name)));',
        'nm = "";',
        'try',
        '  nm = tostr(rb.name);',
        'except e (ANY)',
        '  nm = "EXCEPTION";',
        'endtry',
        'player:tell("  nm: " + nm);',
        'player:tell("  index result: " + tostr(index(nm, "ration bar")));',
        'player:tell("  direct match: " + tostr(nm == "ration bar"));',
        '"check dobjstr type in programmatic call";',
        'player:tell("  dobjstr type: " + tostr(typeof(dobjstr)));',
        'player:tell("  dobjstr val: " + tostr(dobjstr));',
        'player:tell("  args: " + tostr(args));',
        'recycle(rb);',
    ])
    out = send(s, 'eat_debug', wait=2.0)
    print(f'eat_debug:\n{out.strip()[-400:]}')

    # Run wf_test
    print('\n=== Run wf_test ===')
    out = send(s, 'wf_test', wait=4.0)
    print(f'wf_test:\n{out.strip()}')

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
