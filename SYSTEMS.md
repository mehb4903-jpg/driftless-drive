# Driftless Drive: how the systems work

Working notes for whoever picks this up next (including me after a context reset). Read this before touching the game.
Keep it current: when a system changes, update its section here in the same step.

## The basics

- **The game is one file**: `/home/user/driftless-drive/index.html` (~5,000 lines, ~450 KB). It is an HTML *fragment*: no `<html>/<head>/<body>`.
  three.js r128 from cdnjs, then one inline IIFE `<script>` with everything in it.
- **Published as** the artifact `https://claude.ai/artifact/CzE8DajCvedNAxTnHXTf1P`. Publish with the Artifact tool, `url` set to that link and
  `file_path` the index.html. Capabilities are carried forward automatically (room, user, db laps rules); don't pass `capabilities`.
  Small edits: `edits` on the publish call. Big ones: python patch script, then publish.
- **The user wants**: ship after every step, keep things playable on phones (touch buttons) and with a controller, multiplayer kept in sync.

## Two copies of the game

- **Source of truth:** the claude.ai artifact, built from `/home/user/driftless-drive/index.html` in the Claude session that writes
  these notes. Multiplayer there uses the artifact `room` capability (`claude.use('room')`, presence).
- **GitHub copy:** `mehb4903-jpg/driftless-drive` (`index.html` + `README.md`) is a standalone conversion made by a separate Claude
  session ("Export 3D game to HTML"). It swaps the room for PeerJS (WebRTC, `#room=` links) and is a full HTML document. It trails the
  artifact by a version or so, and that session also commits its own fixes there. Treat the two files as related, not identical.
- These notes describe the artifact version; everything except the networking layer applies to both.

## How to edit safely (learned the hard way)

- Patch with python scripts in the scratchpad: `rep(old, new)` that asserts the anchor occurs exactly once, collect failures, write only
  if none failed. Anchors with `›`, `“`, `·` etc are real Unicode characters in the file, not `\u` escapes.
- **Never put a `//` comment on a line that continues afterwards.** A comment added at the end of a replacement swallows the rest of that
  line (`});`, a closing brace). This broke the build four or five times.
- **TDZ**: `setCar()` and the POI builders run at boot, before later `const`s are initialised. State that boot-time code touches must be
  declared early. There is a block "looks and kit you have bought" just before `let PARK = null, RIDE = null, walker = null` for this.
  `POSE` is declared there too. Builders that run at POI-build time (bMall, bBank, gasShop, bStation) may only use consts defined
  above them in the file (`GS`, `BNK`, `SHOPDEF`, `MALLI`, `BANKI` are placed accordingly). `makePerson`/`lookOf` are defined later:
  create people lazily at runtime (first frame you are near), never at build time.
- Name clashes: `BK` is the big-map scale. The bank object is `BNK`. `gAt` is the road-height cache; gravity is `gravAt`.
- Check after every patch: `bash /tmp/claude-0/-home-user/d920d492-d96f-500b-b07e-2e345c0fe66f/scratchpad/chk.sh` (extracts the script,
  `node --check`), then `boot.js` (headless load, prints page errors, `drive: true` if `window.__drive` exists).
- Rollback copies: `scratchpad/index.vNN.html` = the file as it was before version NN+1 work.

## Testing

- Playwright + swiftshader. Route `**/three.min.js` to `scratchpad/three.min.js`, abort Google Fonts. Click `#go` to start.
- `window.__drive` exposes almost everything (P, inp, sim(secs) = fixed steps without reading input, tick(dt) = one full frame incl.
  readInput/camera/HUD, setCar, unlock, travelTo(POI), POI, CITY, ACT, NET, GUN, HACK, H, BNK, GS, SHOPS, MONEY, ... grep the line
  `window.__drive = {`). `DTMAX.paused = true` stops the real frame loop while you script.
