# Wayfar 1444 — TODO
# Survival colonization: survive → establish → automate → colony → expand
# Ordered by what a player actually experiences

## Phase 1 — The Planet (architectural foundation)

- [ ] **Planet generation** — `@create-planet <name> <size> <type>` wizard verb. Bounded coords (e.g. -50 to +50), seed-based Perlin for consistent biomes, planet type affects biome ratios (jungle world, desert world, balanced). ODS creates rooms lazily within bounds. Edges are impassable/ocean. POIs placed during generation (pirate bases, ruins, NPC settlements).
- [ ] **Random landing** — dispatch picks random coordinates far from other players' colonies. No shared crash site. Per-player landing zone. Wiki: shuttle ensures no colonies too close.
- [ ] **Exploration** (#16) — `EXPLORE` fills room 0-100%. At 100%: `MEMORIZE` for fast `TRAVEL`, `DISCOVER` for artifacts/specimens (req Unpaid Cartographer skill). `map biomes` for surrounding area. Terrain surveyor income. This is how players navigate.
- [ ] **Creatures** (#6) — biome-specific wildlife spawning naturally. Carnivores (dangerous), herbivores (resources), named bosses (Mother Muex, planet boss). Loot varies by species. `CON` to assess. Creature AI roaming between tiles. Makes the world alive.

## Phase 2 — Survival Progression (first hours of gameplay)

- [ ] **Early game polish** — hand-gathering is slow (1 unit, no quality). Tool-gathering is better (2 units, quality). Cooking fire for food. Eating raw food = less benefit. Shelter protects (future: weather/creature raids). Hunger/health pressure creates urgency.
- [ ] **Building progression** — enforce crafting chain: shelter → refinery → processing plant → automated harvester → factory. Sector center is a MILESTONE deep in the tree, not early game. Each building step is meaningful and unlocks new capabilities.
- [ ] **Item degradation** (#44) — weapons wear with use, armor degrades on damage. `REPAIR <item>` holding the tool that made it. Keeps crafting demand alive.
- [ ] **Medical + status effects** (#31, #32) — `BANDAGE` (First Aid skill), bleeding/burns/diseases. Infirmary building heals over time. Dangerous biomes cause diseases. Real consequences for combat and exploration.
- [ ] **Communications** (#4) — `say` (local), `chat` (global chatnet), `chatnet history`, `page` (private DM), `who` (online players). Additional nets later. Players need to talk.

## Phase 3 — Colony Building (hours 5-20 of gameplay)

- [ ] **Refining** (#23) — 3 buildings (refinery/organic plant/nuclear plant). Bulk low-quality → fewer high-quality. The quality loop that makes endgame crafting work.
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
