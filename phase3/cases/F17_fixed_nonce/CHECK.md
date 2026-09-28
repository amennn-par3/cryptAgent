# F17_fixed_nonce

Scenario: 16 plaintext bytes and 1 AAD bytes.

- fixed_nonce: expect C-03; trigger `fixed-nonce`. Repair: Fresh random nonce on every encryption; inspect RNG data flow.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
