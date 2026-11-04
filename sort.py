"""Discipline labels and theme lists for the cards already on the Trello board.

New reports are labelled and placed by sync.py as they arrive. This script
handles what's already on the board:

--sort moves labelled cards in Incoming into the theme list that fits them.
Only lists whose name starts with "##" take part ("## Soft locking"); rename a
list to turn automatic sorting on or off. Cards with no fitting theme,
Uncategorized or Unactionable cards, completed cards and cards without a
discipline label stay in Incoming. It runs 5 minutes after each sync on the build computer, so
cards waiting in Incoming find new theme lists the team creates.

--label gives every open card on the board without one its discipline labels,
and marks cards in DONE complete. Cards in Unactionable get the Unactionable
label; Claude labels the rest.

--evaluate compares Claude's labels with the labels a person chose: labels the
team set, or changed after Claude set them (label_changes.jsonl says which
labels Claude set). It only reads.

--undo-moves moves the bot's cards back to where they came from, if they're
still where it put them. It shows how many cards it would move and only goes
ahead when you type "yes".

Without --apply, --sort and --label only write a preview report.

    python sort.py --sort --limit 20             (preview)
    python sort.py --sort --apply                (moves cards)
    python sort.py --sort --apply --log          (the scheduled run)
    python sort.py --label --apply
    python sort.py --evaluate --model haiku --limit 30
    python sort.py --undo-moves --since "2026-11-04 14:30"

The rules Claude follows are in disciplines.md, up to the "sort.py stops
reading here" marker. Answers are cached per card, model, rules, themes and
examples, so a rerun only pays for cards it hasn't asked about yet.
"""

import argparse
import collections
import datetime
import json
import random
import sys

import anthropic

from backup import take_snapshot
from claude_board import (
    LABEL_LOG_PATH, MODELS, MOVE_LOG_PATH, NO_THEME, AUTO_SORT_PREFIX, card_link, ensure_labels,
    log_labels, log_move, make_board, one_line, read_log,
)
from common import (
    DANISH_TIME, DATA_DIR, KEYRING_ANTHROPIC_KEY, KEYRING_TRELLO_KEY, KEYRING_TRELLO_TOKEN,
    Trello, acquire_lock, get_secret, load_config, release_lock, start_log,
)

SAMPLE_SEED = 1  # --limit picks the same cards every run, so models can be compared


def report_header(title, board, prompt, tested, cached):
    now = datetime.datetime.now(DANISH_TIME).strftime("%Y-%m-%d %H:%M")
    return [
        f"# {title}", "",
        f"- Run: {now} (Danish time)",
        f"- Model: {board.model}",
        f"- Prompt version: {prompt.hash} (changes when the rules, theme lists or examples change)",
        f"- Cards asked about: {tested}, of which {cached} were answered on an earlier run or failed, and cost nothing",
        f"- Cost of this run: ${board.cost():.2f}"
        f" ({board.usage['input'] + board.usage['cache_write'] + board.usage['cache_read']:,} input tokens,"
        f" {board.usage['output']:,} output tokens)",
        "",
    ]


