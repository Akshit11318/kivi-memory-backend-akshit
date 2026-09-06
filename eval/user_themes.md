# User-Centric Dictation Themes: Where ASR Fails & Memory Wins

When real users dictate into an audio intelligence tool like Kivi, ASR failures do not happen randomly; they cluster around specific user domains, specialized vocabularies, and acoustic ambiguities.

Standard formatter LLMs cannot fix these because they lack user-specific lexical context. Below are 7 distinct user themes detailing where ASR fails and how personal memory creates the intended output.

---

## Theme 1: Developer & Technical Architecture Dictation
**User Persona:** Software engineer, DevOps lead, or engineering manager dictating PR reviews, architecture notes, and Jira issues.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `we migrated the auth service to fast api` | `We migrated the auth service to fast API.` | `We migrated the auth service to FastAPI.` | Split token: ASR segments compound proper noun into adjective + acronym. |
| `store session state in super base` | `Store session state in super base.` | `Store session state in Supabase.` | Common English phoneme capture: /suːpəbeɪs/ $\to$ "super base". |
| `deploy the worker on cooper netties` | `Deploy the worker on cooper netties.` | `Deploy the worker on Kubernetes.` | Foreign loanword/jargon distortion in fast speech. |
| `check the service latency on red is` | `Check the service latency on red is.` | `Check the service latency on Redis.` | English function word capture: /rɛdɪs/ captured as "red is". |
| `serve the llama model with film` | `Serve the LLaMA model with film.` | `Serve the LLaMA model with vLLM.` | Slurred acronym /vɪlɛm/ or /viː ɛl ɛl ɛm/ captured as dictionary noun "film". |

---

## Theme 2: Healthcare, Clinical & Pharmaceutical Dictation
**User Persona:** Physician, medical resident, or patient dictating prescription instructions, discharge notes, and medical logs.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `take one crow seen tablet after food` | `Take one crow seen tablet after food.` | `Take one Crocin tablet after food.` | Brand homophone: Regional drug brand /kroʊsɪn/ captured as "crow seen". |
| `prescribe met for men 500 mg` | `Prescribe met for men 500 mg.` | `Prescribe Metformin 500 mg.` | Segmentation failure: Generic drug /mɛtfɔːrmɪn/ split into common English phrase. |
| `check if patient is on thyro norm` | `Check if patient is on thyro norm.` | `Check if patient is on Thyronorm.` | Compound splitting: Indian thyroid brand split into two pseudo-words. |
| `give dolo six fifty sos` | `Give dolo 650 SOS.` | `Give Dolo-650 SOS.` | Missing hyphen / brand capitalization in regional OTC analgesic. |
| `start on a zithro my sin for five days` | `Start on a zithro my sin for five days.` | `Start on Azithromycin for five days.` | Multi-token phonetic disintegration of multi-syllable antibiotic. |

---

## Theme 3: FinTech, Banking & Legal Compliance
**User Persona:** Founder, CA, corporate legal counsel, or finance executive dictating wire instructions, balance sheets, and audit notes.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `initiate vendor transfer via arty gs` | `Initiate vendor transfer via Arty GS.` | `Initiate vendor transfer via RTGS.` | Colloquial acronym speed: /ɑːr tiː dʒiː ɛs/ decoded as "arty gs". |
| `deduct ten percent t d s before payout` | `Deduct 10% t d s before payout.` | `Deduct 10% TDS before payout.` | Individual letter hesitation formatted as spaced lowercase letters. |
| `the high court took sue oh mow two notice` | `The high court took sue oh mow two notice.` | `The high court took suo motu notice.` | Latin judicial maxim /suːoʊ moʊtuː/ chopped into English monosyllables. |
| `verify k why see documents first` | `Verify k why see documents first.` | `Verify KYC documents first.` | Acronym confusion: /keɪ waɪ siː/ captured as literal words "k why see". |
| `transfer via you pee eye` | `Transfer via you pee eye.` | `Transfer via UPI.` | Everyday payment system decoded as phonetic string. |

---

## Theme 4: Indian Localities, Geography & Commutes
**User Persona:** Office worker, commuter, or real estate agent dictating navigation notes, delivery addresses, and meeting venues.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `meet me at cora mangala fourth block` | `Meet me at Cora Mangala 4th block.` | `Meet me at Koramangala 4th block.` | Western acoustic prior mapping Indian retroflex/nasal phonology to "Cora". |
| `traffic near h s r layout is heavy` | `Traffic near h s r layout is heavy.` | `Traffic near HSR Layout.` | Spaced lowercase letters for Indian metro sector. |
| `reach the office in indira nager` | `Reach the office in Indira nager.` | `Reach the office in Indiranagar.` | Transliteration suffix split: "nager" instead of canonical "nagar". |
| `send the package to white field` | `Send the package to white field.` | `Send the package to Whitefield.` | Compounding: IT corridor split into two common English words "white field". |

