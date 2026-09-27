# Requirement register

All rows are mandatory for the baseline assessment. Passing means the prescribed checks passed, not universal proof.

| ID | Property | Evidence recipe | Limit |
|---|---|---|---|
| F-01 | Functional correctness | Reference API comparison, round trip, empty and boundary tests | Testing does not prove all inputs correct. |
| C-01 | Initialize libsodium before use | Inspect sodium_init and test its failure seam | Real initialization failure may not be reproducible. |
| C-02 | Approved key generation | Inspect key-generation API and absence of fixed keys | No empirical test proves generator entropy. |
| C-03 | Fresh production nonce | Inspect randombytes_buf data flow; repeated-call test | Random nonce collisions are negligible, not impossible. |
| C-04 | Authenticate before release | Tamper ciphertext, nonce, tag and AAD; wrong-key test | Do not claim replay prevention. |
| M-01 | Bounded sizes and safe arithmetic | Boundary checks, AddressSanitizer, bounded fuzzing | Executed paths only; ASan is not a proof. |
| M-02 | Ownership and lifetime safety | Move and destruction tests, ASan, review | Does not establish safety of arbitrary C++. |
| S-01 | No unintended secret output | Capture stdout/stderr and inspect sinks | Caller-authorized plaintext output is permitted. |
| S-02 | Clear owned secret allocations | Inspect RAII cleanup and optimized code; instrument deallocation before free | No claims about all registers, caches or caller copies. |
| L-01 | No wrapper secret-dependent control or indexing | Restricted source review, with approved library calls trusted | Public lengths and authentication result may affect control flow. |
| L-02 | Complete controlled timing experiment | Native Windows release harness, fixed public lengths and positive/negative controls | No detected leakage is not a constant-time proof; harness pending Phase 4. |
| E-01 | Explicit failure without partial output | Allocation and authentication failure tests; exception-boundary review | OS process termination is outside recoverable-error contract. |
| B-01 | Reproducible Windows build | Compiler, SDK, dependency and source hashes with test logs | Passing on one profile does not pass another. |
