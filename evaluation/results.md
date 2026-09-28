# Cryptagent evaluation

**Run limitation:** All nine live OpenAI reviews returned the application's rate-or-quota error. Their recorded outcome is `review_unavailable`; no live model assessment of these sources was accepted. Case 10 deliberately used a separate process without a key and also returned `review_unavailable`. The intended outcome distribution has NOT been demonstrated. Resolve API billing/quota or rate limiting before running a new evaluation. Preserve these responses as the failed-service run; do not relabel them as code findings.

Model: GPT-6 Astra, medium reasoning. These are source-review tests, not execution or formal proofs.
Expected outcomes are test intentions, not independently established ground truth. No accuracy percentage is inferred.

| Case | Intended outcome | Actual outcome | Model status | Matches intention |
|---|---|---|---|---|
| 01 ignored_authentication_failure | potential_issues | review_unavailable | error | No |
| 02 reused_nonce | potential_issues | review_unavailable | error | No |
| 03 short_authentication_tag | potential_issues | review_unavailable | error | No |
| 04 unauthenticated_associated_data | potential_issues | review_unavailable | error | No |
| 05 output_before_authentication_check | potential_issues | review_unavailable | error | No |
| 06 incorrect_output_capacity | potential_issues | review_unavailable | error | No |
| 07 complete_session_integration | no_issues_identified | review_unavailable | error | No |
| 08 missing_implementation | insufficient_context | review_unavailable | error | No |
| 09 unrelated_sorting | outside_scope | review_unavailable | error | No |
| 10 review_service_unavailable | review_unavailable | review_unavailable | missing_key | Yes |

## 10 review_service_unavailable

Input: [C++ source](inputs/10_review_service_unavailable.cpp). Response: [full JSON](responses/10.json).

Connect an OpenAI API key to enable GPT-6 Astra · Medium. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 01 ignored_authentication_failure

Input: [C++ source](inputs/01_ignored_authentication_failure.cpp). Response: [full JSON](responses/01.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 02 reused_nonce

Input: [C++ source](inputs/02_reused_nonce.cpp). Response: [full JSON](responses/02.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 03 short_authentication_tag

Input: [C++ source](inputs/03_short_authentication_tag.cpp). Response: [full JSON](responses/03.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 04 unauthenticated_associated_data

Input: [C++ source](inputs/04_unauthenticated_associated_data.cpp). Response: [full JSON](responses/04.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 05 output_before_authentication_check

Input: [C++ source](inputs/05_output_before_authentication_check.cpp). Response: [full JSON](responses/05.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 06 incorrect_output_capacity

Input: [C++ source](inputs/06_incorrect_output_capacity.cpp). Response: [full JSON](responses/06.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 07 complete_session_integration

Input: [C++ source](inputs/07_complete_session_integration.cpp). Response: [full JSON](responses/07.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 08 missing_implementation

Input: [C++ source](inputs/08_missing_implementation.cpp). Response: [full JSON](responses/08.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.


## 09 unrelated_sorting

Input: [C++ source](inputs/09_unrelated_sorting.cpp). Response: [full JSON](responses/09.json).

OpenAI reported a rate or quota limit. Check the API project billing and limits. Source observations, if present, remain available.

- F01 **not_reviewed**: The AI review did not produce a validated assessment.
- F02 **not_reviewed**: The AI review did not produce a validated assessment.
- F03 **not_reviewed**: The AI review did not produce a validated assessment.
- F04 **not_reviewed**: The AI review did not produce a validated assessment.
- F05 **not_reviewed**: The AI review did not produce a validated assessment.
