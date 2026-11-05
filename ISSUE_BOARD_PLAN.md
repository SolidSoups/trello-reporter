# Issue board assistant: plan and findings

Status: **planning, nothing built.** Last updated 2026-11-03.

## Goal

The feedback board (**DarkSwarm User Feedback**) collects one card per player report. With hundreds of reports, the same bug shows up many times in different words. We want a second board that holds **one card per distinct issue**, each linking to every report of it, so the team can work from issues and see which are reported most.

## Principles

1. **The feedback board is read-only for the assistant.** No moves, labels, comments or archiving on feedback cards.
2. **Group by symptom and place, never by cause.** An issue card says what players see and where. It never says why. Causes are the team's call.
3. **When in doubt, make a new issue.** Two issue cards that turn out to be one bug are cheap to fix: move the links over. One card holding two different bugs is expensive, because fixing one looks like fixing both.
4. **The assistant only adds.** It creates issue cards and adds report links and comments. It never renames, moves, rewrites or deletes cards the team has worked on. The one exception is its own note comment, which it updates in place.
5. **Every link explains itself.** Each link the assistant adds comes with a one-line reason, so a wrong one is easy to spot.

## The feedback board today (export of 2026-11-03)

| List | Open cards |
|---|---|
| Incoming Tech | 138 |
| Incoming Level Design | 163 |
| Incoming UI | 24 |
| Incoming Art | 7 |
| Incoming Animation | 8 |
| Incoming Game Design | 8 |
| Incoming Audio | 4 |
| DONE | 3 |
| Incoming (sync target) | 0 open, 21 archived test cards |

- 355 open cards, 354 of them created by the sync. All have a screenshot.
- Labels: version, mission, map and `External`. No checklists or custom fields yet.
- Versions: 0.7.4.5747 (241 cards), 0.7.4.5759 (82) and a few older builds.
- The team has sorted reports by discipline. That sorting stays.

### Fields that help matching

Each sync-made card carries Map, Mission, Seed, Tile, Version and Player in its description.

- **Tile** is the strongest place signal. The number in front is the tile's position in that level (`031_…`, `033_…`). The rest is the tile type (`IcePlatforms_Connector_CrystalCaves_A`). Matching should compare tile types and ignore the number.
- **Seed** identifies one generated level. The same seed means the same level, often the same play session, with several players in one group reporting the same moment.
- **Map and Mission** narrow the place, but alone they're too broad: "a door on Chryos" is not one bug.

## Issues in the backlog right now (first pass, not reviewed)

Read from card names and first lines only, no screenshots. The numbers are Trello card numbers on the feedback board. The counts are rough. This is a starting point for review, not a decision.

### Door issues, split by place

Door reports are the largest family. Per principle 2, they're split by map, mission and tile, not merged into one "door bug".

| Proposed issue | Cards | Notes |
|---|---|---|
| Chryos IceBreaker: door opens but can't be passed (invisible wall), on `IcePlatforms_Connector_CrystalCaves_A` | 130, 202, 230, 263, 274, 298, 314, 326, 327, 330, 331, 345, 361 | 13 reports, 11 different seeds, all the same tile type |
| Chryos IceBreaker: door can't be passed, on `Ice_CrystalCave_Refinery_B` | 178, 179, 260, 275, 276 | 178 and 179 share a seed |
| Chryos IceBreaker: door can't be passed, on `Ice_CrystalCave_HiveBrain_A` | 132, 364 | |
| Chryos IceBreaker: carrying a barrel through a door locks it | 342 | Its own issue. Whether it explains the others is for the team to judge |
| Chryos Cold Shock: door opens but can't be passed, on `IcePlatforms_Connector_CrystalCaves_A` | 143, 212, 218, 243, 273, 296, 311, 320, 365 | The same tile type as the IceBreaker group, in a different mission |
| Chryos Cold Shock: door can't be passed, on `CrystalCave_Refinery_B` / other tiles | 141, 223, 272, 367 | |
| Chryos door reports without a usable tile | 227, 253, 318, 372, plus reports sent from the hub or menu: 235, 247, 309 | Need a person or the screenshot to place them |
| Space station: door opens onto a solid wall | 254, 255, 265, 294, 349, 352 | 254/255 and 349/352 share seeds |
| Space station: path blocked / door won't open | 30, 237, 238, 262 | Possibly the same as the row above; kept apart until reviewed |
| Tendraal Bassault: door closes after one player goes through, locking others out | 277, 278, 321 | |
| Tendraal Bassault: door to the objective won't open | 163, 240, 251, 371 | |

