# Findings: real bug report messages

Taken from eight reports in the public channel on 2026-11-03, over two runs, read with `inspect_messages.py`. These override the original spec where the two differ.

## Message shape

A report is one message from the webhook. `content` is empty and `attachments` is empty. Everything is in `embeds[0]`:

```json
{
  "type": 0,
  "content": "",
  "attachments": [],
  "embeds": [
    {
      "type": "rich",
      "description": "## Can't pass through the door to evac, hitting invisible wall.",
      "fields": [
        { "name": "Time", "value": "2026-11-03 13:24:20", "inline": true },
        { "name": "Player", "value": "...", "inline": true },
        { "name": "Map", "value": "DS_MAP_Biome_Ice_A", "inline": true },
        { "name": "Seed", "value": "1596374528", "inline": true },
        { "name": "Branches", "value": "DS_ObjectiveBranch_Ice_LandingZone, ...", "inline": true },
        { "name": "Tile", "value": "033_IcePlatforms_Connector_CrystalCaves_A", "inline": true },
        { "name": "Mission", "value": "DS_DA_MissionType_Chryos_IceBreaker", "inline": true },
        { "name": "Version", "value": "0.7.4.5747", "inline": true }
      ],
      "image": {
        "url": "https://cdn.discordapp.com/attachments/<channel>/<attachment>/screenshot.png?ex=...&is=...&hm=...",
        "proxy_url": "https://media.discordapp.net/attachments/...",
        "width": 2560,
        "height": 1440,
        "content_type": "image/jpeg"
      }
    }
  ],
  "timestamp": "2026-11-03T10:24:55.860000+00:00",
  "id": "1567122399890112576",
  "channel_id": "1564230130061017158",
  "author": { "id": "<same as webhook_id>", "username": "Spidey Bot", "bot": true },
  "webhook_id": "1564292810046316667"
}
```

- `author.id` equals `webhook_id`. `author.username` is the webhook's display name.
- The `reactions` key is missing entirely when a message has no reactions. Treat a missing key as an empty list.
- Field names match `BuildDiscordPayload` exactly. Every value is a string, including `Seed`.

## Screenshot

- **It's in `embeds[0].image`, not `attachments`.** Discord moves a file the embed references as `attachment://` into the embed, and leaves `attachments` empty.
- Download from `embeds[0].image.url`. It's signed and expires. The `ex` query parameter holds the expiry as a hex Unix timestamp. It needs no bot token.
- The image block has no byte size. Check the length of the downloaded bytes instead.
- **The file is a real PNG.** Discord's `image.content_type` says `image/jpeg`, but that's wrong. All five downloads from the second run start with the PNG signature (`\x89PNG`). Upload to Trello as `screenshot.png` and ignore `content_type`.
- Sizes seen: 1.9 to 4.5 MB, at 1920x1080 and 2560x1440. One was 2560x1067, so the capture follows the game window's size.
- **Always upload the screenshot to the card when there is one, but never assume there is one.** A timed-out capture may leave no `image` block, an `image.url` left as `attachment://...`, a failed download or zero bytes. In every case the card is still created, without the screenshot, and the console notes it.

## Decisions

### Time
Use the message's `timestamp` (UTC, set by Discord) as the report time, converted to Danish time (`Europe/Copenhagen`, which follows summer time) for the card. The `Time` field is the player's local clock with no time zone. One report shows 21:19 for a message posted at 10:20 UTC. Ignore `Time`.

Python on Windows has no time zone database of its own, so `zoneinfo` needs the `tzdata` package in `requirements.txt`.

### Sentry
Ignore it. Sentry capture is turned off for bug reports to save Sentry storage, which is kept for errors and crashes. That drops:
- the Sentry URL attachment on the card
- the Sentry part of the plausibility check

The public channel check is then: `Version` matches `^\d+\.\d+\.\d+\.\d+$`, or is the literal `Failed`. The game sends `Failed` when it can't read its own version, and those reports are kept.

One older report still carries a `Sentry` field. Its URL has the form `.../projects/<project>/events/<32 hex>/`, not the `?query={EVENT_ID}` template in the spec. Because the field is ignored, this doesn't matter.

### Optional fields
Reports from the hub (`DS_MAP_SpaceshipHub`) carry only Time, Player, Map and Version. This is normal, because a player may restart and report from the hub. Missing fields are left out of the card description, and no label is created for them.

### Fields on the card
Every embed field goes into the card description, in the order the game sends it, except the names in `ignore_fields` in `config.json` (`Time`, `Sentry`). A field the game adds later shows up on cards without any change to the script.

Two things still depend on field names:
- **Labels** come from `label_fields` in `config.json` (`Version`, `Mission`). If the game renames one of these, the value still shows in the description, but its label silently disappears. Update the config to match.
- **The public channel check** reads `Version`. If that field is renamed, every public report is skipped. That failure shows up right away.

### Labels
Never create an empty label, and never use a placeholder such as `[missing-description]`. If a value is missing or empty, that label is left off.

