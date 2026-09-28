# F16_multi

Scenario: 16 plaintext bytes and 0 AAD bytes.

- log_key: expect S-01; trigger `log`. Repair: Never output secret key bytes.
- oversize_plaintext: expect M-01; trigger `oversize-plaintext`. Repair: Restore the plaintext limit before allocation.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
