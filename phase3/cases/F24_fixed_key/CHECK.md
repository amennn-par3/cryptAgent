# F24_fixed_key

Scenario: 17 plaintext bytes and 255 AAD bytes.

- fixed_key: expect C-02; trigger `fixed-key`. Repair: Use the library key generator; inspect production key source.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
