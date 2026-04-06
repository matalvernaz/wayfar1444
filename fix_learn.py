#!/usr/bin/env python3
"""Fix LEARN verb ownership and reprogram it on $player (#6)."""

import socket, time, re

HOST = 'localhost'
PORT = 7777
PLAYER = 6
WIZARD = 361  # wizard player object


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(3)
    time.sleep(0.5)
    s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.7)
    s.recv(65536)
    return s


def send(s, cmd, wait=0.65):
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


def ev(s, expr, wait=0.55):
    return send(s, f'; {expr}', wait=wait)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def program_verb(s, obj_num, verbname, code_lines):
    out = send(s, f'@program #{obj_num}:{verbname}', wait=0.7)
    if 'programming' not in out.lower():
        print(f'  ERROR @program #{obj_num}:{verbname}: {repr(out[:150])}')
        return out
    old_timeout = s.gettimeout()
    s.settimeout(0.25)
    for line in code_lines:
        send(s, line, wait=0.04)
    s.settimeout(old_timeout)
    result = send(s, '.', wait=2.5)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR #{obj_num}:{verbname}:')
        print(result[:800])
    else:
        print(f'    OK: #{obj_num}:{verbname}')
    return result


SKILLS = [
    # (name, sp_cost, prereq, description, bonus_prop, bonus_amt)
    ('heavy_tan',             75,  '',                   'Heavy Tan: +10 max HP',                    'w_hp_max',   10),
    ('situational_awareness', 75,  '',                   'Situational Awareness: +1 stamina max',    'w_stam_max',  1),
    ('i_work_out',           100,  'situational_awareness', 'I Work Out: +1 defense, +1 stam max',  'w_stam_max',  1),
    ('tough_guy',            250,  'i_work_out',         'Tough Guy: +10 HP, +2 stam max',          'w_hp_max',   10),
    ('knows_end',             50,  '',                   'Knows Which End Hurts: +1 agg max',       'w_agg_max',   1),
    ('self_defense',         100,  'knows_end',          'Self Defense Training: +1 stam max',      'w_stam_max',  1),
    ('slashing',             150,  'knows_end',          'Advanced Slashing: +1 agg max',           'w_agg_max',   1),
    ('power_operation',       50,  '',                   'Power Operation: +1 clarity max',         'w_clar_max',  1),
    ('touchpanel',           100,  'power_operation',    'Touchpanel Training: +1 clarity max',     'w_clar_max',  1),
    ('machine_spirit',       200,  'touchpanel',         'Machine Spirit: +5 max HP',               'w_hp_max',    5),
    ('improvisation',         50,  '',                   'Improvisation: grants IMPROVISE',         '',            0),
    ('crude_planning',       100,  '',                   'Crude Planning: faster crafting',         '',            0),
    ('better_materials',     150,  'crude_planning',     'Better Materials: grants PURIFY',         '',            0),
    ('crafter',              200,  'better_materials',   'Crafter: +1 success, grants STAMP',       '',            0),
    ('sightseer',             25,  '',                   'Sightseer: helps explore/discover',       '',            0),
    ('developing_obs',        75,  'sightseer',          'Developing Observation: better explore',  '',            0),
    ('terrain_details',      150,  'developing_obs',     'Terrain Details: grants SURVEY',          '',            0),
    ('cartographer',         250,  'terrain_details',    'Unpaid Cartographer: grants DISCOVER',    '',            0),
    ('first_aid',             50,  '',                   'First Aid: grants BANDAGE',               'w_hp_max',    2),
    ('pharmacy',             100,  'first_aid',          'Pharmacy: +5 max HP',                     'w_hp_max',    5),
    ('neurosurgeon',         150,  'pharmacy',           'Neurosurgeon: medical mastery',           '',            0),
    ('matrix_coder',          75,  '',                   'Matrix Coder: prereq for hacking',        '',            0),
    ('novice_hacker',         75,  'matrix_coder',       'Novice Hacker: +1 clarity max',           'w_clar_max',  1),
    ('lab_operation',        150,  '',                   'Lab Operation: research access',          '',            0),
    ('research_focus',       150,  '',                   'Research Focus: research bonus',          '',            0),
    ('driving',              100,  '',                   'Driving: operate land vehicles',         '',            0),
    ('flying',               100,  '',                   'Flying: operate aircraft',               '',            0),
]

