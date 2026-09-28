# F23_reject_empty

Scenario: 17 plaintext bytes and 16 AAD bytes.

- reject_empty: expect F-01; trigger `empty`. Repair: Accept a valid zero-length plaintext.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
