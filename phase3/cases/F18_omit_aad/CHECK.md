# F18_omit_aad

Scenario: 16 plaintext bytes and 16 AAD bytes.

- omit_aad: expect C-04; trigger `aad`. Repair: Pass the actual associated data to both operations.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
