# F14_multi

Scenario: 15 plaintext bytes and 255 AAD bytes.

- reject_boundary: expect F-01; trigger `boundary`. Repair: Accept the inclusive maximum size.
- fixed_nonce: expect C-03; trigger `fixed-nonce`. Repair: Fresh random nonce on every encryption; inspect RNG data flow.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
