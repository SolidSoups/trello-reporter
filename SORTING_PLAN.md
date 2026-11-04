# Plan: Claude sorts new reports into the discipline lists

Status: planned, nothing built. Written 2026-11-04.

## Goal

The sync drops every new report into **Incoming**. A new script, `sort.py`, moves each one into the right discipline list (Tech, Level Design, UI, Game Design, Art, Audio, Animation), with a comment saying why. When Claude isn't sure, the card stays in Incoming for a person.

## Rules the bot never breaks

- It only moves cards that are **in Incoming**. It never touches DONE, Unactionable, or a card a person has already moved.
- It never deletes, archives, merges or edits a card. Its only writes are: move, add one comment, add the "Needs sorting" label.
- Every move is logged, and `sort.py --undo` puts cards back.
- `sync.py` doesn't change. Sorting is a separate script with its own lock, so a broken sort can't stop reports from arriving.

## What the board looks like now

From the export of 2026-11-04:

| List | Open cards | List ID |
|---|---|---|
| Incoming | 338 | `6ae9c9bdba0d72db5aed2ad2` |
| Incoming Tech | 140 | `6ae9ce93cef542d3b24b3ccd` |
| Incoming Level Design | 122 | `6ae9cea5dad76d1cd428fbe1` |
| Incoming UI | 35 | `6ae9ce96e791321dc905838b` |
| Incoming Game Design | 8 | `6ae9db8d0e8cace36c8d2a9f` |
| Incoming Art | 6 | `6ae9ce98ce73dba581509a75` |
| Incoming Audio | 5 | `6ae9dffd4efda3c5f3db74ec` |
| Incoming Animation | 0 | `6ae9d90cb9251fcf8648e0ab` |
| Unactionable | 3 | `6aea068c6de049d9f81fbadd` |
| DONE | 99 | `6ae9ce9b12cc839848acd302` |

Findings that shape the plan:

- **The 316 hand-sorted cards are the test set.** The bot gets measured against them before it moves anything.
- **The hand sorting disagrees with itself.** A settings-menu crash and an Infiltrator dash bug are in UI. "Door opens with a barrel in hand" is in Tech, while most door reports are in Level Design. The bot follows written rules, so the team has to agree on them (step 1).
- **Some reports only make sense with the screenshot.** Art titles like "wrong material" or "these are floating slightly" say nothing alone, so the bot sends the screenshot too.
- **Screenshots are big.** The median is 3 MB and the largest is 11 MB (PNG, full resolution). The Claude API takes at most 5 MB per image, and it scales large images down anyway. `sort.py` shrinks each screenshot to 1568 pixels on the long edge and saves it as JPEG before sending. That needs the `Pillow` package.
- **Game Design, Art, Audio and Animation have almost no examples.** Those lists depend on the written rules more than on past cards.

## Step 1: the rules file, `disciplines.md`

A short file in the repo, a few lines per list, saying what belongs there. It's the main thing that steers the bot, and the team owns it.

- Claude drafts it from the 316 sorted cards, and lists the cases where the current sorting disagrees with itself (like the door reports above).
- The team corrects it and decides the disputed cases.
- It includes the rule from earlier: **the bot sorts by symptom, not by a guessed cause.** For example, "door opens but can't be passed" goes to one agreed list. The bot doesn't decide whether a barrel or the level generator caused it.
- It says what "unsure" means: a report that fits two lists, a report too vague to sort ("It is very buggy"), or a report that isn't a bug at all. All of these stay in Incoming.

Changing a rule later is a commit to `disciplines.md`. No code changes.

The file ends with a "cases to decide" section for the team. `sort.py` sends Claude only what comes before the `sort.py stops reading here` marker.

## Step 2: `sort.py`, read-only modes first

### What Claude gets for each card

- **System prompt**, the same for every card, so it's cached:
  - the task
  - `disciplines.md`
  - about 5 example cards per list, text only, picked from the sorted cards
- **The card:**
  - title
  - description (the report text plus fields like map, tile, mission, class)
  - labels
  - the shrunk screenshot

### What Claude answers

Structured output. The API forces this shape:

```json
{"list": "Level Design", "sure": true, "reason": "Player can't pass an opened door on a Chryos connector tile."}
```

- `list` must be one of the discipline names. Unactionable isn't on the list, so a person decides that.
- `sure` set to false means the card stays in Incoming.
- If the API refuses or errors on a card, that card counts as not sure.

### Modes

