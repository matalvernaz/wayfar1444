#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 6: CAC Economy

Adds:
  1. w_credits property on $player (#6) — default 0
  2. sell <item> / sell all — sell to CAC for credits anywhere (radio uplink)
  3. balance verb — show credit balance
  4. prices verb — show CAC buy rates
  5. Update status verb to include credits

Price table:
  Raw resources: ore 5cr, fiber 3cr, water sample 2cr, salvage 4cr
  Processed:     inert metal 15cr, crude wire 12cr
  Consumables:   ration bar 8cr, water canteen 6cr

Run with server live: python3 phase6_economy.py
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


def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.0)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj_expr}:{verbname}: {repr(out[:150])}')
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
        print(f'  CODE ERROR {obj_expr}:{verbname}:')
        print(result[:600])
        return False
    print(f'  OK: {obj_expr}:{verbname}')
    return True


def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}')


SELL_VERB = [
    '"Sell items to the Central Administrative Complex for credits.";',
    '"Usage: sell <item name> | sell all";',
    '"Selling is done via CAC radio uplink — works anywhere on the planet.";',
    'p = player;',
    'query = (typeof(dobjstr) == STR) ? dobjstr | "";',
    'if (query == "" && args != {})',
    '  for w in (args)',
    '    if (typeof(w) == STR)',
    '      query = query == "" ? w | query + " " + w;',
    '    endif',
    '  endfor',
    'endif',
    'if (query == "")',
    '  p:tell("Sell what? (sell <item> or sell all)");',
    '  p:tell("Type \'prices\' to see CAC buy rates.");',
    '  return;',
    'endif',
    '"Build sell list";',
    'sell_list = {};',
    'if (query == "all" || query == "resources")',
    '  for itm in (p.contents)',
    '    sell_list = listappend(sell_list, itm);',
    '  endfor',
    'else',
    '  for itm in (p.contents)',
    '    nm = "";',
    '    try',
    '      nm = tostr(itm.name);',
    '    except e (ANY)',
    '      nm = "";',
    '    endtry',
    '    if (index(nm, query))',
    '      sell_list = listappend(sell_list, itm);',
    '    endif',
    '  endfor',
    'endif',
    'if (sell_list == {})',
    '  p:tell("You\'re not carrying \'" + query + "\'.");',
    '  return;',
    'endif',
    '"Price lookup and sell";',
    'total = 0;',
    'sold = 0;',
    'for itm in (sell_list)',
    '  nm = "";',
    '  try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '  price = 0;',
    '  if (index(nm, "ore") || index(nm, "mineral"))',
    '    price = 5;',
    '  elseif (index(nm, "fiber") || index(nm, "plant"))',
    '    price = 3;',
    '  elseif (index(nm, "water sample") || index(nm, "raw water"))',
    '    price = 2;',
    '  elseif (index(nm, "salvage") || index(nm, "scrap") || index(nm, "wreckage"))',
    '    price = 4;',
    '  elseif (index(nm, "inert metal"))',
    '    price = 15;',
    '  elseif (index(nm, "crude wire"))',
    '    price = 12;',
    '  elseif (index(nm, "ration bar") || index(nm, "ration"))',
    '    price = 8;',
    '  elseif (index(nm, "canteen"))',
    '    price = 6;',
    '  endif',
    '  if (price > 0)',
    '    total = total + price;',
    '    sold = sold + 1;',
    '    recycle(itm);',
    '  endif',
    'endfor',
    'if (sold == 0)',
    '  p:tell("The CAC doesn\'t buy that. (Type \'prices\' to see what they buy.)");',
    '  return;',
    'endif',
    'p.w_credits = p.w_credits + total;',
    'p:tell("[CAC] Purchased " + tostr(sold) + " item(s) for " + tostr(total) + " cr.  Balance: " + tostr(p.w_credits) + " cr");',
]

BALANCE_VERB = [
    '"Show your CAC credit balance.";',
    'player:tell("Credit balance: " + tostr(player.w_credits) + " cr");',
]

PRICES_VERB = [
    '"Show current CAC resource buy rates.";',
    'p = player;',
    'p:tell("=== CAC BUY RATES (radio uplink) ===");',
    'p:tell("  Raw resources:");',
    'p:tell("    ore / mineral sample    5 cr");',
    'p:tell("    native fiber            3 cr");',
    'p:tell("    raw water sample        2 cr");',
    'p:tell("    salvage / scrap         4 cr");',
    'p:tell("  Processed materials:");',
    'p:tell("    inert metal            15 cr");',
    'p:tell("    crude wire             12 cr");',
    'p:tell("  Consumables:");',
    'p:tell("    ration bar              8 cr");',
    'p:tell("    water canteen           6 cr");',
    'p:tell("Usage: sell <item>  or  sell all");',
]

