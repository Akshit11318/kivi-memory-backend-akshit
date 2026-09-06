# Post-ASR Difficulty Catalogue — measured, not imagined

**Status:** this file replaces `eval/topics.list` and `eval/user_themes.md` as the
source of truth for what goes into `eval/cases/`. Those two were written from a
model's *idea* of ASR failure. This one was written by running the difficulties
through `src/kivi_memory/` and writing down what the code actually did.

Every row marked **[M]** was executed against the real pipeline
(`learner.explicit` → `store` → `retrieve` → `decide` → `produce.rewrite`) on a
throwaway SQLite store, for `--profile exact` and `--profile phonetic`. The
"expected" columns are transcripts of observed output, not predictions.

**Measured against `54ae390`.** The phonetic figures were taken while
`retrieve/phonetic.py` (Metaphone plus the `v↔w` swap) was still uncommitted;
that file has since landed in `54ae390` byte-identical to the version measured,
so everything below reproduces on `main`. If the retriever changes — a real
Double Metaphone, a different first-letter rule, a different length floor — then
D3 and cases 03, 05, 06, 10, 11, 14–17 must be re-measured, not re-reasoned.

---

## 0. Why the previous two files cannot be used

Not a style complaint. Four concrete problems, in order of cost.

### 0.1 Most examples are outside the machine's reach

`decide` rewrites **one formatted token into one canonical token**. That is the
whole product. Roughly 60% of the rows in `user_themes.md` need something else:

| Row in `user_themes.md` | What it needs | We have |
| --- | --- | --- |
| `met for men` → `Metformin` | 3 tokens → 1 | 1 → 1 |
| `fast api` → `FastAPI` | 2 → 1 | 1 → 1 |
| `white field` → `Whitefield` | 2 → 1 | 1 → 1 |
| `blink it` → `Blinkit` | 2 → 1 | 1 → 1 |
| `you pee eye` → `UPI` | 3 → 1 | 1 → 1 |
| `k why see` → `KYC` | 3 → 1 | 1 → 1 |
| `h s r` → `HSR` | 3 → 1 | 1 → 1 |
| `zithro my sin` → `Azithromycin` | 3 → 1 | 1 → 1 |
| `sue oh mow two` → `suo motu` | 4 → 2 | 1 → 1 |
| `dolo six fifty` → `Dolo-650` | number formatting | not our job |
| `cepto` → `Zepto` | first letter changes | gate needs `a[0] == b[0]` |

A dataset whose cases the system is structurally unable to pass is not an
evaluation, it is a list of feature requests. They are kept below, but as
**out-of-scope ABSTAIN cases** — which is genuinely worth testing, because the
right answer there is "do nothing, and say why".

### 0.2 Two claims in `topics.list` are factually wrong

Measured with `jellyfish.metaphone` as actually wired in `retrieve/phonetic.py`:

| `topics.list` claim | Measured |
| --- | --- |
| §5: "Stored `Aaditya`, ASR emits `adithya` (Double Metaphone ATTY)" → phonetic APPLY | `aaditya` → `TTY`, `aditya` → `ATTY`, `adithya` → `ATTY`. **No intersection, so phonetic ABSTAINs.** Metaphone keeps the initial `A` for `aditya` and drops it for `aaditya`. |
| §6: "Indian name `Ravi` hashing to RF, identical to `Robbie`" | `ravi` → `{RF, RW}`, `robbie` → `{RB}`. **They never collide.** The docstring in `phonetic.py` already says this; `topics.list` did not get the memo. |
| §1/§5/§6: "Double Metaphone" throughout | `jellyfish` ships **classic single-code Metaphone**. There are no primary/secondary codes, so any case justified by them is unfalsifiable. |

### 0.3 The mechanism prose is decorative

`/suːpəbeɪs/` for Supabase, `/njʊərɪps/` for NeurIPS, `/kroʊsɪn/` for Crocin —
invented transcriptions attached to make a guess look like phonetics. None of
them changes what the code does. Where a case needs a mechanism, this file states
the **grapheme operation** (`a → aa`, `ksh → x`, `th → t`), because that is what
the gate and the metaphone coder actually see.

### 0.4 One user, one voice, two names

29 cases, and `Aditya`/`Kivi` carry 21 of them. Every persona is a
Bangalore-metro engineer. Nothing in the set would catch a regression that only
hits a Chennai surname, a Bengali surname, a doubled-consonant brand, or a
non-Indian colleague. **Budget in this file: `Aaditya` and `Kivi` appear in 2
cases total** — the brief's own example, and the hyphen case that reuses the
`kiwi` surface the brief names as the reason the phonetic profile exists.
Everything else draws from §4.

---

## 1. The capability envelope (measured)

Six hard walls. Every case in §3 is labelled by the wall it tests. A proposed
case that trips a wall *without meaning to* is a bad case.