- Headless frames are slow (~4 fps): real-time things (setTimeout fades, hold-to-prone, pedestrians on the wall clock) need waits.
- Camera: fireGun shoots along the camera ray. After teleporting the player, `tick(0.001)` before aiming or the shot misses.
- Two-player: `scratchpad/mp2.js` has a mock room + virtual clock (`open(b, name)`, `run(A, B, secs)`). Copy its head into new tests.
- Bash commands time out at ~120 s: long tests go in the background or get split.

## World and regions

- Square island, flat city 20x20 blocks: `CITY.E = 1200`, block pitch `CITY.P = 120`, roads on lines `k*120 - 1200`, kerb at 8 m into
  a block, buildings start >= 11 m in. Central avenue at x = 0. `inCity(x, z, margin)`. `CITY.boxes[bi*20+bj]` = building boxes
  `[x0,x1,z0,z1,top]`. `BOXES` = other solid boxes (POIs, mall/bank walls; optional 6th value = bottom). `SOLIDS` = circles `[x,z,r,top]`.
- Reserved blocks: `CITY_RES` (bank [8,12], mall [12,8], police [11,9], city, park, diner [10,5], dealer, barn, observatory, trap, lookout).
- Far-off regions in the same coordinate space: Moon x 12000..36000 (`onMoon`), open space x > 36000 (`inSpace`, SPC), indoor regions
  x < -12000 (`inMall(x)` = any indoors; `inBank(x,z)` = z > 300). `regionOf(o)` returns 'out' | 'mall' | 'bank'.
  `terrainH` returns MALLI.y (60) for x < -12000.
- POIs: `defs` list in the POI IIFE (`['id', 'Name', 'blk'|'road'|'abs'|'fix'|'air', where, findRadius, builder]`). Builders get
  `(p, b, ln, gl)` = POI, body GB, line GB, glow GB; signs via `mallSign(text, w, h, bg, fg)` added to `p.grp`.

## Player, vehicles, on foot

- `P` = player state, `CAR` = current vehicle def from `CARS` (or `FOOTCAR`). `setCar(i)`, `toggleFoot()`/`getOut()`/`getIn()`, `PARK` =
  parked car while on foot. `stepPlayer` -> `stepFoot`/`stepUfo`/`stepHeli`/`stepSpace` or car physics. Fixed step `H_STEP`.
- Health: `HP` (vehicle), `PH` (person), `ARM.v` armour (soaks 70% on foot). `damage(d)`. Down on foot: respawn beside PARK after 10 s.
- Stance `POSE.v` 0/1/2 (stand/crouch/prone): Ctrl tap/hold, touch `tFC`, pad D-pad down. `poseKey(down)`, `poseTick`, `stancePose`.
  Affects speed, camera height, muzzle height, spread, and NPC hit chance (`t.low`). Sent as presence `cr`.
- Camera: `updateCamera`; indoors/city it is pulled in front of walls by `camWalls()`/`camHits()`.

## Weapons

- `GUNS` index: 0 pistol, 1 SMG, 2 shotgun, 3 rifle, 4 fists (melee), 5 revolver, 6 micro SMG, 7 sawed-off, 8 assault rifle, 9 bazooka.
  `GUNSLOT` maps number keys 1..0. `OWN` = owned set (0-4 free). `GM` = box models per gun (index 4 empty). `gunMesh(i, view, att)`.
- `fireGun()`: melee -> `punch()`; rocket -> `launchRocket()`; else hitscan against target list `tg` (npcs, people via `peopleTargets`,
  remote players with head boxes). Headshot x3 rifle / x2 others. Aim assist pulls 10% toward targets inside a 12 degree cone.
- Attachments `ATT[gun] = {dot,long,supp,ext,grip,laser,fin}`, `ATTOWN`, `magOf(i)`, `refreshGuns()`, `laserFrame()`. Scope overlay `#scope`
  (rifle or long scope), red dot overlay `#rdot` (first person + dot). `GUN.scoped`, `GUN.rdot`.
- Rockets/explosions: `ROCKETS`, `stepRockets`, `explode(x,y,z,mine)` (damages everyone in 7 m, shared via presence `bx`).

