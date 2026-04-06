#!/usr/bin/env python3
"""Check game state and run wf_test."""

import socket, time, re, sys

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


def add_verb(s, obj_num, verbname, args='none none none'):
    out = send(s, f'@verb #{obj_num}:{verbname} {args}', wait=0.6)
    ok = 'Verb added' in out or 'already defined' in out.lower()
    if not ok:
        print(f'  WARN @verb #{obj_num}:{verbname}: {repr(out[:100])}')
    return out


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

    # Check $basic_craft_tool
    print('=== Check $basic_craft_tool ===')
    out = ev(s, 'player:tell(tostr($basic_craft_tool))')
    print(f'$basic_craft_tool: {out.strip()[-60:]}')

    # Check $ods verbs
    print('\n=== Check $ods ===')
    out = ev(s, 'player:tell(tostr($ods))')
    print(f'$ods: {out.strip()[-60:]}')
    out = ev(s, 'player:tell(tostr(verbs($ods)))')
    print(f'$ods verbs: {out.strip()[-300:]}')

    # Check $wroom enterfunc
    print('\n=== Check $wroom enterfunc ===')
    out = ev(s, 'player:tell(typeof(verb_info(#452, "enterfunc")) == LIST ? "has enterfunc" | "no enterfunc")')
    print(f'wroom enterfunc: {out.strip()[-60:]}')
    out = ev(s, 'player:tell(typeof(verb_info(#452, "look_self")) == LIST ? "has look_self" | "no look_self")')
    print(f'wroom look_self: {out.strip()[-60:]}')

    # Move to Dispatch Bay to run dispatch
    print('\n=== Move to #563 ===')
    out = ev(s, 'move(player, #563)')
    print(f'move to #563: {out.strip()[-60:]}')
    out = ev(s, 'player:tell("loc=" + tostr(player.location))')
    print(f'location: {out.strip()[-60:]}')

    # Run dispatch to get to wilderness
    out = send(s, 'dispatch', wait=3.0)
    print(f'dispatch:\n{out.strip()[-200:]}')
    out = ev(s, 'player:tell("loc=" + tostr(player.location) + " " + player.location.name)')
    print(f'location after dispatch: {out.strip()[-80:]}')

    # Check if populate gets called when we look
    print('\n=== Check room nodes ===')
    out = ev(s, 'nc = 0; for itm in (player.location.contents); if ("is_node" in properties(itm) && itm.is_node); nc = nc + 1; endif; endfor; player:tell("nodes: " + tostr(nc))', wait=1.0)
    print(f'node count: {out.strip()[-60:]}')

    # Get $ods number and try populate directly
    ods_out = ev(s, 'player:tell(tostr($ods))')
    m = re.search(r'#(\d+)', ods_out)
    if m:
        ods_num = m.group(1)
        print(f'$ods = #{ods_num}')
        out = ev(s, f'#{ods_num}:populate(player.location)', wait=1.0)
        print(f'populate call: {out.strip()[-100:]}')

        # Check nodes again
        out = ev(s, 'nc = 0; for itm in (player.location.contents); if ("is_node" in properties(itm) && itm.is_node); nc = nc + 1; player:tell(itm.name); endif; endfor; player:tell("nodes: " + tostr(nc))', wait=1.0)
        print(f'nodes after populate: {out.strip()[-200:]}')

    # Now try gather
    print('\n=== gather test ===')
    out = send(s, 'gather', wait=1.5)
    print(f'gather list:\n{out.strip()[-300:]}')

    # Also run the wf_test verb now
    # First check what bct_num is
    bct_out = ev(s, 'player:tell(tostr($basic_craft_tool))')
    m = re.search(r'#(\d+)', bct_out)
    bct_num = int(m.group(1)) if m else 592
    print(f'\n$basic_craft_tool = #{bct_num}')

    # Check if bct is valid and not a player
    out = ev(s, f'player:tell(valid(#{bct_num}) ? "valid" | "invalid")')
    print(f'bct valid: {out.strip()[-40:]}')
    out = ev(s, f'player:tell(is_a(#{bct_num}, $player) ? "is player" | "not player")')
    print(f'bct is player: {out.strip()[-40:]}')

    # Re-add wf_test with correct bct_num
    print(f'\n=== Adding wf_test with bct #{bct_num} ===')
    add_verb(s, PLAYER, 'wf_test', 'none none none')
    program_verb(s, PLAYER, 'wf_test', [
        '"Test crafting system from verb context.";',
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
        f'  player:tell("  Gave basic crafting tool: " + tostr(t.location));',
        f'endif',
        'f1 = create($thing); f1.name = "native fiber"; f1.description = "Fibrous."; move(f1, player);',
        'f2 = create($thing); f2.name = "native fiber"; f2.description = "Fibrous."; move(f2, player);',
        'cnt = length(player.contents);',
        'player:tell("  Inv count after add: " + tostr(cnt));',
        'if (cnt == 0)',
        '  player:tell("  ERROR: move() failed from verb context!");',
        '  return;',
        'endif',
        'for x in (player.contents)',
        '  player:tell("    item: " + x.name);',
        'endfor',
        'player:tell("--- craft ration bar ---");',
        'this:craft("ration", "bar");',
        'cnt2 = length(player.contents);',
        'player:tell("  Inv after craft: " + tostr(cnt2));',
        'for x in (player.contents)',
        '  player:tell("    item: " + x.name);',
        'endfor',
        'player:tell("--- eat ration bar ---");',
        'this:eat("ration bar");',
        'player:tell("  w_hp: " + tostr(player.w_hp) + " (expect 55)");',
        'player:tell("  nourished: " + tostr(player.w_nourished > time()));',
        'player:tell("=== WF_TEST END ===");',
    ])

    print('\n=== Running wf_test ===')
    out = send(s, 'wf_test', wait=4.0)
    print(f'wf_test:\n{out.strip()[-800:]}')

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(out.strip()[:60])

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