| # | Wall | Where | Consequence for cases |
| --- | --- | --- | --- |
| W1 | **1:1 only.** `diff_words` keeps only equal-length `replace` spans; inserts, deletes and unequal replaces are dropped. | `learner/align.py:77` | A correction that merges or splits words teaches **nothing**. Compound recovery is out. |
| W2 | **First letter must match**, then ratio ≥ 0.6. | `learner/align.py:108` | `cepto→Zepto`, `elaiyaraja→Ilaiyaraaja`, `ditya→Aaditya` are unlearnable by correction. Only `dictionary_add` can create such a row, and then only `exact` retrieves it. |
| W3 | **Case is never a correction.** Gate rejects `case_only`; `decide_token` returns `already_canonical` when `token.lower() == canonical.lower()`. | `learner/align.py:121`, `decide/conservative.py:39` | `sarvam→Sarvam`, `arxiv→arXiv`, `hsr→HSR` all ABSTAIN. But `archive→arXiv` **applies** — letters differ, not just case. |
| W4 | **Phonetic needs first letter + length ≥ 3 + key intersection.** | `retrieve/phonetic.py:29,59` | `om` (2 chars) is never retrievable phonetically, and three very common Indic patterns are invisible to metaphone — see D3. |
| W5 | **Cue gate is ±2 content words, set intersection.** Empty cues = applies everywhere. | `learner/align.py:134`, `decide/conservative.py:42` | Homograph safety exists **only** if the memory was taught from a sentence. A `dictionary_add` for `Kivi` will rewrite the fruit. |
| W6 | **Uniqueness, not ranking.** Two canonicals for one surface → `conflicting_canonicals`, always ABSTAIN. | `decide/conservative.py:28` | Two real colleagues who sound alike = permanent no-op. That is the intended answer, and it must be a case. |

---

## 2. The difficulty inventory

What actually goes wrong between the microphone and the third transcript. Each
entry: the real phenomenon, why we believe it is real, and what this system owes
the user when it happens.

### Group A — the difficulty is *a spelling the world does not agree on*

The only group where memory is the correct solution rather than a patch.

**D1. Deliberate personal respelling.** Real people carry spellings that no
acoustic model and no LLM prior will ever produce, because the spelling was
chosen *against* convention on purpose. Public, documented examples:
`Rajkumar → Rajkummar` (added `m`), `Ayushman Khurana → Ayushmann Khurrana`
(added `n`, added `r`), `Ekta → Ektaa`, `Tushar → Tusshar`,
`Ajay Devgan → Ajay Devgn` (dropped `a`), `Vivek → Viviek`. The practice —
numerology-driven respelling — is common enough in India that name-numerology
consultancies sell it as a service, and ordinary users do the same without being
famous. Localization writeups on Hindi romanization note the same driver: if an
astrologer says a name should not have six letters or should not start with `k`,
the spelling changes and the person keeps it for life.
→ **In scope. The flagship APPLY.** No formatter gets `Rajkummar` from audio.

**D2. Romanization has no standard.** Names reach Latin script through no agreed
system, so one name has many *correct* spellings and the user owns exactly one:
`Lakshmi/Laxmi/Luxmi`, `Meera/Mira`, `Moorthy/Murthy`, `Akash/Aakash`,
`Bakshi/Baxi`, `Pooja/Puja`, `Deeksha/Diksha`, `Prateek/Pratik`,
`Chowdhury/Choudhury/Choudhary`. The recurring operations are `a↔aa`, `i↔ee`,
`u↔oo`, `ksh↔x`, `t↔th`, `w↔ou`. ASR emits the corpus-frequent variant; the
formatter capitalizes it and stops.
→ **In scope. The volume case.**

**D3. …but the phonetic profile is blind to the three commonest operations.**
Measured, and the most useful finding in this file:

| Operation | Example | metaphone(surface) | metaphone(canonical) | zero-shot retrieval |
| --- | --- | --- | --- | --- |
| `i ↔ ee` | `mira` / `Meera` | `MR` | `MR` | **works** |
| `u ↔ oo` | `murthy` / `Moorthy` | `MR0` | `MR0` | **works** |
| doubled consonant | `ayushman` / `Ayushmann` | `AYXMN` | `AYXMN` | **works** |
| **`ksh ↔ x`** | `lakshmi` / `Laxmi` | `LKXM` | `LKSM` | **fails** |
| **initial `a ↔ aa`** | `akash` / `Aakash` | `AKX` | `KX` | **fails** |
| **dental `t ↔ th`** | `gautam` / `Gautham` | `KTM` | `K0M` | **fails** |

So `--profile phonetic` helps with vowel length and doubling, and helps **not at
all** with the aspirate and conjunct patterns that dominate South Indian and
Sanskritic names. Those need the surface present in `forms` — i.e. `exact` after
one teach. The eval must *show* this asymmetry instead of claiming phonetic
dominates exact. Note that this also invalidates the old set's flagship phonetic
claim, since `aditya`/`Aaditya` is itself an initial-`a↔aa` pair.

**D4. Brand names are misspelled on purpose.** A whole generation of products
ships a name that is a dictionary word with letters removed or doubled: `Groww`,
`Lyft`, `Flickr`, `Tumblr`, `Fiverr`, `Digg`, `Grindr`, `Meesho`. ASR hears the
dictionary word, the formatter writes the dictionary word, and both are wrong
forever. Same shape as D1 but non-Indian and non-name — good for proving the
notebook is about lexical identity, not about people.
→ **In scope.**

**D5. Stylized casing.** `arXiv`, `iPhone`, `eSIM`, `openSUSE`. Split by W3: when
the incoming surface differs in *letters* (`archive` → `arXiv`) the system
applies; when it differs only in *case* (`arxiv` → `arXiv`) it must ABSTAIN with
`already_canonical`. Both halves are cases.

### Group B — the difficulty is *the formatter*, not the ASR

The brief's own framing: two inputs, and either can be the liar.

**D6. Formatter over-correction.** Documented behaviour of LLM transcript
post-correction, not a hypothetical — the generative-error-correction literature
names "over-correction" as a standard failure, where rare surfaces regress to
frequent ones and entities appear that were never spoken, and proposes
conservative filters (minimum edit length, confidence floors ~0.7) specifically
to suppress it. Concretely: ASR gets `sreenivas` right and the formatter writes
`Srinivas`; ASR gets `Groww` right and the formatter writes `Grow`. The notebook
is the only component that can undo this, because `decide` reads the
**formatted** token, not the ASR token.
→ **In scope, and the strongest argument for the product.**