- Labels come from Version, Mission and Map (`label_fields`), plus `External` or `Internal` for the channel.
- A card with no usable screenshot gets the `No screenshot` label (`no_screenshot_label`). That covers a missing image, a failed download or zero bytes.
- The script creates a missing label the first time it needs it, with no colour, and reuses an existing label with the same name. Colours are set by hand in Trello.
- Keyword labels (Door, Stuck, Crash) and a "same session" flag were considered and left out for now.

### Testing with `--latest N`
`sync.py --latest N` creates cards for the newest N reports and nothing else. It adds no ⚙️ and never reads or writes the saved message ID, so testing against the real channel doesn't make the real run skip those reports. Running it twice creates duplicate cards.

Tested 2026-11-03 against the test board with `--latest 5` on the public channel. The cards, labels and screenshots came through correctly. Trello accepts `"color": null` when creating a label, which gives a label with no colour.

## Trello requests

- The key and token go in the `Authorization: OAuth oauth_consumer_key="...", oauth_token="..."` header, never in the query string.
- The app was created as "doesn't use Power-Up capabilities". It needs no iframe URL, OAuth or callback URL. The token comes from `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=<key>`.
- Before writing, the script checks that the list in `config.json` belongs to the board.
- Cards are created with `POST /1/cards` (form data, `idLabels` comma-separated, `pos=bottom`). The screenshot is uploaded with `POST /1/cards/{id}/attachments` as a multipart file named `screenshot.png`.

## Running

| Command | Does |
|---|---|
| `sync.py` | Every message after the saved ID |
| `sync.py --next N` | The next N reports after the saved ID, so a backlog can be worked through in steps |
| `sync.py --dry-run [--next N]` | Preview. Writes nothing |
| `sync.py --latest N` | Test mode: newest N reports, no ⚙️, no saved ID |

Messages are handled one at a time, oldest first. The saved ID lives in `%LOCALAPPDATA%\darkswarm-bug-sync\state.json`, one entry per channel, and moves after every message. That includes chatter and reports that already carry the bot's ⚙️. With no saved ID, the run starts from the beginning of the channel.

For a report, the order is: create the card, upload the screenshot, add ⚙️, save the ID. A failure stops the run before the ID moves, so the next run retries that report. The exception is a failed screenshot upload: the card already exists then, so retrying would create it twice. The card is kept, gets the "No screenshot" label, and the run carries on. `--next N` counts only reports that got a ⚙️ (cards and skipped reports), not chatter or reports that were already done.

The bot needs **Add Reactions** on the channel. Without it, the first report gets a card, the ⚙️ fails, and the run stops.

## Running on a schedule

The sync runs on the build computer, which is always on, every 15 minutes from Task Scheduler. `README.md` has the setup steps.

- **Moving machines is safe** because the ⚙️ lives in Discord. A PC with no `state.json` reads the history once, passes every ⚙️-marked report as already done, and continues.
- **Only one machine runs the sync.** The lock below works per machine.
- **The task runs as the user who ran `--set-secrets`**, with the password stored. Secrets are in that user's Credential Manager, which "Do not store password" mode can't read.
- **Lock:** every run that writes creates `sync.lock` in `%LOCALAPPDATA%\darkswarm-bug-sync\` with an exclusive create, and removes it when done. A run that finds a lock younger than 2 hours exits with code 0, since that isn't a failure. An older lock was left by a crash and is taken over. The task's 2-hour time limit matches that age.
- **Log:** `--log` sends all output, including errors and tracebacks, to `sync.log` in the same folder. Each run starts with a `=====` line and the Danish time. Past 1 MB, the log is renamed to `sync.log.old`.
- **Exit codes:** 0 when the run finished or the lock was taken by another run, 1 on any failure. Task Scheduler shows it as `LastTaskResult`.

### Blank reports
The game's empty-text check doesn't catch whitespace. One real report (`1567118429696299008`) arrived as just `##`: the game sent `## ` plus spaces, and Discord trimmed them. The script strips `##` and any whitespace after it. A report with nothing left is skipped as "empty report text".

Game-side follow-up: trim whitespace before the empty check.

### Card name
- Strip the leading `##` and following whitespace from `embeds[0].description`, then use the first line.
- Shorten only if needed (over about 100 characters). When shortened, cut it and end it with `...`.
- The full report text always goes in the card description, whether or not the name was shortened.

### Marking messages as processed
The marker is the gear reaction ⚙️ (`:gear:`). Teammates use ✅ in the channel themselves, so ✅ means nothing to the script. Only the bot's own ⚙️ counts. The gear is compared without its invisible variation selector, because Discord may return it either way.

The ⚙️ reaction and the saved last-message ID both mean "processed", not "uploaded". A report is processed once the script has finished with it, either way:

- **Card created:** the ⚙️ goes on after the card and its attachments exist, as before. A crash in between retries the report. A failed screenshot upload doesn't count as a crash: the card is kept with the "No screenshot" label (see Running).
- **Skipped** (fails the public channel check): it gets the ⚙️ too, and the skip is logged once. It is never looked at again.

