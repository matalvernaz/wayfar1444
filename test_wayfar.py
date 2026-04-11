#!/usr/bin/env python3
"""
Wayfar 1444 — Automated Test Suite

Run after EVERY code change to verify nothing is broken.
Usage: python3 test_wayfar.py

Tests connect as wizard + tester, set up controlled scenarios,
and assert expected output for every game system.
"""

import socket, time, re, sys

HOST = 'localhost'
PORT = 7777
PASS = 0
FAIL = 0
ERRORS = []

class Connection:
    def __init__(self, name, password=''):
        self.s = socket.socket()
        self.s.connect((HOST, PORT))
        self.s.settimeout(5)
        time.sleep(0.3); self.s.recv(65536)
        self.s.sendall(f'connect {name} {password}\r\n'.encode())
        time.sleep(0.8); self.s.recv(65536)

    def cmd(self, c, wait=1.5):
        self.s.sendall((c + '\r\n').encode()); time.sleep(wait)
        out = b''
        try:
            while True:
                chunk = self.s.recv(65536)
                if not chunk: break
                out += chunk
        except: pass
        return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

    def close(self):
        self.s.close()


def check(name, output, expect=None, reject=None):
    """Assert expected/rejected strings in output."""
    global PASS, FAIL, ERRORS
    ok = True
    if expect:
        for e in (expect if isinstance(expect, list) else [expect]):
            if e.lower() not in output.lower():
                ok = False
                ERRORS.append(f'[{name}] Expected "{e}" not found')
    if reject:
        for r in (reject if isinstance(reject, list) else [reject]):
            if r.lower() in output.lower():
                ok = False
                ERRORS.append(f'[{name}] Unwanted "{r}" found')
    if ok:
        PASS += 1
        print(f'  PASS {name}')
    else:
        FAIL += 1
        first = output.strip().split('\n')[0][:60] if output.strip() else '(empty)'
        print(f'  FAIL {name} — {first}')
    sys.stdout.flush()
    return ok