**D7. Contraction expansion and disfluency stripping shift every index.**
`im gonna ping karthik` → `I'm going to ping Karthik.` (5 tokens → 6);
`matlab um i will ask priya na` → `I will ask Priya.` (7 → 4). Hinglish discourse
particles (`matlab`, `na`, `yaar`, `arre`) get stripped exactly like `um`, and
they are far more common in real Indian dictation than `um` is. Any positional
`token[i] → token[i]` mapping corrupts an unrelated word.
→ **In scope, as an alignment test.**

**D8. Punctuation the formatter attaches.** Possessive `Priya's`, quotes
`"Neil"`, hyphen compounds `Sarvam-Kiwi`, terminal `.`/`?`. Retrieval must strip,
production must re-attach, and the hyphen case must replace one segment only.
→ **In scope.**

### Group C — the difficulty is *real* but memory must refuse

The half of the product that is "leaves the line alone". Under-tested in the old
files, and where a shipped notebook does damage.

**D9. Same sound, two people.** The user works with `Riya` and with `Ria`; with
`Neel` and with `Neal`; with `Karan` and with `Karen`. No lexical fact resolves
this — only speaker identity, which we do not have.
→ **ABSTAIN, `conflicting_canonicals`.**

**D10. Brand vs the ordinary word it stole.** `Kivi`/`kiwi` is the brief's
example, and it is not a special case: `Tumblr`/`tumbler` (the steel tumbler in
every Indian kitchen), `Groww`/`grow`, `Lyft`/`lift`, `Digg`/`dig` all have the
same shape. The cue gate is the only defence, and it exists only if the memory
was taught from a sentence (W5). Both directions must be cases: the household
line ABSTAINs with `context_mismatch`, the work line APPLYs. Cases 30/31 use
`Tumblr` rather than `Kivi` so this behaviour is verified on an entity the
brief did not hand us — measured cues from the teach line are `{post, update}`.

**D11. ASR hallucination.** Whisper-family models emit text nobody said. An AP
investigation found invented content — including invented medical content —
across thousands of samples, with one university researcher reporting
hallucinations in 8 of 10 samples examined; a 2025 clinical-ASR study across
Indian languages measured insertion rates near 37–39% for Hindi and English on
some systems and described models "caught in a loop". So the formatted string
handed to us can contain a span with no audio behind it, e.g. a trailing
`Thank you for watching!`.
→ **Behaviour owed: rewrite the real token, leave the hallucinated span exactly
as it is, do not crash, do not "clean up".** Measured: it does.

**D12. ASR deletion.** The same clinical study reports deletion rates up to 84%
for Kannada, attributed to conjunct-heavy morphology; onset clipping when a mic
opens late is the everyday version. The target word can be **absent** from the
formatted text, or arrive truncated (`ditya`, which W2 then blocks).
→ **ABSTAIN, `no_memory`. Never insert a word the formatter did not produce.**

**D13. Script switching.** Indian dictation flips scripts mid-session; the ASR
may return `प्रिया` where the notebook holds `priyaa`. No transliteration layer
ships here.
→ **ABSTAIN, `no_memory`, documented as a limitation rather than hidden.**

**D14. Spelled-out letters and acronyms.** `h s r`, `k y c`, `you pee eye`,
`q b r`. Real and frequent — user-facing writeups on dictation list acronyms
alongside client names as the top failure cluster — and W1 makes them
unreachable here.
→ **ABSTAIN, out of scope, documented.**

**D15. Content edits wearing a spelling costume.** The user changes `Friday` to
`Thursday`, `ten` to `twenty`, `there` to `their`. Edit distance cannot separate
these from a personal spelling: `there`/`their` scores 0.8 while `kiwi`/`kivi`
scores 0.75, which is exactly why `REFUSE_HOMOPHONE_PAIRS` exists instead of a
threshold.
→ **Learner writes zero rows.**

**D16. The gate cannot tell a respelling from a different person.** Measured
false learn: correcting `Sanjay owns billing.` → `Sanjeev owns billing.` passes
the grapheme gate (same `s`, ratio 0.77), becomes a memory, and thereafter
rewrites every `Sanjay` to `Sanjeev`. Same shape: `Aryan`/`Arjun`,
`Shrey`/`Shreyas`, `Nikhil`/`Nikhilesh`.
→ **Current behaviour is a false APPLY.** See §5 Q1.

**D17. Metaphone collides two different real people.** Measured false APPLY:
memory `Karen` (a real colleague, taught by `dictionary_add`), utterance mentions
`Karan` (a different real colleague). `karan` → `KRN`, `karen` → `KRN`, same
first letter, so `--profile phonetic` rewrites `Karan` → `Karen`. `exact`
correctly ABSTAINs. The `phonetic.py` docstring claims the first-letter rule
kills short-token false positives; for this pair it does not.
→ **Current behaviour is a false APPLY, phonetic only.** See §5 Q1.

**D18. Nothing to do.** Cold store, irrelevant store, empty input, garbage input,
a sentence with no personal vocabulary, `--profile off`. This is the majority of
real utterances and it was 2 of 29 cases.
→ **`formatted == memory_aware`, byte for byte.**

**D19. Teaching a name in a short sentence context-locks it.** Measured, and it
is the cause of the only two failures in the current suite
(`kivi eval --profiles off,exact,phonetic` → `exact 26/28`, `phonetic 26/28`).

Every `correction` stores cues, and a short teach line stores almost none:

| Teach line | Canonical | Cues stored |
| --- | --- | --- |
| `Gautam will lead.` | `Gautham` | `{lead}` |
| `Ananya approved.` | `Ananyaa` | `{approved}` |
| `we use the kiwi app daily` | `Kivi` | `{use, app, daily}` |

