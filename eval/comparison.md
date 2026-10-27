# Evaluation comparison

Scores come from saved automatic checks and recorded qualitative reviews. Model names come from metadata, not folder names.

## Summary

| Run | Recorded model | Questions | Scorer | PASS | FAIL | Pending | ERROR | Pass rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [A-expanded-no-timeout](runs/A-expanded-no-timeout/results.md) | `gemini-3.5-flash-lite` | 45/45 | 1 | 34 | 11 | 0 | 0 | 75.6% |
| [A-expanded-rescored](runs/A-expanded-rescored/results.md) | `gemini-3.5-flash-lite` | 45/45 | 2 | 34 | 11 | 0 | 0 | 75.6% |
| [A-substring](runs/A-substring/results.md) | `gemini-3.5-flash-lite` | 22/22 | 1 | 17 | 5 | 0 | 0 | 77.3% |
| [B-expanded-no-timeout](runs/B-expanded-no-timeout/results.md) | `gemini-3.5-flash-lite` | 45/45 | 1 | 39 | 6 | 0 | 0 | 86.7% |
| [B-expanded-rescored](runs/B-expanded-rescored/results.md) | `gemini-3.5-flash-lite` | 45/45 | 2 | 40 | 5 | 0 | 0 | 88.9% |
| [C-normalized-prompt](runs/C-normalized-prompt/results.md) | `gemini-3.5-flash-lite` | 45/45 | 2 | 41 | 4 | 0 | 0 | 91.1% |
| [D-holdout-3.5](runs/D-holdout-3.5/results.md) | `gemini-3.5-flash-lite` | 15/15 | 2 | 14 | 1 | 0 | 0 | 93.3% |
| [D-holdout-3.8](runs/D-holdout-3.8/results.md) | `gemini-3.8-flash` | 15/15 | 2 | 14 | 1 | 0 | 0 | 93.3% |
| [D-refund-document-3.5-flash](runs/D-refund-document-3.5-flash/results.md) | `gemini-3.5-flash-lite` | 45/45 | 2 | 43 | 2 | 0 | 0 | 95.6% |
| [D-refund-document-3.8-flash](runs/D-refund-document-3.8-flash/results.md) | `gemini-3.8-flash` | 45/45 | 2 | 43 | 2 | 0 | 0 | 95.6% |

## 45 questions, scorer v2

Question-file SHA-256: `e9a8f64bcc6bbf52342c4ce6b630f4fac867dcd718bb5b95bff57254372ca24d`.

| Run | Checks OK | Tool calls | Searches | Empty searches | Document reads | Step limits | Total case time (s) | Median case time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A-expanded-rescored | 42/45 | 105 | 92 | 61 | 0 | 1 | 1440.24 | 28.87 |
| B-expanded-rescored | 44/45 | 57 | 43 | 4 | 0 | 0 | 967.57 | 18.43 |
| C-normalized-prompt | 44/45 | 49 | 35 | 6 | 0 | 0 | 810.85 | 14.17 |
| D-refund-document-3.5-flash | 43/45 | 47 | 31 | 6 | 2 | 1 | 245.55 | 5.44 |
| D-refund-document-3.8-flash | 44/45 | 68 | 46 | 7 | 5 | 1 | 510.93 | 9.55 |

### Different outcomes

| Question | A-expanded-rescored | B-expanded-rescored | C-normalized-prompt | D-refund-document-3.5-flash | D-refund-document-3.8-flash |
| --- | --- | --- | --- | --- | --- |
| `opening_march` | FAIL | PASS | PASS | PASS | PASS |
| `closed_january_first` | FAIL | PASS | PASS | PASS | PASS |
| `electric_bike_age` | PASS | PASS | FAIL | PASS | PASS |
| `bike_sales` | PASS | FAIL | PASS | PASS | PASS |
| `cat_in_basket` | PASS | PASS | PASS | FAIL | FAIL |
| `unusual_payment` | PASS | FAIL | FAIL | FAIL | PASS |
| `revolut_payment` | FAIL | FAIL | PASS | PASS | FAIL |
| `refund_voucher` | FAIL | PASS | FAIL | PASS | PASS |
| `unrelated_git` | FAIL | FAIL | PASS | PASS | PASS |
| `shop_location` | FAIL | PASS | FAIL | PASS | PASS |
| `rental_documents_and_deposit` | FAIL | PASS | PASS | PASS | PASS |
| `long_rental_discount` | FAIL | PASS | PASS | PASS | PASS |
| `staff_contact` | FAIL | PASS | PASS | PASS | PASS |
| `refund_already_cancelled` | FAIL | PASS | PASS | PASS | PASS |
| `refund_completed_booking` | FAIL | FAIL | PASS | PASS | PASS |

## 15 questions, scorer v2

Question-file SHA-256: `5f9400608bbd27f8d0486ebbd6f5461f59ecf8c3d3fc6e8bec495d5d1b48d818`.

| Run | Checks OK | Tool calls | Searches | Empty searches | Document reads | Step limits | Total case time (s) | Median case time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D-holdout-3.5 | 15/15 | 21 | 15 | 3 | 4 | 0 | 95.03 | 5.15 |
| D-holdout-3.8 | 14/15 | 27 | 20 | 4 | 5 | 1 | 192.65 | 12.18 |

