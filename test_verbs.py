#!/usr/bin/env python3
"""
Add a 'wf_test' verb to $player that runs the full craft/eat loop from INSIDE
a verb context (where move() works properly). Also move wizard to #563 for dispatch test.
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777
PLAYER = 6
DISPATCH_ROOM = 563


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


def add_verb(s, obj_num, verbname, args='none none none'):
    out = send(s, f'@verb #{obj_num}:{verbname} {args}', wait=0.6)
    ok = 'Verb added' in out or 'already defined' in out.lower()
    if not ok:
        print(f'  WARN @verb #{obj_num}:{verbname}: {repr(out[:100])}')
    return out


def program_verb(s, obj_num, verbname, code_lines):
    out = send(s, f'@program #{obj_num}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program #{obj_num}:{verbname}: {repr(out[:150])}')
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

    # 1. Move wizard to Planetary Dispatch Bay #563
    print('=== Moving wizard to #563 (Planetary Dispatch Bay) ===')
    out = ev(s, 'move(player, #563); player:tell("loc=" + tostr(player.location))', wait=0.7)
    print(f'move result: {out.strip()[-80:]}')

    # 2. Test dispatch verb
    print('\n=== Testing dispatch (should go to wilderness) ===')
    out = send(s, 'dispatch', wait=3.0)
    print(f'dispatch:\n{out.strip()[-300:]}')

    out = ev(s, 'player:tell("loc=" + tostr(player.location) + " " + player.location.name)', wait=0.7)
    print(f'location after dispatch: {out.strip()[-80:]}')

    # 3. Test gather in wilderness
    print('\n=== Test gather ===')
    out = send(s, 'gather', wait=1.0)
    print(f'gather list: {out.strip()[-300:]}')

    out = send(s, 'gather ore', wait=1.5)
    print(f'gather ore: {out.strip()[-150:]}')

    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber: {out.strip()[-150:]}')

    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber 2: {out.strip()[-150:]}')

    out = send(s, 'i', wait=1.0)
    print(f'inventory: {out.strip()[-300:]}')

    # 4. Add wf_test verb for in-verb crafting test
    print('\n=== Adding wf_test verb ===')
    # Get $basic_craft_tool number
    out = ev(s, 'player:tell(tostr($basic_craft_tool))', wait=0.7)
    m = re.search(r'#(\d+)', out)
    bct_num = int(m.group(1)) if m else 574
    print(f'$basic_craft_tool = #{bct_num}')

    add_verb(s, PLAYER, 'wf_test', 'none none none')
    program_verb(s, PLAYER, 'wf_test', [
        '"Full craft/eat/drink test from within verb context.";',
        'player:tell("=== WF_TEST BEGIN ===");',
        'player.w_hp = 50; player.w_hp_max = 100; player.w_sp = 100;',
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
        'f1 = create($thing); f1.name = "native fiber"; f1.description = "Fibrous."; move(f1, player);',
        'f2 = create($thing); f2.name = "native fiber"; f2.description = "Fibrous."; move(f2, player);',
        'cnt = length(player.contents);',
        'player:tell("  Inventory count after giving items: " + tostr(cnt));',
        'for x in (player.contents)',
        '  player:tell("    " + tostr(x) + " " + x.name);',
        'endfor',
        'player:tell("");',
        'player:tell("--- Craft test ---");',
        'this:craft("ration", "bar");',
        'cnt2 = length(player.contents);',
        'player:tell("  Inventory after craft: " + tostr(cnt2));',
        'for x in (player.contents)',
        '  player:tell("    " + tostr(x) + " " + x.name);',
        'endfor',
        'player:tell("");',
        'player:tell("--- Eat test ---");',
        'this:eat("ration bar");',
        'player:tell("  w_hp after eat: " + tostr(player.w_hp) + " (expect 55)");',
        'player:tell("  w_nourished>now: " + tostr(player.w_nourished > time()) + " (expect 1)");',
        'player:tell("=== WF_TEST END ===");',
    ])

    # 5. Run wf_test verb
    print('\n=== Running wf_test ===')
    out = send(s, 'wf_test', wait=3.0)
    print(f'wf_test output:\n{out.strip()[-600:]}')

    # 6. Test dispatch and gather work
    print('\n=== Final status check ===')
    out = send(s, 'st', wait=1.5)
    print(f'st output:\n{out.strip()[-400:]}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