Then the next real utterance has a completely different neighbourhood — the
window around `Gautam` in *"Ask Gautam and Ananya to join the sprint demo."* is
`{ask, ananya, join}` — so the intersection is empty and the decider returns
`context_mismatch`. The user taught the spelling of a colleague's name and it
silently stopped working one sentence later.

For a homograph (`kiwi`) that gate is exactly right. For a person's name it is
exactly wrong: a name's spelling belongs to the person, not to the sentence. The
mechanism is attached to the wrong axis — **teach source** (`correction` gets
cues, `dictionary_add` gets none) instead of **homograph risk**. The two current
failures and case 32 are the same bug seen from opposite ends: corrections
over-restrict, dictionary adds under-restrict.
→ **See §5 Q3.** This one is worth fixing before generating cases, because it
changes the expected value of every correction-taught APPLY in §3.

---

## 3. The case list

44 cases. `[M]` = expected values transcribed from a real run. `X` = `exact`,
`P` = `phonetic`. `off` is always ABSTAIN with formatted returned unchanged, so
it is omitted from the tables.

Teach column: `dict(canonical; forms)` = `kivi observe --dictionary-add`;
`corr(formatted → final)` = `kivi observe --correction`; `—` = empty store.

### 3.1 Group A — APPLY on personal spelling (D1, D2, D4, D5)

| # | id | Teach | ASR | formatted | expected memory-aware | X | P | tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | `apply_brief_pdf` **[M]** | corr(`Ask Aditya to review the Sarvam Kiwi service.` → `Ask Aaditya to review the Sarvam Kivi service.`) | `ask aditya to review the sarvam kiwi service` | `Ask Aditya to review the Sarvam Kiwi service.` | `Ask Aaditya to review the Sarvam Kivi service.` | APPLY | APPLY | brief parity — **1 of 2 Aaditya/Kivi** |
| 02 | `apply_respell_added_consonant` **[M]** | corr(`Rajkumar shared the deck.` → `Rajkummar shared the deck.`) | `rajkumar shared the deck` | `Rajkumar shared the deck.` | `Rajkummar shared the deck.` | APPLY | APPLY | D1 |
| 03 | `apply_respell_zeroshot_phonetic` **[M]** | dict(`Ayushmann`; `ayushmann`) | `ayushman is joining the call` | `Ayushman is joining the call.` | X unchanged / P `Ayushmann is joining the call.` | ABSTAIN `no_memory` | APPLY | D1 + the W4 win |
| 04 | `apply_respell_dropped_letter` **[M]** | dict(`Devgn`; `devgn, devgan`) | `devgan sir approved it` | `Devgan sir approved it.` | `Devgn sir approved it.` | APPLY | APPLY | D1, subtractive respell |
| 05 | `apply_variant_i_to_ee` **[M]** | dict(`Meera`; `meera`) | `mira sent the invoice` | `Mira sent the invoice.` | X unchanged / P `Meera sent the invoice.` | ABSTAIN | APPLY | D2, D3 row 1 |
| 06 | `apply_variant_u_to_oo` **[M]** | dict(`Moorthy`; `moorthy`) | `murthy will sign off` | `Murthy will sign off.` | X unchanged / P `Moorthy will sign off.` | ABSTAIN | APPLY | D2, D3 row 2 |
| 07 | `apply_variant_ksh_after_teach` **[M]** | corr(`Lakshmi handled the audit.` → `Laxmi handled the audit.`) | `lakshmi handled the audit` | `Lakshmi handled the audit.` | `Laxmi handled the audit.` | APPLY | APPLY | D2 `ksh→x` is learnable even though W4 is blind to it |
| 08 | `apply_bengali_surname_variant` **[M]** | dict(`Choudhury`; `choudhury, chowdhury`) | `chowdhury signed the lease` | `Chowdhury signed the lease.` | `Choudhury signed the lease.` | APPLY | APPLY | D2, non-Hindi region |
| 09 | `apply_brand_doubled_letter` **[M]** | dict(`Groww`; `groww, grow`) | `i moved my sip to grow` | `I moved my SIP to grow.` | `I moved my SIP to Groww.` | APPLY | APPLY | D4 |
| 10 | `apply_brand_dropped_vowel_zeroshot` **[M]** | dict(`Lyft`; `lyft`) | `book a lift to the airport` | `Book a lift to the airport.` | X unchanged / P `Book a Lyft to the airport.` | ABSTAIN | APPLY | D4 + W4 win |
| 11 | `apply_brand_flickr_zeroshot` **[M]** | dict(`Flickr`; `flickr`) | `upload them to flicker` | `Upload them to flicker.` | X unchanged / P `Upload them to Flickr.` | ABSTAIN | APPLY | D4 |
| 12 | `apply_stylized_letters_differ` **[M]** | dict(`arXiv`; `arxiv, archive`) | `the paper is on archive` | `The paper is on archive.` | `The paper is on arXiv.` | APPLY | APPLY | D5, in-scope half |
| 13 | `apply_internal_codename` **[M]** | dict(`Chitragupt`; `chitragupt, chitragupta`) | `migrate the chitragupta queue` | `Migrate the Chitragupta queue.` | `Migrate the Chitragupt queue.` | APPLY | APPLY | D1 for org jargon |

> Case 13 must be a real **letters** difference, not a capitalization fix — W3
> makes `chitragupta → Chitragupta` ABSTAIN with `already_canonical`.

### 3.2 Group A′ — the honest ABSTAINs the phonetic profile cannot reach (D3, W4)

These four exist so nobody can claim `phonetic` dominates `exact`.