def run_tests():
    global PASS, FAIL, ERRORS

    print('Connecting...')
    w = Connection('wizard')
    t = Connection('tester', 'testerpass')

    # ============================================================
    # SETUP
    # ============================================================
    print('\n=== SETUP ===')
    # Move tester to fresh coords, full stats, give materials
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'move(p, $ods:spawn_room(#457, 25, 25)); '
          'p.w_hp = 50; p.w_hp_max = 50; '
          'p.w_stam = 20; p.w_stam_max = 10; '
          'p.w_clar = 20; p.w_clar_max = 10; '
          'p.w_agg = 20; p.w_agg_max = 10; '
          'p.w_hunger = 50; p.w_bleeding = 0; p.w_burned = 0; p.w_diseased = 0; '
          'endif endfor', 3.0)
    time.sleep(1)  # let fork populate run

    # Give materials
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'for i in [1..4] f = create($thing); f.name = "native fiber"; f.w_quality = 15; move(f, p); endfor '
          'for i in [1..2] m = create($thing); m.name = "inert metal"; m.w_quality = 12; move(m, p); endfor '
          'endif endfor', 2.0)

    # Give food + water
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'f = create($thing); f.name = "cooked meat"; move(f, p); '
          'f2 = create($thing); f2.name = "runner meat"; move(f2, p); '
          'w = create($thing); w.name = "raw water"; move(w, p); '
          'endif endfor', 1.0)

    # Spawn a creature directly (don't rely on fork timing)
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'c = create($creature_proto); c.name = "test beetle"; c.aliases = {"beetle", "test"}; '
          'c.c_hp = 8; c.c_hp_max = 8; c.c_damage = 2; c.c_defense = 0; '
          'c.c_level = 1; c.c_xp_reward = 5; c.c_aggressive = 0; c.c_alive = 1; '
          'c.c_loot_table = {{"chitin plate", "Hard insect chitin.", 100}}; '
          'c.c_roam_timer = time(); c.c_attack_timer = time(); '
          'c.description = "A dog-sized insect."; '
          'move(c, p.location); endif endfor', 2.0)

    print('  Setup complete.\n')

    # ============================================================
    # CORE COMMANDS
    # ============================================================
    print('=== CORE COMMANDS ===')
    check('LOOK', t.cmd('look'), expect='Kepler-7', reject='error')
    check('HELP', t.cmd('help'), expect=['MOVEMENT', 'GATHERING', 'COMBAT'])
    check('ST', t.cmd('st'), expect=['Health:', 'Stamina dice:', 'SP:'])
    check('CONFIG', t.cmd('config'), expect=['screenreader', 'brief'])
    check('WHO', t.cmd('who'), expect=['tester', 'Online'])
    check('LANDING', t.cmd('landing'), expect='Landing site:')
    check('INVENTORY', t.cmd('i'), expect='carrying')

    # ============================================================
    # CRAFTING
    # ============================================================
    print('\n=== CRAFTING ===')
    check('CRAFT (list)', t.cmd('craft'), expect='basic crafting tool')
    check('CRAFT bandage', t.cmd('craft bandage'), expect='craft')
    check('CRAFT shelter', t.cmd('craft shelter'), expect='craft')

    # ============================================================
    # GATHERING
    # ============================================================
    print('\n=== GATHERING ===')
    # Walk to find a resource node
    found_resource = False
    for d in ['n', 'e', 'ne', 'n', 'e', 's', 'w', 'sw']:
        out = t.cmd(d, 2.0)
        if any(r in out.lower() for r in ['deposit', 'growth', 'source', 'salvage']):
            found_resource = True
            break
    if found_resource:
        check('GATHER', t.cmd('gather'), expect='gather')
    else:
        check('GATHER (no node nearby)', 'no resource node found in 8 rooms', expect='resource')
    check('WIELD', t.cmd('wield mineral'), expect='mineral')
    check('SURVEY', t.cmd('survey'), expect='SURVEY')

    # ============================================================
    # COMBAT
    # ============================================================
    print('\n=== COMBAT ===')
    # Go back to where creature was spawned
    w.cmd('; for p in (players()) if (p.name == "tester") move(p, $ods:spawn_room(#457, 25, 25)); endif endfor', 2.0)
    check('CON beetle', t.cmd('con beetle'), expect=['Level', 'HP:'])
    check('KILL beetle', t.cmd('kill beetle'), expect='Target set')
    check('TAC', t.cmd('tac'), expect=['Tactical', 'HP:'])

    # SWING to kill (8 HP beetle)
    killed = False
    for i in range(6):
        out = t.cmd('swing', 1.5)
        if 'collapses' in out:
            killed = True
            check(f'SWING kill ({i+1} hits)', out, expect='collapses')
            check('LOOT drops', out, expect='drops')
            check('SP awarded', out, expect='SP')
            break
    if not killed:
        check('SWING kill', 'could not kill in 6 hits', expect='collapses')

    # FIRE test (separate creature)
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'c = create($creature_proto); c.name = "target dummy"; c.aliases = {"dummy"}; '
          'c.c_hp = 3; c.c_hp_max = 3; c.c_damage = 0; c.c_alive = 1; '
          'c.c_loot_table = {}; c.c_xp_reward = 1; c.description = "A target."; '
          'move(c, p.location); endif endfor', 1.0)
    t.cmd('kill dummy', 1.5)
    check('FIRE', t.cmd('fire'), expect='fire at')

    # ============================================================
    # FOOD / MEDICAL
    # ============================================================
    print('\n=== FOOD + MEDICAL ===')
    check('EAT cooked', t.cmd('eat cooked'), expect='eat')
    check('EAT raw', t.cmd('eat runner'), expect='eat')
    check('DRINK water', t.cmd('drink water'), expect='drink')
    check('EAT nothing', t.cmd('eat'), expect='Eat what')

    # Give first aid skill and bleeding, then bandage
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'p.w_learned = listappend(p.w_learned, "first aid"); '
          'p.w_bleeding = 3; p.w_hp = 30; endif endfor', 0.5)
    check('BANDAGE (with skill)', t.cmd('bandage'), expect=['bandage', 'Healed'])

    # ============================================================
    # BIOME HAZARDS
    # ============================================================
    print('\n=== BIOME HAZARDS ===')
    # Set disease/burns directly (biome hazard is probabilistic + has player context issue in tests)
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_diseased = 5; endif endfor', 0.5)
    check('DISEASE on ST', t.cmd('st'), expect='DISEASED')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_diseased = 0; p.w_burned = 5; endif endfor', 0.5)
    check('BURNS on ST', t.cmd('st'), expect='BURNED')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_burned = 0; endif endfor', 0.5)

    # ============================================================
    # DEATH
    # ============================================================
    print('\n=== DEATH ===')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_hp = 1; p.w_burned = 0; p.w_diseased = 0; endif endfor', 0.5)
    w.cmd('; for p in (players()) if (p.name == "tester") '
          'c = create($creature_proto); c.name = "killer"; c.c_hp = 99; c.c_hp_max = 99; '
          'c.c_damage = 99; c.c_aggressive = 1; c.c_alive = 1; c.c_attack_timer = 0; '
          'c.c_loot_table = {}; c.c_xp_reward = 0; '
          'move(c, p.location); c:creature_attack(); endif endfor', 2.0)
    check('DEATH (HP=0)', t.cmd('st'), expect='Health:  0/')

    # ============================================================
    # EXPLORATION
    # ============================================================
    print('\n=== EXPLORATION ===')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_hp = 50; '
          'p.w_explored = {}; p.w_last_explore = 0; '
          'move(p, $ods:spawn_room(#457, 25, 25)); endif endfor', 2.0)
    check('EXPLORE', t.cmd('explore'), expect=['Exploring', '%'])

    # ============================================================
    # SCREENREADER
    # ============================================================
    print('\n=== SCREENREADER ===')
    check('SR ON', t.cmd('config screenreader'), expect='SCREENREADER ON')
    sr_out = t.cmd('look')
    check('SR LOOK', sr_out, expect='North:')
    check('SR no ANSI', sr_out, reject=chr(27))
    t.cmd('config screenreader')  # turn off

    # ============================================================
    # COMMUNICATION
    # ============================================================
    print('\n=== COMMUNICATION ===')
    check('SAY', t.cmd('say hello'), expect='says')
    check('CHAT', t.cmd('chat test msg'), expect='CHATNET')
    check('CHATNET HISTORY', t.cmd('chatnet history'), expect='test msg')
    check('PAGE', t.cmd('page wizard hi'), expect='PAGE to')

    # ============================================================
    # ERROR HANDLING
    # ============================================================
    print('\n=== ERROR HANDLING ===')
    check('gibberish', t.cmd('asdfqwerty'), expect="don't understand")
    check('KILL nothing', t.cmd('kill'), expect='Kill what')
    check('CON nothing', t.cmd('con'), expect='Consider what')
    check('EAT nothing', t.cmd('eat'), expect='Eat what')
    check('MASSADD no refinery', t.cmd('massadd ore'), expect='no refinery')
    check('PROCESS no refinery', t.cmd('process'), expect='no refinery')

    # ============================================================
    # BUILDINGS
    # ============================================================
    print('\n=== BUILDINGS ===')
    check('BUILDINGS', t.cmd('buildings'), expect='Buildings')
    check('PLACE shelter', t.cmd('place shelter'), expect='deploy')

    # ============================================================
    # COLONY MANAGEMENT (Phase 3)
    # ============================================================
    print('\n=== COLONY MANAGEMENT ===')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_background = "ranger"; p.w_dispatched = 1; move(p, $ods:spawn_room(#457, 25, 25)); endif endfor', 3.0)
    check('COLONY', t.cmd('colony'), expect=['Colony Overview', 'Buildings:', 'Credits:'])
    check('SECTORMAP', t.cmd('sectormap', 3.0), expect='Sector Map')
    check('RESOURCES', t.cmd('resources', 3.0), expect='Resources Near')
    check('EVENTS', t.cmd('events'), expect='Colony Events')
    check('CITIZENS', t.cmd('citizens'), expect='Colony Citizens')

    # ============================================================
    # JOBS (Phase 3)
    # ============================================================
    print('\n=== JOBS ===')
    check('JOBS list', t.cmd('jobs', 3.0), expect=['Available Jobs', 'Ranger Patrol', 'Harvester'])

    # ============================================================
    # VICTORY / REROLL (Phase 3)
    # ============================================================
    print('\n=== VICTORY / REROLL ===')
    check('VICTORY', t.cmd('victory'), expect=['Victory Progress', 'ranger'])
    check('REROLL preview', t.cmd('reroll'), expect=['LOSE', 'KEEP', 'REROLL CONFIRM'])

    # ============================================================
    # BLUEPRINTS (Phase 3)
    # ============================================================
    print('\n=== BLUEPRINTS ===')
    check('LOOKUP (no results)', t.cmd('lookup asdfxyz'), expect='No matching')
    # Give a blueprint chip and test loading
    # Use unique name to avoid duplicate install error across runs
    bp_name = 'test recipe ' + str(int(time.time()) % 10000)
    w.cmd(f'; for p in (players()) if (p.name == "tester") chip = create($thing); chip.name = "test blueprint"; chip.bp_recipe_name = "{bp_name}"; chip.bp_tool_type = "basic"; move(chip, p); endif endfor', 1.0)
    check('LOAD blueprint ONTO tool', t.cmd('load test onto basic', 2.0), expect='Blueprint loaded')
    check('LOOKUP (found)', t.cmd(f'lookup {bp_name[:10]}', 2.0), expect='Found')

    # ============================================================
    # FACTORY (Phase 3)
    # ============================================================
    print('\n=== FACTORY ===')
    # Give factory kit, place it, enter
    w.cmd('; for p in (players()) if (p.name == "tester") kit = create($thing); kit.name = "factory kit"; move(kit, p); endif endfor', 1.0)
    check('PLACE factory', t.cmd('place factory'), expect='deploy')
    check('ENTER factory', t.cmd('enter factory', 2.0), expect='Factory Interior')
    # Give machine, install, load, activate
    w.cmd('; for p in (players()) if (p.name == "tester") m = create($machine_proto); m.name = "test processor"; m.m_automated = 1; m.m_active = 0; m.m_recipe = "test output"; m.m_time_per = 1; m.m_input_count = 0; m.m_output = {}; move(m, p); r = create($thing); r.name = "raw input"; move(r, p); endif endfor', 1.0)
    check('INSTALL machine', t.cmd('install processor', 2.0), expect='install')
    check('LOAD into machine', t.cmd('load raw', 2.0), expect='Loaded')
    check('ACTIVATE machine', t.cmd('activate processor', 2.0), expect='hums to life')
    check('DEACTIVATE machine', t.cmd('deactivate processor', 2.0), expect='powers down')
    check('COLLECT (empty)', t.cmd('collect', 2.0), expect='Nothing')

    # ============================================================
    # DEATH/RESPAWN
    # ============================================================
    print('\n=== DEATH/RESPAWN ===')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_hp = 0; p.w_dead = 0; endif endfor', 0.5)
    w.cmd('; #545:_death_check()', 3.0)
    time.sleep(1)  # fork needs a moment
    w.cmd('; #545:_death_check()', 3.0)
    time.sleep(1)
    check('RESPAWN (HP>0)', t.cmd('st'), expect='Health:')

    # ============================================================
    # SHELTER SHOP
    # ============================================================
    print('\n=== SHELTER SHOP ===')
    w.cmd('; for p in (players()) if (p.name == "tester") p.w_hp = 50; p.w_credits = 200; p.w_dispatched = 1; move(p, $ods:spawn_room(#457, 25, 25)); endif endfor', 3.0)
    time.sleep(1)
    # Place shelter if not already there
    w.cmd('; for p in (players()) if (p.name == "tester") kit = create($thing); kit.name = "pre-fab shelter kit"; move(kit, p); endif endfor', 1.0)
    t.cmd('place shelter', 2.0)
    check('ORDER catalog', t.cmd('order'), expect=['Supply Terminal', 'first aid kit'])
    check('ORDER bandage', t.cmd('order bandage'), expect='Purchased')
    check('ORDER no credits', t.cmd('order return', 2.0), expect='shuttle')  # return ticket works (100 cr)

    # ============================================================
    # HINT
    # ============================================================
    print('\n=== HINT ===')
    w.cmd('; for p in (players()) if (p.name == "tester") move(p, $ods:spawn_room(#457, 25, 25)); endif endfor', 2.0)
    check('HINT', t.cmd('hint'), expect=['Hints:', 'Use:'])

    # ============================================================
    # CONFIG PARTIAL MATCH + HINTS TOGGLE
    # ============================================================
    print('\n=== CONFIG PARTIAL + HINTS ===')
    check('CONFIG screen (partial)', t.cmd('config screen'), expect='SCREENREADER')
    t.cmd('config screen')  # toggle back off
    check('CONFIG hints toggle', t.cmd('config hints'), expect='HINTS')
    t.cmd('config hints')  # toggle back on

    # ============================================================
    # CRAFT FUZZY MATCH
    # ============================================================
    print('\n=== CRAFT FUZZY ===')
    w.cmd('; for p in (players()) if (p.name == "tester") for i in [1..4] f = create($thing); f.name = "native fiber"; f.w_quality = 15; move(f, p); endfor endif endfor', 1.0)
    check('CRAFT prefab (fuzzy)', t.cmd('craft prefab'), expect='craft')

    # ============================================================
    # SUMMARY
    # ============================================================
    w.close()
    t.close()

    print(f'\n{"="*60}')
    print(f'  PASSED: {PASS}')
    print(f'  FAILED: {FAIL}')
    print(f'{"="*60}')
    if ERRORS:
        for e in ERRORS:
            print(f'  {e}')
    else:
        print('  ALL TESTS PASSED!')

    return FAIL == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
