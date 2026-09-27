# F20_multi

Scenario: 16 plaintext bytes and 65536 AAD bytes.

- oversize_aad: expect M-01; trigger `oversize-aad`. Repair: Restore the AAD limit in encryption.
- reject_empty: expect F-01; trigger `empty`. Repair: Accept a valid zero-length plaintext.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
