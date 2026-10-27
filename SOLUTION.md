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

Run a real evaluation on the current code, choosing a fresh output directory:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.5-flash-lite --questions eval/questions.json --variant D-development-3.5 --output-dir eval/runs/new-development-3.5
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.5-flash-lite --questions eval/questions_holdout.json --variant D-holdout-3.5 --output-dir eval/runs/new-holdout-3.5
```

These commands make API requests and may incur charges. Existing output files are overwritten.
`--model` overrides the environment explicitly. `--variant` labels a run; it does not restore historical implementations.
For a model comparison, change only `--model` and the output directory while keeping code, prompt, questions and scorer fixed.
The [README](README.md) includes the 3.8 comparison command and local hook installation.

After reviewing the saved answers and traces, update only each entry's `review` status and reason, then regenerate reports offline:

```powershell
uv run --locked python -m eval.run_eval --report-only --output-dir eval/runs/new-holdout-3.5
uv run --locked python -m eval.compare_runs
```

## Architecture and decisions

The application uses the Google Gen AI SDK directly through the Interactions API.
The recorded runs used SDK 2.33.0. `uv.lock` makes the dependency set reproducible.

| Module | Responsibility |
| --- | --- |
| `helpdesk/config.py` | Paths, fixed time, refund thresholds, retrieval settings, allowed document names and request settings |
| `helpdesk/booking.py` | Read bookings and convert dates and monetary values |
| `helpdesk/refund.py` | Deterministic refund totals, components and return methods |
| `helpdesk/policies.py` | Read Markdown, split sections, rank matches and read a complete allowed document |
| `helpdesk/llm.py` | Tool schemas, prompt, dispatcher, model loop, shared client factory and CLI |
| `eval/run_eval.py` | Execute question sets, record traces, perform automatic checks and write reviewed reports |
| `eval/compare_runs.py` | Compare saved reports, grouped by question hash and scorer version |

A handwritten loop keeps the execution flow visible without adding an agent framework.
For each question, the model chooses tools; Python validates and executes them and sends results back using the matching `call_id`.
`previous_interaction_id` preserves context within that question. The tool declarations and system instruction are sent on every round.
Multiple function calls in a single response are supported.

There are at most five logical model requests per question. If the fifth response still requests tools, the loop returns a staff fallback without executing tools whose results could not be sent back.
SDK retries can add HTTP attempts beyond this logical request count.

The dispatcher allows exactly the declared functions, validates their single non-empty string argument and returns structured argument errors to the model.
It does not evaluate arbitrary code. Full-document reads additionally allow only `faq.md`, `prices.md` and `cancellations.md`.

### Provider and model

The default is Gemini 3.5 Flash-Lite. It supported the required tool calling and worked during development.
Gemini 3.8 Flash was evaluated on the final D implementation using the same datasets and prompt.
The reviewed scores were equal, while 3.5 used fewer tools and had lower observed wall time in those runs. This supports keeping the simpler default; it does not prove general model superiority.
Early availability probes failed or timed out. Later direct requests identified quota errors (429) and a billing prerequisite (402), and subsequent evaluations completed. These infrastructure failures are distinct from wrong policy answers.

### Data and refund rules

The supplied README, Markdown policies and bookings are the business sources of truth.
Bookings use `TypedDict`; ISO timestamps become timezone-aware `datetime` values and amounts become `Decimal`.
Tool results serialize dates and amounts as strings. `TypedDict` provides static checking, not runtime schema validation.

Refunds always use the supplied business time, `2026-06-10T09:00:00+02:00`, rather than the real system clock.

| Confirmed booking: time before rental start | Refund of rental price |
| --- | ---: |
| At least 48 hours | 100% |
| At least 24 hours, below 48 hours | 50% |
| Below 24 hours | 0% |

For an allowed cancellation, the full stored deposit is returned and the booking fee is never refunded.
`in_progress`, `completed` and `cancelled` bookings cannot be cancelled again and yield zero from this attempt. This says nothing about historical refunds.
Stored rental and deposit values are booking aggregates; they are not multiplied by bike count or discounted again.

The final tool returns cancellation eligibility, rental/deposit/booking-fee components, total, return methods and the policy source.
Rental refunds paid by card return to the same card within five working days; voucher rental refunds become new vouchers.
The deposit follows its original payment method. The data do not separately identify that method, so the tool does not infer it from the booking's `paid_with` field.
A component with no refund has no return method. Unknown booking IDs keep their explicit not-found result.
Exceptional weather refunds remain a staff decision.

No fractional-cent rounding rule is invented because the supplied policy does not specify one.

### Retrieval and instructions

Markdown is split at `#` and `##` headings, preserving introductory text such as the VAT statement.
Search normalizes case, removes a small stop-word list and applies explicit token aliases, such as `bikes`/`bike`, `payment`/`pay` and purchase/sales vocabulary.
It ranks sections by matching tokens, giving headings weight 3, and returns the top three positive matches with their filename, heading and text.
The aliases normalize retrieval vocabulary; they do not decide answers.

