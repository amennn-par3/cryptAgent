# F12_multi

Scenario: 15 plaintext bytes and 1 AAD bytes.

- omit_aad: expect C-04; trigger `aad`. Repair: Pass the actual associated data to both operations.
- log_plaintext: expect S-01; trigger `log`. Repair: Remove plaintext logging, including debug sinks.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
