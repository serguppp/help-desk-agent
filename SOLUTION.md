# CityWheels Help Desk Agent

## Overview

A command-line assistant for the fictional CityWheels bike rental shop.
It answers questions about policies, prices, bookings, and cancellation
refunds using the supplied Markdown documents and booking data.

The LLM decides which tools to request. Python executes the tools and
calculates booking-specific refund amounts. The application does not
cancel bookings, modify reservations, or process payments.


## Installation and usage

Requirements:

- Python 3.12
- uv
- Git, used by the evaluator to record the source commit
- A Gemini API key and access to the configured model

Run the following commands from the repository root.

Install the locked dependencies:

```powershell
uv sync --locked --dev
```

For a fresh checkout, create the local configuration:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and configure:

```dotenv
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

The real API key belongs only in the local environment or `.env`.
The repository ignores `.env`; `.env.example` contains no real key.

Start the CLI:

```powershell
uv run --locked --env-file .env python -u -m helpdesk.llm
```

Example questions:

```text
What is the status of CW-1002?
How much will I get back if I cancel CW-1002?
Can my 14-year-old rent an electric bike?
```

Enter `exit` or `quit` to leave. Empty input is ignored, and EOF or
Ctrl+C exits gracefully.

Each question currently starts an independent conversation. Follow-up
questions must include the necessary context, such as the booking ID.

## Architecture and technical decisions

The application uses the Google Gen AI SDK directly through the
Interactions API.

| Module | Responsibility |
| --- | --- |
| `helpdesk/config.py` | File paths and fixed business time |
| `helpdesk/booking.py` | Read and convert booking data |
| `helpdesk/refund.py` | Calculate cancellation refunds |
| `helpdesk/policies.py` | Load, split, and search policy documents |
| `helpdesk/llm.py` | Tool declarations, dispatcher, agent loop, and CLI |
| `eval/run_eval.py` | Run evaluation, check outputs, and generate reports |

### Agent loop

For each question:

1. Send the question, system instruction, and tool declarations to Gemini.
2. Inspect the response for function calls.
3. Validate each requested tool name and its arguments.
4. Execute only explicitly allowed Python functions.
5. Serialize their results and return them using the corresponding
   `call_id`.
6. Continue through `previous_interaction_id` until the model returns
   a final answer or the step limit is reached.

Multiple tool calls in one response are supported.

Each user question allows up to five model requests. If the model still
requests tools on the fifth response, the agent stops and asks the user
to contact staff.

I implemented the tool-calling loop directly with the Gemini SDK.
The workflow is linear, and keeping it explicit makes argument
validation, tool execution, and the request limit easy to inspect
and test.

### Provider and model

The recorded baseline uses:

- Provider: Google Gemini API
- Model: `gemini-3.5-flash-lite`
- SDK: `google-genai` 2.33.0
- API: Interactions

I chose Gemini because it provided tool calling and was available
for this project. The baseline uses gemini-3.5-flash-lite, which worked
during development after a trial with another model returned a 503
high-demand error.

### Data representation

Bookings use `TypedDict`, with explicit conversion of JSON values:

- ISO timestamps become `datetime` values.
- Monetary values become `Decimal`.
- Dates and monetary values are serialized as strings in tool results.

`TypedDict` keeps the structures simple and provides static checking.
It does not perform runtime schema validation. I chose explicit conversion
instead of introducing an additional application-level validation library.

## Tools and business rules

The supplied `README.md`, policies, and bookings are the sources of truth.

### `get_booking`

Reads `data/bookings.json`, converts its records, and finds an exact
booking ID.

An unknown ID returns a structured not-found result rather than raising
an exception. Empty or non-string arguments are rejected.

All records are converted before lookup. Consequently, an invalid record
can prevent reading another booking.

### `calculate_refund`

The tool accepts only `booking_id`. The model cannot supply prices,
refund rates, or a replacement current time.

All calculations use the fixed business time:

```text
2026-06-10T09:00:00+02:00
```

For a booking with status `confirmed`:

| Time before rental start | Rental-price refund |
| --- | ---: |
| At least 48 hours | 100% |
| At least 24 hours but less than 48 | 50% |
| Less than 24 hours | 0% |

The deposit is added in full for an allowed cancellation. The booking fee
is excluded.

Bookings with status `in_progress`, `completed`, or `cancelled` cannot be
cancelled and receive no refund from this cancellation attempt. This does
not describe any historical refund.

The stored rental price and deposit are booking totals. The calculation
does not multiply them by the number of bikes or recalculate add-ons.

For example, CW-1002 has 33 hours remaining:

```text
80 EUR × 50% + 300 EUR deposit = 340 EUR
```

`Decimal` avoids binary floating-point errors. The supplied policies do
not define rounding for fractional cents, so no additional rounding rule
has been invented.

Refund methods come from the cancellation policy: rental refunds for
voucher payments are vouchers, while deposits follow their original
payment method. Exceptional storm refunds require a staff decision.

The current tool returns a total rather than a structured breakdown of
refund components and methods. The evaluation identified a weakness in
how the model explains the voucher/deposit distinction.

### `search_policies`

The baseline intentionally uses a simple retrieval method:

1. Read UTF-8 Markdown files from `data/policies`.
2. Split them at `#` and `##` headings.
3. Preserve introductory content, including the EUR/VAT statement.
4. Match the complete, lowercased query as a contiguous substring.
5. Return heading matches before body-only matches.

