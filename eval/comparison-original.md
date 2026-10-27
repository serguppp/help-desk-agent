# Retrieval comparison

| Metric | A | B |
| --- | ---: | ---: |
| PASS | 34 | 39 |
| FAIL | 11 | 6 |
| MANUAL_REVIEW | 0 | 0 |
| ERROR | 0 | 0 |
| Tool calls | 105 | 57 |
| Policy searches | 92 | 43 |
| Empty searches | 61 | 4 |
| Step-limit failures | 1 | 0 |

## Changed outcomes

| Question | A | B |
| --- | --- | --- |
| opening_march | FAIL | PASS |
| closed_january_first | FAIL | PASS |
| bike_sales | PASS | FAIL |
| unusual_payment | PASS | FAIL |
| refund_voucher | FAIL | PASS |
| shop_location | FAIL | PASS |
| rental_documents_and_deposit | FAIL | PASS |
| long_rental_discount | FAIL | PASS |
| staff_contact | FAIL | PASS |

## Configuration

- A: A-expanded-no-timeout, source commit 57fccfdcd73014cfd7c1dddf3efcd226c3660996
- B: B-expanded-no-timeout, source commit 386efdd006fcf687619fe6334746202fab384af4
- Questions SHA-256: e9a8f64bcc6bbf52342c4ce6b630f4fac867dcd718bb5b95bff57254372ca24d
- Scorer version: 1

A uses substring matching. B uses tokenization, heading-weighted ranking and a top-three limit.
This compares retrieval variants, not tokenization alone.
One run per variant on development questions does not establish statistical significance.
Empty searches can be appropriate for undocumented topics; fewer empty results alone do not prove better answers.