The saved ID in `%LOCALAPPDATA%` moves to each message as soon as that message is processed, so the next run starts after it.

Only webhook messages are processed. Chatter from people in the channel gets no ⚙️ and is ignored. The saved ID moves past it.

A ⚙️ on a skipped message means a person posting fake reports through the leaked webhook URL sees the same reaction as a real reporter. That's accepted.

## Board workflow (decided 2026-11-04)

The board changes from one list per discipline to labels for disciplines and lists for themes.

### Discipline labels
Every report gets one or two discipline labels, each with its own colour:

| Label | Colour | Meaning |
|---|---|---|
| Tech | blue | |
| UI | sky | |
| Level Design | green | |
| Art | pink | |
| Animation | lime | |
| Game Design | purple | |
| Audio | orange | |
| Uncategorized | yellow | Claude is very unsure. A person picks the discipline. |
| Unactionable | black | The report says too little to act on. |

- **Two labels are allowed** when a report really involves two disciplines, for example a crash in a menu. That makes a wrong sort less likely: the right team still sees the card.
- Uncategorized and Unactionable stand alone. A card never has one of them together with a discipline label.
- The version, mission, map, External and No screenshot labels stay as they are. They have no colour, so the discipline labels stand out.
- The rules for which label a report gets are in `disciplines.md`.

### Theme lists
- A list groups reports about the same theme, for example Softlocking, Performance issues, Aiming issues. A list is a theme, not one exact bug.
- The team creates the theme lists by hand. Claude never creates lists.
- New reports arrive in **Incoming**, as before.
- **There's no DONE list.** A fixed report is marked complete (the card's checkbox) and stays in its theme list, so each theme keeps its count of open and fixed reports.

### Moving to the new workflow
1. **Labels first.** Each card gets its discipline label:
   - Cards in a discipline list (Incoming Tech, Incoming UI, ...) got the matching label. The team sorted them, so Claude wasn't asked. (This was a one-off for the switch-over. The old lists are gone, and `config.json` no longer lists them.)
   - Cards in Unactionable get the Unactionable label.
   - Cards in Incoming and DONE are labelled by Claude (Haiku 5.5) using `disciplines.md`.
   - Cards in DONE are also marked complete.
   - A card that already has a discipline label is left alone, so the step can be run again safely.
2. **Moving is done by hand.** The team moves the cards out of the old discipline lists when it's ready. The script doesn't move cards.
3. **Sorting into themes** has two parts:
   - **Re-sort (built, `sort.py --sort`):** run by hand now and then. It goes through Incoming and moves each labelled card into a theme list that fits. If none fits, the card stays, since the team may create a fitting list later. Uncategorized, Unactionable and completed cards stay in Incoming for a person. There are no General lists: the discipline labels already let each team find the cards left in Incoming.
   - **Only lists whose name starts with `##` get automatic sorting**, for example `## Soft locking`. A list without it, such as `UI issues`, is left alone. The team turns sorting on or off per list by renaming it.
   - **The sync labels and places new reports (built 2026-11-04).** For each batch of up to 20 new reports, Claude is asked for the labels and a `##` list, 4 reports at a time, and then the cards are created in order, straight into their list or Incoming. Progress is still saved per report. A flood of 200 reports takes about 5 minutes. If Claude can't be reached or no key is stored, cards arrive unlabelled in Incoming, and the next run labels and places them.
   - **The sort runs every hour** on the build computer, so cards in Incoming find lists the team creates later. A run where nothing changed asks Claude nothing and costs nothing. It takes a snapshot only when it's about to move cards.
   - **The sync and the sort share one lock,** so they never write to the board at the same time.
   - **A backup runs every night at 03:00.** It saves the board only. Screenshots stay in Discord: each card links to its message, and fetching the message again gives a fresh screenshot link. `backup.py --attachments` saves them too, for a full copy now and then.
   - No comments on moved cards. Reasons go in the run report and `moves.jsonl`.

### Choosing a model
`sort.py --evaluate` tested Claude against the 213 cards the team had sorted by hand (2026-11-04):

| Model | Agreed with the team | Unsure | Cost for 213 cards |
|---|---|---|---|
| Haiku 5.5, first rules | 105 | 85 | $0.06 |
| Haiku 5.5, revised rules | 156 | 14 | $0.07 |
| Sonnet 5.5, revised rules | 165 | 5 | $1.45 |

Most disagreements were cards where the rules and the hand sorting differ (lighting to Art, balance to Game Design, crashes to Tech), not mistakes. Haiku made about 8 real mistakes and Sonnet about 5. The team chose **Haiku**: it's 1/20th of the cost, and rule fixes close most of the gap.

What made the difference: the first rules told Claude to be unsure when the screenshot didn't confirm the report. Saying "a clear text is enough" cut unsure answers from 85 to 14.

## Still open

Nothing for the sync. A timed-out screenshot hasn't been seen yet, but the script doesn't depend on it (see Screenshot).