**Worth the team's attention:** the two Chryos "door opens but can't be passed" groups share one tile type, `IcePlatforms_Connector_CrystalCaves_A`, across two missions and more than 20 seeds. That points at that tile rather than at one player's actions. It's an observation for the level design team, and the assistant should not treat it as a reason to merge.

### Other groups

| Proposed issue | Cards | Rough count |
|---|---|---|
| Prologue: missing wall in the battery/bridge room, fall into the void | 91, 114, 117, 123, 154, 164, 200, 204, 256, 280, 281, 301, 344, 373 (probably 48, 49) | ~15 |
| Progress lost after restarting, especially non-host players | 198, 233, 250, 257, 285, 288, 346, 359, 374 | 9 |
| Enemies stuck in or clipping through walls | 124, 125, 129, 147, 150, 165, 279, 339, 360, 366 | ~10, probably several issues by map |
| Clients can't see some enemies | 35, 36, 37, 38, 40, 231 (maybe 315) | 6-7 |
| Weapon state breaks: wrong weapon held, can't reload or swap | 229, 299, 319, 332, 334, 351 | ~6 |
| Minimap grey until Tab is pressed | 77, 137, 190, 252 (related: 207) | 4 |
| Grenade held in the rifle pose in equipment / class select | 109, 111, 239, 264 | 4 |
| Stuck after extraction, or after dashing into extract | 31, 33, 245 | 3 |
| Trapped by a trap or grabber, can't move afterwards | 84, 112, 178, 293 | 4 |
| Falling through or out of the Tendraal map | 27, 75, 168, 172, 176, 186, 203, 215, 228, 236, 313, 338 | ~12, almost certainly several places |
| Debug or placeholder lights visible | 39, 167, 221, 271 | 4 |
| Floating purple circle by crystals (Chryos) | 182, 183 | 2 |
| DX12 crash or freeze at startup | 259, 266 | 2 |
| Capped at 30 fps in missions | 350, 354 | 2 |
| Flamethrower won't reload | 169, 170 | 2 |
| Reactor core falls off the map | 93, 304 | 2 |
| Infiltrator vanish makes enemies despawn | 193, 292 | 2 |
| Host pressing F11 lets crawlers through walls | 56, 57 | 2 |
| Audio desync for non-host players | 323, 324 | 2 |
| Space station level generation broken | 328, 337 | 2 |

Most of the remaining ~200 cards are single reports.

### Not actionable from the text alone

197 "Bugging", 348 "lol", 214 "Look at me", 224 "r u serious", 199 "It is very buggy", 194 "Tendraal - Bassault", 98 "Stuck", 92 "He's not doing anything", and 375, which is empty. The screenshot may still show the problem. These go to **Needs triage**, never into a group.

## Design

### The issue board

A new board, working name **DarkSwarm Issues**.

Proposed lists (decision 1):

| List | Holds |
|---|---|
| Unreviewed | New issue cards created by the assistant, waiting for a person |
| Needs triage | Reports the assistant couldn't place: vague, empty, or unclear |
| Tech, Level Design, UI, Art, Animation, Game Design, Audio | Accepted issues, by discipline |
| Done | Fixed or closed issues |

### An issue card

