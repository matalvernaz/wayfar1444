# Wayfar 1444 — TODO

## In Progress / Next Up

- [ ] **Redesign B** Backgrounds/classes at character creation — pick background on first login, sets starting stats; store as `w_background`

## Planned

- [ ] **Redesign C** Skill system — `w_skills` dict, skill shop NPC, buy skills with credits, skills gate content
- [ ] **Redesign D** Per-player colonies — `place sector center` spawns 3-room complex (plaza + governor's office + factorium) owned by player
- [ ] **Redesign E** NPC workers — hire/fire colonists at sector center, auto-gather resources on a timer
- [ ] **#4** Test/fix CHATNET/CHAT comms (verbs exist on $player but untested)
- [ ] **#6** NPCs/creatures — colony citizens gather autonomously, hostile fauna roam and attack
- [ ] **#7** Second planet — Xeris Prime (icy mining world), launch pad travel between planets
- [ ] **#8** Skill trees — hunter, pilot, botanist, hacker, engineer; XP from activities
- [ ] **#9** Dice pool combat — turn-based, stats feed into rolls, loot on kill
- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise (cosmetic)
- [ ] **#6** NPCs/creatures — colony citizens gather autonomously, hostile fauna roam and attack
- [ ] **#7** Second planet — Xeris Prime (icy mining world), launch pad travel between planets
- [ ] **#8** Skill trees — hunter, pilot, botanist, hacker, engineer; XP from activities
- [ ] **#9** Dice pool combat — turn-based, stats feed into rolls, loot on kill
- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise (cosmetic)

## Completed

- [x] **Redesign A** CAC economy — `w_credits` on $player; `sell <item>` / `sell all` (radio uplink, works anywhere); `balance`; `prices`; `status` updated with credits + stamina bar
- [x] Building system — `pre-fab shelter kit` recipe (inert metal + 2x fiber); `place <kit>` deploys `$building` at current coords; `buildings` lists structures in room; $building prototype #117 with b_type/b_owner/b_hp/b_x/b_y props
- [x] Food/water consumables — craft (ration bar, water canteen), eat/drink restore HP+Nourished; HellCore !obj bug fixed
- [x] Resource nodes — `$ods:populate` creates typed nodes in new rooms; `gather [type]` works in all wilderness rooms and Impact Site Zero
- [x] Player survival stats — hunger/health/stamina on $player with vitals/eat/drink/rest/build/treat/status verbs
- [x] Heartbeat decay + death/respawn — #545 in Colony Hub; 5-min tick, starvation kills, respawn at #459 with hunger=20/health=30/stamina=50
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
