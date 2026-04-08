#!/usr/bin/env python3
"""
Wayfar 1444 — Phase 10: NPC Workers (Redesign E)

Adds:
  1. $npc_worker prototype — colonial worker with w_job/w_owner/w_last_tick
  2. $worker_list global on #0 — all active workers (ticks even for offline players)
  3. hire <job> verb — hire a worker in your factorium (100 cr, max 3)
  4. fire <job> verb — fire a worker in your factorium
  5. workers verb — list your colony's workforce
  6. Extended #545:tick — processes $worker_list, deposits items every 5 min

Run with server live: python3 phase10_workers.py
"""

import socket, time, re, sys

HOST = 'localhost'
PORT = 7777
PLAYER = 6
HEARTBEAT = 545   # survival monitor

def connect():
    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(5)
    time.sleep(0.5); s.recv(65536)
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8); s.recv(65536)
    return s

def send(s, cmd, wait=0.7):
    s.sendall((cmd + '\r\n').encode()); time.sleep(wait)
    out = b''; deadline = time.time() + max(wait + 0.3, 0.35)
    try:
        while time.time() < deadline:
            chunk = s.recv(65536)
            if not chunk: break
            out += chunk
    except: pass
    return re.sub(r'\x1b\[[0-9;]*m', '', out.decode('utf-8', errors='replace'))

def ev(s, e, wait=0.7): return send(s, '; ' + e, wait)

def program_verb(s, obj_expr, verbname, code_lines):
    out = send(s, f'@program {obj_expr}:{verbname}', wait=1.5)
    if 'programming' not in out.lower():
        print(f'  ERROR @program {obj_expr}:{verbname}: {repr(out[:150])}')
        return False
    old = s.gettimeout(); s.settimeout(0.5)
    for i, line in enumerate(code_lines):
        send(s, line, wait=0.08)
        if i % 15 == 14:
            print(f'    ... {i+1}/{len(code_lines)}')
    s.settimeout(old)
    result = send(s, '.', wait=5.0)
    if re.search(r'[1-9]\d* error', result):
        print(f'  CODE ERROR {obj_expr}:{verbname}:\n{result[:400]}')
        return False
    print(f'  OK: {obj_expr}:{verbname}')
    return True

def add_verb(s, obj_expr, verbname, args='none none none'):
    out = send(s, f'@verb {obj_expr}:{verbname} {args}', wait=0.6)
    if 'Verb added' not in out and 'already defined' not in out.lower():
        print(f'  WARN @verb {obj_expr}:{verbname}: {repr(out[:80])}')

def extract_num(out):
    """Extract OBJNUM=# tagged output."""
    m = re.search(r'OBJNUM=#(\d+)', out)
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# hire verb — must be in factorium; 100 cr; max 3 workers; valid jobs
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Updated sell verb — sells from inventory; in factorium also sells room items
# ─────────────────────────────────────────────────────────────────────────────

