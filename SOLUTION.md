# CityWheels Help Desk Agent

## Run the project

Requirements: Python 3.12+, uv, Git and a Gemini API key with access and remaining quota for the chosen model.
Run these commands from the repository root:

```powershell
uv sync --locked --dev
Copy-Item .env.example .env
```

Create `.env` once, then set `GEMINI_API_KEY` and `GEMINI_MODEL=gemini-3.5-flash-lite`.
The key is read from the environment. `.env` is ignored; `.env.example` contains no real key.

```powershell
uv run --locked --env-file .env python -u -m helpdesk.llm
uv run --locked pytest -q
uv run --locked pre-commit run --all-files
```

The CLI accepts repeated questions. `exit`, `quit`, Ctrl+C or EOF exits; empty input is ignored.
Questions do not share conversation history. Include a booking ID again when asking a follow-up.
The assistant quotes hypothetical cancellations; it never modifies bookings or processes payments.

Run the current implementation on the development questions, choosing a fresh output directory:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.5-flash-lite --questions eval/questions.json --variant D-development-3.5 --output-dir eval/runs/new-development-3.5
```

This makes API requests. `--model` selects the model explicitly; `--variant` labels the run. Use `eval/questions_holdout.json` for the 15 new questions.
The [README](README.md) contains model-comparison commands, review/report regeneration and hook installation. Existing output files are overwritten, so preserve previous runs in separate directories.

## Architecture and decisions

The agent uses Google Gen AI SDK 2.33.0 through the Interactions API, with dependencies pinned by `uv.lock`.

| Module | Responsibility |
| --- | --- |
| `helpdesk/config.py` | Paths, fixed time, refund thresholds, retrieval settings, allowed document names and request settings |
| `helpdesk/booking.py` | Read bookings and convert dates and monetary values |
| `helpdesk/refund.py` | Deterministic refund totals, components and return methods |
| `helpdesk/policies.py` | Read Markdown, split sections, rank matches and read a complete allowed document |
| `helpdesk/llm.py` | Tool schemas, prompt, dispatcher, model loop, shared client factory and CLI |
| `eval/run_eval.py` | Execute question sets, record traces, perform automatic checks and write reviewed reports |
| `eval/compare_runs.py` | Compare saved reports, grouped by question hash and scorer version |

I used the SDK directly to keep validation, execution and the request budget visible in one loop. The model chooses tools; Python validates and executes them and returns results with the matching `call_id`.
`previous_interaction_id` preserves context within one question. Every round includes the tool declarations and system instruction. Multiple calls in one response are supported.

The five-round budget bounds repeated searches and API usage. If the fifth response still requests tools, the loop returns a staff fallback without executing tools whose results could not be sent back.
This prevents an endless tool loop, but can stop a question before a useful answer is produced. SDK retries can add HTTP attempts beyond this logical request count.

The dispatcher accepts only declared tools with one non-empty string argument and returns argument errors to the model. Document access is restricted to `faq.md`, `prices.md` and `cancellations.md`.

### Provider and model

Gemini 3.5 Flash-Lite provided the required tool calling. I compared it with 3.8 Flash on the same final implementation and questions. Scores were equal, while 3.5 used fewer tools and had lower observed wall time, so I retained it as the default.

### Data and refund rules

The supplied README, Markdown policies and bookings are the business sources of truth.
`TypedDict` keeps the JSON dictionary shape with static checking. Explicit conversion produces timezone-aware `datetime` values for supplied dates and `Decimal` amounts to avoid binary floating-point rounding. Tool results serialize both as strings. Runtime validation remains limited.

Refunds always use the supplied business time, `2026-06-10T09:00:00+02:00`, rather than the real system clock.

| Confirmed booking: time before rental start | Refund of rental price |
| --- | ---: |
| At least 48 hours | 100% |
| At least 24 hours, below 48 hours | 50% |
| Below 24 hours | 0% |

Allowed cancellation returns the full deposit and excludes the booking fee. Other statuses (`in_progress`, `completed`, `cancelled`) yield zero from this attempt, without implying anything about historical refunds. Stored prices and deposits are booking totals, so they are not multiplied by bike count or discounted again.

After incomplete voucher explanations in evaluation, I expanded the tool to return eligibility, each refund component, the total, return methods and policy source together.
Rental refunds paid by card return to the same card within five working days; voucher rental refunds become new vouchers.
The deposit follows its original payment method, which is not separately recorded and is not inferred from `paid_with`. Zero-refund components have no return method. Unknown IDs return not-found; weather exceptions remain a staff decision.

No fractional-cent rounding rule is invented because the supplied policy does not specify one.

### Retrieval and instructions

Markdown is split at `#` and `##` headings, preserving introductory text such as the VAT statement.
Search normalizes case, removes a small stop-word list and applies explicit token aliases, such as `bikes`/`bike`, `payment`/`pay` and purchase/sales vocabulary.
It ranks matching tokens, gives headings weight 3 and returns the top three positive matches with filename, heading and text. Heading weight favors the FAQ's question headings; the three-result limit bounds the context sent to the model. These are simple heuristics, not parameters selected through a separate tuning study.

