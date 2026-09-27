# F29_log_key

Scenario: 1048576 plaintext bytes and 255 AAD bytes.

- log_key: expect S-01; trigger `log`. Repair: Never output secret key bytes.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
