# Comparison of A, B and C

| Metric | A | B | C |
| --- | ---: | ---: | ---: |
| PASS | 34 | 40 | 41 |
| FAIL | 11 | 5 | 4 |
| MANUAL_REVIEW | 0 | 0 | 0 |
| ERROR | 0 | 0 | 0 |
| Tool calls | 105 | 57 | 49 |
| Policy searches | 92 | 43 | 35 |
| Empty searches | 61 | 4 | 6 |
| Step-limit failures | 1 | 0 | 0 |

## Changed outcomes

| Question | A | B | C |
| --- | --- | --- | --- |
| opening_march | FAIL | PASS | PASS |
| closed_january_first | FAIL | PASS | PASS |
| electric_bike_age | PASS | PASS | FAIL |
| bike_sales | PASS | FAIL | PASS |
| unusual_payment | PASS | FAIL | FAIL |
| revolut_payment | FAIL | FAIL | PASS |
| refund_voucher | FAIL | PASS | FAIL |
| unrelated_git | FAIL | FAIL | PASS |
| shop_location | FAIL | PASS | FAIL |
| rental_documents_and_deposit | FAIL | PASS | PASS |
| long_rental_discount | FAIL | PASS | PASS |
| staff_contact | FAIL | PASS | PASS |
| refund_already_cancelled | FAIL | PASS | PASS |
| refund_completed_booking | FAIL | FAIL | PASS |

## Configuration

- A: `A-expanded-no-timeout`, source commit `57fccfdcd73014cfd7c1dddf3efcd226c3660996`, run time `2026-10-27T15:40:21.063961+00:00`.
- B: `B-expanded-no-timeout`, source commit `386efdd006fcf687619fe6334746202fab384af4`, run time `2026-10-27T16:18:33.997822+00:00`.
- C: `C-normalized-prompt`, source commit `99f9d7b02d7fd18ddc568985c75aaaeaac1da582`, run time `2026-10-27T17:04:17.346485+00:00`.
- Model: `gemini-3.5-flash-lite`.
- SDK: `2.33.0`.
- Scorer version: 2.
- Questions SHA-256: `e9a8f64bcc6bbf52342c4ce6b630f4fac867dcd718bb5b95bff57254372ca24d`.

## Interpretation

- A uses substring matching.
- B introduces tokenization, heading-weighted ranking and a top-three limit; the prompt is unchanged from A.
- C adds token aliases and changes the prompt. Its result reflects both changes together.
- A and B were rescored offline using scorer v2; their original answers were preserved.
- Each variant has one run on the same 45 development questions.
- These results do not establish statistical significance or performance on unseen questions.
- Fewer searches or empty results alone do not prove better answer quality.
- Original A/B scoring is preserved in comparison-original.md; rescored A/B results are in comparison-rescored.md.
