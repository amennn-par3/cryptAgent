# F19_log_plaintext

Scenario: 16 plaintext bytes and 255 AAD bytes.

- log_plaintext: expect S-01; trigger `log`. Repair: Remove plaintext logging, including debug sinks.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
