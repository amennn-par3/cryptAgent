# F15_multi

Scenario: 15 plaintext bytes and 65536 AAD bytes.

- ignore_auth: expect C-04, E-01; trigger `tamper`. Repair: Reject failed authentication and return no value.
- omit_aad: expect C-04; trigger `aad`. Repair: Pass the actual associated data to both operations.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