def write_report(name, lines):
    stamp = datetime.datetime.now(DANISH_TIME).strftime("%Y-%m-%d_%H%M")
    path = DATA_DIR / f"{name}_{stamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def evaluate(board, limit):
    """Compare Claude's labels with the discipline labels a person chose."""
    if not LABEL_LOG_PATH.exists():
        print(f"No label log on this PC ({LABEL_LOG_PATH.name}), so Claude's own labels can't be told apart"
              " from the team's. Testing against every labelled card.")
    cards = board.board_cards()
    truth = board.team_labelled(cards)
    examples = board.label_examples(cards, truth, for_test=True)
    prompt = board.label_prompt(examples)

    example_ids = {card["id"] for group in examples.values() for card in group}
    test = [card for card in cards if card["id"] in truth and card["id"] not in example_ids]
    print(f"{len(test)} cards labelled by the team to test, {len(example_ids)} used as examples.")
    if limit and limit < len(test):
        test = random.Random(SAMPLE_SEED).sample(sorted(test, key=lambda c: c["id"]), limit)
        print(f"Testing a sample of {limit}.")

    results = board.ask_all([board.card_item(card) for card in test], prompt)
    cached = len(test) - board.usage["calls"]

    per_group = collections.defaultdict(collections.Counter)
    confusions = collections.Counter()
    disagreements, unsure, errors = [], [], []
    two_labels = 0
    for card in test:
        team = " + ".join(truth[card["id"]])
        answer = results[card["id"]]
        if isinstance(answer, str):
            per_group[team]["error"] += 1
            errors.append((card, answer))
            continue
        labels = board.labels_for(answer)
        two_labels += len(labels) == 2
        if labels in ([board.uncategorized], [board.unactionable]):
            per_group[team]["unsure"] += 1
            unsure.append((card, team, labels[0], answer))
        elif set(labels) & set(truth[card["id"]]):
            per_group[team]["agree"] += 1
        else:
            per_group[team]["disagree"] += 1
            confusions[(team, " + ".join(labels))] += 1
            disagreements.append((card, team, labels, answer))

    lines = report_header("Labelling evaluation", board, prompt, len(test), cached)
    lines += ["Agree: Claude and the team share at least one label. Unsure: Claude chose Uncategorized or Unactionable.", "",
              "| Team's labels | Tested | Agree | Disagree | Unsure | Error |", "|---|---|---|---|---|---|"]
    total = collections.Counter()
    for name, counts in sorted(per_group.items(), key=lambda item: -sum(item[1].values())):
        total.update(counts)
        lines.append(f"| {name} | {sum(counts.values())} | {counts['agree']} | {counts['disagree']} | {counts['unsure']} | {counts['error']} |")
    lines.append(f"| **All** | {sum(total.values())} | {total['agree']} | {total['disagree']} | {total['unsure']} | {total['error']} |")
    labelled = total["agree"] + total["disagree"]
    if labelled:
        lines += ["", f"When Claude gave discipline labels, one of them matched the team on {total['agree']} of {labelled}"
                      f" cards ({100 * total['agree'] / labelled:.0f}%). It gave two labels on {two_labels} cards."]

    lines += ["", "## Most common disagreements", "", "| Team's labels | Claude's labels | Cards |", "|---|---|---|"]
    lines += [f"| {team} | {claude} | {count} |" for (team, claude), count in confusions.most_common()]
    lines += ["", "## Disagreements", ""]
    for card, team, labels, answer in sorted(disagreements, key=lambda d: (d[1], d[2])):
        lines += [f"- [{one_line(card['name'], 80)}]({card_link(card)})  ",
                  f"  Team: **{team}**, Claude: **{' + '.join(labels)}**. {answer['reason']}"]
    lines += ["", "## Uncategorized and Unactionable", ""]
    for card, team, label, answer in unsure:
        lines += [f"- [{one_line(card['name'], 80)}]({card_link(card)})  ",
                  f"  Team: **{team}**, Claude: **{label}**. {answer['reason']}"]
    if errors:
        lines += ["", "## Errors", ""]
        lines += [f"- [{one_line(card['name'], 80)}]({card_link(card)}): {error}" for card, error in errors]

    path = write_report(f"evaluate_{board.model}", lines)
    print(f"Agree {total['agree']}, disagree {total['disagree']}, unsure {total['unsure']}, errors {total['error']}."
          f" Cost ${board.cost():.2f}.")
    print(f"Report: {path}")


