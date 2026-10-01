# AES source-review pilot v1

Selected for the fixed AES-128-GCM / C++20 / Windows CNG / message-tampering
profile and exact F01–F05 output contract. This is an experimental supervised
fine-tuning pilot, not a claim of production security accuracy.

Source pool: the 22 AES-profile training records in the historical repaired-v3
release (16 distinct snippets, six related full-session variants). Validation
and test come from the original AES development corpus, four records each.
These are held out from this run, but have been inspected in earlier project
experiments. They are NOT a fresh independent benchmark.

The original records are preserved. The new release regenerates messages with
the active prompt, corrects overly certain labels, validates exact source
quotes through the production validator, rejects duplicate normalized source,
checks family overlap, records hashes, and checks the complete token length
without truncation. No whitespace augmentation inflates the count.

Missing AAD or empty-input requirements in partial snippets are now marked
insufficient context, rather than inferred from comments. Conditional nonce
reuse concerns are stated conditionally. A 32-byte key or non-profile tag is
a profile mismatch, not proof that AES-256 or another tag length is universally
insecure. No Windows runtime tests were performed.

Some non-CNG examples teach outside-scope behavior only; they do not add another
supported language, library or cryptographic scheme. Full-session variants stay
together in training. Related API patterns appear in development evaluation;
the small result cannot establish broad generalization.

The candidate currently contains **22 train, 4 validation and 4 test** code
samples. Build it once with `python training/build_aes_pilot.py`. See
`data/manifest.json` for counts, target distribution, hashes and token lengths.
The manifest deliberately marks training as not ready: the full-session label
review was interrupted and the development evaluation split is not fresh.
Native execution and stronger independent evaluation remain pending. The model
never supplies its own training labels.

API facts checked against Microsoft documentation:
- [BCryptDecrypt](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptdecrypt)
- [Authenticated cipher mode parameters](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/ns-bcrypt-bcrypt_authenticated_cipher_mode_info)

Adapters/checkpoints and evaluation outputs go under ignored `training/runs/`.
Training does not activate an adapter in the web app.
