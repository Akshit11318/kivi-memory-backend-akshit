#!/usr/bin/env python3
"""Generate a large (>=10,000 word), deterministic stress-test corpus.

Builds three artifacts in this directory:
  - corpus.txt       one paragraph per line, >=10,000 words total
  - ground_truth.json  per-paragraph expected hits (what a perfect system
                        would APPLY) plus per-paragraph vocabulary notes
  - teaches.json     the PARTIAL set of observations to replay before
                      running the corpus -- only ~60% of the vocabulary
                      below is taught; the rest appears in the corpus but
                      the notebook has never seen it ("partial learning")

Vocabulary spans three categories, ~56 entries total:
  - name: pure personal-name respellings, never ambiguous once taught
  - homograph: a brand/product name that collides with an ordinary English
    word (Kivi/kiwi, Groww/grow, Notion/notion, Slack/slack, ...) -- these
    need real sense-checking, not just a stored form match
  - phonetic: a technical term with a plausible ASR misspelling but no
    sense ambiguity (Grafana/graffana, Postgres/postgress, ...)

Deterministic: fixed seed, re-running overwrites the same three files with
the same content.

Usage:
    uv run python scripts/stress_test/generate_corpus.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260908
TARGET_WORDS = 10500
TAUGHT_FRACTION = 0.6

OUT_DIR = Path(__file__).resolve().parent

# -- Vocabulary -------------------------------------------------------------
# Every entry's sentence templates place the vocabulary word in the middle
# of the sentence, never as the first word -- sidesteps sentence-initial
# capitalization entirely, so `forms`/`canonical` casing in the corpus
# always matches exactly what's written here.

NAME_VOCAB = [
    ("Akshit", ["akshith"]),
    ("Ankita", ["ankeeta"]),
    ("Priya", ["priyaa"]),
    ("Ravi", ["ravee"]),
    ("Gautam", ["gautham"]),
    ("Srinivas", ["sreenivas"]),
    ("Chowdhury", ["choudhury"]),
    ("Tanmay", ["tanmaay"]),
    ("Prateek", ["pratik"]),
    ("Deeksha", ["diksha"]),
    ("Lakshmi", ["laxmi"]),
    ("Chaithanya", ["chaitanya"]),
    ("Nikhil", ["nikhal"]),
    ("Rohith", ["rohit"]),
    ("Akash", ["aakash"]),
    ("Ishan", ["ishaan"]),
    ("Kabeer", ["kabir"]),
    ("Zaara", ["zara"]),
    ("Ayesha", ["aisha"]),
    ("Divyaa", ["divya"]),
    ("Megna", ["meghna"]),
    ("Varoon", ["varun"]),
    ("Naveenn", ["naveen"]),
    ("Snehaa", ["sneha"]),
    ("Arjunn", ["arjun"]),
    ("Kaviya", ["kavya"]),
    ("Tanvee", ["tanvi"]),
    ("Yashh", ["yash"]),
    ("Vikramm", ["vikram"]),
    ("Shreyaa", ["shreya"]),
]

NAME_TEMPLATES = [
    "Please loop in {word} before the next status update.",
    "I asked {word} to review the draft over the weekend.",
    "The manager confirmed that {word} will join the call tomorrow.",
    "Send the invoice details to {word} by end of day.",
    "According to {word}, the shipment should arrive on Thursday.",
    "We scheduled a quick sync with {word} to discuss the roadmap.",
    "Everyone thanked {word} for organizing the offsite so well.",
    "The client specifically requested that {word} lead the demo.",
]

HOMOGRAPH_VOCAB = [
    (
        "Kivi",
        ["kiwi", "kivi"],
        "Our platform Kivi handles ASR post-processing for enterprise clients.",
        [
            "The on-call engineer restarted {word} after the nightly batch job failed.",
            "We rolled back the {word} deployment once the error rate spiked.",
            "The staging environment for {word} needs a fresh database migration.",
        ],
        [
            "We packed some {word} and grapes for the picnic on Saturday.",
            "The fruit salad tasted better once we added sliced {word}.",
            "Her favorite snack growing up was {word} sprinkled with a little salt.",
        ],
    ),
    (
        "Groww",
        ["grow", "groww"],
        "He opened a mutual fund SIP on Groww last month.",
        [
            "She moved her entire stock portfolio to {word} after reading reviews online.",
            "The onboarding flow for {word} now takes under two minutes to complete.",
            "He set up an automatic SIP contribution through {word} every payday.",
        ],
        [
            "With enough sunlight the tomato saplings should {word} within a few weeks.",
            "The company wants its regional offices to {word} steadily this year.",
            "Good soil and regular watering help the seedlings {word} much faster.",
        ],
    ),
    (
        # Every canonical below is a deliberately stylized respelling (one
        # doubled/altered letter) of the ordinary English word in `forms`,
        # never just a case difference -- kivi's already_canonical cheap
        # door fires on any case-insensitive match regardless of sense, so
        # a pure-case pair (e.g. canonical "Notion" with form "notion")
        # would never reach the sense-check at all, in either sense. That's
        # correct system behavior, not a bug, but it means the pair could
        # never demonstrate one. A real spelling difference (Kivi/kiwi,
        # Groww/grow) is what actually exercises the LLM helper.
        "Notionn",
        ["notion"],
        "The team documents every spec and meeting note in Notionn.",
        [
            "Update the launch checklist in {word} before the review meeting.",
            "The onboarding guide lives in a shared {word} workspace now.",
            "She linked the design doc from {word} in the ticket description.",
        ],
        [
            "He had only a vague {word} of what the client actually wanted.",
            "The whole {word} of working weekends made the team uncomfortable.",
            "It was a strange {word}, but she couldn't shake the feeling.",
        ],
    ),
    (
        "Slackk",
        ["slack"],
        "Ping the on-call engineer on Slackk if the alert doesn't clear.",
        [
            "The release announcement went out on {word} right after the deploy.",
            "Most of the design feedback happens in a dedicated {word} channel.",
            "He missed the update because he wasn't checking {word} that morning.",
        ],
        [
            "Cut him some {word}, he only joined the project last week.",
            "The rope went completely {word} once the anchor hit the seabed.",
            "There was too much {word} in the schedule to hit the deadline.",
        ],
    ),
    (
        "Dockerr",
        ["docker"],
        "Deploy the payments service using Dockerr so environments stay consistent.",
        [
            "The build pipeline packages every service into a {word} image.",
            "We finally migrated the legacy job runner onto {word} last sprint.",
            "Rebuilding the {word} image fixed the missing dependency issue.",
        ],
        [
            "The old {word} at the harbor helped unload the cargo ship by hand.",
            "Her grandfather worked as a {word} for over twenty years.",
            "A retired {word} told us stories about the old shipping routes.",
        ],
    ),
    (
        "Postmann",
        ["postman"],
        "We test every new API endpoint with Postmann before merging.",
        [
            "Import the updated collection into {word} before running the suite.",
            "The QA team automated the regression checks using {word} scripts.",
            "He shared the {word} environment file so everyone hits the same host.",
        ],
        [
            "The {word} delivered the package just before the storm started.",
            "As a kid she wanted to be a {word} because of the uniform.",
            "The {word} rang the bell twice since no one answered the door.",
        ],
    ),
    (
        "Zoomm",
        ["zoom"],
        "Join the client kickoff on Zoomm at three in the afternoon.",
        [
            "The interview panel switched to {word} after the office wifi dropped.",
            "She recorded the training session on {word} for anyone who missed it.",
            "The support call moved from a phone line to a {word} meeting.",
        ],
        [
            "The sports car seemed to {word} past every other vehicle on the highway.",
            "Kids love watching the toy rocket {word} across the living room floor.",
            "The motorbike would {word} down the empty street every morning.",
        ],
    ),
    (
        "Mintt",
        ["mint"],
        "He tracks every monthly expense using Mintt.",
        [
            "The budgeting dashboard on {word} flagged an unusual charge this week.",
            "She linked her savings account to {word} to track spending automatically.",
            "The subscription reminder came straight from the {word} notifications.",
        ],
        [
            "A sprig of fresh {word} made the lemonade taste much better.",
            "He always orders {word} chocolate chip when it's on the menu.",
            "The garden has a small patch of {word} growing near the fence.",
        ],
    ),
    (
        "Credd",
        ["cred"],
        "Pay the credit card bill this month through Credd for the reward points.",
        [
            "The reminder to pay the bill came from {word} two days early.",
            "He redeemed a small cashback voucher through the {word} app.",
            "Her credit score improved after she started using {word} regularly.",
        ],
        [
            "He earned serious street {word} after fixing the server at midnight.",
            "Nobody questioned her {word} once they saw the finished project.",
            "The intern gained a lot of {word} with the team that week.",
        ],
    ),
    (
        "Slicee",
        ["slice"],
        "The Slicee card gives cashback on every online purchase.",
        [
            "She applied for a {word} card after seeing the referral offer.",
            "The statement from {word} listed every transaction from last week.",
            "He upgraded his {word} account to unlock the higher cashback tier.",
        ],
        [
            "Could you pass me another {word} of the birthday cake, please.",
            "He ordered an extra {word} of cheese on his sandwich.",
            "A thin {word} of lemon finished off the iced tea nicely.",
        ],
    ),
    (
        "Jarr",
        ["jar"],
        "He saves spare change automatically using the Jarr app.",
        [
            "The weekly round-up feature in {word} added almost two hundred rupees.",
            "She set a savings goal inside {word} for the upcoming trip.",
            "The notification from {word} showed her total savings for the month.",
        ],
        [
            "The pickles were stored in a large glass {word} on the shelf.",
            "He accidentally knocked the cookie {word} off the kitchen counter.",
            "Grandma kept spare buttons in an old {word} by the sewing machine.",
        ],
    ),
    (
        "Angell",
        ["angel"],
        "Check the Angell portfolio dashboard before the market opens.",
        [
            "He transferred additional funds into his {word} trading account.",
            "The quarterly report from {word} arrived in his inbox this morning.",
            "She placed a limit order through {word} right before the close.",
        ],
        [
            "Everyone at the shelter said she was an absolute {word} to the animals.",
            "The choir sang softly, almost like a chorus of {word} voices.",
            "He called his grandmother an {word} for raising three kids alone.",
        ],
    ),
    (
        "Ringg",
        ["ring"],
        "The Ringg doorbell camera caught the delivery on video this morning.",
        [
            "The motion alert from {word} went off twice during the afternoon.",
            "He checked the {word} app footage after hearing a noise outside.",
            "She installed a second {word} camera near the back gate.",
        ],
        [
            "She wore a small silver {word} on her right hand.",
            "The boxers circled each other slowly around the {word}.",
            "He could hear the phone {word} from the other room.",
        ],
    ),
    (
        "Windowss",
        ["windows"],
        "Update the Windowss drivers before the client demo tomorrow.",
        [
            "The laptop kept freezing until we reinstalled {word} completely.",
            "IT pushed a mandatory {word} security patch overnight.",
            "The new build only supports the latest version of {word}.",
        ],
        [
            "She opened the {word} to let some fresh air into the room.",
            "The storm shattered two {word} on the ground floor.",
            "Sunlight poured in through the tall {word} of the old house.",
        ],
    ),
    (
        "Applee",
        ["apple"],
        "The new Applee update finally fixed the battery drain bug.",
        [
            "He waited in line for hours to get the latest {word} phone.",
            "The design team only ships builds tested on {word} devices.",
            "Support confirmed the crash only happens on {word} hardware.",
        ],
        [
            "She packed an {word} and a sandwich for the school trip.",
            "An {word} a day, or so the old saying goes.",
            "The orchard let visitors pick their own {word} every autumn.",
        ],
    ),
    (
        "Uberr",
        ["uber"],
        "Book an Uberr for the airport run first thing tomorrow.",
        [
            "The driver from {word} arrived almost ten minutes early.",
            "She cancelled the {word} once her colleague offered a ride instead.",
            "He filed an expense report for the {word} rides taken that week.",
        ],
        [
            "The whole plan felt {word} ambitious for a team this small.",
            "He described the presentation as {word} impressive to everyone in the room.",
            "The renovation turned out to be an {word} expensive mistake.",
        ],
    ),
]

PHONETIC_VOCAB = [
    ("Grafana", ["grafanna", "graffana"]),
    ("Postgres", ["postgress"]),
    ("Terraform", ["terrafrom"]),
    ("Kubernetes", ["kubernets", "kubernetis"]),
    ("Snowflake", ["snowflak"]),
    ("Jenkins", ["jenkings"]),
    ("Redis", ["readis"]),
    ("Nginx", ["enginx"]),
    ("Kafka", ["kafkaa"]),
    ("Airflow", ["airflo"]),
    ("Tableau", ["tablow"]),
    ("Figma", ["figmaa"]),
]

PHONETIC_TEMPLATES = [
    "Restart the {word} service before the incident review begins.",
    "The alert from {word} has been silent since last night's deploy.",
    "We migrated the {word} configuration to the new cluster last week.",
    "Check the {word} dashboard for anything unusual overnight.",
    "The on-call rotation flagged a {word} timeout around midnight.",
]

FILLER_SENTENCES = [
    "The quarterly all-hands meeting has been rescheduled to next Friday afternoon.",
    "Attendance is optional for remote employees who are traveling this week.",
    "The vendor confirmed the shipment will arrive sometime before the weekend.",
    "Everyone agreed the new seating arrangement made the office feel less crowded.",
    "The finance team is still reconciling last quarter's expense reports.",
    "A brief power outage delayed the morning stand-up by about ten minutes.",
    "The cafeteria menu changes every Monday according to the new schedule.",
    "Several teammates took the day off to celebrate the long weekend.",
    "The printer on the third floor has been out of toner since Tuesday.",
    "Facilities finally fixed the air conditioning in the east wing conference room.",
    "The onboarding checklist was updated to include the new security training.",
    "Traffic on the highway was unusually heavy during the evening commute.",
    "The weather forecast predicts light rain for most of the afternoon.",
    "A new coffee machine was installed near the second floor break room.",
    "The annual survey results will be shared with the whole company next month.",
    "Parking near the office has gotten noticeably harder to find lately.",
    "The book club decided to read something shorter for the next meeting.",
    "Several plants in the lobby were replaced after the renovation project.",
    "The security badge system will be upgraded over the coming weekend.",
    "A local bakery started delivering pastries to the office every Friday.",
    "The recycling bins were moved closer to the elevators last week.",
    "Everyone was reminded to submit their timesheets before the holiday.",
    "The building management sent a notice about the elevator maintenance.",
    "A few employees organized a small farewell lunch for a retiring colleague.",
    "The quarterly newsletter included an update on the community volunteering program.",
    "The gym downstairs added new equipment as part of its winter refresh.",
    "Public transit delays affected several commuters during the storm.",
    "The library added a new section for local history and travel guides.",
    "A neighborhood festival is planned for the first weekend of next month.",
    "The city announced new bike lanes along the main avenue downtown.",
]


def _build_vocab_entries() -> list[dict]:
    entries: list[dict] = []
    for canonical, forms in NAME_VOCAB:
        entries.append(
            {
                "canonical": canonical,
                "forms": forms,
                "category": "name",
                "teach_text": None,
                "correct_templates": NAME_TEMPLATES,
                "wrong_templates": [],
            }
        )
    for canonical, forms, teach_text, correct_templates, wrong_templates in HOMOGRAPH_VOCAB:
        entries.append(
            {
                "canonical": canonical,
                "forms": forms,
                "category": "homograph",
                "teach_text": teach_text,
                "correct_templates": correct_templates,
                "wrong_templates": wrong_templates,
            }
        )
    for canonical, forms in PHONETIC_VOCAB:
        entries.append(
            {
                "canonical": canonical,
                "forms": forms,
                "category": "phonetic",
                "teach_text": None,
                "correct_templates": PHONETIC_TEMPLATES,
                "wrong_templates": [],
            }
        )
    return entries


def _teach_observations(entry: dict) -> list[dict]:
    return [
        {
            "user_id": "stress",
            "source": "dictionary_add",
            "canonical": entry["canonical"],
            "forms": entry["forms"],
            "context": entry["teach_text"],
        }
    ]


def main() -> None:
    rng = random.Random(SEED)
    vocab = _build_vocab_entries()
    rng.shuffle(vocab)

    split = int(len(vocab) * TAUGHT_FRACTION)
    taught = vocab[:split]
    untaught = vocab[split:]
    taught_by_canonical = {e["canonical"]: e for e in taught}

    teaches: list[dict] = []
    for entry in taught:
        teaches.extend(_teach_observations(entry))

    paragraphs: list[str] = []
    ground_truth: list[dict] = []
    word_count = 0
    paragraph_index = 0

    while word_count < TARGET_WORDS:
        sentences: list[tuple[str, dict | None]] = []  # (sentence, expected_hit_or_None)

        # 2-3 filler sentences for padding and realism.
        for _ in range(rng.randint(2, 3)):
            sentences.append((rng.choice(FILLER_SENTENCES), None))

        # 2-4 vocabulary sentences per paragraph, mixing taught/untaught and
        # (for homographs) correct/wrong sense.
        for _ in range(rng.randint(2, 4)):
            entry = rng.choice(vocab)
            is_taught = entry["canonical"] in taught_by_canonical

            use_wrong_sense = entry["category"] == "homograph" and entry["wrong_templates"] and rng.random() < 0.4
            use_canonical_already = rng.random() < 0.1

            if use_wrong_sense:
                template = rng.choice(entry["wrong_templates"])
                surface = rng.choice(entry["forms"])
                sentence = template.format(word=surface)
                # Homograph in the wrong sense must never be corrected, taught or not.
                sentences.append((sentence, None))
            elif use_canonical_already:
                template = rng.choice(entry["correct_templates"])
                sentence = template.format(word=entry["canonical"])
                # Already the canonical spelling -- nothing to correct.
                sentences.append((sentence, None))
            else:
                template = rng.choice(entry["correct_templates"])
                surface = rng.choice(entry["forms"])
                sentence = template.format(word=surface)
                # already_canonical fires whenever the surface matches the
                # canonical case-insensitively, regardless of who taught
                # what -- safety net in case any vocab entry's forms ever
                # include a case-only variant of its own canonical.
                if is_taught and surface.lower() != entry["canonical"].lower():
                    sentences.append((sentence, {"from": surface, "to": entry["canonical"]}))
                else:
                    sentences.append((sentence, None))

        rng.shuffle(sentences)
        paragraph = " ".join(s for s, _ in sentences)
        expected_hits = [hit for _, hit in sentences if hit is not None]

        paragraphs.append(paragraph)
        ground_truth.append({"paragraph": paragraph_index, "expected_hits": expected_hits})
        word_count += len(paragraph.split())
        paragraph_index += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "corpus.txt").write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    (OUT_DIR / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "teaches.json").write_text(json.dumps(teaches, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "vocab_manifest.json").write_text(
        json.dumps(
            {
                "taught": sorted(e["canonical"] for e in taught),
                "untaught": sorted(e["canonical"] for e in untaught),
                "total_vocab": len(vocab),
                "total_words": word_count,
                "total_paragraphs": paragraph_index,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {paragraph_index} paragraphs, {word_count} words")
    print(f"vocab: {len(vocab)} total, {len(taught)} taught, {len(untaught)} untaught")
    total_hits = sum(len(g["expected_hits"]) for g in ground_truth)
    print(f"ground truth: {total_hits} expected hits across the corpus")


if __name__ == "__main__":
    main()
