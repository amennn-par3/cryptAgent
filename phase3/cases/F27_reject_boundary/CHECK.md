# F27_reject_boundary

Scenario: 1048576 plaintext bytes and 1 AAD bytes.

- reject_boundary: expect F-01; trigger `boundary`. Repair: Accept the inclusive maximum size.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