The initial substring search was easy to explain but missed paraphrases. Token matching improved recall, but a short query can still miss a relevant section entirely.
The final `read_policy_document` tool lets the model read a complete supplied document when search is insufficient.
The corpus is small: three documents, about 4,400 characters. A document-read fallback was a smaller addition than embeddings or a vector database.

The prompt requires tool-grounded claims, code-calculated booking refunds, clarification when the booking ID is missing, and staff referral for unavailable or unrelated information.
It distinguishes rental payments from deposits, prohibits claims of actual booking changes and leaves weather exceptions to staff.
These instructions are not guarantees: the evaluation still detects unsupported claims and incorrect stopping behavior.

## Tests and error handling

The current offline suite has **193 passing cases**, including parameterized tests.
It covers booking conversion and lookup, invalid arguments, file errors, all supplied refund amounts, statuses, 24/48-hour boundaries, fee exclusion, refund components and methods, retrieval, document access, fake-model loops, CLI errors and evaluation reporting.
Temporary files and monkeypatching isolate tests from the supplied booking data. No model key or network is required for the tests.

Unit tests check deterministic functions. Offline integration tests exercise file reads and fake-model tool-call/result round trips.
Real-model evaluation checks behavior that a fake model cannot establish, such as choosing a useful query or refusing an unrelated request.
The GitHub Actions workflow runs Ruff, formatting, mypy and offline pytest on pushes and pull requests without a model key.
Local pre-commit hooks run the same categories of checks when installed.

The CLI handles provider failures, timeouts, common data errors, unexpected response types and empty model output without showing the key.
The evaluator records error type/status and saves results after each question. Interrupted runs cannot currently resume, and systemic quota errors do not automatically stop the full evaluation.

Request timeouts were disabled for the saved experiments and remain `None` in configuration. A stalled request therefore requires interruption; the five-round budget is not a wall-clock deadline.
The shared client factory keeps CLI/evaluator settings consistent and converts seconds to the milliseconds expected by `HttpOptions` when a finite timeout is configured.
An offline MockTransport check found that SDK 2.33.0 normalizes the old retry setting of zero: both that setting and the explicit minimum setting made two transport calls for a simulated 503. The application does not claim that SDK retries are disabled.

## Evaluation results

The 45-question development set includes ten expected refund amounts and three unrelated refusal requests.
After development changes were complete, a separate 15-question holdout added paraphrases, combined requirements, two refunds and two unrelated requests.
Its questions were not used to tune D before the recorded model comparison, but share the same small domain and documents.

| Dataset | Variant / model | PASS | FAIL | Pass rate |
| --- | --- | ---: | ---: | ---: |
| 45 development questions | A / 3.5 Flash-Lite, rescored v2 | 34 | 11 | 75.6% |
| 45 development questions | B / 3.5 Flash-Lite, rescored v2 | 40 | 5 | 88.9% |
| 45 development questions | C / 3.5 Flash-Lite | 41 | 4 | 91.1% |
| 45 development questions | D / 3.5 Flash-Lite | 43 | 2 | 95.6% |
| 45 development questions | D / 3.8 Flash | 43 | 2 | 95.6% |
| 15 holdout questions | D / 3.5 Flash-Lite | 14 | 1 | 93.3% |
| 15 holdout questions | D / 3.8 Flash | 14 | 1 | 93.3% |

All listed runs completed with no recorded API errors. Equal totals hide different failures.
The [complete comparison](eval/comparison.md) links every raw report, records model/prompt/question provenance, tool counts and timings, and includes the initial 17/22 run separately.

A to B changed tokenization, ranking and result count together, while retaining the prompt. It improved retrieval, including seasonal opening hours.
C added aliases and changed instructions; it improved some answers but introduced regressions in age advice, voucher explanation and location lookup.
D added structured refund output and complete-document reading. Both D runs correctly explained voucher/deposit returns and recovered the location through a full FAQ read. These are combined changes, so a single improvement cannot be attributed to one feature alone.