The initial substring search missed paraphrases. Token matching improved retrieval in the development run, but still missed some sections. I added `read_policy_document` so the model could read the complete relevant document after an unsuccessful search. All three documents total about 4,400 characters, making this fallback practical for the supplied data.

The prompt requires tool-grounded answers, Python-calculated refunds, a booking-ID clarification when needed and staff referral for unavailable or unrelated information. It separates rental/deposit payments and prohibits claims of actual booking changes.

## Tests and error handling

The suite has **193 passing cases** covering booking conversion/lookup, file and argument errors, all supplied refunds and statuses, 24/48-hour boundaries, refund components/methods, retrieval, document access, CLI errors and evaluation reporting.
Temporary files isolate tests from supplied data. Fake-model tests verify tool-call/result round trips without network or keys; real-model evaluation separately checks query selection, grounding and refusals.
GitHub Actions runs Ruff, formatting, mypy and offline pytest on pushes and pull requests. Installed pre-commit hooks run the same checks on commits.

The CLI handles provider failures, common data errors, unexpected response types and empty output without showing the key. The evaluator records error type/status and saves results after each question; interrupted runs cannot currently resume.

### Why timeouts were disabled

Initial requests hit the 30-second timeout. I disabled it to check whether slower responses would complete rather than terminate those attempts at that cutoff. The recorded runs and current `REQUEST_TIMEOUT_SECONDS` setting retain this choice.
Later direct API checks identified quota errors (429) and a billing prerequisite (402); they did not establish that Google service overload caused the earlier waits.

The tradeoff is that a stalled call can wait indefinitely and require Ctrl+C. The five-round budget limits rounds, not elapsed time. A finite request timeout should be restored for regular use. The shared client factory applies the same setting to CLI and evaluation and handles the SDK's seconds/milliseconds distinction.

An offline MockTransport check also showed that SDK 2.33.0 made two HTTP attempts for a simulated 503 with both the original zero-retry setting and the current explicit minimum setting. SDK retries are therefore possible.

## Evaluation results

### Why 45 development questions and 15 holdout questions

The task requires at least ten questions, including two refunds and two refusals. I expanded the initial 22 questions to 45 to cover all three policy files and all ten supplied bookings, including refund boundaries and booking statuses. The development set contains ten expected refund amounts and three unrelated refusal requests.

After the D implementation was complete, I prepared 15 additional questions covering new wording, combined requirements, undocumented topics, two refunds and two refusals. They were not used to tune D before the recorded comparison. They provide a separate check on the same domain while keeping API execution and qualitative review manageable within the assignment's time budget.

### Recorded results

| Dataset | Variant / model | PASS | FAIL | Pass rate |
| --- | --- | ---: | ---: | ---: |
| 45 development questions | A / 3.5 Flash-Lite, rescored v2 | 34 | 11 | 75.6% |
| 45 development questions | B / 3.5 Flash-Lite, rescored v2 | 40 | 5 | 88.9% |
| 45 development questions | C / 3.5 Flash-Lite | 41 | 4 | 91.1% |
| 45 development questions | D / 3.5 Flash-Lite | 43 | 2 | 95.6% |
| 45 development questions | D / 3.8 Flash | 43 | 2 | 95.6% |
| 15 holdout questions | D / 3.5 Flash-Lite | 14 | 1 | 93.3% |
| 15 holdout questions | D / 3.8 Flash | 14 | 1 | 93.3% |

All listed runs completed with no recorded API errors. The [complete comparison](eval/comparison.md) links the raw reports, configuration, tool counts and timings. It keeps the initial 17/22 result separate because that run used a different dataset.

A to B changed tokenization, ranking and result count together, while retaining the prompt. It improved retrieval, including seasonal opening hours.
C added aliases and changed instructions; it improved some answers but introduced regressions in age advice, voucher explanation and location lookup.
D added structured refund output and complete-document reading. Both D runs correctly explained voucher/deposit returns and recovered the location through a full FAQ read. These are combined changes, so a single improvement cannot be attributed to one feature alone.

