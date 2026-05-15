# Task 4: Localization Brief — Arabic (Gulf Dialect) Voice Agent Rollout

## 1. What Changes About the Prompt Itself, Beyond Translation?

### Structural Changes

1. **Gender agreement.** Arabic has grammatical gender that affects verb conjugation, adjectives, and pronouns. The prompt must specify whether the agent speaks as masculine or feminine (default: feminine, as most Arabic voice assistants use a female voice). The greeting changes: `مرحباً` (neutral) vs `أهلاً بك` (to a male) vs `أهلاً بكِ` (to a female). The prompt should include a rule: _"Use feminine singular conjugation for the assistant's self-reference. Address the caller using masculine or feminine based on their name if known; default to masculine if unknown."_

2. **Date format.** Arabic dates are written day-month-year (not month-day-year). The prompt must specify: _"Always express dates in DD/MM/YYYY format. Read the date as: 'اليوم كذا من شهر كذا سنة كذا' (day X of month X year X)."_

3. **Phone number grouping.** Gulf phone numbers are typically 10 digits (05XX XXX XXX). The digit-readback rule must be updated to group as `05XX` pause `XXX` pause `XXX` instead of the US-style `XXX-XXX-XXXX`.

4. **Diglossia handling.** Arabic has a gap between Modern Standard Arabic (MSA, formal) and Gulf dialect (spoken). The prompt should instruct: _"Use Gulf dialect (اللهجة الخليجية) for all conversational turns. Use MSA only for reading formal text like practice names or addresses."_ Without this, the agent sounds like a news anchor, not a receptionist.

5. **Islamic greeting sensitivity.** The prompt should include: _"If the caller says 'السلام عليكم', respond with 'وعليكم السلام ورحمة الله وبركاته'. Do not initiate religious greetings, but always respond appropriately."_ This is a cultural expectation, not a translation issue.

6. **Time format.** Saudi Arabia uses 12-hour time with `صباحاً` (AM) and `مساءً` (PM), but some contexts use 24-hour. The prompt should specify 12-hour with AM/PM indicators.

## 2. What Changes About Your Evaluation Strategy?

### Metric Adjustments

| Metric                        | Change for Arabic                                                                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Field Completion Rate**     | Same metric, but test with Arabic names (bin, bint, Al-) and phone formats (05XX).                                                                                 |
| **ASR Robustness Score**      | **Critical change.** Arabic ASR has higher WER than English, especially for Gulf dialect. Lower the pass threshold from 75% to 60% for v1, with a plan to improve. |
| **Dialect Fidelity**          | **New metric.** % of responses that use Gulf dialect vs MSA. Measured by a dialect classifier. Target: ≥90% Gulf dialect.                                          |
| **Gender Agreement Accuracy** | **New metric.** % of responses where verb/adjective gender agrees with the caller. Target: ≥95%.                                                                   |
| **Cultural Appropriateness**  | Human evaluation: does the agent handle greetings, Ramadan timing, and family names correctly?                                                                     |

### Dataset Changes

- Add 50 Arabic-specific test scenarios: caller uses a kunya (Abu X), caller uses an Islamic greeting, caller references Ramadan timings, caller has a compound name (Mohammed bin Salman Al-Saud).
- Add 30 noisy ASR transcripts with Gulf-accented Arabic (where `ق` is pronounced `g`, `ج` is pronounced `y` or `j` depending on region).
- Add 10 scenarios where the caller switches between Arabic and English mid-sentence (code-switching, common in Gulf countries).

## 3. Two Specific TTS or ASR Risks for Arabic Dialects

### Risk 1: Gulf Arabic Phonemes Missing from TTS Voices

**Problem:** Many commercial TTS engines (especially older ones) are trained on MSA, not Gulf dialect. Gulf Arabic has distinct phonemes:

- The `ق` (qaf) is pronounced as a hard `g` sound (like English "go") in Gulf dialect, not the uvular `q` of MSA.
- The `ج` (jim) is pronounced `y` in some Gulf regions (e.g., `مسجد` → `masyed` not `masjed`).
- The `ك` (kaf) in the second-person feminine suffix is pronounced `ch` or `ts` in some Gulf dialects (`كتابك` → `kitaabich`).

**Mitigation:**

- Select a TTS provider that explicitly supports Gulf Arabic (e.g., Microsoft's `ar-SA` voice or ElevenLabs' Gulf Arabic model).
- Before launch, run a phoneme-level audit: generate 100 test utterances and have a native Gulf Arabic speaker rate naturalness.
- If no suitable Gulf Arabic TTS exists, use MSA TTS but apply SSML phoneme tags (`<phoneme alphabet="ipa" ph="g...">`) for known Gulf-specific words.

### Risk 2: ASR Confusion on Numbers and Names

**Problem:** Arabic ASR systems frequently confuse:

- `ستة` (6, sitta) vs `سبعة` (7, sab'a) — similar onset sounds.
- `ثلاثة` (3, thalatha) vs `ثمانية` (8, thamanya) — similar syllable structure.
- Compound names like `عبدالرحمن` may be transcribed as two words or one.
- `بن` (bin, "son of") is often dropped by ASR, losing the family connection.

**Mitigation:**

- Implement explicit digit confirmation for phone numbers (same as English v2 prompt), but with Arabic digit names.
- For names, use a two-step confirmation: "هل اسمك عبدالرحمن بن سعود؟" (Is your name Abdulrahman bin Saud?) — the caller confirms the full name, not just the first name.
- Add a post-ASR name normalization step that checks common name patterns (Al-, bin, bint, Abu, Um) and corrects likely ASR errors.

## 4. Sociocultural Consideration Affecting Appointment-Booking UX

### Gender-Specific Clinic Access

In Saudi Arabia, many dental clinics have separate sections for male and female patients, or specific hours/days for families vs single men. Some clinics are women-only with female staff. A male caller cannot book an appointment for a female family member at a women-only clinic without specifying the patient's gender.

**Impact on the booking flow:**

- After collecting the caller's name, the agent must ask: _"Is this appointment for yourself or for someone else?"_
- If "someone else," ask: _"Is the patient male or female?"_
- Based on the answer, the agent must check the practice's gender-specific availability before offering times.
- The prompt must include a rule: _"If the practice has gender-separated sections, only offer times available for the patient's gender. Do not assume the caller's gender from their voice."_

**Why this matters:** Without this check, the agent might book a male patient into a women-only slot, causing a scheduling conflict and a poor patient experience. This is not a bug — it's a cultural requirement that would not exist in a Western deployment.