- **Name:** symptom and place, for example "Chryos IceBreaker: door opens but can't be passed (CrystalCaves connector)".
- **Description:**

  ```
  What players see: …
  Where: Map, Mission, Tile type(s)
  Versions seen: …

  Matching notes:
  <written by the team; the assistant reads this to decide what belongs here>
  ```

- **Reports checklist:** one item per feedback card, holding the card's link. Trello shows each link as a card preview. The count shows on the card front.
- **Comments:** one per report the assistant links, with the reason.
- **Labels:** map and mission. The assistant may add `Reported again` when a report arrives for a Done issue.

The **Matching notes** let the team steer the assistant, for example "Only the door right after the hive brains. Doors that never open at all are a different issue." The assistant never writes to that section.

### One run of the assistant

1. **Read the issue board:** every issue card, its description, and the feedback card IDs in its Reports checklists.
2. **Find unprocessed reports:** feedback cards that no issue card links to. No local record is needed, so this works the same from any machine. Removing a link makes that report get processed again.
3. **For each unprocessed report, oldest first:**
   1. Narrow the candidates (see Scale).
   2. Ask Claude: this report plus the candidates. It answers in a fixed format: `{issue: <card id> | "new" | "triage", confidence, reason}`.
   3. Act on the answer:
      - **Existing issue:** add the link to its Reports checklist, and comment with the reason.
      - **New:** create an issue card in Unreviewed, with this report as the first link.
      - **Triage:** add the link to the **Needs triage** card's checklist.
      - **Existing issue in Done:** link it, and add `Reported again`.
   4. **Add the result to the in-memory catalogue right away,** so later reports in the same run can match a card that was just created.
4. **Log every action** to a local log file, with an undo option.

### Matching rules given to Claude

- Link only when the report describes **the same symptom in the same place**: the same map and mission, and the same tile type when both have one.
- **Never reason about causes.** "Both involve doors" is not a match.
- The same seed is supporting evidence, not proof.
- The issue's Matching notes override the general rules.
- Too vague to tell, or empty: answer `triage`.
- **Unsure: answer `new`.**

### Assistant notes (observations)

Besides linking reports, the assistant points out patterns the team might miss. For example:

> NOTE: Most of the Chryos "door opens but can't be passed" reports happen on the same tile type, `IcePlatforms_Connector_CrystalCaves_A`: 22 reports across IceBreaker and Cold Shock, from 20 different seeds. See also: <link to the other issue card>.

**What a note may say:**
- Facts it can count: a shared tile type, map, mission, seed or version across reports or issues; reports stopping after a certain version; reports from one play session; a jump in new reports.
- Which issue cards look related, with links.
- Always with the numbers and the report links behind them.

**What a note may not do:**
- Claim a cause. "Same tile type" is a fact; "the tile is broken" is the team's conclusion.
- Merge, move or rename anything because of a note.

**Where notes go:**
- **On the issue card,** as one comment that starts with `NOTE (assistant):`. The assistant keeps a single note comment per card and edits it when the numbers change, instead of adding a new comment each time. Team comments are never touched.
- **Patterns spanning several issues** also go on a card in an **Assistant notes** list, linking every issue involved. That card is a running list the team can scan.

**How notes are made:**
1. Plain Python counts what the data shows: tile types, seeds, versions and maps per issue, across all issues. That's cheap and exact.
2. Only patterns past a threshold (for example, the same tile type in 5 or more reports across 2 or more issues) go to Claude, which writes the note text from those counts.
3. This runs on its own schedule, for example once a day, not on every 15-minute run, since patterns change slowly.

The note text is written by Claude, but the numbers in it come from the counting step, so a note can't overstate the data.

### Checking off (decision 4)

- **A.** The issue board is the only record. The team ticks Reports checklist items as they confirm them. The feedback board is never touched.
- **B.** As A, plus: when an issue moves to Done, the assistant adds a `Resolved` label and a comment linking the issue to each of its feedback cards. That only adds to the feedback board.
- **C.** As B, plus it archives those feedback cards.

