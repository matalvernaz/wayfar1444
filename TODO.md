# Wayfar 1444 — TODO
# Survival colonization: survive → establish → automate → colony → expand
# Ordered by what a player actually experiences

## Phase 1 — The Planet (architectural foundation)

- [x] **Planet generation** — `@create-planet <name> <size> <type>` wizard verb. Bounded coords, seed-based Perlin, planet type affects biome ratios (6 types). ODS with biome remapping. MAP BIOMES for wide area view. @list-planets wizard verb. CONFIG command with screenreader mode.
- [x] **Random landing** — dispatch picks random coords far from other colonies (min 15 tiles), avoids dangerous biomes and planet edges. LANDING command shows home coords + direction. Prevents double dispatch.
- [x] **Exploration** (#16) — `EXPLORE` fills room 0-100% with progress bar + skill bonuses. MEMORIZE/TRAVEL/UNMEMORIZE for fast travel (up to 20 spots). DISCOVER for artifacts/specimens/features (req Unpaid Cartographer). Trinket finds while exploring.
- [x] **Creatures** (#6) — biome-specific wildlife spawning. Carnivores (aggressive, attack on timer), herbivores (passive). 14 creature types across 7 biomes. CON to assess. Loot drops on death. Creature roaming AI. KILL/SWING/FIRE work on creatures. Heartbeat integration.

## Phase 2 — Survival Progression (first hours of gameplay)

- [x] **Early game polish** — GATHER (hand-gathering, slow, 1 unit, low quality), HELP (comprehensive command reference), TAC (tactical display), ST/STATUS (dice pools, hunger, SP/credits). Tool-gathering via HARVEST still better.
- [x] **Building display** — BUILDINGS command shows owned buildings with locations/HP. PLACE verb cleaned up with wilderness check. No artificial progression gates — crafting tools + materials are the natural gate. Building names cleaned (strips "kit" suffix).
- [x] **Item degradation** (#44) — weapons/tools lose durability on use. REPAIR command restores 25% per use. Examine shows condition (Good/Worn/Damaged/Nearly broken/BROKEN). SWING/FIRE degrade weapons on hit.
- [x] **Medical + status effects** (#31, #32) — BANDAGE (First Aid skill or bandage item), bleeding from creature attacks (30% chance, -2 HP/tick), burns from volcanic zones (-50% dice regen), disease from fungal zones (-1 HP/tick). EAT/DRINK commands with raw vs cooked food difference. Nourished buff from cooked food. Status effects on ST display.
- [x] **Communications** (#4) — WHO (player list with location/idle), CHAT (global chatnet), CHATNET HISTORY (last 50), PAGE (private DM), say (HellCore built-in). Players can talk.

## Phase 3 — Colony Building (hours 5-20 of gameplay)

- [x] **Refining** (#23) — 3 building types (refinery/organic processing/nuclear enrichment). MASSADD for bulk input, PROCESS to refine, RESET to clear. Building quality affects output quality (min-max rebuild loop). REFINERY status command with estimate.
- [ ] **Automated crafting** (#27) — engineering tool machines with input/output hoppers. Colony runs production without player input.
- [ ] **Governor's office** (#20) — colony management verbs: citizens, sectormap, construction rights, collection config, events log, rollcall.
- [ ] **Jobs** (#17) — ~30 repeatable achievements (FARMER, FACTORIUM LABOR, STRUCTURE CRAFTER, CENTER OF ATTENTION, PLANETARY HERO, etc.). Awards SP/credits. Drives progression.
- [ ] **Reroll/ascension** (#15) — complete background victory condition → reroll points. Lose skills/SP, keep buildings/inventory. SP cap +100 per reroll to 3500.
- [ ] **Blueprints** (#25) — discoverable recipes. `LOAD chip onto tool`. Found at pirate bases, discoveries. `lookup <thing> with datapad`.

## Phase 4 — The Wider World

- [ ] **Central Complex expansion** (#18) — full space station hub. Shops (smartpads, medical kits, ammo). Ship refueling. Link-up terminal for joining colonies.
- [ ] **Multi-planet** (#7) — different biome ratios per planet. Shuttle/drop pod travel. 5 solar systems (DSO-12 first). Different resource availability drives travel.
- [ ] **Vehicles** (#28) — q-cycle (no skill), land vehicles (Driving skill), aircraft (Flying). Vehicle assembly station.
- [ ] **Starships** (#29) — starship complex building, assembly tool. Ships = rooms (bridge/generator/turrets/engineering). Warp gates. Asteroid mining.
- [ ] **Farming** (#34) — seeding tool, farm plots, agricultural pod building. Landslide farming harvestor.
- [ ] **Fishing** (#37) — fishing gear, alien waters. CAREER ANGLER job.
- [ ] **Artifacts & research** (#38) — Laboratory building. Research q-locked items → relics, chips, equipment.

## Phase 5 — Advanced / Endgame

- [ ] **Hacking** (#26) — smartpads, HACK command, q-chip programs, outlaw status.
- [ ] **Robots** (#36) — micro-bot tool, robotic fabrication table, robot control.
- [ ] **Factions** (#39) — sector allegiance, faction HQ, political systems.
- [ ] **Black markets** (#40) — 6 randomized shop types per planet.
- [ ] **Implants** (#33) — augmentations from black markets.
- [ ] **NPC settlements** (#45) — establish organically on planets. Pirate outposts, faction bases.
- [ ] **Weapon modules** (#30) — module capacity, permanently installed, stat bonuses.

## Bugs / Cosmetic

- [ ] **#10** Silence Heart Of God `#150` division-by-zero noise
- [ ] Clean up duplicate/orphaned verbs on $player from iterative development

## Completed (systems built, may need revision as architecture changes)

- [x] Biomes — 7 types (5 major + 2 dangerous overlay)
- [x] Skill tree — 19 categories, 77 skills, SP-based
- [x] Resource classes — 4 types, tiered yields, tool compatibility, respawning
- [x] Crafting tools — tool-based dispatch, recipes on tool objects
- [x] Equipment slots — weapon/armor/gadget/special with combat integration
- [x] Harvesting — WIELD/SURVEY/CONFIGURE/HARVEST with 4 starter tools
- [x] Combat — dice pools, KILL/SWING/FIRE/TAC/CON, weapon/armor bonuses
- [x] NPC workers — CREWHIRE/CREWFIRE, 12hr delivery, stockpile cap
- [x] Per-player colonies — sector center (3 rooms), colony/enter/out/labor
- [x] Economy — sell with quality pricing, credits
- [x] Item quality — harvest quality, crafting skill bonus, grade display
- [x] Material processor — raw → refined materials
- [x] Building stats — crime/civ/econ/rec/ind ratings
- [x] New player flow — Alpha Complex → background → dispatch
- [x] Connection — create command, @quit, confunc