def label_board(board, config, limit, apply):
    lists = board.trello.request("GET", f"/boards/{board.trello.board_id}/lists", params={"fields": "name"})
    list_names = {lst["id"]: lst["name"] for lst in lists}
    unactionable_list = board.sorting["unactionable_list_id"]
    done_list = board.sorting["done_list_id"]

    cards = sorted(board.board_cards(), key=lambda c: c["id"])
    prompt = board.label_prompt(board.label_examples(cards, board.team_labelled(cards)))

    # Cards that already have one of Claude's labels are done, unless they're in DONE and not yet complete.
    todo, already = [], 0
    for card in cards:
        labelled = board.has_board_label(card)
        needs_complete = card["idList"] == done_list and not card.get("dueComplete")
        if labelled:
            already += 1
        if not labelled or needs_complete:
            todo.append(card)
    print(f"{len(cards)} open cards, {already} already have a discipline label, {len(todo)} to change.")
    if limit:
        todo = todo[:limit]

    to_ask = [card for card in todo if not board.has_board_label(card) and card["idList"] != unactionable_list]
    results = board.ask_all([board.card_item(card) for card in to_ask], prompt)
    cached = len(to_ask) - board.usage["calls"]

    plan = []  # (card, label names to add or None on error, source, reason, mark complete)
    for card in todo:
        complete = card["idList"] == done_list and not card.get("dueComplete")
        if board.has_board_label(card):
            plan.append((card, [], "labels already set", "", complete))
        elif card["idList"] == unactionable_list:
            plan.append((card, [board.unactionable], "team's list", "", complete))
        else:
            answer = results[card["id"]]
            if isinstance(answer, str):
                plan.append((card, None, "error", answer, False))
            else:
                plan.append((card, board.labels_for(answer), "Claude", answer["reason"], complete))

    changed, failed = 0, 0
    if apply and any(labels or complete for _, labels, _, _, complete in plan):
        # The board as it was before this run. Labelling deletes nothing, so the screenshots aren't needed.
        take_snapshot(board.trello, config, "before-label-apply", attachments=False)
        label_ids = ensure_labels(board)
        for card, labels, source, reason, complete in plan:
            if labels is None:
                continue
            try:
                for name in labels:
                    board.trello.request("POST", f"/cards/{card['id']}/idLabels", params={"value": label_ids[name]})
                if complete:
                    board.trello.request("PUT", f"/cards/{card['id']}", params={"dueComplete": "true"})
            except RuntimeError as error:
                failed += 1
                print(f"  {card_link(card)}: {error}")
                continue
            changed += 1
            log_labels({"card": card["id"], "link": card_link(card), "name": card["name"],
                        "added_labels": labels, "marked_complete": complete, "source": source, "reason": reason})

    title = "Labels written to the board" if apply else "Proposed labels (preview, nothing was written)"
    lines = report_header(title, board, prompt, len(to_ask), cached)
    groups = collections.defaultdict(list)
    for card, labels, source, reason, complete in plan:
        group = "Errors" if labels is None else " + ".join(labels) or "Only marked complete"
        groups[group].append((card, source, reason, complete))
    order = sorted(groups, key=lambda g: (g == "Errors", g in (board.uncategorized, board.unactionable), -len(groups[g])))
    lines += ["| Labels | Cards |", "|---|---|"] + [f"| {group} | {len(groups[group])} |" for group in order] + [""]
    for group in order:
        lines += [f"## {group} ({len(groups[group])})", ""]
        for card, source, reason, complete in groups[group]:
            where = list_names.get(card["idList"], "?")
            done_note = ", marked complete" if complete else ""
            detail = f": {reason}" if reason else ""
            lines.append(f"- [{one_line(card['name'], 80)}]({card_link(card)}) ({where}, from {source}{done_note}){detail}")
        lines.append("")

    path = write_report("labels" if apply else "labels-preview", lines)
    summary = ", ".join(f"{group}: {len(groups[group])}" for group in order) or "Nothing to do"
    print(f"{summary}. Claude cost ${board.cost():.2f}.")
    if apply:
        print(f"Labelled {changed} cards, {failed} failed. Every change is logged in {LABEL_LOG_PATH}.")
    print(f"Report: {path}")