## People (NPCs)

- Pedestrians: pure function of the shared clock, `pedAt(bi,bj,k,t,o)`, 7 per block on the sidewalk loop (inset 9.7). Drawn near you
  (`PEOPLE.vis`). Hidden while an actor with the same src exists or `PEOPLE.hide`.
- Actors (`ACT`): people this client runs, shared to others via presence `ac` (rendered there as `REMA`). `spawnActor(src, x,y,z, yaw, seed,
  opts)`; states st 0 fight, 1 flee, 2 dead, 3 calm. `stepActor`, `hurtActor`, `hitPerson`, `peopleTargets(tg, R)`. Options: gun, hp, dmg,
  acc, slow, cop, wpn ('ar'|'sg'), cdm, heist, guard, police, look, tgt. Other players damage our actors via presence `adm`.
- Traffic: shared deterministic sim (`TR`, `trStep`, rail cars), bodies near you (`npcs`, `makeNpc`). Each car has a driver `n.drv`;
  shooting a car on foot -> `exitDriver(n)` -> driver actor fights. Car modes: 0 rail, 1 chase, 2 return, 4-6 beam/fall/wreck, 7 puppet, 8 abandoned.
- Cops: `copStep(a, t, dt)` = shared logic for any `a.cop` actor (LOS check `canSee`, bursts/shotgun, follow through doors via
  `copDoor(region, from)`, catch-up teleport for mall cops). `copShot`.
  - Mall police: `mallAlarm()` on gunfire in the mall; 4 officers rise from the fountain (120 hp, full strength).
  - Bank job police: `spawnPolice(n, where, tag)`, 70 hp, cdm 0.4 acc 0.55.
  - Bank guards: 40 hp, dmg 7, acc 0.6.

## Police and wanted stars

- `WANTED = { lv 0-3, last {x,z}, seenT, clearT, dispT }`. `wantedAtLeast(n)` (ignored indoors/space/moon/while down), `wantedSeen()`
  (refresh last-seen), `clearWanted(quiet)` (also on going down), `crimeKill(a)`.
- Crimes: gunfire `witnessed(x,z)` (officer LOS within 70 m, any officer within 40 m, or within 110 m of the station) -> 1; killing a
  civilian -> 1; till/safe/ATM -> 1; hitting an officer, a police car, or the cashier -> 2; killing an officer -> lv+1 (min 2).
  "Was it me" detection: `MYHIT = performance.now()` is set by every damage path the player causes (hitPerson, explode, car hits);
  `hurtActor` treats a death within 60 ms as the player's kill.
- Station: `bStation` + `PSTN { x, z, y, offs[6] (idle officers, made lazily, `o.out` when deployed as actor 'so'+k), bays[4], box }`.
  Idle officers are targets (`pp.off`) -> `activateOfficer(o)`.
- Police cars `PCARS` (`newPcar`, `makePoliceCar` = white sedan + 'police' livery + light bar + POLICE text). States: parked, board
  (waiting for officers), drive, stop, wreck, gone. Crew count `c.crew` (officers inside are not actors). `stepPcar`: grid navigation
  `navPoint` (street lines `roadLine`), top speed `PC_MAX` = 85 km/h, unstick by reversing, bump/run over the player, `unloadCar` near you,
  officers re-board (`a.task = 'board'`, `boardStep`) if you drive off. `dmgPoliceCar` (160 hp).
- `dispatch()` every 2.5 s while live units < stars: station car + idle officers if the station is within 1.3 km, else a patrol car
  (`patrol: true`, crew aboard) spawned ~230 m away out of sight (max 3).
- Police actors: `policeOpts(lv, k)` (cop + police flags; 90 hp; damage/aim scale with stars). In `copStep`: stand down at 0 stars,
  board task, report sightings, and when they cannot see you they walk to `WANTED.last` instead of tracking you.
- Losing them: unseen > 6 s and outside the circle `WR[lv]` (90/140/200 m) around last-seen, or unseen > 30 s. 20 s after clearing, units
  out of your way reset (station cars teleport home, patrols removed, officers back at their posts).