### Different outcomes

| Question | D-holdout-3.5 | D-holdout-3.8 |
| --- | --- | --- |
| `holdout_phone_holder` | PASS | FAIL |
| `holdout_student_rates` | FAIL | PASS |

## 45 questions, scorer v1

Question-file SHA-256: `e9a8f64bcc6bbf52342c4ce6b630f4fac867dcd718bb5b95bff57254372ca24d`.

| Run | Checks OK | Tool calls | Searches | Empty searches | Document reads | Step limits | Total case time (s) | Median case time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A-expanded-no-timeout | 42/45 | 105 | 92 | 61 | 0 | 1 | 1440.24 | 28.87 |
| B-expanded-no-timeout | 43/45 | 57 | 43 | 4 | 0 | 0 | 967.57 | 18.43 |

### Different outcomes

| Question | A-expanded-no-timeout | B-expanded-no-timeout |
| --- | --- | --- |
| `opening_march` | FAIL | PASS |
| `closed_january_first` | FAIL | PASS |
| `bike_sales` | PASS | FAIL |
| `unusual_payment` | PASS | FAIL |
| `refund_voucher` | FAIL | PASS |
| `shop_location` | FAIL | PASS |
| `rental_documents_and_deposit` | FAIL | PASS |
| `long_rental_discount` | FAIL | PASS |
| `staff_contact` | FAIL | PASS |

## 22 questions, scorer v1

Question-file SHA-256: `8734ece3ef7282ca91c969003fb583b46764efff0c5997e7deda8dae1a099579`.

| Run | Checks OK | Tool calls | Searches | Empty searches | Document reads | Step limits | Total case time (s) | Median case time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A-substring | 22/22 | 46 | 38 | 23 | 0 | 0 | 395.14 | 15.60 |

## Recorded failures

- [A-expanded-no-timeout](runs/A-expanded-no-timeout/results.md): `opening_march`, `closed_january_first`, `revolut_payment`, `refund_voucher`, `unrelated_git`, `shop_location`, `rental_documents_and_deposit`, `long_rental_discount`, `staff_contact`, `refund_already_cancelled`, `refund_completed_booking`.
- [A-expanded-rescored](runs/A-expanded-rescored/results.md): `opening_march`, `closed_january_first`, `revolut_payment`, `refund_voucher`, `unrelated_git`, `shop_location`, `rental_documents_and_deposit`, `long_rental_discount`, `staff_contact`, `refund_already_cancelled`, `refund_completed_booking`.
- [A-substring](runs/A-substring/results.md): `closed_january_first`, `bike_sales`, `revolut_payment`, `refund_voucher`, `unrelated_geography`.
- [B-expanded-no-timeout](runs/B-expanded-no-timeout/results.md): `bike_sales`, `unusual_payment`, `revolut_payment`, `unrelated_git`, `refund_already_cancelled`, `refund_completed_booking`.
- [B-expanded-rescored](runs/B-expanded-rescored/results.md): `bike_sales`, `unusual_payment`, `revolut_payment`, `unrelated_git`, `refund_completed_booking`.
- [C-normalized-prompt](runs/C-normalized-prompt/results.md): `electric_bike_age`, `unusual_payment`, `refund_voucher`, `shop_location`.
- [D-holdout-3.5](runs/D-holdout-3.5/results.md): `holdout_student_rates`.
- [D-holdout-3.8](runs/D-holdout-3.8/results.md): `holdout_phone_holder`.
- [D-refund-document-3.5-flash](runs/D-refund-document-3.5-flash/results.md): `cat_in_basket`, `unusual_payment`.
- [D-refund-document-3.8-flash](runs/D-refund-document-3.8-flash/results.md): `cat_in_basket`, `revolut_payment`.

## Configuration

