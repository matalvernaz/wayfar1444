#!/usr/bin/env python3
"""
setup_heartbeat.py — Install/update the survival heartbeat on Wayfar 1444.

Creates a heartbeat object in Colony Hub (#157) if none exists.
Programs tick, start, and npc_idle verbs.

Tick logic (every 5 min):
  - Hunger decays -4
  - Stamina recovers +2 if hunger > 30, else falls -3
  - Health falls -5 per tick when starving (hunger == 0)
  - DEATH: if health <= 0, teleport to crash site #459, restore
    hunger=20 / health=30 / stamina=50, announce respawn
  - Re-schedules itself via fork(300)

Death/respawn is tested immediately after install (set health=0, run tick).
"""

import socket, time, re

HOST = 'localhost'
PORT = 7777

HUB      = 504   # Colony Hub (confirmed from fix_colony.py / hellcore.db.new)
LZ       = 459   # Impact Site Zero (crash site / respawn point)
PLAYER   = 6     # $player


TICK_VERB = [
    '"Decay survival stats for all connected players; handle death + re-schedule.";',
    'set_task_perms(this.owner);',
    'for p in (connected_players())',
    '  "--- hunger decay ---";',
    '  nh = p.hunger - 4;',
    '  if (nh < 0)',
    '    nh = 0;',
    '  endif',
    '  p.hunger = nh;',
    '  "--- stamina: recover if fed, fall if hungry ---";',
    '  if (p.hunger > 30)',
    '    ns = p.stamina + 2;',
    '    if (ns > 100)',
    '      ns = 100;',
    '    endif',
    '  else',
    '    ns = p.stamina - 3;',
    '    if (ns < 0)',
    '      ns = 0;',
    '    endif',
    '  endif',
    '  p.stamina = ns;',
    '  "--- health falls when starving ---";',
    '  if (p.hunger == 0)',
    '    nhp = p.health - 5;',
    '    if (nhp <= 0)',
    '      nhp = 0;',
    '    endif',
    '    p.health = nhp;',
    '    if (nhp > 0)',
    '      p:tell("[SURVIVAL] You are starving. Find food or you will die.");',
    '    endif',
    '  elseif (p.hunger < 20)',
    '    p:tell("[SURVIVAL] Warning: hunger critical (" + tostr(p.hunger) + "/100).");',
    '  endif',
    '  "--- death check ---";',
    '  if (p.health <= 0)',
    '    p.hunger  = 20;',
    '    p.health  = 30;',
    '    p.stamina = 50;',
    '    p:tell("");',
    '    p:tell("*** YOU HAVE DIED ***");',
    '    p:tell("Starvation claimed you. You wake at the crash site, barely alive.");',
    '    p:tell("");',
    '    move(p, #' + str(LZ) + ');',
    '    p.location:announce(p.name + " crawls back from the brink of death.", p);',
    '  endif',
    'endfor',
    '"--- NPC idle chatter ---";',
    'this:npc_idle();',
    '"--- re-schedule in 300 seconds (5 min) ---";',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

START_VERB = [
    '"Start the survival heartbeat loop.";',
    'player:tell("Survival monitor starting (5-minute decay cycle).");',
    'fork (300)',
    '  this:tick();',
    'endfork',
]

NPC_IDLE_VERB = [
    '"Fire random idle chatter for NPCs registered on this monitor.";',
    'for npc in (this.npcs)',
    '  if (!valid(npc))',
    '    break;',
    '  endif',
    '  lines = npc.idle_lines;',
    '  if (length(lines) == 0)',
    '    break;',
    '  endif',
    '  idx = random(length(lines));',
    '  npc.location:announce(npc.name + " says, \\"" + lines[idx] + "\\"");',
    'endfor',
]

TICK_NOW_VERB = [
    '"Run one tick immediately (for testing/admin).";',
    'player:tell("Running one heartbeat tick now...");',
    'this:tick();',
]


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7)
    try: s.recv(65536)
    except: pass
    return s


def send(s, cmd, wait=0.5):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.5):
    return send(s, f'; {expr}', wait)


def program_verb(s, obj, verbname, code_lines):
    """Program verbname on obj (targets first verb with that name)."""
    out = send(s, f'@program #{obj}:{verbname}', wait=0.6)
    if 'programming' not in out.lower():
        print(f'  WARN entering @program #{obj}:{verbname}: {repr(out[:120])}')
    s.settimeout(0.15)
    for line in code_lines:
        send(s, line, wait=0.03)
    s.settimeout(3)
    out = send(s, '.', wait=2.0)
    if re.search(r'[1-9]\d* error', out):
        print(f'  ERROR #{obj}:{verbname}: {repr(out[:400])}')
        return False
    return True


