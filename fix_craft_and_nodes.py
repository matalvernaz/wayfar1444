#!/usr/bin/env python3
"""
Fix $basic_craft_tool pointer, verify craft, check node population.
"""

import socket, time, re

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

    # 1. Fix $basic_craft_tool pointer
    print('=== Fix $basic_craft_tool ===')

    # Find the real craft tool prototype - it should be a non-player $thing
    # Phase4 created it as #574 but something reset it back to #361
    # Let's check what #574 is
    out = ev(s, 'player:tell(valid(#574) ? (#574.name) | "invalid")', wait=0.7)
    print(f'#574 = {out.strip()[-60:]}')

    out = ev(s, 'player:tell(valid(#569) ? (#569.name) | "invalid")', wait=0.7)
    print(f'#569 = {out.strip()[-60:]}')

    # Scan for any "basic crafting tool" object
    out = ev(s, '''
found_bct = 0;
for i in [560..600]
  if (valid(#i) && !is_a(#i, $player) && !is_a(#i, $room))
    if (index(#i.name, "crafting") || index(#i.name, "craft"))
      player:tell("found: #" + tostr(i) + " = " + #i.name);
      found_bct = i;
    endif
  endif
endfor
player:tell("scan done. found=" + tostr(found_bct));
'''.strip(), wait=1.5)
    print(f'Scan result: {out.strip()[-200:]}')

    # Extract the found object number
    m = re.search(r'found: #(\d+)', out)
    if m:
        bct_num = int(m.group(1))
        print(f'Found craft tool at #{bct_num}')
    else:
        # Need to create it fresh
        print('Creating new basic_craft_tool prototype...')
        out = ev(s, 'bct = create($thing); bct.name = "basic crafting tool"; bct.description = "A portable fabrication unit. Type craft to see recipes."; player:tell(tostr(bct))', wait=1.0)
        m = re.search(r'#(\d+)', out)
        if m:
            bct_num = int(m.group(1))
            print(f'Created at #{bct_num}')
        else:
            print(f'ERROR: {out.strip()[:200]}')
            s.close()
            return

    # Set $basic_craft_tool to the correct object
    out = ev(s, f'$basic_craft_tool = #{bct_num}; player:tell(tostr($basic_craft_tool))', wait=0.7)
    print(f'Set $basic_craft_tool = {out.strip()[-40:]}')

    # 2. Update craft verb on $player to use correct bct_num
    print(f'\n=== Update craft verb on $player to use #{bct_num} ===')
    # Check current craft verb
    out = ev(s, 'player:tell(tostr(verb_info(#6, "craft")))', wait=0.7)
    print(f'craft verb_info: {out.strip()[-60:]}')

    # Reprogram with correct bct_num - just the tool check prefix
    # The crafting recipes are already correct, just the is_a check uses hardcoded number
    # We need to update line 4 of the verb which was f'  if (is_a(itm, #{OLD_BCT_NUM}))'
    # Easiest: just reprogram entirely with new number

    import sys; sys.path.insert(0, '/home/matt/wayfar')
    from phase4_craft import CRAFT_CODE

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
    program_verb(s, PLAYER, 'craft', craft_with_tool_check)

    # 3. Give wizard a fresh crafting tool instance
    print(f'\n=== Give wizard crafting tool (instance of #{bct_num}) ===')
    # Remove any old crafting tools
    out = ev(s, f'for itm in (player.contents); if (index(itm.name, "craft")); recycle(itm); break; endif; endfor', wait=0.7)
    # Create new instance
    out = ev(s, f't = create(#{bct_num}); move(t, player.location); player:tell("created at " + tostr(t.location))', wait=0.7)
    print(f'create tool: {out.strip()[-80:]}')
    # Pick it up
    out = send(s, f'get basic crafting tool', wait=1.0)
    print(f'get tool: {out.strip()[-100:]}')

    # Check inventory
    out = send(s, 'i', wait=0.8)
    print(f'inventory: {out.strip()[-200:]}')

    # 4. Check node population for current room
    print('\n=== Node population check ===')
    out = ev(s, 'player:tell("location: " + tostr(player.location) + " " + player.location.name)', wait=0.7)
    print(f'current room: {out.strip()[-80:]}')

    out = ev(s, 'nc = 0; for itm in (player.location.contents); if ("is_node" in properties(itm)); nc = nc + 1; endif; endfor; player:tell("nodes: " + tostr(nc))', wait=1.0)
    print(f'node count: {out.strip()[-60:]}')

    # Try to populate the room
    out = ev(s, '$ods:populate(player.location); player:tell("populated")', wait=1.5)
    print(f'populate: {out.strip()[-80:]}')

    out = ev(s, 'nc = 0; for itm in (player.location.contents); if ("is_node" in properties(itm)); nc = nc + 1; player:tell("  " + itm.name); endif; endfor; player:tell("nodes: " + tostr(nc))', wait=1.0)
    print(f'nodes after populate: {out.strip()[-200:]}')

    # 5. Full test: gather + craft + eat
    print('\n=== Full gameplay test ===')
    out = send(s, 'gather', wait=1.0)
    print(f'gather list:\n{out.strip()[-300:]}')

    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber: {out.strip()[-150:]}')
    out = send(s, 'gather fiber', wait=1.5)
    print(f'gather fiber 2: {out.strip()[-100:]}')

    out = send(s, 'i', wait=0.8)
    print(f'inventory: {out.strip()[-200:]}')

    out = send(s, 'craft ration bar', wait=2.0)
    print(f'craft ration bar: {out.strip()[-200:]}')

    out = send(s, 'i', wait=0.8)
    print(f'inventory after craft: {out.strip()[-200:]}')

    out = ev(s, 'player.w_hp = 80')
    out = send(s, 'eat ration', wait=1.5)
    print(f'eat ration: {out.strip()[-200:]}')

    hp = ev(s, 'player:tell("w_hp=" + tostr(player.w_hp))', wait=0.7)
    print(f'w_hp after eat: {hp.strip()[-40:]}')

    # 6. Save DB
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=3.0)
    print(out.strip()[:80])

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