Results contain the source filename, heading, and text. All matching
sections are returned; there is no top-k ranking or tokenization yet.

This was useful as an understandable baseline, but it is sensitive to
wording. For example, `buy a bike` does not match `Do you sell bikes?`.

## Instructions, validation, and error handling

The system instruction requires the model to:

- Answer using tool-provided information.
- Use `calculate_refund` for booking-specific refund amounts.
- Avoid invented details, prices, and facts.
- Distinguish unrelated questions from relevant but undocumented topics.
- Refer unanswered questions to staff.
- Avoid claiming that bookings were changed or cancelled.
- Avoid guaranteeing exceptional weather refunds.

These are behavioral instructions, not guarantees. Evaluation is needed
to check whether the model follows them.

The dispatcher allows only the three declared tools and requires exactly
one non-empty string argument. Unknown tools and invalid arguments return
structured errors to the model.

Data errors are kept separate from argument errors. In particular, invalid
JSON is not converted into a misleading tool-argument error. A missing
or empty policies directory raises a file error instead of looking like
a successful search with no matches.

The CLI handles timeouts, provider errors, common data errors, and empty
model responses. Requests have a 30-second timeout, and automatic SDK
retries are disabled. This is a per-request timeout, not a 30-second
deadline for the entire agent loop.

The tools are read-only and the dispatcher does not execute arbitrary
code. However, booking IDs are not authentication, and this demonstration
is not suitable for exposing real customer bookings without access control.

## Tests

Run all offline tests with one command:

```powershell
uv run --locked pytest -q
```

The current suite contains 120 passing tests, including parameterized
cases. No API key or model connection is required.

The offline tests cover:

- Booking lookup, data conversion, invalid arguments, and file errors.
- Refund rules, booking statuses, and the 24/48-hour boundaries.
- Policy splitting and retrieval.
- Agent tool execution, serialization, multiple calls, and step limits.
- CLI error handling and evaluation reporting.

Unit tests verify individual functions. Offline integration tests check
file reads, refund calculations, and tool execution with a fake model.
Real-model answer quality is evaluated separately.

Ruff, formatting, mypy, and tests can also be run together:

```powershell
uv run --locked pre-commit run --all-files
```

To enable the local commit hooks:

```powershell
uv run --locked pre-commit install
```

## Evaluation

### Running it

The evaluation dataset contains 22 questions, including four cases with
expected refund amounts and three unrelated requests requiring refusal.

Run an evaluation:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --variant A-substring
```

This makes real API requests and overwrites the default report files.
Preserve existing results before another run, or choose another directory:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --variant A-substring --output-dir eval/runs/another-run
```

`--variant` records a label; it does not change the retrieval algorithm.

The evaluator saves:

- `eval/results.json`: questions, answers, tool traces, checks, review
  notes, timings, and configuration.
- `eval/results.md`: a readable report and status counts.

Results are saved after each question. A failed request does not prevent
later questions from running. Interrupted evaluations are not resumable.

### Assessment method

Automatic checks inspect tool use, booking IDs, refund values, selected
facts, empty answers, and step-limit failures.

