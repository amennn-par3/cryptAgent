# F11_multi

Scenario: 15 plaintext bytes and 0 AAD bytes.

- fixed_nonce: expect C-03; trigger `fixed-nonce`. Repair: Fresh random nonce on every encryption; inspect RNG data flow.
- fixed_key: expect C-02; trigger `fixed-key`. Repair: Use the library key generator; inspect production key source.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