- Map: `policeBlips(g, k)` (cop dots, car squares, flashing search circle). HUD: `#wanted` shows stars, `.srch` while searching.
- Targeting: aim assist weights cops 3x closer; heli/Blick lock-on gets `copTargets()` (wrappers with `copT`, `hitBy`).
- Multiplayer: police actors go out as normal actors (`ac`, flag q[11]); moving police cars in presence `pc`; others render them
  (`REMPC`) and hide their own parked copy with the same id.

## Money and robbery

- `MONEY.v` (localStorage dd-cash), `addCash(n)`, HUD `#cash`. `dropCash(x,y,z,amt,piles)` -> `CASH` piles, shared via presence `cd`/`cg`.
  Deaths drop cash (people; players drop 25%).
- ATMs (`ATMS`, 18 on sidewalks) -> `tryRob()` -> PIN mini-game `HACK` (`hackKey`, `hackSubmit`, `hackFail`; `HACK.kind` = 'atm' | 'gate' |
  'safe'). Empty for 5 min, shared via presence `at`.
- Gas station (Halfway Diner, `gasShop()` + `GS`): hollow building, cashier hold-up by aiming a gun (6 s), safe in the back room = $420
  (`crackSafe`/`safeCracked`). Timers shared via presence `gs`. `gasFrame(dt)`.
- Bank job (`H`, `heistFrame`, `startHeist`, `heistStage`): ring outside Driftless Savings, 10 s lobby, stages 1 guards, 2 gate keypad,
  3 drill (100 s, runs while crew is inside), 4 pallets, 5 drop-off at (360,-120), 6 done ($15,000 split), 7 failed (12 min).
  Lowest crew id runs it and broadcasts `hs`; lobby via `hl`; non-leader gate hack via `hk`; closed-until via `bk`. Interior at BANKI.

## Mall and shops

- Mall interior at MALLI; doors via `mallGo(inside)`. Shops in `SHOPDEF` (units 0-3 west, 5-6 east), props via `shopProps`, keepers made
  lazily in `shopBuild()`. Menu: `openShop`, `drawShop`, `shopStock(def, cat)` returning rows `{name, right, blurb, dim, buy}`.
  - Iron Works: guns, rockets, armour. Threads/Sole Search: `WEAR` list -> `FIT` outfit -> `rebuildWalker()`.
  - Tactical Bench: `MODS`, `FINS`, on the gun in hand. Wrap City: `DECAL` -> `DEC[carId]` -> `applyLook(model, car, look)`.
  - Torque Shop: `TUNE` -> `UPG[carId]` -> `applyUpg(car)` (accel, vmax, grip, brk, nos). Nitrous: `CAR.nos`, `P.nos`.
  - Shop items apply to `tgtCar()` = parked car or `LASTCAR`.
- Saved in localStorage: dd-cash, dd-guns, dd-rockets, dd-armour, dd-fit, dd-ward, dd-att, dd-attown, dd-upg, dd-dec.

## Multiplayer (room presence)

- `netSend()` builds one presence object ~18 Hz; `netUpdate()` reads peers. Fields: v n col rd w hp dm g c m p q vel bo beam frz oil pre
  ice ts nq ac adm cd cg at ft cv bx ar pu cr hl hs hk bk gs (+ pc for police cars). Validate everything received (`num`, `vec`, `hexOK`,
  `cleanFit`, `cleanLook`).
- Damage to another player: cumulative `NET.dm` map; the receiver applies the increase (first hit counts in full).
- Shared clock `NET.now()`; time of day, traffic, lights and pedestrians are all derived from it.

## Other systems (short)

- Moon/space: `MOON`, `SPC`, `spaceHop(to)`, `stepSpace`, vehicles with `space: true`.
- Mall police banner / wanted HUD: `#wanted`, `wantedHud()`.
- Parachute: `buildChute`, `openChute`, `CHUTE`. Controller: `gpPick`, `readInput` (pad mapping), `rumble`.