Suggested: start with A, add B if people want status visible on the feedback board.

## Scale

The feedback board is expected to grow to thousands of reports, and the issue board to hundreds or thousands of issues.

**What grows with the board:**
- **Reading both boards every run.** Trello returns cards in pages, so thousands of cards take a few requests per board. That's fine every 15 minutes.
- **The catalogue sent to Claude.** One issue takes about 80-150 tokens: name, place, tile, matching notes and one example. 300 issues is about 40,000 tokens; 3,000 issues would be about 400,000. Sending everything for every report gets slow and expensive as the board grows.

**Narrowing candidates first.** Before asking Claude, the assistant keeps only plausible issues:
1. Issues with the **same map** (the hub and main menu also count as "any map", since players often report after leaving the mission).
2. Then the **same mission**, and the **same tile type** when the report has one.
3. Then simple word overlap between the report text and the issue name or summary, keeping the top 30-50.
4. **Done issues** stay candidates, so regressions get noticed.

That keeps each request around 5,000-10,000 tokens however big the board gets. It's plain Python with no new service. The risk is a correct match being filtered out, for example when a player reports from the hub. The cost of that is a duplicate issue card, which is the cheap failure.

**Trello limits to check before building:**
- How many items one checklist can hold. A bug with hundreds of reports could hit it. If so, continue in "Reports (2)".
- Practical limits on open cards per board. Done issues may need archiving now and then. That's the team's call; the assistant never archives.
- The rate limit (100 requests per 10 seconds per token) is shared with the sync. Both run one request at a time, so it shouldn't be a problem.

**Cost grows with new reports, not board size,** because of the narrowing. It's estimated, not measured. To be checked in phase 3.

## Risks

| Risk | Mitigation |
|---|---|
| Two different bugs linked to one issue | Split-when-unsure rules, a reason on every link, team-written matching notes, a cheap fix (move the link) |
| One bug spread over several issue cards | Expected and cheap: the team moves links over. A later "issues that look alike" report could suggest candidates |
| A vague report guessed into an issue | The `triage` answer, never guessed |
| A correct match filtered out by narrowing | The fallback is a new issue card, which is cheap |
| Unreviewed piling up | The team needs a routine. The assistant keeps working either way |
| Feedback board cards deleted or moved | Links break or point at a moved card. The assistant only reads feedback cards, so nothing gets worse |
| Model cost or quality | Measured before switching on (phase 3) |

## Open decisions

1. **Issue board lists:** disciplines plus Unreviewed / Needs triage / Done, as above?
2. **Who matches:** the Claude API running automatically on the build computer (needs an API key, billed per use), or Claude Code sessions run by hand?
3. **Which model:** chosen by measurement in phase 3, between Haiku 5.5, Sonnet 5.5 and Opus 5.5.
4. **Checking off:** A, B or C.
5. **Screenshots:** text only, or also send the screenshot for short or vague reports? Better matches, higher cost.
6. **Separate from the sync or part of it:** a second scheduled script, or a step at the end of each sync run? Separate keeps a failure in one from blocking the other.
7. **Assistant notes:** which patterns count, the thresholds, and how often notes are refreshed (once a day suggested).

## Phases

1. **Settle the decisions above.**
2. **Build the first issue board from the backlog,** in a Claude Code session: I write the issue list as a file, the team reviews and edits it, and a helper creates the board. No API cost.
3. **Measure:** take about 30-50 reports from the reviewed backlog as an answer key. Run them through the matching step with each candidate model. Compare wrong links, missed links and cost, then pick the model.
4. **Dry run:** the assistant prints what it would do with new reports, and writes nothing. Check it for a few days.
5. **Switch on** on the build computer.
6. **Assistant notes:** the daily pattern step, first as a dry run that prints the notes it would post.
7. **Optional:** checking-off option B, and a periodic "issues that look alike" report for the team.