def sort_incoming(board, config, limit, apply):
    themes = board.theme_lists()
    if not themes:
        print(f"No list has automatic sorting turned on. Start a list's name with '{AUTO_SORT_PREFIX} ' to turn it on.")
        return
    print(f"Theme lists: {', '.join(themes)}")

    cards = board.board_cards()
    prompt = board.theme_prompt({name: [card for card in cards if card["idList"] == list_id]
                                 for name, list_id in themes.items()})

    special = {board.uncategorized, board.unactionable}
    candidates, skipped = [], collections.Counter()
    for card in sorted((card for card in cards if card["idList"] == board.incoming_id), key=lambda c: c["id"]):
        names = {label["name"] for label in card["labels"]}
        if card.get("dueComplete"):
            skipped["marked complete"] += 1
        elif names & special:
            skipped["Uncategorized or Unactionable"] += 1
        elif not names & set(board.disciplines):
            skipped["no discipline label yet"] += 1
        else:
            candidates.append(card)
    print(f"{len(candidates) + sum(skipped.values())} cards in Incoming, {len(candidates)} to sort."
          + "".join(f" Skipped, {reason}: {count}." for reason, count in skipped.items()))
    if limit:
        candidates = candidates[:limit]

    results = board.ask_all([board.card_item(card) for card in candidates], prompt)
    cached = len(candidates) - board.usage["calls"]

    groups = collections.defaultdict(list)  # theme name, NO_THEME or "Errors" -> [(card, reason)]
    for card in candidates:
        answer = results[card["id"]]
        if isinstance(answer, str):
            groups["Errors"].append((card, answer))
        else:
            groups[answer["theme"]].append((card, answer["reason"]))

    moved, not_moved = 0, []
    to_move = [(card, theme, reason) for theme in themes for card, reason in groups.get(theme, [])]
    if apply and to_move:
        take_snapshot(board.trello, config, "before-sort-apply", attachments=False)
        for card, theme, reason in to_move:
            # A person may have moved the card while Claude was answering.
            current = board.trello.request("GET", f"/cards/{card['id']}", params={"fields": "idList,closed"})
            if current["idList"] != board.incoming_id or current["closed"]:
                not_moved.append((card, "no longer in Incoming"))
                continue
            try:
                board.trello.request("PUT", f"/cards/{card['id']}", params={"idList": themes[theme], "pos": "bottom"})
            except RuntimeError as error:
                not_moved.append((card, str(error)))
                continue
            moved += 1
            log_move({"type": "move", "card": card["id"], "link": card_link(card), "name": card["name"],
                      "from": board.incoming_id, "to": themes[theme], "to_name": theme, "model": board.model,
                      "reason": reason, "by": "sort"})

    title = "Cards moved to theme lists" if apply else "Proposed sorting of Incoming (preview, nothing was moved)"
    lines = report_header(title, board, prompt, len(candidates), cached)
    order = [theme for theme in themes if theme in groups] + [g for g in (NO_THEME, "Errors") if g in groups]
    heading = {NO_THEME: "Stays in Incoming (no theme fits)"}
    lines += ["| Theme | Cards |", "|---|---|"]
    lines += [f"| {heading.get(group, group)} | {len(groups[group])} |" for group in order] + [""]
    for group in order:
        lines += [f"## {heading.get(group, group)} ({len(groups[group])})", ""]
        for card, reason in groups[group]:
            labels = ", ".join(label["name"] for label in card["labels"] if label["name"] in board.label_colors)
            lines.append(f"- [{one_line(card['name'], 80)}]({card_link(card)}) ({labels}): {reason}")
        lines.append("")
    if not_moved:
        lines += ["## Not moved", ""] + [f"- [{one_line(card['name'], 80)}]({card_link(card)}): {why}" for card, why in not_moved]

    # Quiet scheduled runs shouldn't fill the data folder with reports.
    if to_move or not apply:
        path = write_report("sort" if apply else "sort-preview", lines)
        print(f"Report: {path}")
    print(", ".join(f"{heading.get(group, group)}: {len(groups[group])}" for group in order)
          + f". Claude cost ${board.cost():.2f}.")
    if apply:
        print(f"Moved {moved} cards, {len(not_moved)} not moved." + (f" Logged in {MOVE_LOG_PATH}." if moved else ""))


