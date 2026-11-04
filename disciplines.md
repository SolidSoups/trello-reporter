# Which list a bug report goes in

These are the rules the sorting bot follows. The team owns this file. To change how cards get sorted, edit it and commit. No code changes needed.

Draft written 2026-11-04 from the 316 cards the team had already sorted. Rules marked **(proposed)** go against at least one card that's already sorted. Those cases are listed at the bottom.

## How to sort

- **Sort by what the player saw, not by a guessed cause.** "Door opens but I can't walk through" is a door that can't be passed. Don't decide whether a barrel, the level generator or the network caused it. The team finds the cause.
- **Look at the screenshot.** Many reports are a few words ("wrong material", "stuck here", "look at me") and only make sense with the picture. If the text and the screenshot together still don't say what's wrong, you're not sure.
- **One list per card.** If a report has several problems, sort by the one that blocks the player most. Mention the others in the reason.
- **Reports in other languages are normal.** Sort them the same way.
- **Suggestions and feedback count.** Sort them to the team that would make the change.
- **Be unsure when:**
  - the report fits two lists equally well
  - neither the text nor the screenshot says what's wrong ("It is very buggy", "Bugging", a blank report)
  - it isn't about the game at all

  An unsure card stays in Incoming for a person. That's always better than a wrong move.

## The lists

### Tech

Code and systems: things that behave wrong, as opposed to things built or drawn wrong.

- Weapons, reloading, ammo, grenades, melee, weapon switching
- Class abilities and gadgets: turret, cloak, dash, coil, revive
- Player state: downed, revived, dead, stuck in a state, can't move or shoot after an action
- Enemy behaviour (AI): not attacking, can't find a path to the player, walking in circles, despawning, seeing a cloaked player
- Enemies stuck in or walking through walls, including enemies seen inside walls **(proposed)**
- Things only some players see: invisible enemies, enemies only the host can see, eggs not bursting on a client, other players' sound or animation out of sync
- Physics objects: barrels, the reactor core and coils flying off the map or stacking strangely **(proposed)**
- Crashes, freezes, failure to start, DirectX 12 or Vulkan problems, wherever they happen **(proposed)**
- Performance: low frame rate, lag, stutter **(proposed)**
- Connection: errors, can't join, lost connection
- Saving and progression: lost level, credits or unlocks, the wrong class after picking one
- Input and controls: keybinds that don't work, keyboard layouts (AZERTY), controller vibration
- Mission logic: objectives that don't complete, extraction that doesn't end the mission, no "Mission accomplished"
- Animation glitches (pose, aim direction, a gun held wrong, a character lying down) while the Animation list is unused **(proposed)**

### Level Design

The places the players move through: how they're built, blocked, lit and filled.

- **Doors that open but can't be passed, doors that never open, doors that close before everyone is through.** Wherever the door is, and whatever the player was holding.
- Invisible walls, solid walls inside doorways, blocks in a doorway
- Holes, gaps, missing walls or railings, places to fall off or under the map
- Players stuck in the level geometry: in a crack, on a ledge, under a building
- Out of bounds: reaching places players shouldn't, seeing outside the level, a hidden spot to stand in
- Missing collision: walking through rocks or terrain
- Blocked progress caused by the layout: no way to reach the extract or the reactor
- Pacing: an area that feels empty, quiet or too full, few enemies on the way to extraction
- Enemy spawn points in the wrong place: spawning outside the playable area
- Leftover debug objects in a level: debug lights, placeholder objects

### UI

Menus, the HUD and anything on screen that isn't the game world.