These checks are deliberately limited. Finding a number or status word
does not establish the meaning of the whole answer. Refusal quality,
unsupported claims, and completeness require qualitative review.

A final `PASS` requires successful automatic checks and a recorded review
with a reason. Qualitative assessments and review notes were prepared
with ChatGPT/Codex assistance; they are not an independent human benchmark.

After editing only the `review` fields, regenerate the report without API
calls:

```powershell
uv run --locked python -m eval.run_eval --report-only
```

### Recorded baseline

The committed baseline was run on 2026-10-27 using source commit
`3e7adcceedf5399a2c3eff9d53b28368890b195c`.

| Result | Count |
| --- | ---: |
| PASS | 17 |
| FAIL | 5 |
| Pending review | 0 |
| ERROR | 0 |

The reviewed pass rate is 77.3%. All 22 questions completed, with no API
errors or step-limit failures.

The run included 38 policy searches, of which 23 returned no matches.
Some empty results were appropriate for undocumented topics; others
prevented answering questions covered by the policies.

The five failures were:

| Case | Finding |
| --- | --- |
| January 1 opening | Searches missed the opening-hours section, causing a false claim that information was unavailable |
| Buying a bike | Searches for buy/purchase/sales did not match the FAQ wording `sell` |
| Revolut payment | The payment policy was retrieved, but the answer omitted known card acceptance and clarification of the ambiguous payment method |
| Voucher refund | The amount was correct, but the answer omitted the separate deposit-return rule |
| Unrelated geography | The agent declined the question but omitted the required staff referral |

The Revolut and voucher cases were judged incomplete under the recorded
expectations; they were not refund calculation errors.

Detailed evidence is available in [the evaluation report](eval/results.md)
and [raw results](eval/results.json).

After exploratory tests, I updated the system instruction to distinguish
unrelated questions from relevant questions missing from the documents.
The baseline still failed to refer the geography question to staff.

This is one run on 22 development questions. It does not measure
performance on unseen questions or variation between repeated runs.

## AI-assisted development

ChatGPT/Codex helped with implementation examples, complete test examples,
SDK debugging, evaluation criteria, review notes, and this documentation.

### SDK response typing

An AI-generated integration example accessed `output_text` directly on
the result of `client.interactions.create`. Pylance and mypy reported that
the SDK return type could also be a stream.

The code was changed to check `isinstance(interaction, Interaction)`
before accessing `output_text`.

### Test isolation

An earlier proposed refund test called the function against the actual
`bookings.json` file and then checked that its contents were unchanged.
If a regression introduced a write, the assertion would detect it only
after the real file had been modified.

I requested a monkeypatch-based version. During review, we changed the
test to use a temporary copy and redirected `BOOKINGS_PATH` to it.

### Retrieval approach

The assistant initially suggested tokenizing policy queries. I decided
to start with literal substring matching and evaluate it before adding
tokenization, giving me a baseline for comparison.

The evaluation exposed missed matches, including searches for buying
bikes that did not match the FAQ wording “sell bikes.”

Tokenization is planned as a separate experiment using the same questions,
model, prompt, and request limit. It has not yet been implemented or
compared. Tokenization alone will not connect words such as “buy” and
“sell”; that requires query normalization or another retrieval strategy.

## Limitations and next steps

Current limitations include:

- Literal substring retrieval without synonyms or semantic matching.
- Prompt-based grounding that cannot guarantee correct model behavior.
- A small, development-informed evaluation set and one recorded run.
- Limited automatic assessment of natural-language answers.
- Conversion of booking data without full runtime schema validation:
  invalid local amounts or timezone-free dates are not comprehensively
  rejected.
- No explicit refund-component or payment-method fields in tool output.
- No conversation memory between CLI questions.
- No support for hypothetical cancellation times such as tomorrow.
- External API availability, usage limits, and costs.
- SDK exception imports from an internal module that may change after an
  upgrade.
- No authentication or production customer-data protections.
- No GitHub Actions workflow yet.

Next, I would compare token-based retrieval with the preserved baseline,
keeping the questions, model, prompt, and request limit unchanged.
Other improvements would include structured refund explanations,
targeted data validation, offline CI, conversation memory, and
a comparison with another model.