# F29_oversize_plaintext

Scenario: 1048576 plaintext bytes and 255 AAD bytes.

- oversize_plaintext: expect M-01; trigger `oversize-plaintext`. Repair: Restore the plaintext limit before allocation.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
