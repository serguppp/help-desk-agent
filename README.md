# CityWheels Help Desk Agent

Command-line help desk assistant using Gemini tool calling and the supplied CityWheels data.
See [SOLUTION.md](SOLUTION.md) for design decisions and limitations and [eval/comparison.md](eval/comparison.md) for all recorded evaluations.

## Setup

Requirements: Python 3.12+, uv, Git and a Gemini API key with model access and remaining quota.
Run commands from the repository root.

```powershell
uv sync --locked --dev
Copy-Item .env.example .env
```

Create `.env` once and set `GEMINI_API_KEY` and `GEMINI_MODEL=gemini-3.5-flash-lite`.
Keep the real key in `.env`; do not commit it.

## Run the assistant

```powershell
uv run --locked --env-file .env python -u -m helpdesk.llm
```

Try `What is the status of CW-1002?` or `How much will I get back if I cancel CW-1004?`.
Use `exit`, `quit`, Ctrl+C or EOF to leave. Each question is independent; include the booking ID in follow-ups.
Calculations use the supplied fixed business time, not the actual system date. No booking is modified.

## Run offline checks

```powershell
uv run --locked pytest -q
uv run --locked pre-commit run --all-files
uv run --locked pre-commit install
```

Tests and CI do not call a real model. The local hooks run on commits; GitHub Actions runs on pushes and pull requests.

## Run evaluations

These commands make real API requests and may incur charges. Select a new output directory for each run; existing result files are overwritten.
`--model` overrides `GEMINI_MODEL` explicitly. `--variant` is a label and does not select historical code.

45 development questions on the current implementation:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.5-flash-lite --questions eval/questions.json --variant D-development-3.5 --output-dir eval/runs/new-development-3.5
```

15 holdout questions on the same implementation and model:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.5-flash-lite --questions eval/questions_holdout.json --variant D-holdout-3.5 --output-dir eval/runs/new-holdout-3.5
```

For a model comparison, keep code, questions, prompt and scorer unchanged:

```powershell
uv run --locked --env-file .env python -u -m eval.run_eval --model gemini-3.8-flash --questions eval/questions_holdout.json --variant D-holdout-3.8 --output-dir eval/runs/new-holdout-3.8
```

Review the saved answer and tool trace against `expected_answer` and the supplied policies. In each entry of `results.json`, fill `review` with `{"status": "PASS", "reason": "..."}` or `{"status": "FAIL", "reason": "..."}`. Do not edit answers or traces. Automatic success alone is not a final pass.

Regenerate a reviewed report and the comparison without API calls:

```powershell
uv run --locked python -m eval.run_eval --report-only --output-dir eval/runs/new-holdout-3.5
uv run --locked python -m eval.compare_runs
```

The comparison reads every `eval/runs/*/results.json` and groups results by question-file hash and scorer version. Historical A/B rescored reports reuse their original responses.
Results are saved after each question. Interrupted runs cannot currently be resumed. Client timeouts were disabled for the recorded experiments, so use Ctrl+C to interrupt a stalled request. Check quota/billing before repeating a run; an API error is not evidence of a wrong business answer.

## Supplied dataset documentation

The following section is preserved from the starting dataset README.

---

# CityWheels help desk — base data

CityWheels is a made-up bike rental shop. These files hold the data for its help desk agent. There is no code here: you write it.

## Files

| File | What it holds |
| --- | --- |
| `data/policies/prices.md` | Bike types, rental prices, add-ons, deposits and late return fees. |
| `data/policies/cancellations.md` | Rules for cancelling or changing a booking, and for refunds. |
| `data/policies/faq.md` | Answers to common questions: opening hours, age limits, payment, what to do when something goes wrong. |
| `data/bookings.json` | Example bookings. |

## Bookings

Each booking in `data/bookings.json` has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Booking number, for example `CW-1001`. |
| `status` | `confirmed`, `in_progress`, `completed` or `cancelled`. |
| `bike_type` | `city`, `e-bike` or `kids`. |
| `bikes` | How many bikes are booked. |
| `start`, `end` | When the rental starts and ends, with the time zone. |
| `add_ons` | Extras, such as `child_seat`. |
| `rental_price_eur` | Price of the rental itself, with add-ons. |
| `booking_fee_eur` | Fee for booking online. |
| `deposit_eur` | Deposit paid with the booking. |
| `paid_with` | `card` or `voucher`. |

## The current date

The bookings are set in June 2026. So that answers are the same every time, treat the current date and time as:

**2026-06-10 09:00, Europe/Warsaw time (UTC+02:00).**

## Example questions

- What time do you open on Saturday?
- How much is an e-bike for a whole day?
- I want to cancel booking CW-1002. How much will I get back?
- Can my 14-year-old rent an e-bike?
- What is the capital of Australia?