def undo_moves(trello, config, since):
    """Move cards the bot moved back to where they came from, if they're still in the list it put them in."""
    latest = {}
    for entry in read_log(MOVE_LOG_PATH):
        if datetime.datetime.fromisoformat(entry["time"]) < since:
            continue
        if entry["type"] == "move":
            latest[entry["card"]] = entry
        elif entry["type"] == "undo":
            latest.pop(entry["card"], None)
    if not latest:
        sys.exit("No moves to undo in that period.")

    # Find out what would happen before asking, so the question gives the real numbers.
    print(f"Checking {len(latest)} cards the bot moved...")
    to_undo, left = [], 0
    for entry in latest.values():
        current = trello.request("GET", f"/cards/{entry['card']}", params={"fields": "idList,closed"})
        if current["idList"] == entry["to"] and not current["closed"]:
            to_undo.append(entry)
        else:
            left += 1
    if not to_undo:
        sys.exit(f"Nothing to undo: all {left} cards have been moved by someone since.")

    first = min(entry["time"] for entry in to_undo)[:16].replace("T", " ")
    last = max(entry["time"] for entry in to_undo)[:16].replace("T", " ")
    print(f"\nThis moves {len(to_undo)} cards back to the list they came from, moved by the bot between {first} and {last}:")
    for name, count in collections.Counter(entry.get("to_name", "?") for entry in to_undo).most_common():
        print(f"  {count:4}  out of {name}")
    if left:
        print(f"{left} more were moved by someone since, and are left alone.")
    if not sys.stdin.isatty():
        sys.exit("Undo has to be confirmed, so run it in a terminal.")
    try:
        answer = input(f"\nType yes to move {len(to_undo)} cards: ")
    except EOFError:
        answer = ""
    if answer.strip().lower() != "yes":
        sys.exit("Nothing was moved.")

    take_snapshot(trello, config, "before-undo-moves", attachments=False)
    undone, moved_meanwhile = 0, 0
    for entry in to_undo:
        # Someone may have moved the card while the question was waiting for an answer.
        current = trello.request("GET", f"/cards/{entry['card']}", params={"fields": "idList,closed"})
        if current["idList"] != entry["to"] or current["closed"]:
            moved_meanwhile += 1
            continue
        trello.request("PUT", f"/cards/{entry['card']}", params={"idList": entry["from"], "pos": "bottom"})
        undone += 1
        log_move({"type": "undo", "card": entry["card"], "link": entry["link"], "name": entry["name"],
                  "from": entry["to"], "to": entry["from"]})
    print(f"Moved {undone} cards back. Every undo is logged in {MOVE_LOG_PATH}.")
    if moved_meanwhile:
        print(f"{moved_meanwhile} were moved by someone while you were confirming, and were left alone.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--evaluate", action="store_true", help="test Claude on the labels the team chose")
    mode.add_argument("--label", action="store_true", help="give every open card its discipline labels")
    mode.add_argument("--sort", action="store_true", help="move labelled cards in Incoming into matching theme lists")
    mode.add_argument("--undo-moves", action="store_true", help="move cards the bot moved back to where they came from")
    parser.add_argument("--apply", action="store_true", help="with --label or --sort: write the changes to the board")
    parser.add_argument("--since", metavar='"YYYY-MM-DD HH:MM"',
                        help="with --undo-moves: only undo moves made since then (Danish time)")
    parser.add_argument("--model", choices=MODELS, help="model to use (default: sorting.model in config.json)")
    parser.add_argument("--limit", type=int, metavar="N", help="only handle N cards")
    parser.add_argument("--log", action="store_true", help="write all output to sort.log, for scheduled runs")
    args = parser.parse_args()

    if args.log:
        start_log("sort", sys.argv[1:])
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.limit is not None and args.limit < 1:
        sys.exit("--limit needs a number of 1 or more.")
    if args.apply and not (args.label or args.sort):
        sys.exit("--apply only goes with --label or --sort.")
    since = datetime.datetime.min.replace(tzinfo=DANISH_TIME)
    if args.since:
        try:
            since = datetime.datetime.strptime(args.since, "%Y-%m-%d %H:%M").replace(tzinfo=DANISH_TIME)
        except ValueError:
            sys.exit('--since needs a time like "2026-11-04 14:30".')

    needed = [KEYRING_TRELLO_KEY, KEYRING_TRELLO_TOKEN] + ([] if args.undo_moves else [KEYRING_ANTHROPIC_KEY])
    secrets = {name: get_secret(name) for name in needed}
    if not all(secrets.values()):
        sys.exit("Missing secrets. Run: python sync.py --set-secrets")
    config = load_config()
    trello = Trello(secrets[KEYRING_TRELLO_KEY], secrets[KEYRING_TRELLO_TOKEN], config)

    # Runs that write share the sync's lock, so they never touch the board at the same time as a sync.
    writes = args.apply or args.undo_moves
    if writes and not acquire_lock("sort.py"):
        return
    try:
        if args.undo_moves:
            undo_moves(trello, config, since)
            return
        board = make_board(config, trello, secrets[KEYRING_ANTHROPIC_KEY], MODELS.get(args.model))
        print(f"Model: {board.model}")
        try:
            if args.evaluate:
                evaluate(board, args.limit)
            elif args.sort:
                sort_incoming(board, config, args.limit, args.apply)
            else:
                label_board(board, config, args.limit, args.apply)
        finally:
            board.save_answers()
    except (RuntimeError, anthropic.APIError) as error:
        sys.exit(f"\nStopped: {error}")
    finally:
        if writes:
            release_lock()


if __name__ == "__main__":
    main()
