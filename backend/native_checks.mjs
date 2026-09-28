// Untrusted source is NEVER executed in the web server process.
// No executable adapter is enabled until a Windows-isolated worker is installed
// and its results can be tied to a source hash, toolchain and profile version.
export function nativeEvidence(profile) {
  return profile.checks.map(check => ({...check, status:'not_run', evidenceType:'none',
    reason:'Native compilation and execution are not connected in this first version.'}));
}