| # | id | Teach | ASR | formatted | expected | X | P | tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 14 | `phonetic_blind_ksh_x` **[M]** | dict(`Laxmi`; `laxmi`) | `lakshmi handled the audit` | `Lakshmi handled the audit.` | unchanged | ABSTAIN | ABSTAIN | `LKXM ≠ LKSM` |
| 15 | `phonetic_blind_initial_aa` **[M]** | dict(`Aakash`; `aakash`) | `akash owns the migration` | `Akash owns the migration.` | unchanged | ABSTAIN | ABSTAIN | `AKX ≠ KX` |
| 16 | `phonetic_blind_dental_th` **[M]** | dict(`Gautham`; `gautham`) | `gautam reviewed the pr` | `Gautam reviewed the PR.` | unchanged | ABSTAIN | ABSTAIN | `KTM ≠ K0M` |
| 17 | `phonetic_short_token_floor` **[M]** | dict(`Ohm`; `ohm`) | `om joined the standup` | `Om joined the standup.` | unchanged | ABSTAIN | ABSTAIN | W4 length ≥ 3 |

### 3.3 Group B — the formatter is the liar (D6)

| # | id | Teach | ASR | formatted | expected memory-aware | X | P | tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | `formatter_regressed_name` **[M]** | dict(`Sreenivas`; `sreenivas`) | `ask sreenivas to join` | `Ask Srinivas to join.` | `Ask Sreenivas to join.` | APPLY | APPLY | D6; ASR was right |
| 19 | `formatter_regressed_brand` **[M]** | dict(`Fiverr`; `fiverr`) | `the fiverr invoice is ready` | `The Fiver invoice is ready.` | `The Fiverr invoice is ready.` | APPLY | APPLY | D6 on a brand |
| 20 | `formatter_regressed_western_name` **[M]** | dict(`Sofia`; `sofia, sophia`) | `sofia joins from berlin` | `Sophia joins from Berlin.` | `Sofia joins from Berlin.` | APPLY | APPLY | D6, non-Indian; `Sofia→Sophia` is a reported real dictation error |

### 3.4 Group B′ — alignment and punctuation (D7, D8)

| # | id | Teach | ASR | formatted | expected memory-aware | X | P | tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | `align_contraction_expansion` **[M]** | dict(`Karthick`; `karthick, karthik`) | `im gonna ping karthik` | `I'm going to ping Karthik.` | `I'm going to ping Karthick.` | APPLY | APPLY | D7, 5 → 6 tokens |
| 22 | `align_hinglish_filler_stripped` **[M]** | dict(`Priyaa`; `priyaa, priya`) | `matlab um i will ask priya na` | `I will ask Priya.` | `I will ask Priyaa.` | APPLY | APPLY | D7, 7 → 4, real fillers |
| 23 | `align_asr_stutter` **[M]** | dict(`Deeksha`; `deeksha, diksha`) | `ask ask diksha for the file` | `Ask Diksha for the file.` | `Ask Deeksha for the file.` | APPLY | APPLY | D7, repeated ASR token |
| 24 | `punct_possessive` **[M]** | dict(`Priyaa`; `priyaa, priya`) | `priya's laptop is slow` | `Priya's laptop is slow.` | `Priyaa's laptop is slow.` | APPLY | APPLY | D8, clitic preserved |
| 25 | `punct_hyphen_segment` **[M]** | dict(`Kivi`; `kivi, kiwi`) | `the sarvam kiwi rollout` | `The Sarvam-Kiwi rollout.` | `The Sarvam-Kivi rollout.` | APPLY | APPLY | D8, one segment only — **2 of 2 Aaditya/Kivi** |
| 26 | `punct_quoted_token` **[M]** | dict(`Neel`; `neel, neil`) | `neil said quote ship it` | `"Neil" said, "ship it."` | `"Neel" said, "ship it."` | APPLY | APPLY | D8, quotes preserved |
| 27 | `multi_mention_per_token` **[M]** | dict(`Pooja`; `pooja, puja`) | `puja told puja to call puja` | `Puja told Puja to call Puja.` | `Pooja told Pooja to call Pooja.` | APPLY ×3 | APPLY ×3 | per-token, not all-or-nothing |
| 28 | `two_entities_one_line` **[M]** | dict(`Sreenivas`; `sreenivas, srinivas`) + dict(`Groww`; `groww, grow`) | `srinivas checked the grow dashboard` | `Srinivas checked the Grow dashboard.` | `Sreenivas checked the Groww dashboard.` | APPLY ×2 | APPLY ×2 | independent per-token decisions |

### 3.5 Group C — refusal (D9–D15, D18)

