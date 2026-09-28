# F08_ignore_auth

Scenario: 1 plaintext bytes and 16 AAD bytes.

- ignore_auth: expect C-04, E-01; trigger `tamper`. Repair: Reject failed authentication and return no value.

Run through tools/run_native.py after native setup. Exit 10 is a contract violation; other unexpected nonzero exits are infrastructure/crash evidence requiring review. Source labels remain separate from execution evidence.