- Minimap and map: grey, missing markers, stuck at the wrong size
- Menus: navigation, Esc and Back, the bug report window, the server browser, menus clickable too early
- HUD: health, objective tracker, ability cooldowns, hit markers, weapon icons
- Settings menus and key rebinding menus (a setting that doesn't take effect goes to Tech)
- Armory and skin previews, class and skill overviews
- Requests for information on screen ("show a cooldown timer", "show enemies on the minimap")

### Game Design

How the game plays and whether it's clear, as opposed to whether it works.

- Balance: damage, cooldowns, ammo amounts, how long a player stays downed **(proposed)**
- Exploits that are working as built but shouldn't be: animation cancelling, spamming the turret, standing somewhere enemies can't reach **(proposed)**
- Unclear mechanics: "what does this ability do?", "capturing isn't clear"
- Rewards that feel wrong: a skin that's barely different
- Requests for new mechanics: melee while reloading, a flashlight toggle

### Art

How things look.

- Wrong or missing materials and textures
- Z-fighting (two surfaces flickering through each other) **(proposed)**
- Floating or sunk-in objects
- Lighting, fog, sky and backgrounds that look wrong
- Effects: missing or wrong particles and glows
- Weapon and character models or skins that look wrong

### Audio

Anything heard.

- Sound cutting out, missing, playing twice or looping
- Sound out of sync between players
- Wrong sound for an action
- Volume: too loud, too noisy, a sudden jump **(proposed)**
- Direction: a sound coming from the wrong side **(proposed)**

### Animation

Movement of characters, enemies and weapons that looks wrong: poses, spawn animations, aiming, how weapons are held. **(proposed)** The list is empty today, and the team decides whether to use it. Until then these reports go to Tech.

### Never chosen by the bot

- **Unactionable:** a person decides this. If you think a report can't be acted on, be unsure.
- **DONE.**

<!-- sort.py stops reading here. Everything below is for the team. -->

## For the team: cases to decide

Where the 316 sorted cards disagree with each other or with the rules above. Each needs one answer, which then goes into the rules.

1. **Doors that open but can't be passed.** About 25 are in Level Design. Two are in Tech: [the barrel one](https://trello.com/c/YPoP4q4L) and [BBzZZXpw](https://trello.com/c/BBzZZXpw). Proposed: all go to Level Design, with no cause guessed.
2. **Enemies stuck in walls.** About 12 are in Tech ([0OU4Se8K](https://trello.com/c/0OU4Se8K), [qhONgB6m](https://trello.com/c/qhONgB6m), [CUHxwR79](https://trello.com/c/CUHxwR79)) and 5 are in Level Design ([NjkU79jZ](https://trello.com/c/NjkU79jZ), [LoXO1i0w](https://trello.com/c/LoXO1i0w), [wnPhOkF5](https://trello.com/c/wnPhOkF5)). Proposed: Tech, since AI and movement decide where enemies walk.
3. **Player falls through the map.** Mostly Level Design. In Tech: [fallen through map, can't revive](https://trello.com/c/CoVUAD6o) and [under floor after using an ability](https://trello.com/c/c9bXzfZp). Proposed: Level Design, except when an ability or object pushed the player there.
4. **Objects thrown off the map.** The reactor core is in Tech ([izsOZX3m](https://trello.com/c/izsOZX3m), [HhcrHvkC](https://trello.com/c/HhcrHvkC)), and coils are in Level Design ([x26shdj2](https://trello.com/c/x26shdj2)). Proposed: Tech.
5. **Crashes.** All are in Tech except [crash on Back from settings](https://trello.com/c/N34OCcEV), which is in UI. Proposed: every crash goes to Tech.
6. **Performance.** In Tech, apart from [Severe lag](https://trello.com/c/J1ruSTuq) and [graphics settings do nothing](https://trello.com/c/7MEzlEbV), which are in UI. Proposed: Tech.
7. **Visual problems in levels.** Z-fighting, [debug light](https://trello.com/c/lseVDr4w), [flickering textures](https://trello.com/c/gftEsDm9), [wrong egg texture](https://trello.com/c/lXbRQbIF) and [lighting](https://trello.com/c/shseGZpv) are in Level Design. [A light source still visible](https://trello.com/c/FR4D0q3K) is in Tech. Proposed: debug leftovers to Level Design, and textures, z-fighting and lighting to Art.
8. **Sound.** Audio has 5 cards, but [too noisy](https://trello.com/c/sQiCYBTd), [volume to 11](https://trello.com/c/QGW2oELh), [sound from the wrong side](https://trello.com/c/tiaFLAEP) and [grenade sound after switching](https://trello.com/c/ot4kCp9D) are in Tech. Proposed: everything heard goes to Audio, except a sound that follows a code bug (like the grenade), which goes to Tech.
9. **Balance, exploits and feedback.** Game Design has 8 cards, but [barrel damage](https://trello.com/c/0iHA3eNL), [turret has no cooldown after dying](https://trello.com/c/hAf6WjWp), [melee animation cancel](https://trello.com/c/GU6eCPUW), [flashlight toggle](https://trello.com/c/1Tb8raCU) and [controller vibration](https://trello.com/c/rRiEOSv6) are in Tech, and [flamethrower ammo per box](https://trello.com/c/Xrf0SIkj) is in Level Design. Proposed: balance and exploits go to Game Design, and settings requests (vibration) to Tech.
10. **Animation.** The list is empty. [Grappler spawn animation](https://trello.com/c/VZwWZyad), [A pose](https://trello.com/c/aPusC3bT), [guns cross](https://trello.com/c/84W54H03), [pistols point down](https://trello.com/c/oz8vBczS) and [lying down after printing](https://trello.com/c/vCYBP8aJ) are in Tech. Does the Animation list get used?
11. **Ability feel.** [Infiltrator dash cooldown feels random](https://trello.com/c/lg87vwsw) is in UI, because it asks for a cooldown timer. Proposed: keep it in UI when the request is for something on screen.
12. **Reports with nothing to go on.** "lol", "Look at me", "Bugging" and "Stuck" are sorted in Level Design, and two blank reports are in Tech and UI. They may have been sorted from the screenshot. Should the bot do the same, or leave such cards for a person?