| # | id | Teach | ASR | formatted | expected | X | P | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 29 | `refuse_conflict_two_people` **[M]** | dict(`Riya`; `riya, ria`) + dict(`Ria`; `ria, riya`) | `ria sent the deck` | `Ria sent the deck.` | unchanged | ABSTAIN | ABSTAIN | `conflicting_canonicals`, both memory ids in the trace (D9, W6) |
| 30 | `refuse_homograph_household` **[M]** | corr(`Post the update on Tumbler.` → `Post the update on Tumblr.`) — learns cues `{post, update}` | `buy two steel tumbler for the kitchen` | `Buy two steel tumbler for the kitchen.` | unchanged | ABSTAIN | ABSTAIN | `context_mismatch` (D10, W5) |
| 31 | `apply_homograph_work_line` **[M]** | same teach as 30 | `post the update on tumbler tonight` | `Post the update on Tumbler tonight.` | `Post the update on Tumblr tonight.` | APPLY | APPLY | the paired positive: cue overlap |
| 32 | `refuse_dictionary_add_has_no_cues` **[M]** | dict(`Groww`; `groww, grow`) | `the plants will grow faster now` | `The plants will grow faster now.` | **currently `…will Groww faster…`** | APPLY | APPLY | W5 exposed: `dictionary_add` stores no cues, so nothing gates it. Documented limitation — §5 Q2 |
| 33 | `refuse_already_canonical` **[M]** | dict(`Meera`; `meera, mira`) | `meera approved it` | `Meera approved it.` | unchanged | ABSTAIN | ABSTAIN | `already_canonical` (W3) |
| 34 | `refuse_case_only_sentence_initial` **[M]** | dict(`Sarvam`; `sarvam`) | `sarvam ai is hiring` | `sarvam AI is hiring.` | unchanged, still lowercase | ABSTAIN | ABSTAIN | `already_canonical` — we do not fix casing (W3, D5) |
| 35 | `tolerate_hallucinated_tail` **[M]** | dict(`Karthick`; `karthick, karthik`) | `ask karthik for the invoice` | `Ask Karthik for the invoice. Thanks for watching!` | `Ask Karthick for the invoice. Thanks for watching!` | APPLY on target only | same | D11: fix the real token, leave the invented span byte-identical |
| 36 | `refuse_deleted_target` **[M]** | dict(`Moorthy`; `moorthy, murthy`) | `murthy will sign the papers` | `The papers will be signed.` | unchanged | ABSTAIN | ABSTAIN | D12: never insert a word the formatter dropped |
| 37 | `refuse_onset_clipped` **[M]** | dict(`Aaditya`; `aaditya, aditya`) | `ditya will confirm` | `Ditya will confirm.` | unchanged | ABSTAIN | ABSTAIN | D12 + W2 first letter. Uses the brief entity only as *setup*, asserts nothing about it |
| 38 | `refuse_script_switch` **[M]** | dict(`Priyaa`; `priyaa, priya`) | `प्रिया ने भेजा` | `प्रिया ने भेजा.` | unchanged | ABSTAIN | ABSTAIN | D13, no transliteration layer |
| 39 | `refuse_multitoken_compound` **[M]** | dict(`Blinkit`; `blinkit`) | `order it on blink it` | `Order it on blink it.` | unchanged | ABSTAIN | ABSTAIN | D14 + W1 |
| 40 | `refuse_spelled_letters` **[M]** | dict(`HSR`; `hsr`) | `traffic near h s r layout` | `Traffic near h s r layout.` | unchanged | ABSTAIN | ABSTAIN | D14 + W1 + W3 |
| 41 | `learner_refuse_content_edit` **[M]** | corr(`Ship it on Friday.` → `Ship it on Thursday.`) | `ship it on friday` | `Ship it on Friday.` | unchanged, **0 rows written** | ABSTAIN | ABSTAIN | D15 `not_grapheme_similar` |
| 42 | `learner_refuse_grammar_homophone` **[M]** | corr(`Send it to there team.` → `Send it to their team.`) | `send it to there team` | `Send it to there team.` | unchanged, **0 rows written** | ABSTAIN | ABSTAIN | D15 `refused_homophone` |
| 43 | `noop_clinic_line_empty_store` **[M]** | — | `patient reports mild fever since monday` | `Patient reports mild fever since Monday.` | identical | ABSTAIN | ABSTAIN | D18, non-tech domain |
| 44 | `noop_irrelevant_store_dispatch_line` **[M]** | dict(`Choudhury`; …) + dict(`Deeksha`; …) | `the truck will reach the warehouse by six` | `The truck will reach the warehouse by six.` | identical | ABSTAIN | ABSTAIN | D18, `no_memory` on every token |

### 3.6 Port unchanged from the existing set

Already correct and cheap — copy, don't rewrite:
`case_09_empty_garbage_input`, `case_12_cold_start_reset`,
`case_13_duplicate_observe_idempotent`, `case_15_multi_user_isolation`,
`case_22_merge_dictionary_forms`, `case_23_reinforcement_crossing_threshold`,
`case_25_confidence_boundary_075`, `case_27_invalid_profile_error`,
`case_05_weak_confidence_abstain`, `case_06_observe_no_assertion`,
`case_11_word_boundary` (keep the `Kivimaki` substring test, but re-teach it
from a §4 entity so it stops being a third `Kivi` case).

That gives **44 new + 11 ported = 55** cases, with `Aaditya`/`Kivi` asserted in 2.

---

## 4. Entity pools (use these instead of two names)

Sample without replacement. No entity may appear in more than **3** cases; no
first name may appear in more than **2**.

**Respelled personal names (D1)** — the canonical is the *user's*, the surface is
what ASR/the formatter produces:
`Rajkummar/rajkumar`, `Ayushmann/ayushman`, `Khurrana/khurana`, `Ektaa/ekta`,
`Tusshar/tushar`, `Devgn/devgan`, `Viviek/vivek`, `Snehaa/sneha`,
`Maheshh/mahesh`, `Priyaa/priya`, `Ravee/ravi`.

**Romanization variants (D2)** — pick the pair, then pick which side the user owns:
`Meera/Mira`, `Moorthy/Murthy`, `Laxmi/Lakshmi`, `Aakash/Akash`, `Baxi/Bakshi`,
`Pooja/Puja`, `Deeksha/Diksha`, `Prateek/Pratik`, `Sreenivas/Srinivas`,
`Gautham/Gautam`, `Karthick/Karthik`, `Chaithanya/Chaitanya`, `Swetha/Shweta`,
`Choudhury/Chowdhury`, `Seeta/Sita`, `Neesha/Nisha`, `Neel/Neil/Neal`.

