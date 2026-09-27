# Native Windows setup

Use Windows 11 x64, Visual Studio 2022 C++ Build Tools (v143, Windows SDK, CMake tools,
AddressSanitizer component), Python 3.11+ and an official x64 static libsodium package.
Do not enable sanitizers on the prebuilt crypto dependency. Match /MT runtime linkage.

1. Obtain the official Visual Studio libsodium archive from
   https://download.libsodium.org/libsodium/releases/ and verify its vendor signature
   according to https://doc.libsodium.org/installation . No download is performed here.
2. Extract it to a chosen local directory. Locate include/sodium.h and the x64 static
   Release libsodium.lib. Do not use a DLL import library with this SODIUM_STATIC profile.
3. Open **Developer PowerShell for VS 2022** and move into cryptagent.
4. Supply exact paths (replace these example values with your actual extracted paths):
```powershell
$env:CRYPTAGENT_SODIUM_INCLUDE = 'C:\dependencies\libsodium\include'
$env:CRYPTAGENT_SODIUM_LIBRARY = 'C:\dependencies\libsodium\x64\Release\v143\static\libsodium.lib'
cmake -S . -B build -A x64 "-DSODIUM_INCLUDE_DIR=$env:CRYPTAGENT_SODIUM_INCLUDE" "-DSODIUM_LIBRARY=$env:CRYPTAGENT_SODIUM_LIBRARY"
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
python tools/run_native.py --pilot --out native-results
```
The archive's actual layout may differ; use the paths you located. The runner uses
these same two environment variables. It invokes CMake with argument arrays, not shell text.

For diagnostic builds set `-DCRYPTAGENT_ASAN=ON`, use configuration RelWithDebInfo,
and install the MSVC ASan runtime/component. Do not use sanitizer timing measurements.
MSVC does not provide the same UndefinedBehaviorSanitizer workflow as other compilers;
this baseline uses MSVC ASan, /analyze and explicit integer/length tests. No UBSan
coverage is claimed. Full /analyze and fuzzing integration is Phase 4.

Before research runs populate phase1/windows-profile.json with exact compiler and SDK
versions, libsodium version, archive hash and verified signature provenance. Native
runner hashes supplied library/header files, but those hashes alone do not authenticate
the publisher. Keep the complete dependency tree and tool versions with the experiment.
Native timing uses QueryPerformanceCounter or a reviewed Windows harness, controls,
CPU/configuration records and fixed public lengths. That adapter is not implemented here.

Never run arbitrary user submissions with this local fixture runner. Phase 4 needs
actual Windows worker isolation. Installing tools and downloading binaries are not
performed by this package's scripts.
