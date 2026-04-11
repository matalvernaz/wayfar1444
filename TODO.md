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
- [x] **Automated crafting** (#27) — Factory building with interior room. INSTALL machines, LOAD materials into input hopper, ACTIVATE for automated production, COLLECT from output. Machine heartbeat processing. Known polish: OUT from factory, RUNNING display.
- [x] **Governor's office** (#20) — COLONY overview, SECTORMAP (11x11 building map), RESOURCES (biome/resource percentages), EVENTS/HISTORY log, CITIZENS/POPULATION (NPC worker list). Works from anywhere using landing coords.
- [x] **Jobs** (#17) — 7 repeatable achievements with progress tracking: Ranger Patrol (kills), Harvester (resources), Explorer (areas), Merchant (sales), Builder (buildings), Crafter (items), Factorium Labor. JOBS command with progress bars. Auto-completes and awards SP+credits. Events logged.
- [x] **Reroll/ascension** (#15) — VICTORY shows progress toward background goal. REROLL CONFIRM resets skills/SP, keeps buildings/items/credits, awards reroll points if victory met. SP cap +100 per reroll to 3500. Safety confirmation required.
- [x] **Blueprints** (#25) — LOAD <chip> ONTO <tool> installs blueprint recipes. LOOKUP <item> searches installed blueprints. Blueprint chips are physical items with bp_recipe_name property. Discoverable via exploration, loot, etc.

## Phase 4 — The Wider World

- [ ] **Central Complex expansion** (#18) — full space station hub. Shops (smartpads, medical kits, ammo). Ship refueling. Link-up terminal for joining colonies. Loan terminal. Rec dome. Holotheater. Medical bay. Multiple hangars. Admin level with lounge/vending.
- [ ] **Multi-planet** (#7) — different biome ratios per planet. Shuttle/drop pod travel. 5 solar systems (DSO-12 first). Different resource availability drives travel. Moons with rarer resources, no atmosphere, EVA suits required. Gas giants for fuel scooping.
- [ ] **Vehicles** (#28) — q-cycle (no skill), land vehicles (Driving skill), aircraft (Flying). Vehicle assembly station. Escort vehicles (8T-RL, 8T-BL). Vehicle weapons and modules. Fuel tanks. Cockpit interfaces. Explosions on destruction. Airboards/jetpacks for personal transport.
- [ ] **Starships** (#29) — starship complex building, assembly tool. Ships = rooms (bridge/generator/turrets/engineering). Warp gates. Asteroid mining with dual cargo bays. Tractor beams. Solar carriers that load smaller ships. Thrust-to-mass ratio affects speed. Power consumption tracking. Respawn terminals on ships. Pre-assembled modular chassis models for purchase.
- [x] **Farming** (#34) — seeding tool (craftable), PLANT/TEND/REAP commands, biome-specific crops (7 types), farm plot growth stages via heartbeat (~30 min to mature), quality system, FARMER job. Remaining: agriculture pod indoor farming, landslide farming harvestor, maker block food production.
- [x] **Fishing** (#37) — wooden fishing rig (craftable), FISH command in water biomes (forest/jungle/coastal), 21 alien fish species, weather affects catch rate, fish as food items, CAREER ANGLER job. Remaining: salt water fishing gear (equipment tool), fishtank storage.
- [ ] **Artifacts & research** (#38) — Laboratory building. Research q-locked items → relics, chips, equipment. Relic engine research from odd trinkets (moon-exclusive drops). Random stat-boosting relics with potential negative bonuses.
- [x] **Weather system** — per-planet weather (17 types), planet-type-specific distributions, WEATHER command, weather in room descriptions, severe weather damage (lightning/ice/sand/volcanic), weather announcements, rain boosts fishing. Remaining: asteroid showers on barren, temperature gradient equator-to-pole.
- [ ] **Cave/dungeon generation** — waypoint-based procedural dungeons. Underground points of interest with daily respawning. Digging system with 3D on-demand spawning for vertical excavation. Moon dungeons with hackable containers.
- [ ] **Crew commands** — hire up to 3 civilians (expandable via skills/reroll). Orders: converge, hold ground/guard, loot corpses, attack, drop everything. Crew follow and assist in combat.
- [ ] **Transit system** — travel directly to planetary coordinates. Menu showing nearby shops, sector centers, points of interest.

## Phase 5 — Advanced / Endgame

- [ ] **Hacking** (#26) — smartpads, HACK command, q-chip programs, outlaw status. Hack uncontrolled buildings/vehicles. Multiple hack nodes with selectable programs. Firewall challenges. Success grants ownership/control. Code-locked doors (1111-9999). Secure containers.
- [ ] **Robots** (#36) — micro-bot tool, robotic fabrication table, robot control. Voice commands, direct orders via control handpad. Guard duty defending controllers. Robot selling. Machine arena for robot salvage/combat.
- [ ] **Factions** (#39) — sector allegiance, faction HQ, political systems. NPC faction reputation (-1000 to +5000). Killing faction members reduces rep. Faction delivery tasks at contract offices. Faction collapse events. Law enforcement system.
- [ ] **Black markets** (#40) — 6 randomized shop types per planet (Implant, Munitions, Superior Equipment, Starships, Medical, Robots).
- [ ] **Implants** (#33) — augmentations from black markets. Static bonuses, damage resistances, or drug release capacity.
- [ ] **NPC settlements** (#45) — establish organically on planets. Pirate outposts, faction bases. Pirate hideouts on moons. NPC pilot routines. Civilian building construction (construction sites in 3x3 around sector center).
- [ ] **Weapon modules** (#30) — module capacity, permanently installed, stat bonuses. Armor modules and secondary prefix system with potential resistances/dodge/hacking bonuses.
- [ ] **Bio-engineering** — Bio-Organic Synthesis Tool. SCRAPE command for harvesting genetic sequences from corpses. Red strands (aggression), green strands (health), rare mutagen strands. Scaffolding + reagents for creature creation. Incubation. Created creatures follow and assist until death. Lost creatures escape into wild ecosystem.
- [ ] **Superior weapons** — random 4% loot chance from creatures. 6 quality tiers (cyan, green, blue, purple, yellow, red). Quality-scaled ammo capacity. Stat multipliers. Superior armor with +25 module capacity.
- [ ] **Grenades & explosives** — 25mm grenade rifle, 40mm grenade launcher, demolition charges (12hr real-time delay), plasma grenades, proximity charges. Frag grenades cause minimal vehicle damage. Missile silos with X/Y coordinate targeting.
- [ ] **Drugs & consumables** — drug injectors usable on self/others. Medical skill rolls reduce duration. Dice pool/regeneration drugs. Broad-spectrum vaccine. Sky-stick smokeables (dice recovery, clarity bonuses) from vending machines. Cough mechanics with relaxant inhaler remedy.
- [ ] **Diseases expanded** — spore cough. Gas masks and rebreather modules provide immunity. Radiation sickness. Burns from thermal/laser/plasma (stackable, 5-min duration).
- [ ] **Battlegrounds** — team competition PvP arena. Queue system. Awards money, skillpoints, battleground points. Equipment storage. Proper cleanup after matches.
- [ ] **Social professions** — Musician (sing/play every 15min, 10-min buff duration, listeners get buffs every 5min). Preacher (PREACH 10-min cooldown buffs nearby, BLESS 20-point restore). Consultant (crafting skill buffs).
- [ ] **TV/media system** — SENSI TV station. News reporting faction events, advertisements. Multiple TV channels with programming. Trading cards and albums (collectible text items).
- [ ] **Sector defense** — turret systems (gatling gun variants, easel-mounted). Minigame with NPC warning civilians during vehicle attacks. Civilians manning turrets. Missile turrets. Invasion/defense framework.
- [ ] **Civilian AI expansion** — paramedic module (auto-bandage injured). Gathering module (harvest resources, manage backpacks, build storehouses). Maintenance technician (building/vehicle repairs). Game hunter type. Personality traits (intelligence, reliability) affecting behavior.
- [ ] **Building decay** — abandoned buildings decay after extended inactivity. Warning mails before destruction. Dismantling returns ~50% components (100% with Crude Planning skill).
- [ ] **Noise propagation** — $noise framework for vehicle/weapon/explosive audio propagating through rooms. Laser tripwire trigger devices.

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