| Command | Does | Writes to the board |
|---|---|---|
| `sort.py --evaluate --model X` | Runs every sorted card (except the example cards) through Claude and compares the answers with where your team put them | No |
| `sort.py --dry-run` | Proposes a list for every card in Incoming | No |
| `sort.py` | Sorts the cards in Incoming | Yes |
| `sort.py --undo` | Moves back the cards the bot moved | Yes |

`--evaluate` writes a report to `%LOCALAPPDATA%\darkswarm-bug-sync\`:

- agreement per list (for example, "Tech: 121 of 135 match")
- how many cards Claude marked as not sure
- every disagreement: card link, your team's list, Claude's list, Claude's reason

Each disagreement is either the bot's mistake or a gap in `disciplines.md`. Go back to step 1, fix the rules, and run it again.

`--dry-run` writes the same kind of list for the 338 cards in Incoming, so the team can skim it before the first real run.

### Answer cache

Answers are saved by card ID (and by the version of `disciplines.md` they were made with). A dry run followed by a real run doesn't pay twice, and a card that's already been asked isn't asked again unless the rules changed.

## Step 3: pick the model

Run `--evaluate` with each model on the same cards. One card is about 3,500 input tokens (1,600 of text, 1,900 of screenshot) and about 100 output tokens.

| Model | Evaluation (~290 cards) | 338-card backlog | 50 new cards a day |
|---|---|---|---|
| Haiku 5.5 | ~$0.15 | ~$0.15 | ~$0.03 |
| Sonnet 5.5 | ~$2.50 | ~$3 | ~$0.40 |
| Opus 5.5 | ~$5 | ~$6 | ~$0.80 |

Caching the system prompt lowers all of these. Choose the cheapest model whose agreement is close to the best one. The model name goes in `config.json`, so switching later is a config change.

## Step 4: sorting for real

For each card in Incoming, oldest first:

1. Skip the card if it has the "Needs sorting" label. A person has to sort it.
2. Ask Claude, or use the cached answer.
3. **Sure:**
   - `PUT /1/cards/{id}` with the new `idList`
   - a comment: "Sorted to Incoming Level Design by the sorting bot: player can't pass an opened door on a Chryos connector tile."
   - a line in the move log
4. **Not sure:** add the "Needs sorting" label and leave the card in Incoming.

Right before moving a card, the script reads the card again and checks it's still in Incoming. A person may have moved it while Claude was answering.

### Move log and undo

`%LOCALAPPDATA%\darkswarm-bug-sync\moves.jsonl` holds one line per move: time, card ID, card name, from list, to list, model, reason.

- `sort.py --undo` reverses every move in the log.
- `sort.py --undo --since "2026-11-05 07:00"` reverses only the moves since that time.
- Undo only moves a card back if it's still in the list the bot put it in. If a person moved it since, undo leaves it alone and says so.

### First run

1. Run `--dry-run` on the 338 cards and skim the list.
2. Run `sort.py --next 20`, then check those 20 cards on the board.
3. Run the rest.

## Step 5: running it on the build computer

- `config.json` gets a `sorting` section:
  - the model
  - the Incoming list ID
  - list name → list ID for each discipline
  - the "Needs sorting" label name
- `requirements.txt` adds `anthropic` and `Pillow`.
- `setup.cmd` asks for a fourth secret, the Anthropic API key, which goes into Credential Manager like the others.
- `start-schedule.cmd` and `stop-schedule.cmd` also register and remove a second task, "DarkSwarm Bug Sort", every 15 minutes, 5 minutes after the sync. It has its own lock and its own log, `sort.log`.
- `status.cmd` shows both tasks.

## What you set up

- An Anthropic Console account, credit and an API key. You create these yourself.
- Optionally, a spend limit in the Console, so a bug in the script can't run up a bill.

## Decisions for the team

1. The disputed cases in `disciplines.md`: doors, crashes, ability bugs (Tech or UI?), feedback and requests (Game Design?).
2. Animation has 0 cards. Should the bot sort into it at all?
3. Should the bot ever move to Unactionable? Proposed: no. "Needs sorting" covers it, and a person moves the card.
4. Does a "not sure" card go back to Claude once the rules change, or does it stay with people for good?

## Order of work

| Step | Needs | Spends money |
|---|---|---|
| 1. Draft `disciplines.md` | The board export | No |
| 2. `sort.py --evaluate` and `--dry-run` | API key | Yes, about $8 for all three models |
| 3. Pick the model | Evaluation results | No |
| 4. Real sorting, undo | Agreement the team is happy with | Small |
| 5. Scheduling on the build computer | Steps 1–4 | Daily, see step 3 |