def add_and_program(s, obj, verbname, args, code_lines):
    """
    Ensure verb exists on obj and program it.
    Strategy: delete ALL copies of verbname from obj, add fresh, then program.
    This avoids the @program 'ignoring' trap when a verb doesn't actually exist.
    """
    # Find and delete all copies of verbname on this specific object
    for attempt in range(5):
        pos_out = ev(
            s,
            f'idx = 0; for i in [1..length(verbs(#{obj}))]; '
            f'if (verbs(#{obj})[i] == {repr(verbname)}); idx = i; break; endif; endfor; '
            f'player:tell(tostr(idx))',
            wait=0.6,
        )
        m = re.search(r'(\d+)\r?\n=> 0', pos_out)
        if not m:
            break
        idx = int(m.group(1))
        if idx == 0:
            break
        ev(s, f'delete_verb(#{obj}, {idx})', wait=0.4)
        print(f'  Deleted #{obj}:{verbname} at index {idx}')

    # Add fresh verb
    send(s, f'@verb #{obj}:{verbname} {args}', wait=0.5)
    print(f'  Added @verb #{obj}:{verbname} {args}')

    return program_verb(s, obj, verbname, code_lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_or_create_heartbeat(s):
    """
    Return the object number of the heartbeat in HUB, creating if needed.
    If an existing one is found, it will be re-used (verbs re-programmed).
    """
    # Check #0.colony_heartbeat global first
    out = ev(s, f'player:tell(tostr(#0.colony_heartbeat))', wait=0.5)
    m = re.search(r'#(\d+)', out)
    if m:
        num = int(m.group(1))
        if num > 0:
            # Verify it's still valid
            ok = ev(s, f'player:tell(valid(#{num}) ? "yes" | "no")', wait=0.4)
            if 'yes' in ok:
                print(f'  Found heartbeat via #0.colony_heartbeat: #{num}')
                return num

    # Scan hub contents for "survival monitor" — get list, then check each
    out = ev(s, f'player:tell(tostr(#{HUB}.contents))', wait=0.5)
    nums = re.findall(r'#(\d+)', out)
    for n in nums:
        name_out = ev(s, f'player:tell(#{n}.name)', wait=0.3)
        if 'survival monitor' in name_out.lower():
            num = int(n)
            print(f'  Found existing heartbeat in hub: #{num}')
            # Store it as a global for next time
            ev(s, f'#0.colony_heartbeat = #{num}', wait=0.4)
            return num

    # Not found — create fresh
    print(f'  No heartbeat found in #{HUB}, creating...')
    out = ev(
        s,
        f'o = create($thing); o.name = "survival monitor"; '
        f'o.owner = #2; move(o, #{HUB}); player:tell(tostr(o))',
        wait=0.8,
    )
    m = re.search(r'(#\d+)', out)
    if not m:
        print(f'  FATAL: could not create heartbeat object. Output: {repr(out[:200])}')
        return None
    num = int(m.group(1)[1:])
    # Add npcs list property so npc_idle verb can reference it
    ev(s, f'add_property(#{num}, "npcs", {{}}, {{#2, "rc"}})', wait=0.4)
    print(f'  Created heartbeat #{num} in #{HUB}')
    return num


if __name__ == '__main__':
    print('Wayfar 1444 — Heartbeat Setup')
    print('=' * 60)

    s = connect()

    # --- Find or create heartbeat object ---
    hb = find_or_create_heartbeat(s)
    if not hb:
        print('ABORT: no heartbeat object.')
        s.close()
        exit(1)

    # --- Program all verbs ---
    print(f'\n=== Programming #{hb} verbs ===')
    ok = add_and_program(s, hb, 'tick',     'this none none', TICK_VERB)
    print(f'  tick:     {"OK" if ok else "FAIL"}')

    ok = add_and_program(s, hb, 'start',    'this none none', START_VERB)
    print(f'  start:    {"OK" if ok else "FAIL"}')

    ok = add_and_program(s, hb, 'npc_idle', 'this none none', NPC_IDLE_VERB)
    print(f'  npc_idle: {"OK" if ok else "FAIL"}')

    ok = add_and_program(s, hb, 'tick_now', 'this none none', TICK_NOW_VERB)
    print(f'  tick_now: {"OK" if ok else "FAIL"}')

    # --- Test: verify death/respawn works ---
    print('\n=== Testing death/respawn ===')
    # Save current location and stats
    out_loc = ev(s, 'player:tell(tostr(player.location))', wait=0.4)
    m = re.search(r'#(\d+)', out_loc)
    original_loc = int(m.group(1)) if m else LZ

    # Save stats
    out_stats = ev(s, 'player:tell(tostr(player.hunger) + "/" + tostr(player.health) + "/" + tostr(player.stamina))', wait=0.4)
    print(f'  Pre-test stats: {out_stats.strip()[:60]}')

    # Set health to 0 and hunger to 0 to trigger death
    ev(s, 'player.health = 0', wait=0.3)
    ev(s, 'player.hunger = 0', wait=0.3)
    print('  Set health=0, hunger=0 — running one tick via eval...')

    # Call tick_now via ; eval (verb is "this none none" so must call via :method())
    out = ev(s, f'#{hb}:tick_now()', wait=3.0)
    print(f'  tick output:\n    {out.strip()[:300]}')

    # Check where we are and what our stats are
    out_loc2 = ev(s, 'player:tell(tostr(player.location) + " " + player.location.name)', wait=0.5)
    out_stats2 = ev(s, 'player:tell("hunger=" + tostr(player.hunger) + " health=" + tostr(player.health) + " stamina=" + tostr(player.stamina))', wait=0.4)
    print(f'  Post-death location: {out_loc2.strip()[:80]}')
    print(f'  Post-death stats:    {out_stats2.strip()[:80]}')

    if f'#{LZ}' in out_loc2 or 'Impact Site' in out_loc2:
        print('  PASS: teleported to crash site')
    else:
        print('  WARN: location unexpected, check output above')

    # --- Start heartbeat loop ---
    print(f'\n=== Starting heartbeat loop on #{hb} ===')
    # start verb is "this none none" — must call via ; eval
    out = ev(s, f'#{hb}:start()', wait=1.5)
    print(f'  {out.strip()[:100]}')

    # --- Save ---
    print('\n=== Saving database ===')
    out = send(s, '@dump-database', wait=2.5)
    print(out.strip()[:80])

    s.sendall(b'QUIT\r\n')
    s.close()
    print(f'\nDone. Heartbeat #{hb} is running with 5-min decay + death/respawn at #{LZ}.')