**Different people who collide (D9, D16, D17)** — never merge these:
`Riya`/`Ria`, `Karan`/`Karen`, `Rohan`/`Rowan`, `Sanjay`/`Sanjeev`,
`Aryan`/`Arjun`, `Aadhya`/`Adhya`, `Shrey`/`Shreyas`.

**Brands misspelled on purpose (D4)**: `Groww/grow`, `Lyft/lift`,
`Flickr/flicker`, `Tumblr/tumbler`, `Fiverr/fiver`, `Meesho/mesho`,
`Digg/dig`.

**Out-of-reach on purpose (D14, W1/W2)**: `Blinkit/blink it`, `Zepto/cepto`,
`HSR/h s r`, `KYC/k y c`, `UPI/you pee eye`, `Whitefield/white field`,
`Ilaiyaraaja/elaiyaraja`.

**Stylized casing (D5)**: `arXiv/archive`, `arXiv/arxiv`, `iPhone/iphone`,
`eSIM/esim`.

**Sentence domains** — rotate, do not stack them all in engineering. Two cases
maximum per domain: engineering standup · fintech/SIP · clinic OPD note ·
school parent message · logistics dispatch · real-estate site visit · HR
recruiting · newsroom desk · household/grocery · college lab · legal filing ·
customer support ticket.

### 4.1 Entity ledger for §3 (check this before adding a case)

Assertion counts in the 44-case list, after rebalancing. Anything not listed is
used once.

| Entity | Cases | Count |
| --- | --- | --- |
| `Kivi` | 01, 25 | **2 (at brief budget)** |
| `Aaditya` | 01 asserted; 37 setup-only | **2 (at brief budget)** |
| `Groww` | 09, 28, 32 | 3 (at cap) |
| `Priyaa` | 22, 24, 38 | 3 (at cap) |
| `Sreenivas` | 18, 28 | 2 |
| `Meera` | 05, 33 | 2 |
| `Laxmi` / `Lakshmi` | 07, 14 | 2 |
| `Moorthy` | 06, 36 | 2 |
| `Karthick` | 21, 35 | 2 |
| `Choudhury` | 08, 44 | 2 |
| `Deeksha` | 23, 44 | 2 |
| `Tumblr` | 30, 31 | 2 |
| `Sarvam` | 34 asserted; appears in the 01/25 sentences | 1 |

---

## 5. Decisions I need from you

**Q1 — D16/D17 are measured false APPLYs. Bug or documented limitation?**
- `Sanjay → Sanjeev` gets learned as a spelling correction (grapheme gate cannot
  see that these are two people).
- `Karan → Karen` gets rewritten under `--profile phonetic` (`KRN == KRN`).

Three options: (a) write them as **known-limitation** cases whose expected value
is today's wrong output — honest but ships a footgun; (b) write them as expected
**ABSTAIN** and add the guard, roughly *if both surfaces are ≥ 4 chars and their
edit distance ≥ 2 and neither is a stored form of the other, refuse* — 5 lines in
`decide` plus a config constant; (c) restrict `phonetic` to surfaces that differ
only by the vowel-length / doubling operations in D3. **My recommendation: (b)**,
because a per-user notebook that renames colleagues is worse than one that
abstains, and the eval already has the vocabulary for a new refuse reason.

**Q2 — case 32: should `dictionary_add` be cue-gated?** Today `dict(Groww)` will
rewrite "the plants will grow faster". The README says this is intentional
("Empty cues → no gate. That word applies anywhere."). Keep as documented, or add
an optional `--context "…"` to `observe --dictionary-add`?

**Q3 — D19: should the cue gate key off homograph risk instead of teach source?**
This is the one I'd fix first; it is currently failing 2 of 29 cases and it
breaks the "teach once, works later" demo journey for names.

The signal is already in the data: **was the surface the formatter handed us
capitalized mid-sentence?**

| Teach line | Formatted surface | Formatter's read | Gate |
| --- | --- | --- | --- |
| `Gautam will lead.` | `Gautam` | proper noun | **no cue gate** — a name applies everywhere |
| `we use the kiwi app daily` | `kiwi` (lowercase, mid-sentence) | common noun | **keep cue gate** — homograph risk is real |

So: store cues as today, but have `decide` consult them only when the memory was
created from a surface the formatter did *not* treat as a proper noun. That is a
one-boolean column on `memories` plus one clause in `decide_token`, it keeps
case 30/31 (`Tumblr`/`tumbler`) passing, and it makes cases 02 and 20 pass for
the right reason instead of being deleted. Alternatives: require ≥2 cue overlap
only for lowercase surfaces; or add `observe --scope word|context` and make the
user say. **Recommendation: the capitalization signal**, with `--scope` as the
manual override.

**Q4 — where do D14's out-of-reach cases live?** They pass trivially (everything
ABSTAINs on `no_memory`), so they measure nothing about *this* system, but they
are the honest record of what a word notebook cannot do. Keep all 4 in the main
set, or move them to a separate `eval/cases/out_of_scope/` folder that the
reported score does not average over? **Recommendation: separate folder**, so
the headline pass rate is not inflated by cases that cannot fail.

---

## 6. Generation contract for the case-writing model

Paste §1–§4 with this. Nothing else — no architecture questions, no
"suggest improvements".

