# F25_log_plaintext

Scenario: 17 plaintext bytes and 65536 AAD bytes.

- log_plaintext: expect S-01; trigger `log`. Repair: Remove plaintext logging, including debug sinks.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