SKILL_DEFS_MOO = '{' + ', '.join(
    f'{{{moo_str(sk[0])}, {sk[1]}, {moo_str(sk[2])}, {moo_str(sk[3])}, {moo_str(sk[4])}, {sk[5]}}}'
    for sk in SKILLS
) + '}'


def fix_learn(s):
    print('\n=== Checking learn verb ===')

    # Check current verb_info
    out = ev(s, f'verb_info(#{PLAYER}, "learn")')
    print(f'  Current verb_info: {out.strip()}')

    # Step 1: Change ownership to wizard using set_verb_info
    print('\n  Setting verb owner to wizard...')
    out = ev(s, f'set_verb_info(#{PLAYER}, "learn", {{#{WIZARD}, "rxd", "learn"}})')
    print(f'  set_verb_info result: {out.strip()}')

    # Verify ownership changed
    out = ev(s, f'verb_info(#{PLAYER}, "learn")')
    print(f'  New verb_info: {out.strip()}')

    # Step 2: Reprogram with full skill-buying code
    print('\n  Reprogramming learn verb...')
    program_verb(s, PLAYER, 'learn', [
        '"Spend SP to learn a skill. Usage: learn <skill_name>";',
        'skill = dobjstr;',
        'if (skill == "")',
        '  player:tell("Learn what? Type SKILLS to see the list.");',
        '  return;',
        'endif',
        f'skill_defs = {SKILL_DEFS_MOO};',
        'found = 0; cost = 0; prereq = ""; desc = ""; bprop = ""; bamt = 0;',
        'for def in (skill_defs)',
        '  if (def[1] == skill)',
        '    found = 1; cost = def[2]; prereq = def[3];',
        '    desc = def[4]; bprop = def[5]; bamt = def[6];',
        '    break;',
        '  endif',
        'endfor',
        'if (!found)',
        '  player:tell("Unknown skill: " + skill + ". Type SKILLS for the list.");',
        '  return;',
        'endif',
        'learned = player.w_learned;',
        'if (skill in learned)',
        '  player:tell("You already know " + skill + ".");',
        '  return;',
        'endif',
        'if (prereq != "" && !(prereq in learned))',
        '  player:tell("Requires " + prereq + " first.");',
        '  return;',
        'endif',
        'if (player.w_sp < cost)',
        '  player:tell("Not enough SP. Need " + tostr(cost) + ", have " + tostr(player.w_sp) + ".");',
        '  return;',
        'endif',
        'player.w_sp = player.w_sp - cost;',
        'player.w_learned = listappend(learned, skill);',
        'if (bprop == "w_hp_max")',
        '  player.w_hp_max = player.w_hp_max + bamt;',
        '  player.w_hp = player.w_hp + bamt;',
        'elseif (bprop == "w_stam_max")',
        '  player.w_stam_max = player.w_stam_max + bamt;',
        'elseif (bprop == "w_clar_max")',
        '  player.w_clar_max = player.w_clar_max + bamt;',
        'elseif (bprop == "w_agg_max")',
        '  player.w_agg_max = player.w_agg_max + bamt;',
        'endif',
        'player:tell("You learn: " + desc);',
        'player:tell("[SP remaining: " + tostr(player.w_sp) + "]");',
    ])

    # Verify final state
    out = ev(s, f'verb_info(#{PLAYER}, "learn")')
    print(f'  Final verb_info: {out.strip()}')

    # Quick test: set SP high and try learning sightseer
    print('\n  Setting w_sp=500 for test...')
    ev(s, f'#{PLAYER}.w_sp = 500')
    ev(s, f'#{PLAYER}.w_learned = {{}}')
    print('  Test: learn sightseer')
    out = send(s, 'learn sightseer')
    print(f'  Result: {out.strip()}')

    out = ev(s, f'#{PLAYER}.w_sp')
    print(f'  w_sp after learn: {out.strip()} (should be 475)')

    out = ev(s, f'#{PLAYER}.w_learned')
    print(f'  w_learned: {out.strip()} (should include sightseer)')


def main():
    s = connect()
    fix_learn(s)
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
