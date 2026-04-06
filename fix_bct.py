#!/usr/bin/env python3
"""
Fix $basic_craft_tool:
1. Add basic_craft_tool property to #0 if missing
2. Create craft tool prototype properly
3. Update craft verb to hardcode the number (no $alias needed)
4. Test move() from verb context
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


def main():
    s = connect()

    # 1. Check if #592 is a valid craft tool
    print('=== Check #592 ===')
    out = ev(s, 'player:tell(valid(#592) ? (#592.name) | "invalid")')
    print(f'#592: {out.strip()[-60:]}')
    out = ev(s, 'player:tell(is_a(#592, $player) ? "is player" | "not player")')
    print(f'#592 is player: {out.strip()[-50:]}')

    # 2. Add basic_craft_tool property to #0
    print('\n=== Add $basic_craft_tool property to #0 ===')
    # Check if property exists
    out = ev(s, 'player:tell("basic_craft_tool" in properties(#0) ? "exists" | "missing")')
    print(f'property check: {out.strip()[-50:]}')

    # Add it if missing (use @addprop or add_property)
    out = send(s, '@addprop #0.basic_craft_tool #0', wait=1.0)
    print(f'@addprop: {out.strip()[-80:]}')

    # Now set it
    out = ev(s, 'add_property(#0, "basic_craft_tool", #592, {#0.owner, "r"})')
    print(f'add_property: {out.strip()[-80:]}')

    # Check value
    out = ev(s, 'player:tell(tostr($basic_craft_tool))')
    print(f'$basic_craft_tool: {out.strip()[-60:]}')

    # 3. Test move from within a verb
    print('\n=== Test move() from verb context ===')
    out = send(s, '@verb #6:move_test none none none', wait=0.6)
    program_verb(s, PLAYER, 'move_test', [
        '"Test if move works from verb context.";',
        'a = create($thing);',
        'a.name = "move test item";',
        'move(a, player);',
        'player:tell("item location: " + tostr(a.location));',
        'player:tell("player.contents: " + tostr(length(player.contents)));',
        'if (a.location == player)',
        '  player:tell("SUCCESS: move worked!");',
        'else',
        '  player:tell("FAIL: item not in inventory. loc=" + tostr(a.location));',
        'endif',
        '"clean up";',
        'recycle(a);',
    ])

    out = send(s, 'move_test', wait=2.0)
    print(f'move_test:\n{out.strip()[-200:]}')

    # 4. If move works, run full wf_test with correct bct
    # Check if move worked from output
    if 'SUCCESS' in out:
        print('\nmove() works from verb context!')
        bct_num = 592

        from phase4_craft import CRAFT_CODE

        print(f'\n=== Update craft verb on $player (bct #{bct_num}) ===')
        craft_with_tool_check = [
            '"Craft items using a basic crafting tool from inventory.";',
            'tool = 0;',
            'for itm in (player.contents)',
            f'  if (is_a(itm, #{bct_num}))',
            '    tool = itm; break;',
            '  endif',
            'endfor',
            'if (tool == 0)',
            '  player:tell("You need a basic crafting tool. (You don\'t have one.)");',
            '  return;',
            'endif',
        ] + CRAFT_CODE
        program_verb(s, PLAYER, 'craft', craft_with_tool_check)

        print(f'\n=== Adding wf_test (bct #{bct_num}) ===')
        out = send(s, '@verb #6:wf_test none none none', wait=0.6)
        program_verb(s, PLAYER, 'wf_test', [
            '"Full craft/eat test.";',
            'player:tell("=== WF_TEST BEGIN ===");',
            'player.w_hp = 50; player.w_hp_max = 100;',
            f'has_tool = 0;',
            f'for itm in (player.contents)',
            f'  if (is_a(itm, #{bct_num}))',
            f'    has_tool = 1; break;',
            f'  endif',
            f'endfor',
            f'if (!has_tool)',
            f'  t = create(#{bct_num}); move(t, player);',
            f'  player:tell("  Gave basic crafting tool.");',
            f'endif',
            'f1 = create($thing); f1.name = "native fiber"; move(f1, player);',
            'f2 = create($thing); f2.name = "native fiber"; move(f2, player);',
            'cnt = length(player.contents);',
            'player:tell("  Inventory: " + tostr(cnt) + " items");',
            'for x in (player.contents)',
            '  player:tell("    - " + x.name);',
            'endfor',
            'player:tell("--- craft ration bar ---");',
            'this:craft("ration", "bar");',
            'cnt2 = length(player.contents);',
            'player:tell("  After craft: " + tostr(cnt2) + " items");',
            'for x in (player.contents)',
            '  player:tell("    - " + x.name);',
            'endfor',
            'player:tell("--- eat ration ---");',
            'this:eat("ration bar");',
            'player:tell("  w_hp: " + tostr(player.w_hp) + " (expect 55)");',
            'player:tell("  nourished>now: " + tostr(player.w_nourished > time()));',
            'player:tell("=== WF_TEST END ===");',
        ])

        out = send(s, 'wf_test', wait=4.0)
        print(f'\n=== wf_test output ===\n{out.strip()[-800:]}')
    else:
        print('\nmove() FAILED from verb context — further debugging needed')
        print(f'output was: {out.strip()[-100:]}')

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(f'\nSave: {out.strip()[:60]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