| Final D run | Remaining failures |
| --- | --- |
| Development / 3.5 | Repeated searches reach the step limit for cats; the unusual payment question is misclassified and answered without supporting tools |
| Development / 3.8 | Cats still reach the step limit; the Revolut answer adds an unsupported universal claim about card acceptance |
| Holdout / 3.5 | Absence of a documented student discount becomes an unjustified categorical denial |
| Holdout / 3.8 | The phone-holder question reaches the step limit instead of explaining that the information is unavailable |

D used 47 versus 68 tool calls on development questions (3.5 versus 3.8), taking 245.55 versus 510.93 seconds. Holdout used 21 versus 27 calls and 95.03 versus 192.65 seconds. These wall times depend on network conditions and model rounds; no token or monetary-cost measurements were recorded.

Automatic checks inspect tool use, IDs, amounts, status, not-found wording and step limits. Final passes require whole-answer review, including unsupported additions. Reviews used ChatGPT/Codex assistance; notes explain borderline judgments.

Scorer v2 accepts selected zero-refund phrases. B changed from 39/45 to 40/45 after a correct answer expressed in words stopped failing the currency-number check. Original answers/traces and both report versions were preserved; this changed the evaluator, not the response.

### Why one retained run per configuration

Execution time, API quotas and manual review effort constrained the evaluation. I prioritized policy coverage, recording successive implementations and comparing two models over repeated measurements of each configuration. Earlier interrupted attempts and availability probes are not treated as additional completed evaluations.

A single retained run does not measure response variability. The results show what happened in these runs, not the probability of a correct answer to a new question. In particular, the 45 questions guided development, so their score is not an independent test result.

For reproducibility, reports store the question hash, prompt, model and traces. The holdout runner's `--questions` change was uncommitted during those runs and was committed afterward, so its recorded source commit alone is incomplete provenance. The later cleanup preserved the evaluated D prompt and all saved scorer-v2 checks; it was verified offline without another live run.

## AI-assisted development

ChatGPT/Codex helped draft implementation and test code, debug SDK integration, prepare questions and review notes, compare results, clean up code and edit documentation.

An early integration suggestion accessed `output_text` directly on the SDK result. Pylance and mypy reported that the return type could also be a stream. The code was changed to check `isinstance(interaction, Interaction)` before accessing non-streaming fields.

An earlier non-mutation test called the refund function against the real `bookings.json` and checked afterward that it was unchanged. That would detect an accidental write only after modifying the source file. I requested a monkeypatch version, and the test now uses a temporary copy.

The assistant initially proposed tokenization. I chose to measure a simple substring baseline first and then compare the changed approach. This gave the later retrieval changes a measured baseline. Tokenization alone did not connect purchase wording with the FAQ's sales wording, which led to explicit aliases.

An offline transport test also corrected the assistant's false claim that setting retries to zero disabled SDK retries.

## Corrections still needed

The evaluation identifies specific follow-up work:

| Area | Evidence | Proposed correction |
| --- | --- | --- |
| Search stopping in `helpdesk/llm.py` | Both models exhaust the budget on cats; 3.8 also does so on phone holders | Stop repeated searches after the relevant full document has been read and return a topic-specific information gap with staff referral |
| Scope and grounding in `helpdesk/llm.py` | 3.5 mishandles a humorous payment question and asserts there is no student discount; 3.8 overstates Revolut acceptance | Distinguish the topic from unusual wording, and distinguish missing documentation from a prohibition or acceptance guarantee |
| Request settings in `helpdesk/config.py` | Timeout removal permits indefinite waiting | Restore a finite request timeout; keep the round budget as a separate limit |
| Evaluation control in `eval/run_eval.py` | Quota/billing failures interrupted development runs | Stop on systemic quota/billing errors and add resume that verifies the model, prompt and question configuration |

Changes to search stopping or instructions need another evaluation, including regression checks for previously correct answers. The current reports retain their observed failures.

Booking data are converted but not comprehensively validated. Before accepting externally supplied bookings, add checks for finite nonnegative amounts, unique IDs, timezone-aware dates and a valid start/end range. Currently, one malformed record can block lookup of another booking because all records are parsed first.

The integration imports Interactions exceptions from an internal SDK module. Keep the lockfile and run the offline tests when upgrading that dependency.