SELL_VERB = [
    '"Sell items to the Central Administrative Complex for credits.";',
    '"Usage: sell <item name> | sell all";',
    'p = player;',
    'query = typeof(dobjstr) == STR ? dobjstr | "";',
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
    '"Build sell list from inventory";',
    'sell_list = {};',
    'if (query == "all" || query == "resources")',
    '  for itm in (p.contents)',
    '    sell_list = listappend(sell_list, itm);',
    '  endfor',
    '  "If in own factorium, also sell room items";',
    '  loc = p.location;',
    '  if ("labor_cd" in properties(loc))',
    '    if ("sc_owner" in properties(loc) && loc.sc_owner == p)',
    '      for itm in (loc.contents)',
    '        if (itm != p && !is_a(itm, $npc_worker))',
    '          sell_list = listappend(sell_list, itm);',
    '        endif',
    '      endfor',
    '    endif',
    '  endif',
    'else',
    '  for itm in (p.contents)',
    '    nm = "";',
    '    try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '    if (index(nm, query))',
    '      sell_list = listappend(sell_list, itm);',
    '    endif',
    '  endfor',
    '  "If in own factorium, also search room";',
    '  loc = p.location;',
    '  if ("labor_cd" in properties(loc))',
    '    if ("sc_owner" in properties(loc) && loc.sc_owner == p)',
    '      for itm in (loc.contents)',
    '        if (itm != p && !is_a(itm, $npc_worker))',
    '          nm = "";',
    '          try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '          if (index(nm, query))',
    '            sell_list = listappend(sell_list, itm);',
    '          endif',
    '        endif',
    '      endfor',
    '    endif',
    '  endif',
    'endif',
    'if (sell_list == {})',
    '  p:tell("You\'re not carrying \'" + query + "\'.");',
    '  return;',
    'endif',
    'is_scav = p.w_background == "scavenger";',
    'has_com1 = "commerce_1" in p.w_learned;',
    'has_com2 = "commerce_2" in p.w_learned;',
    'total = 0;',
    'sold = 0;',
    'for itm in (sell_list)',
    '  nm = "";',
    '  try nm = tostr(itm.name); except e (ANY) nm = ""; endtry',
    '  price = 0;',
    '  if (index(nm, "ore") || index(nm, "mineral"))',
    '    price = has_com2 ? 10 | 5;',
    '  elseif (index(nm, "fiber") || index(nm, "plant"))',
    '    price = 3;',
    '  elseif (index(nm, "water sample") || index(nm, "raw water"))',
    '    price = 2;',
    '  elseif (index(nm, "salvage") || index(nm, "scrap") || index(nm, "wreckage"))',
    '    base = is_scav ? 6 | 4;',
    '    price = has_com2 ? base * 2 | base;',
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
    '    if (has_com1)',
    '      price = price + 1;',
    '    endif',
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


HIRE_VERB = [
    '"Hire a colonial worker. Usage: hire <ore|fiber|water|salvage>. Must be in factorium.";',
    'p = player;',
    'loc = p.location;',
    '"Must be in a factorium";',
    'if (!("labor_cd" in properties(loc)))',
    '  p:tell("You can only hire workers from inside your Factorium.");',
    '  return;',
    'endif',
    '"Must own this factorium";',
    'if ("sc_owner" in properties(loc) && loc.sc_owner != p)',
    '  p:tell("This is not your factorium.");',
    '  return;',
    'endif',
    '"Parse job type";',
    'job = "";',
    'if (typeof(dobjstr) == STR && dobjstr != "")',
    '  job = dobjstr;',
    'elseif (args != {})',
    '  job = args[1];',
    'endif',
    'valid_jobs = {"ore", "fiber", "water", "salvage"};',
    'if (!(job in valid_jobs))',
    '  p:tell("Valid jobs: ore, fiber, water, salvage");',
    '  p:tell("Usage: hire <job>");',
    '  return;',
    'endif',
    '"Check max workers (3 per factorium)";',
    'worker_count = 0;',
    'for itm in (loc.contents)',
    '  if (is_a(itm, $npc_worker))',
    '    worker_count = worker_count + 1;',
    '  endif',
    'endfor',
    'if (worker_count >= 3)',
    '  p:tell("Your factorium is at capacity (3 workers max). Fire one first.");',
    '  return;',
    'endif',
    '"Check cost";',
    'cost = 100;',
    'if (p.w_credits < cost)',
    '  p:tell("Hiring costs " + tostr(cost) + " cr. You have: " + tostr(p.w_credits) + " cr.");',
    '  return;',
    'endif',
    '"Create worker";',
    'w = create($npc_worker);',
    'w.name = "colonial worker (" + job + ")";',
    'w.description = "A hired colonist assigned to gather " + job + " from the surrounding terrain.";',
    'w.w_job = job;',
    'w.w_owner = p;',
    'w.w_last_tick = time();',
    'move(w, loc);',
    '"Add to global worker list";',
    '$worker_list = listappend($worker_list, w);',
    '"Deduct credits";',
    'p.w_credits = p.w_credits - cost;',
    'p:tell("You hire a " + job + " gatherer. [-" + tostr(cost) + " cr | Balance: " + tostr(p.w_credits) + " cr]");',
    'p:tell("Workers gather resources every 5 minutes and deposit them here.");',
    'loc:announce(p.name + " hires a colonial worker.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# fire verb — must be in factorium; fire by job type
# ─────────────────────────────────────────────────────────────────────────────

FIRE_VERB = [
    '"Fire a colonial worker. Usage: fire <ore|fiber|water|salvage>. Must be in factorium.";',
    'p = player;',
    'loc = p.location;',
    'if (!("labor_cd" in properties(loc)))',
    '  p:tell("You can only fire workers from inside your Factorium.");',
    '  return;',
    'endif',
    'if ("sc_owner" in properties(loc) && loc.sc_owner != p)',
    '  p:tell("This is not your factorium.");',
    '  return;',
    'endif',
    '"Parse target";',
    'target_job = "";',
    'if (typeof(dobjstr) == STR && dobjstr != "")',
    '  target_job = dobjstr;',
    'elseif (args != {})',
    '  target_job = args[1];',
    'endif',
    '"Find worker matching job (or first worker if no job given)";',
    'found = 0;',
    'for itm in (loc.contents)',
    '  if (is_a(itm, $npc_worker))',
    '    if (target_job == "" || itm.w_job == target_job)',
    '      found = itm;',
    '      break;',
    '    endif',
    '  endif',
    'endfor',
    'if (found == 0)',
    '  if (target_job == "")',
    '    p:tell("No workers here to fire. Use: fire <ore|fiber|water|salvage>");',
    '  else',
    '    p:tell("No " + target_job + " worker found here.");',
    '  endif',
    '  return;',
    'endif',
    '"Remove from global list and recycle";',
    '$worker_list = setremove($worker_list, found);',
    'jname = found.w_job;',
    'recycle(found);',
    'p:tell("You dismiss the " + jname + " gatherer.");',
    'loc:announce(p.name + " dismisses a colonial worker.", p);',
]


# ─────────────────────────────────────────────────────────────────────────────
# workers verb — show your colony workforce
# ─────────────────────────────────────────────────────────────────────────────

WORKERS_VERB = [
    '"Show your colony workforce. Works from anywhere.";',
    'p = player;',
    'if (!valid(p.w_colony))',
    '  p:tell("You have no colony. Place a sector center first.");',
    '  return;',
    'endif',
    'plaza = p.w_colony;',
    'fact = $nothing;',
    'if ("south_exit" in properties(plaza) && valid(plaza.south_exit))',
    '  fact = plaza.south_exit;',
    'endif',
    'if (!valid(fact))',
    '  p:tell("Your colony has no factorium.");',
    '  return;',
    'endif',
    'workers = {};',
    'for itm in (fact.contents)',
    '  if (is_a(itm, $npc_worker))',
    '    workers = listappend(workers, itm);',
    '  endif',
    'endfor',
    'p:tell("=== " + plaza.name + " — WORKFORCE ===");',
    'if (workers == {})',
    '  p:tell("  No workers hired. Go to your Factorium and type: hire <ore|fiber|water|salvage>");',
    '  p:tell("  Cost: 100 cr each | Max: 3 workers | Gathers every 5 min");',
    '  return;',
    'endif',
    'now = time();',
    'for w in (workers)',
    '  elapsed = now - w.w_last_tick;',
    '  next_in = 300 - elapsed;',
    '  if (next_in < 0) next_in = 0; endif',
    '  p:tell("  [" + w.w_job + "] next gather in " + tostr(next_in) + "s");',
    'endfor',
    'items_here = {};',
    'for itm in (fact.contents)',
    '  if (!is_a(itm, $npc_worker))',
    '    items_here = listappend(items_here, itm.name);',
    '  endif',
    'endfor',
    'if (items_here != {})',
    '  p:tell("  Stockpile: " + tostr(length(items_here)) + "/50 item(s) in factorium");',
    '  p:tell("  (Go to factorium, then \'sell all\' to cash in)");',
    'endif',
]


# ─────────────────────────────────────────────────────────────────────────────
# Extended #545:tick — add worker processing at end
# ─────────────────────────────────────────────────────────────────────────────

TICK_VERB_EXTENDED = [
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
    '    p.hunger = 20;',
    '    p.health = 30;',
    '    p.stamina = 50;',
    '    p:tell("");',
    '    p:tell("*** YOU HAVE DIED ***");',
    '    p:tell("Starvation claimed you. You wake at the crash site, barely alive.");',
    '    p:tell("");',
    '    move(p, #459);',
    '    p.location:announce(p.name + " crawls back from the brink of death.", p);',
    '  endif',
    'endfor',
    '"--- NPC idle chatter ---";',
    'this:npc_idle();',
    '"--- Worker tick: deposit gathered resources (cap 50 items per factorium) ---";',
    'now = time();',
    'clean_list = {};',
    'for w in ($worker_list)',
    '  if (!valid(w))',
    '    "Skip recycled workers — will not be added to clean_list";',
    '  else',
    '    clean_list = listappend(clean_list, w);',
    '    if ((now - w.w_last_tick) >= 300)',
    '      w.w_last_tick = now;',
    '      "Check stockpile cap: count non-worker items in factorium";',
    '      stock_count = 0;',
    '      for c in (w.location.contents)',
    '        if (!is_a(c, $npc_worker))',
    '          stock_count = stock_count + 1;',
    '        endif',
    '      endfor',
    '      if (stock_count >= 50)',
    '        "Stockpile full — skip production, notify owner";',
    '        owner = w.w_owner;',
    '        if (valid(owner) && (owner in connected_players()))',
    '          owner:tell("[COLONY] Factorium stockpile full (50 items). Sell or collect resources.");',
    '        endif',
    '      else',
    '        "Produce item based on job";',
    '        job = w.w_job;',
    '        iname = "ore sample";',
    '        idesc = "A rough chunk of alien mineral ore.";',
    '        if (job == "fiber")',
    '          iname = "fiber bundle";',
    '          idesc = "A bundle of dried alien plant fiber.";',
    '        elseif (job == "water")',
    '          iname = "water sample";',
    '          idesc = "A sealed flask of filtered water.";',
    '        elseif (job == "salvage")',
    '          iname = "salvage scrap";',
    '          idesc = "Twisted metal and polymer pulled from ruins.";',
    '        endif',
    '        item = create($thing);',
    '        item.name = iname;',
    '        item.description = idesc;',
    '        move(item, w.location);',
    '        "Notify owner if connected";',
    '        owner = w.w_owner;',
    '        if (valid(owner) && (owner in connected_players()))',
    '          owner:tell("[COLONY] Your " + job + " gatherer deposited a " + iname + " in the factorium.");',
    '        endif',
    '      endif',
    '    endif',
    '  endif',
    'endfor',
    '$worker_list = clean_list;',
    '"--- re-schedule in 300 seconds (5 min) ---";',
    'fork (300)',
    '  this:tick();',
    'endfork',
]


def main():
    s = connect()

    # ── 1. Create $npc_worker prototype via temp verb ─────────────────────────
    print('=== Create $npc_worker prototype ===')
    # Check if already set up (npc_worker property exists on #0 AND points to valid obj)
    out = ev(s, 'player:tell("NW_EXISTS=" + tostr("npc_worker" in properties(#0)))', wait=0.7)
    nw_exists = '1' in out.strip()[-10:]
    npc_num = None
    if nw_exists:
        out2 = ev(s, 'player:tell("OBJNUM=" + tostr(#0.npc_worker))', wait=0.7)
        existing = extract_num(out2)
        if existing and existing > 0:
            npc_num = existing
            print(f'  $npc_worker already exists: #{npc_num}')
    if npc_num is None:
        # Use a temp verb to create the prototype and return its number
        add_verb(s, f'#{PLAYER}', '"_nw_setup"', 'none none none')
        program_verb(s, f'#{PLAYER}', '_nw_setup', [
            '"Create $npc_worker prototype and register on #0.";',
            'if (!("npc_worker" in properties(#0)))',
            '  add_property(#0, "npc_worker", $nothing, {player, "rw"});',
            'endif',
            'if (!valid(#0.npc_worker))',
            '  nw = create($thing);',
            '  nw.name = "npc_worker prototype";',
            '  add_property(nw, "w_job", "ore", {player, "rw"});',
            '  add_property(nw, "w_owner", $nothing, {player, "rw"});',
            '  add_property(nw, "w_last_tick", 0, {player, "rw"});',
            '  #0.npc_worker = nw;',
            'endif',
            'player:tell("OBJNUM=" + tostr(#0.npc_worker));',
        ])
        out3 = send(s, '_nw_setup', wait=3.0)
        npc_num = extract_num(out3)
        if not npc_num:
            print(f'  ERROR creating $npc_worker: {repr(out3[-120:])}')
            s.close(); return
        print(f'  $npc_worker = #{npc_num}')

    # ── 2. Create $worker_list global ────────────────────────────────────────
    print('\n=== Setup $worker_list on #0 ===')
    out = ev(s, 'player:tell("worker_list" in properties(#0))', wait=0.7)
    if '1' in out.strip()[-5:]:
        print('  $worker_list already exists')
    else:
        ev(s, 'add_property(#0, "worker_list", {}, {wizard, "rw"})', wait=0.8)
        print(f'  Created $worker_list')

    # ── 3. hire verb ──────────────────────────────────────────────────────────
    print('\n=== hire verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"hire"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'hire', HIRE_VERB)

    # ── 4. fire verb ──────────────────────────────────────────────────────────
    print('\n=== fire verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"fire"', 'any none none')
    program_verb(s, f'#{PLAYER}', 'fire', FIRE_VERB)

    # ── 5. workers verb ───────────────────────────────────────────────────────
    print('\n=== workers verb on $player ===')
    add_verb(s, f'#{PLAYER}', '"workers"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'workers', WORKERS_VERB)

    # ── 6. Extend #545:tick ───────────────────────────────────────────────────
    print('\n=== Extend #545:tick with worker processing ===')
    program_verb(s, f'#{HEARTBEAT}', 'tick', TICK_VERB_EXTENDED)

    # ── 6b. Update sell verb — sell from factorium room ───────────────────────
    print('\n=== Update sell verb (factorium support) ===')
    program_verb(s, f'#{PLAYER}', 'sell', SELL_VERB)

    # ── 6c. Clean up excess stockpile in existing factorium ──────────────────
    print('\n=== Clean up excess factorium stockpile ===')
    add_verb(s, f'#{PLAYER}', '"_cleanup_stock"', 'none none none')
    program_verb(s, f'#{PLAYER}', '_cleanup_stock', [
        '"Clean up excess items in factorium, keep max 50.";',
        'if (!valid(player.w_colony)) player:tell("No colony."); return; endif',
        'plaza = player.w_colony;',
        'if (!("south_exit" in properties(plaza))) return; endif',
        'fact = plaza.south_exit;',
        'if (!valid(fact)) return; endif',
        'items = {};',
        'for itm in (fact.contents)',
        '  if (!is_a(itm, $npc_worker) && itm != player)',
        '    items = listappend(items, itm);',
        '  endif',
        'endfor',
        'excess = length(items) - 50;',
        'if (excess <= 0)',
        '  player:tell("Stockpile OK (" + tostr(length(items)) + " items, cap 50).");',
        '  return;',
        'endif',
        'player:tell("Recycling " + tostr(excess) + " excess items (keeping 50)...");',
        'for i in [1..excess]',
        '  recycle(items[i]);',
        'endfor',
        'player:tell("Done. Factorium now has 50 items.");',
    ])
    out = send(s, '_cleanup_stock', wait=10.0)
    print(out.strip()[-200:])

    # ── 7. Test ───────────────────────────────────────────────────────────────
    print('\n=== Test workers ===')
    add_verb(s, f'#{PLAYER}', '"worker_test"', 'none none none')
    program_verb(s, f'#{PLAYER}', 'worker_test', [
        '"Test NPC worker hire/fire/tick.";',
        'p = player;',
        'p:tell("=== WORKER_TEST BEGIN ===");',
        '"Setup: clear any existing colony, create fresh one";',
        'for itm in (player.location.contents)',
        '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
        '    recycle(itm);',
        '  endif',
        'endfor',
        'if (valid(player.w_colony))',
        '  old_plaza = player.w_colony;',
        '  if ("east_exit" in properties(old_plaza))',
        '    old_gov = old_plaza.east_exit; if (valid(old_gov)) recycle(old_gov); endif',
        '  endif',
        '  if ("south_exit" in properties(old_plaza))',
        '    old_fact = old_plaza.south_exit; if (valid(old_fact)) recycle(old_fact); endif',
        '  endif',
        '  recycle(old_plaza);',
        '  player.w_colony = $nothing;',
        'endif',
        '"Also clear stale workers from $worker_list";',
        'clean = {};',
        'for w in ($worker_list)',
        '  if (valid(w)) clean = listappend(clean, w); endif',
        'endfor',
        '$worker_list = clean;',
        '"Build colony";',
        'm1 = create($thing); m1.name = "inert metal"; move(m1, player);',
        'm2 = create($thing); m2.name = "inert metal"; move(m2, player);',
        'w1 = create($thing); w1.name = "crude wire"; move(w1, player);',
        'w2 = create($thing); w2.name = "crude wire"; move(w2, player);',
        'this:craft("sector", "center");',
        'this:place("sector", "center");',
        'p:tell("  Colony: " + player.location.name);',
        '"Go to factorium";',
        'this:s();',
        'p:tell("  In factorium: " + player.location.name);',
        '"Give ourselves credits";',
        'old_cr = player.w_credits;',
        'player.w_credits = 500;',
        '"Hire ore worker";',
        'this:hire("ore");',
        'p:tell("  After hire: " + tostr(player.w_credits) + " cr (expect 400)");',
        '"Check workers";',
        'wcount = 0;',
        'for itm in (player.location.contents)',
        '  if (is_a(itm, $npc_worker))',
        '    wcount = wcount + 1;',
        '    p:tell("  Worker found: " + itm.name + " job=" + itm.w_job);',
        '  endif',
        'endfor',
        'p:tell("  Worker count: " + tostr(wcount) + " (expect 1)");',
        'p:tell("  $worker_list size: " + tostr(length($worker_list)));',
        '"Simulate tick by backdating w_last_tick";',
        'for w in (player.location.contents)',
        '  if (is_a(w, $npc_worker))',
        '    w.w_last_tick = time() - 301;',
        '  endif',
        'endfor',
        '"Run tick manually";',
        '#545:tick_now();',
        '"Check factorium for deposited item";',
        'items_found = {};',
        'for itm in (player.location.contents)',
        '  if (!is_a(itm, $npc_worker))',
        '    items_found = listappend(items_found, itm.name);',
        '  endif',
        'endfor',
        'p:tell("  Items in factorium: " + tostr(items_found) + " (expect ore sample)");',
        '"Test workers verb (from factorium)";',
        'this:out(); this:out();',
        'p:tell("  Location after out+out: " + player.location.name);',
        'this:workers();',
        '"Test fire verb";',
        'this:colony();',
        'this:s();',
        'this:fire("ore");',
        'wcount2 = 0;',
        'for itm in (player.location.contents)',
        '  if (is_a(itm, $npc_worker)) wcount2 = wcount2 + 1; endif',
        'endfor',
        'p:tell("  After fire, worker count: " + tostr(wcount2) + " (expect 0)");',
        '"Cleanup colony";',
        'this:out();',
        'old_plaza2 = player.w_colony;',
        'if (valid(old_plaza2))',
        '  og = old_plaza2.east_exit; of = old_plaza2.south_exit;',
        '  if (valid(og)) recycle(og); endif',
        '  if (valid(of))',
        '    for itm in (of.contents)',
        '      recycle(itm);',
        '    endfor',
        '    recycle(of);',
        '  endif',
        '  recycle(old_plaza2);',
        '  player.w_colony = $nothing;',
        'endif',
        'for itm in (player.location.contents)',
        '  if (is_a(itm, $building) && "sc_plaza" in properties(itm))',
        '    recycle(itm);',
        '  endif',
        'endfor',
        'player.w_credits = old_cr;',
        'p:tell("=== WORKER_TEST END ===");',
    ])

    # Add tick_now verb that runs tick immediately (for testing)
    add_verb(s, f'#{HEARTBEAT}', '"tick_now"', 'none none none')
    program_verb(s, f'#{HEARTBEAT}', 'tick_now', [
        '"Run tick immediately (test/debug only).";',
        'set_task_perms(this.owner);',
        '"--- Worker tick ---";',
        'now = time();',
        'clean_list = {};',
        'for w in ($worker_list)',
        '  if (!valid(w))',
        '    "skip";',
        '  else',
        '    clean_list = listappend(clean_list, w);',
        '    if ((now - w.w_last_tick) >= 300)',
        '      w.w_last_tick = now;',
        '      "Check stockpile cap";',
        '      stock_count = 0;',
        '      for c in (w.location.contents)',
        '        if (!is_a(c, $npc_worker))',
        '          stock_count = stock_count + 1;',
        '        endif',
        '      endfor',
        '      if (stock_count >= 50)',
        '        "Stockpile full";',
        '      else',
        '        job = w.w_job;',
        '        iname = "ore sample";',
        '        idesc = "A rough chunk of alien mineral ore.";',
        '        if (job == "fiber")',
        '          iname = "fiber bundle";',
        '          idesc = "A bundle of dried alien plant fiber.";',
        '        elseif (job == "water")',
        '          iname = "water sample";',
        '          idesc = "A sealed flask of filtered water.";',
        '        elseif (job == "salvage")',
        '          iname = "salvage scrap";',
        '          idesc = "Twisted metal and polymer pulled from ruins.";',
        '        endif',
        '        item = create($thing);',
        '        item.name = iname;',
        '        item.description = idesc;',
        '        move(item, w.location);',
        '        owner = w.w_owner;',
        '        if (valid(owner) && (owner in connected_players()))',
        '          owner:tell("[COLONY] Your " + job + " gatherer deposited a " + iname + " in the factorium.");',
        '        endif',
        '      endif',
        '    endif',
        '  endif',
        'endfor',
        '$worker_list = clean_list;',
        'player:tell("tick_now done. worker_list size: " + tostr(length($worker_list)));',
    ])

    out = send(s, 'worker_test', wait=20.0)
    print(out.strip())

    # Save
    out = send(s, '@dump-database', wait=3.0)
    print(f'\nSave: {out.strip()[:60]}')
    s.close()
    print('\nDone.')


if __name__ == '__main__':
    main()
