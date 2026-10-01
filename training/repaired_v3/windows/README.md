# Pending native Windows evidence

These AES-128-GCM/Windows CNG sources and this harness are source-reviewed only.
No Windows compiler or runtime was available when they were authored. Do not mark
them native-verified based on compilation elsewhere or the Linux FHE tests.

On Windows with CMake and the Visual Studio C++ workload, from the repository root:

```powershell
cmake -S training/repaired_v3/windows -B runtime/cng-review
cmake --build runtime/cng-review --config Release
foreach ($variant in 'correct','empty','authentication','publication','keysize','bounds') {
    & "runtime/cng-review/Release/aes_$variant.exe"
    if ($LASTEXITCODE -ne 0) { throw "Native test execution failed: $variant" }
}
```

The harness emits observations, not an automatic security verdict. Inspect actual
behavior before promoting any source-reviewed label. The corrected case should
round-trip empty and nonempty messages, reject ciphertext/nonce/tag/AAD changes,
leave no output on rejection, use a 128-bit key and distinct nonces, and enforce
the documented length limits. The key-size mutation should report 256 bits.
Ignoring an authentication status is a source-level concern even if a particular
provider happens to reject through a secondary length check; do not fabricate a
successful tampering witness. Counter exhaustion and concurrency are not tested;
the source explicitly specifies single-threaded operation.
