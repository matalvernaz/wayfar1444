#!/usr/bin/env python3
"""Reprogram the LEARN verb on $player (#6) - ownership already fixed."""

import socket, time, re

HOST = 'localhost'
PORT = 7777
PLAYER = 6


def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(4)
    time.sleep(0.5)
    s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8)
    s.recv(65536)
    return s


def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode())
    time.sleep(wait)
    out = b''
    deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))


def ev(s, expr, wait=0.6):
    return send(s, f'; {expr}', wait=wait)


def moo_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


SKILLS = [
    ('heavy_tan',             75,  '',                   'Heavy Tan: +10 max HP',                 'w_hp_max',   10),
    ('situational_awareness', 75,  '',                   'Situational Awareness: +1 stamina max', 'w_stam_max',  1),
    ('i_work_out',           100,  'situational_awareness', 'I Work Out: +1 stam max',           'w_stam_max',  1),
    ('tough_guy',            250,  'i_work_out',         'Tough Guy: +10 HP, +2 stam max',       'w_hp_max',   10),
    ('knows_end',             50,  '',                   'Knows Which End Hurts: +1 agg max',    'w_agg_max',   1),
    ('self_defense',         100,  'knows_end',          'Self Defense: +1 stam max',            'w_stam_max',  1),
    ('slashing',             150,  'knows_end',          'Advanced Slashing: +1 agg max',        'w_agg_max',   1),
    ('power_operation',       50,  '',                   'Power Operation: +1 clarity max',      'w_clar_max',  1),
    ('touchpanel',           100,  'power_operation',    'Touchpanel Training: +1 clar max',     'w_clar_max',  1),
    ('machine_spirit',       200,  'touchpanel',         'Machine Spirit: +5 max HP',            'w_hp_max',    5),
    ('improvisation',         50,  '',                   'Improvisation: grants IMPROVISE',      '',            0),
    ('crude_planning',       100,  '',                   'Crude Planning: faster crafting',      '',            0),
    ('better_materials',     150,  'crude_planning',     'Better Materials: grants PURIFY',      '',            0),
    ('crafter',              200,  'better_materials',   'Crafter: +1 success, grants STAMP',    '',            0),
    ('sightseer',             25,  '',                   'Sightseer: helps explore/discover',    '',            0),
    ('developing_obs',        75,  'sightseer',          'Developing Obs: better explore',       '',            0),
    ('terrain_details',      150,  'developing_obs',     'Terrain Details: grants SURVEY',       '',            0),
    ('cartographer',         250,  'terrain_details',    'Cartographer: grants DISCOVER',        '',            0),
    ('first_aid',             50,  '',                   'First Aid: grants BANDAGE',            'w_hp_max',    2),
    ('pharmacy',             100,  'first_aid',          'Pharmacy: +5 max HP',                  'w_hp_max',    5),
    ('neurosurgeon',         150,  'pharmacy',           'Neurosurgeon: medical mastery',        '',            0),
    ('matrix_coder',          75,  '',                   'Matrix Coder: prereq for hacking',     '',            0),
    ('novice_hacker',         75,  'matrix_coder',       'Novice Hacker: +1 clarity max',        'w_clar_max',  1),
    ('lab_operation',        150,  '',                   'Lab Operation: research access',       '',            0),
    ('research_focus',       150,  '',                   'Research Focus: research bonus',       '',            0),
    ('driving',              100,  '',                   'Driving: operate land vehicles',      '',            0),
    ('flying',               100,  '',                   'Flying: operate aircraft',            '',            0),
]

def skill_defs_lines(skills):
    """Return list of MOO assignment lines that build skill_defs in chunks of 9."""
    chunk_size = 9
    chunks = [skills[i:i+chunk_size] for i in range(0, len(skills), chunk_size)]
    lines = []
    chunk_vars = []
    for ci, chunk in enumerate(chunks):
        var = f'_sd{ci}'
        chunk_vars.append(var)
        entries = ', '.join(
            f'{{{moo_str(sk[0])}, {sk[1]}, {moo_str(sk[2])}, {moo_str(sk[3])}, {moo_str(sk[4])}, {sk[5]}}}'
            for sk in chunk
        )
        lines.append(f'{var} = {{{entries}}};')
    # splice all chunks into skill_defs
    splice = ', '.join(f'@{v}' for v in chunk_vars)
    lines.append(f'skill_defs = {{{splice}}};')
    return lines


def main():
    s = connect()

    print('verb_info before:', ev(s, f'verb_info(#{PLAYER}, "learn")').strip())

    # Enter @program mode
    print('Entering @program mode...')
    out = send(s, f'@program #{PLAYER}:learn', wait=1.0)
    if 'programming' not in out.lower():
        print(f'ERROR: {repr(out[:200])}')
        s.close()
        return
    print('  In programming mode.')

    lines = [
        '"Spend SP to learn a skill. Usage: learn <skill_name>";',
        'skill = dobjstr;',
        'if (skill == "")',
        '  player:tell("Learn what? Type SKILLS to see the list.");',
        '  return;',
        'endif',
        *skill_defs_lines(SKILLS),
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
    ]

    # Send lines with slight delay to avoid pipe issues
    old_timeout = s.gettimeout()
    s.settimeout(0.3)
    for i, line in enumerate(lines):
        try:
            send(s, line, wait=0.06)
            if i % 10 == 9:
                print(f'  ... sent {i+1}/{len(lines)} lines')
        except Exception as e:
            print(f'  Error at line {i}: {e}')
            s.close()
            return

    s.settimeout(old_timeout)
    print('  Sending "." to compile...')
    result = send(s, '.', wait=3.0)

    if re.search(r'[1-9]\d* error', result):
        print('CODE ERRORS:')
        print(result[:1000])
    else:
        print('  Compiled OK')
        # Find the "0 errors" or similar
        m = re.search(r'\d+ error', result)
        if m:
            print(f'  {m.group()}')

    # Test it
    print('\nTesting learn verb...')
    ev(s, f'#{PLAYER}.w_sp = 500')
    ev(s, f'#{PLAYER}.w_learned = {{}}')
    out = send(s, 'learn sightseer', wait=1.0)
    print(f'learn sightseer => {out.strip()}')

    sp_after = ev(s, f'#{PLAYER}.w_sp').strip()
    learned = ev(s, f'#{PLAYER}.w_learned').strip()
    print(f'w_sp: {sp_after} (expect ~475)')
    print(f'w_learned: {learned}')

    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