| Run | Model | Source commit | SDK | Max rounds | Request timeout (s) | Prompt SHA-256 | Run time UTC |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| [A-expanded-no-timeout](runs/A-expanded-no-timeout/results.json) | `gemini-3.5-flash-lite` | `57fccfdcd73014cfd7c1dddf3efcd226c3660996` | 2.33.0 | 5 | Disabled | `251afe619968f6e2fe4e28a7a2e66ab09b9c63fe66f99703b3b8e32e59ffb751` | 2026-10-27T15:40:21.063961+00:00 |
| [A-expanded-rescored](runs/A-expanded-rescored/results.json) | `gemini-3.5-flash-lite` | `57fccfdcd73014cfd7c1dddf3efcd226c3660996` | 2.33.0 | 5 | Disabled | `251afe619968f6e2fe4e28a7a2e66ab09b9c63fe66f99703b3b8e32e59ffb751` | 2026-10-27T15:40:21.063961+00:00 |
| [A-substring](runs/A-substring/results.json) | `gemini-3.5-flash-lite` | `3e7adcceedf5399a2c3eff9d53b28368890b195c` | 2.33.0 | 5 | Not recorded | `251afe619968f6e2fe4e28a7a2e66ab09b9c63fe66f99703b3b8e32e59ffb751` | 2026-10-27T13:17:38.886906+00:00 |
| [B-expanded-no-timeout](runs/B-expanded-no-timeout/results.json) | `gemini-3.5-flash-lite` | `386efdd006fcf687619fe6334746202fab384af4` | 2.33.0 | 5 | Disabled | `251afe619968f6e2fe4e28a7a2e66ab09b9c63fe66f99703b3b8e32e59ffb751` | 2026-10-27T16:18:33.997822+00:00 |
| [B-expanded-rescored](runs/B-expanded-rescored/results.json) | `gemini-3.5-flash-lite` | `386efdd006fcf687619fe6334746202fab384af4` | 2.33.0 | 5 | Disabled | `251afe619968f6e2fe4e28a7a2e66ab09b9c63fe66f99703b3b8e32e59ffb751` | 2026-10-27T16:18:33.997822+00:00 |
| [C-normalized-prompt](runs/C-normalized-prompt/results.json) | `gemini-3.5-flash-lite` | `99f9d7b02d7fd18ddc568985c75aaaeaac1da582` | 2.33.0 | 5 | Disabled | `ced04b5efcb075d006433182d62894761ed1e2cf703ce37aec18fdfad86f41d8` | 2026-10-27T17:04:17.346485+00:00 |
| [D-holdout-3.5](runs/D-holdout-3.5/results.json) | `gemini-3.5-flash-lite` | `873cdca9829a3a0045b00c81873b88fb4fc04e67` | 2.33.0 | 5 | Disabled | `e7bb3983eae9c11920e3d1e34aca749545021f972478a9e9a105f154bb90a48d` | 2026-10-27T19:00:22.743110+00:00 |
| [D-holdout-3.8](runs/D-holdout-3.8/results.json) | `gemini-3.8-flash` | `873cdca9829a3a0045b00c81873b88fb4fc04e67` | 2.33.0 | 5 | Disabled | `e7bb3983eae9c11920e3d1e34aca749545021f972478a9e9a105f154bb90a48d` | 2026-10-27T19:07:37.943356+00:00 |
| [D-refund-document-3.5-flash](runs/D-refund-document-3.5-flash/results.json) | `gemini-3.5-flash-lite` | `873cdca9829a3a0045b00c81873b88fb4fc04e67` | 2.33.0 | 5 | Disabled | `e7bb3983eae9c11920e3d1e34aca749545021f972478a9e9a105f154bb90a48d` | 2026-10-27T18:53:11.032617+00:00 |
| [D-refund-document-3.8-flash](runs/D-refund-document-3.8-flash/results.json) | `gemini-3.8-flash` | `873cdca9829a3a0045b00c81873b88fb4fc04e67` | 2.33.0 | 5 | Disabled | `e7bb3983eae9c11920e3d1e34aca749545021f972478a9e9a105f154bb90a48d` | 2026-10-27T18:44:12.433443+00:00 |

## Changes and interpretation

- A: literal substring retrieval. B: tokenization, heading-weighted ranking and a top-three limit, with the same prompt as A. This compares all retrieval changes together.
- C: token aliases and a changed prompt. D: structured refund components/methods, full-document reading and revised instructions. Improvements cannot be attributed to one change alone.
- Use scorer-v2 A/B reports for the 45-question comparison. Rescored reports reuse original answers and traces; they are not additional model runs.
- B changes from 39/45 to 40/45 after recognizing a zero refund expressed in words. This corrects the evaluator, not the agent.
- The original 22-question run and the new 15-question holdout are separate datasets. Do not compare their percentages directly with the 45-question development set.
- The D model comparisons have matching recorded prompts, SDK, business time and request budget. Check the configuration table before attributing differences to a model.
- Both D models score 43/45 on development questions and 14/15 on holdout questions, but fail different cases. There is no quality winner from these single runs.
- On the 45-question set, D 3.5 fails the cat step limit and the unusual payment question. D 3.8 fails the cat step limit and adds an unsupported universal Revolut-card acceptance claim.
- On holdout, 3.5 incorrectly asserts that no student rate exists; 3.8 reaches the step limit on phone holders. These show that reading the full document does not guarantee correct reasoning or stopping.

## Limits of the comparison

- The 45 development questions guided implementation changes. The holdout uses new questions from the same source documents, not an external benchmark.
- Qualitative reviews assess the whole answer, including unsupported additions. Some correct central answers omit secondary details; their review notes explain the judgment.
- Automatic checks alone do not establish correctness. Pending review is not a pass, and safe step-limit fallbacks remain failures.
- One run per configuration is insufficient to establish statistical significance or reliability on unseen questions.
- Wall times depend on service load, network conditions and the number of model rounds. They are observations, not a controlled performance benchmark. No token-based cost measurements were recorded.
- A source commit does not capture uncommitted evaluator changes. The D holdout runs used --questions before that change was committed; question and prompt hashes are preserved.
- Earlier scoring is retained in [comparison-original.md](comparison-original.md) and [comparison-rescored.md](comparison-rescored.md). Original results and rescored copies remain available.
- API quota and billing troubleshooting probes are not evaluation runs and are not included in these tables.
