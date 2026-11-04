# Which discipline label a bug report gets

These are the rules the labelling bot follows. The team owns this file. To change how cards get labelled, edit it and commit. No code changes needed.

Draft written 2026-11-04 from the 316 cards the team had already sorted. Rules marked **(proposed)** go against at least one card that's already sorted. Those cases are listed at the bottom.

## How to label

- **Label by what the player saw, not by a guessed cause.** "Door opens but I can't walk through" is a door that can't be passed. Don't decide whether a barrel, the level generator or the network caused it. The team finds the cause.
- **A clear text is enough.** If the text says what's wrong, trust it. Screenshots are often taken a moment too late or from the wrong angle, so a screenshot that doesn't show the problem is never a reason to be unsure.
- **Use the screenshot for short or vague reports.** Many reports are a few words ("wrong material", "stuck here", "look at me") and only make sense with the picture.
- **One or two labels.** Give one label when one team owns the problem. Give two when the report really involves two teams, for example a crash in a menu (Tech and UI), or a door that can't be passed while carrying a barrel (Level Design and Tech). Don't add a second label just in case.
- **Several problems in one report:** label the one that blocks the player most, plus a second one if another problem in the report clearly belongs to another team. Mention the rest in the reason.
- **Reports in other languages are normal.** Label them the same way.
- **Suggestions and feedback count.** Label them for the team that would make the change.
- **Be unsure only when** neither the text nor the screenshot says what the problem is, so a person would also have to guess ("It is very buggy", "Bugging", "very noisy here" with nothing to show whether it's sound or the picture). Knowing what the problem is but weighing two labels is not a reason to be unsure: give both. An unsure card gets **Uncategorized**.
- **Unactionable** is for reports that say too little for anyone to act on, even after a person looks at them: a blank report with a screenshot that shows nothing wrong, "r u serious", a report that isn't about the game. If a person could still work out the problem from the screenshot, it's Uncategorized, not Unactionable.

## The discipline labels

### Tech

Code and systems: things that behave wrong, as opposed to things built or drawn wrong.

- Weapons, reloading, ammo, grenades, melee, weapon switching
- Class abilities and gadgets: turret, cloak, dash, coil, revive
- Objects players place or carry (turrets, coils, barrels, the reactor core), even when the problem is how they look, such as a turret floating **(proposed)**
- Interacting, picking up, shooting or hitting through walls and closed doors **(proposed)**
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
- Wrong numbers and values: kills showing 0, wrong rewards or XP, even when they're seen in a menu **(proposed)**
- Enemies spawning without end, or spawning on top of players **(proposed)**
- Players put in the wrong place by a class ability, an object or another player: under the floor after a skill, floating, out of bounds with the coil **(proposed)**

### Level Design

The places the players move through: how they're built, blocked, lit and filled.

- **Doors that open but can't be passed, doors that never open, doors that close before everyone is through.** Wherever the door is, and whatever the player was holding.
- Invisible walls, solid walls inside doorways, blocks in a doorway
- Holes, gaps, missing walls or railings, places to fall off or under the map
- Players stuck in the level geometry: in a crack, on a ledge, under a building
- Out of bounds: reaching places players shouldn't by walking, jumping or falling, seeing outside the level. If an ability or object got them there, it's Tech.
- Missing collision: walking through rocks or terrain
- Blocked progress caused by the layout: no way to reach the extract or the reactor
- Pacing: an area that feels empty, quiet or too full, few enemies on the way to extraction
- Enemy spawn points in the wrong place: spawning outside the playable area
- Leftover debug objects in a level: debug lights, placeholder objects
- Hazards built into the level (fans, lasers, pits, traps) that hurt or kill players unfairly, for example from too far away **(proposed)**

### UI

Menus, the HUD and anything on screen that isn't the game world. UI is about how things are shown, not whether the values shown are right: a kill count showing 0 is Tech.

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
- Requests to change how something works, even when it's about doors or reviving: a grace period after a revive, a door trick that traps the swarm **(proposed)**

### Art

How things look.

- Wrong or missing materials and textures
- Z-fighting (two surfaces flickering through each other) **(proposed)**
- Floating or sunk-in scenery and props (not objects players place, which go to Tech)
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

Movement of characters, enemies and weapons that looks wrong: poses (a character stuck in an A pose, lying down after printing), spawn animations, aim direction, how weapons are held, guns crossing. If the movement also breaks gameplay (can't shoot, can't turn), add Tech.

### Uncategorized and Unactionable

See "How to label" above. These two labels always stand alone, never with a discipline label.

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