```
You are writing JSON fixtures for an existing, frozen system. You are not
designing it. Read sections 1-4 of difficulty_catalogue.md as binding.

For each case in section 3 emit exactly one file eval/cases/<id>.json with:

{
  "id": "<id from the table>",
  "family": "<one of the families in eval/cases/manifest.json>",
  "difficulty": "<D1..D18 ids this case exercises>",
  "wall": "<W1..W6 ids this case exercises, or [] >",
  "title": "<one line, names the phenomenon, not the entity>",
  "why_real": "<one sentence: what really happens to a real user. No IPA.>",
  "setup": { "observations": [ ... ] },
  "inputs": { "asr": "...", "formatted": "...", "user_id": "..." },
  "expected": {
    "decision": "APPLY" | "ABSTAIN",
    "memory_aware": "...",
    "reason": "<exact reason string from decide/conservative.py or
                learner/align.py: ok | no_memory | low_confidence |
                already_canonical | context_mismatch |
                conflicting_canonicals | not_grapheme_similar |
                refused_homophone | case_only | both_function_words>",
    "affected_tokens": [ {"from": "...", "to": "..."} ],
    "expected_profile_results": {
      "off":      {"decision": "ABSTAIN", "memory_aware": "<formatted verbatim>"},
      "exact":    {...}, "phonetic": {...}, "llm": {...}
    }
  }
}

Hard rules, in priority order:

1. Copy the ASR / formatted / expected strings from the section 3 table
   verbatim, including punctuation and capitalization. Do not "improve" them.
2. Never write a case that needs 2 tokens to become 1, or 1 to become 2.
3. Never write a case whose only difference is capitalization and expect APPLY.
4. Never write a correction observation whose two words start with different
   letters and expect it to be learned.
5. "off" is always {ABSTAIN, formatted verbatim}. No exceptions.
6. If exact and phonetic differ, say so explicitly in both entries and add a
   one-line "profile_note" explaining which retriever finds it and why.
7. reason strings must be copied from the enum above. Do not invent
   "phonetic_collision" or "entity_ambiguous".
8. Aaditya and Kivi may be ASSERTED in exactly 2 cases (01 and 25). They may
   appear as setup-only in case 37. Nowhere else.
9. No entity in more than 3 cases; no first name in more than 2; no more than
   2 cases per sentence domain from section 4.
10. No IPA, no invented phoneme strings, no "Double Metaphone" (the code uses
    classic single-code Metaphone).

Before emitting each file, self-check and state PASS/FAIL for each:
  - token counts: does formatted differ from asr only by formatting?
  - does the rewrite change letters, not just case?
  - do both correction words start with the same letter?
  - is the reason string in the enum?
  - is off == formatted verbatim?
  - entity budget still satisfied?
Emit nothing that FAILs. List the FAILs instead and stop.
```

---

## 7. Provenance

Behavioural claims came from executing the pipeline (working copy, see the note
at the top: 44 of 44 case rows and every metaphone key in D3 were run, not
guessed); the external claims came from these sources.

- Svarah / Indian-accented English ASR, and the finding that everyday utterances
  full of brand, bank and food entities are the hardest slice —
  [arXiv 2305.15760](https://arxiv.org/html/2305.15760v1),
  [AI4Bharat/Svarah](https://github.com/AI4Bharat/Svarah)
- Named entities are the weak spot of end-to-end ASR, and contextual biasing
  buys 15–46% relative error reduction on bias-listed terms —
  [Contextual density ratio, arXiv 2206.14623](https://arxiv.org/pdf/2206.14623),
  [Retrieval-augmented NE correction](https://www.alphaxiv.org/abs/2409.06062),
  [Slot error rate](https://deepgram.com/learn/slot-error-rate-developer-guide-asr-accuracy)
- LLM post-correction over-corrects and hallucinates entities that were never
  spoken; conservative filters are the standard mitigation —
  [Revisiting ASR error correction](https://arxiv.org/html/2405.15216),
  [RAG-enhanced GEC](https://arxiv.org/pdf/2509.23630)
- Whisper hallucination in the wild, including medical settings —
  [AP investigation coverage](https://cbsaustin.com/news/nation-world/researchers-say-an-ai-powered-transcription-tool-used-in-hospitals-invents-things-no-one-e-fabrication-transcripts-artificial-intelligence-white-house-alondra-nelson-princeton),
  [Careless Whisper](https://montrealethics.ai/careless-whisper-speech-to-text-hallucination-harms/),
  [non-speech-induced hallucination, arXiv 2501.11378](https://arxiv.org/pdf/2501.11378)
- Insertion/deletion asymmetry in Indic clinical ASR (Hindi/English insertions
  ~37–39%, Kannada deletions to 84%) —
  [ASR Under the Stethoscope, arXiv 2512.10967](https://arxiv.org/html/2512.10967)
- No standard romanization for Indian names; `a/aa`, `i/ee`, `u/oo`, `ksh/x`
  variation, and numerology-driven respelling —
  [MultiLingual on Hindi transliteration variants](https://multilingual.com/localizing-user-experience-hindi-transliterations-and-spelling-variants/),
  [The Diplomat](https://thediplomat.com/2021/01/spell-it-out-should-english-transcription-of-indian-words-be-reformed/),
  [Hunterian transliteration](https://en.wikipedia.org/wiki/Hunterian_transliteration),
  [google/personfinder issue #345](https://github.com/google/personfinder/issues/345)
- Public respelling examples (`Devgn`, `Rajkummar`, `Ayushmann Khurrana`) —
  [Ajay Devgn](https://en.wikipedia.org/wiki/Ajay_Devgn) and numerology-practice
  coverage
- What dictation users actually report losing: client names, product terms,
  acronyms, places, usernames; `Sofia`→`Sophia` —
  [Talkpad](https://talkpad.ai/blog/voice-typing-vocabulary-personal-dictionary/),
  [Dictation gets client names wrong](https://medium.com/@ryanshrott/dictation-keeps-getting-client-names-and-industry-terms-wrong-heres-what-fixes-it-3c9a68d047c6),
  [Adobe transcription custom-word requests](https://community.adobe.com/feature-requests-730/transcription-dictionary-and-correction-tools-1555734)