# Updated status verb that includes credits
STATUS_VERB = [
    '"Show player survival stats and credit balance.";',
    'p = player;',
    'loc = p.location;',
    'p:tell("=== STATUS ===");',
    '"HP";',
    'hpbar = "";',
    'hpfill = (p.w_hp * 10) / p.w_hp_max;',
    'for i in [1..10]',
    '  hpbar = hpbar + ((i <= hpfill) ? "#" | ".");',
    'endfor',
    'p:tell("  HP      : [" + hpbar + "] " + tostr(p.w_hp) + "/" + tostr(p.w_hp_max));',
    '"Stamina";',
    'stbar = "";',
    'stfill = (p.w_stam * 10) / p.w_stam_max;',
    'for i in [1..10]',
    '  stbar = stbar + ((i <= stfill) ? "#" | ".");',
    'endfor',
    'p:tell("  Stamina : [" + stbar + "] " + tostr(p.w_stam) + "/" + tostr(p.w_stam_max));',
    '"Hunger / nourished";',
    'if (p.w_nourished > time())',
    '  mins = (p.w_nourished - time()) / 60;',
    '  p:tell("  Nourished (" + tostr(mins) + " min remaining)");',
    'else',
    '  hunger = p.w_hp_max - p.w_hp;',
    '  if (hunger <= 0)',
    '    p:tell("  Hunger  : Well fed");',
    '  elseif (hunger < 20)',
    '    p:tell("  Hunger  : Peckish");',
    '  elseif (hunger < 40)',
    '    p:tell("  Hunger  : Hungry");',
    '  else',
    '    p:tell("  Hunger  : Starving!");',
    '  endif',
    'endif',
    '"Credits";',
    'p:tell("  Credits : " + tostr(p.w_credits) + " cr");',
    '"Location";',
    'if ("x" in properties(loc))',
    '  p:tell("  Coords  : (" + tostr(loc.x) + ", " + tostr(loc.y) + ")");',
    'endif',
]


def main():
    s = connect()

    # ── 1. Add w_credits property to $player ─────────────────────────────────
    print('=== Add w_credits to $player ===')
    # Check if already exists
    out = ev(s, 'player:tell("w_credits" in properties($player))', wait=0.7)
    if '1' in out.strip()[-20:]:
        print('  w_credits already exists')
    else:
        out = ev(s, 'add_property($player, "w_credits", 0, {player, "rw"})', wait=0.8)
        print(f'  add_property: {out.strip()[-60:]}')
        out = ev(s, 'player:tell("w_credits" in properties($player))', wait=0.7)
        print(f'  exists now: {out.strip()[-20:]}')

    # ── 2. sell verb ──────────────────────────────────────────────────────────
    print('\n=== sell verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"sell"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'sell', SELL_VERB)

    # ── 3. balance verb ───────────────────────────────────────────────────────
    print('\n=== balance verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"balance"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'balance', BALANCE_VERB)

    # ── 4. prices verb ────────────────────────────────────────────────────────
    print('\n=== prices verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"prices"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'prices', PRICES_VERB)

    # ── 5. Update status verb ─────────────────────────────────────────────────
    print('\n=== Update status verb on $player ===')
    program_verb(s, f'#{PLAYER}', 'status', STATUS_VERB)

    # ── 6. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test economy ===')
    program_verb(s, f'#{PLAYER}', 'econ_test', [
        '"Test: sell resources, check balance.";',
        'player:tell("=== ECON_TEST BEGIN ===");',
        '"Reset credits";',
        'player.w_credits = 0;',
        '"Give test items";',
        'o1 = create($thing); o1.name = "ore chunk"; move(o1, player);',
        'o2 = create($thing); o2.name = "ore chunk"; move(o2, player);',
        'f1 = create($thing); f1.name = "native fiber"; move(f1, player);',
        'w1 = create($thing); w1.name = "raw water sample"; move(w1, player);',
        'sc = create($thing); sc.name = "salvage fragment"; move(sc, player);',
        '"Show prices";',
        'this:prices();',
        'player:tell("---");',
        '"Sell all";',
        'this:sell("all");',
        'player:tell("  Expected: 2x ore(10) + 1x fiber(3) + 1x water(2) + 1x salvage(4) = 19 cr");',
        'player:tell("  Got: " + tostr(player.w_credits) + " cr");',
        '"Sell something not buyable";',
        'k = create($thing); k.name = "basic crafting tool"; move(k, player);',
        'this:sell("tool");',
        '"Test balance verb";',
        'this:balance();',
        '"Test status shows credits";',
        'this:status();',
        'player:tell("=== ECON_TEST END ===");',
        '"Cleanup";',
        'for itm in (player.contents)',
        '  if (itm.name == "basic crafting tool")',
        '    recycle(itm);',
        '  endif',
        'endfor',
    ])
    out = send(s, 'econ_test', wait=8.0)
    print(out.strip())

    # ── 7. Save ───────────────────────────────────────────────────────────────
    out = send(s, '@dump-database', wait=3.0)
    print(f'Save: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