| Final D run | Remaining failures |
| --- | --- |
| Development / 3.5 | Repeated searches reach the step limit for cats; the unusual payment question is misclassified and answered without supporting tools |
| Development / 3.8 | Cats still reach the step limit; the Revolut answer adds an unsupported universal claim about card acceptance |
| Holdout / 3.5 | Absence of a documented student discount becomes an unjustified categorical denial |
| Holdout / 3.8 | The phone-holder question reaches the step limit instead of explaining that the information is unavailable |

On the 45-question D runs, 3.5 made 47 tool calls versus 68 for 3.8; summed case times were 245.55 versus 510.93 seconds.
On holdout, they made 21 versus 27 tool calls and took 95.03 versus 192.65 seconds.
Network conditions, service load and extra rounds affect these times; they are not a controlled latency benchmark. Token usage and actual monetary costs were not recorded.

Automatic checks cover tool names, booking IDs, refund amounts, booking status, not-found wording, nonempty answers and step limits.
A final pass also requires a qualitative review of the whole answer: correct primary facts do not excuse contradictory recommendations or unsupported additions.
Reviews and their rationales were prepared with ChatGPT/Codex assistance, not an independent human benchmark. Some answers omit secondary details without changing the answer to the question; the notes explain those judgments.

Scorer v2 recognizes selected unambiguous zero-refund phrases. Rescoring preserved original answers and traces: B moved from 39/45 to 40/45 because a semantically correct zero refund had been rejected for omitting a numeric currency amount.
The original and rescored reports are retained. This is an evaluator correction, not an improvement in the model's response.

Each configuration has one recorded run. Development-set tuning, a small holdout and subjective review prevent strong claims about generalization or statistical significance.
The D holdout evaluator's `--questions` change was uncommitted when run; the recorded commit alone does not fully reproduce that evaluator. The actual question hash, prompt, model and traces are preserved, and the change is now committed.
Cleanup was verified offline against all saved scorer-v2 checks and the evaluated D prompt; no fresh live-model run was performed after that refactor.

## AI-assisted development

ChatGPT/Codex helped with implementation and test examples, SDK debugging, question drafting, review notes, comparisons, code cleanup and documentation. The repository therefore includes AI-generated contributions; this was not autocomplete-only assistance.

An early integration suggestion accessed `output_text` directly on the SDK result. Pylance and mypy reported that the return type could also be a stream. The code was changed to check `isinstance(interaction, Interaction)` before accessing non-streaming fields.

An earlier non-mutation test called the refund function against the real `bookings.json` and checked afterward that it was unchanged. That would detect an accidental write only after damaging the source file. I requested a monkeypatch version, and the test now uses a temporary copy. No damage to the actual file was observed.

The assistant initially proposed tokenization. I chose to measure a simple substring baseline first and then compare the changed approach. This was a change in development direction, not an AI factual error. The measurements also showed that tokenization alone does not connect purchase wording with the FAQ's sales wording.

The assistant also incorrectly described the original zero-retry setting as disabling SDK retries. An offline transport experiment showed the actual retry behavior, and the claim was corrected. This reinforced the need to check SDK behavior rather than infer it from a parameter name.

## Limitations and next steps

- Retrieval is lexical and uses a small hand-maintained alias list. Full-document reads improve access to facts but do not guarantee useful queries or a final answer within the step budget.
- Grounding and refusals depend on model behavior. A model can still invent an exception, overstate card acceptance or confuse missing information with a prohibition.
- Booking conversion is not comprehensive runtime validation. Negative/non-finite amounts, duplicate IDs, timezone-free timestamps and inconsistent date ranges are not all rejected. All records are parsed before lookup, so one malformed record can block another booking.
- There is no memory between CLI questions and no support for hypothetical cancellation times such as tomorrow. Adding memory alone would not make future-time refund calculation correct.
- Authentication and production customer-data access control are outside this demonstration. Booking IDs are not credentials.
- The API can fail, enforce quotas or require billing. Timeouts are disabled and evaluation resume is not implemented.
- Interactions exceptions are imported from an internal SDK module. The lockfile and offline tests help detect changes but do not make that import a stable API.

With more time, I would first add a finite configurable request timeout, stop repeated attempts after systemic quota/billing failures, and support safe evaluation resume with matching configuration checks.
Then I would target the observed stopping and undocumented-policy errors and evaluate repeated runs on additional frozen questions.
Conversation memory would be a later optional feature; a framework, web UI or vector database is unnecessary for this dataset.
