# Wayfar 1444 — TODO

## In Progress / Next Up

- [ ] **#2** Player stats — hunger/health/stamina properties, heartbeat decay, `status` command, death + respawn
- [ ] **#3** Food/water consumables — gathered resources → eat/drink verbs restore stats

## Planned

- [ ] **#4** Test/fix CHATNET/CHAT comms (verbs exist on $player but untested)
- [ ] **#5** Building system — craft structures from materials, place at coordinates, persist in room
- [ ] **#6** NPCs/creatures — colony citizens gather autonomously, hostile fauna roam and attack
- [ ] **#7** Second planet — Xeris Prime (icy mining world), launch pad travel between planets
- [ ] **#8** Skill trees — hunter, pilot, botanist, hacker, engineer; XP from activities
- [ ] **#9** Dice pool combat — turn-based, stats feed into rolls, loot on kill
- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise (cosmetic)

## Completed

- [x] Resource nodes — `$ods:populate` creates typed nodes in new rooms; `gather [type]` works in all wilderness rooms and Impact Site Zero
- [x] Player survival stats — hunger/health/stamina on $player with vitals/eat/drink/rest/build/treat/status verbs
- [x] Perlin noise C extension (`perlin_2d`)
- [x] `chr()` / `ord()` C extensions
- [x] On-demand room spawning via `$ods` (#458)
- [x] Coordinate-based movement (n/s/e/w on $player #6)
- [x] ANSI 7x5 overhead map (`look_self` on $wroom #452)
- [x] 5-biome terrain system on Kepler-7 (#457)
- [x] Impact Site Zero crash site at (0,0)
- [x] Resource node prototypes ($ore_node, $fiber_node, $water_node, $salvage_node)
- [x] Fix duplicate movement verb render (removed explicit `look_self` call — enterfunc handles it)
- [x] Fix planet name showing `[]` in room headers
