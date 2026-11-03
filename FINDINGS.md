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
`sync.py --latest N` creates cards for the newest N reports and nothing else. It adds no ✅ and never reads or writes the saved message ID, so testing against the real channel doesn't make the real run skip those reports. Running it twice creates duplicate cards.

Tested 2026-11-03 against the test board with `--latest 5` on the public channel. The cards, labels and screenshots came through correctly. Trello accepts `"color": null` when creating a label, which gives a label with no colour.

## Trello requests

- The key and token go in the `Authorization: OAuth oauth_consumer_key="...", oauth_token="..."` header, never in the query string.
- The app was created as "doesn't use Power-Up capabilities". It needs no iframe URL, OAuth or callback URL. The token comes from `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=<key>`.
- Before writing, the script checks that the list in `config.json` belongs to the board.
- Cards are created with `POST /1/cards` (form data, `idLabels` comma-separated, `pos=bottom`). The screenshot is uploaded with `POST /1/cards/{id}/attachments` as a multipart file named `screenshot.png`.

## Still to build

- The full run: process every report after the saved message ID, add ✅ to processed messages, and save the ID in `%LOCALAPPDATA%\darkswarm-bug-sync\state.json`. The bot needs the Add Reactions permission on the channel first.

### Blank reports
The game's empty-text check doesn't catch whitespace. One real report (`1567118429696299008`) arrived as just `##`: the game sent `## ` plus spaces, and Discord trimmed them. The script strips `##` and any whitespace after it. A report with nothing left is skipped as "empty report text".

Game-side follow-up: trim whitespace before the empty check.

### Card name
- Strip the leading `##` and following whitespace from `embeds[0].description`, then use the first line.
- Shorten only if needed (over about 100 characters). When shortened, cut it and end it with `...`.
- The full report text always goes in the card description, whether or not the name was shortened.

### Marking messages as processed
The ✅ reaction and the saved last-message ID both mean "processed", not "uploaded". A report is processed once the script has finished with it, either way:

- **Card created:** the ✅ goes on after the card and its attachments exist, as before. A crash in between retries the report.
- **Skipped** (fails the public channel check): it gets the ✅ too, and the skip is logged once. It is never looked at again.

The saved ID in `%LOCALAPPDATA%` moves to each message as soon as that message is processed, so the next run starts after it.

Only webhook messages are processed. Chatter from people in the channel gets no ✅ and is ignored. The saved ID moves past it.

A ✅ on a skipped message means a person posting fake reports through the leaked webhook URL sees the same tick as a real reporter. That's accepted.

## Still open

Nothing. A timed-out screenshot hasn't been seen yet, but the script doesn't depend on it (see Screenshot).