---

## Theme 5: Academic, AI Research & Scientific Publishing
**User Persona:** Machine learning researcher, PhD scholar, or university faculty dictating paper drafts and seminar summaries.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `read the latest paper on archive` | `Read the latest paper on archive.` | `Read the latest paper on arXiv.` | Stylized casing homophone: /ɑːrkaɪv/ is homophonic with dictionary "archive". |
| `our submission to new rips was accepted` | `Our submission to new rips was accepted.` | `Our submission to NeurIPS was accepted.` | Top ML conference /njʊərɪps/ decoded as literal English words "new rips". |
| `compare results with llama three` | `Compare results with llama 3.` | `Compare results with LLaMA-3.` | Animal noun capture: open-source model capitalized as the animal "llama". |
| `the paper cites amicus cure ee eye` | `The paper cites amicus cure ee eye.` | `The paper cites amicus curiae.` | Latin academic citation mutilated phonetically. |

---

## Theme 6: Indian Workplace Names & Cross-Cultural Colleague Dictation
**User Persona:** Team member coordinating across diverse regions in India.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `gautam will present the quarterly deck` | `Gautam will present the quarterly deck.` | `Gautham will present the quarterly deck.` | Aspirated dental stop: /ɡaʊt̪ʰəm/ mapped to standard Western Latin "Gautam". |
| `srinivas reviewed the deployment pull request` | `Srinivas reviewed the deployment pull request.` | `Sreenivas reviewed the deployment pull request.` | Vowel length transliteration: /iː/ transliterated as "i" instead of "ee". |
| `ask choudhury for the signed agreement` | `Ask Choudhury for the signed agreement.` | `Ask Chowdhury for the signed agreement.` | Regional Bengali vs North Indian spelling variation of identical surname. |
| `priya will head customer success` | `Priya will head customer success.` | `Priyaa will head customer success.` | Personal preference: single vowel lengthening (/jɑː/ vs /jə/). |
| `tanmay submitted the sprint budget` | `Tanmay submitted the sprint budget.` | `Tanmaay submitted the sprint budget.` | Terminal syllable lengthening preferred by individual user. |

---

## Theme 7: Everyday Lifestyle, Quick-Commerce & Regional Food
**User Persona:** Consumer dictating grocery reminders, meal preferences, and home logistics.

| ASR Raw Output | Formatter Output | Correct Memory-Aware Output | Failure Mechanism |
| :--- | :--- | :--- | :--- |
| `order vegetables on blink it` | `Order vegetables on blink it.` | `Order vegetables on Blinkit.` | Quick-commerce brand captured as English imperative phrase "blink it". |
| `get milk from cepto in ten minutes` | `Get milk from cepto in 10 minutes.` | `Get milk from Zepto in 10 minutes.` | Voicing confusion on initial sibilant: /z/ captured as /s/ ("cepto"). |
| `let us order pun near mac honey for dinner` | `Let us order pun near mac honey for dinner.` | `Let us order Paneer Makhani for dinner.` | Indic cuisine phonemes /pəniːr məkʰniː/ mapped to string of common words. |
| `pack two masala dose uh for breakfast` | `Pack two masala dose uh for breakfast.` | `Pack two Masala Dosa for breakfast.` | Regional dish name ending /doːsə/ decoded with hesitation particle "dose uh". |

---

## Why Standard Formatter LLMs Fail Without Word-Level Memory
1. **Priors Over Intent:** Formatter LLMs rely on web-scale token probabilities. Without explicit personal memory, they regress toward the mean (e.g. converting `arXiv` to `archive`, or `Sreenivas` to `Srinivas`).
2. **Cannot Guess Private Spelling:** A general model cannot know whether this specific user's colleague spells their name *Choudhury*, *Chowdhury*, or *Choudhary*.
3. **Over-Standardization:** As demonstrated in Case 24, formatters often take an ASR output that was already correct for a proper noun and standardize it away.
4. **Memory Injection is the Smallest Solution:** Storing a per-user lexical belief (`canonical` + `observed_forms` + `confidence >= 0.75`) with SequenceMatcher alignment fixes these exact failures without needing a heavyweight model redesign.
