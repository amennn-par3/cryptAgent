#!/usr/bin/env bash
# Project-local toolchains; no sudo, system driver changes, or home-profile edits.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_dir"
mkdir -p runtime
if [[ ! -x runtime/fhe-venv/bin/python ]]; then python3 -m venv runtime/fhe-venv; fi
runtime/fhe-venv/bin/python -m pip install --disable-pip-version-check -r training/expanded/requirements-probes.txt
if [[ ! -d runtime/openfhe-source ]]; then
    git clone --depth 1 --branch v1.4.2 https://github.com/openfheorg/openfhe-development.git runtime/openfhe-source
fi
[[ "$(git -C runtime/openfhe-source rev-parse HEAD)" == aa391988d354d4360f390f223a90e0d1b98839d7 ]]
runtime/fhe-venv/bin/cmake -S runtime/openfhe-source -B runtime/openfhe-build \
    -DCMAKE_INSTALL_PREFIX="$repo_dir/runtime/openfhe" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_UNITTESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_BENCHMARKS=OFF -DBUILD_STATIC=OFF -DWITH_OPENMP=OFF
runtime/fhe-venv/bin/cmake --build runtime/openfhe-build -j 4
runtime/fhe-venv/bin/cmake --install runtime/openfhe-build
if [[ ! -x runtime/rust/bin/rustc ]]; then
    archive=rust-1.91.1-x86_64-unknown-linux-gnu.tar.xz
    wget -q "https://static.rust-lang.org/dist/$archive" -O "runtime/$archive"
    wget -q "https://static.rust-lang.org/dist/$archive.sha256" -O "runtime/$archive.sha256"
    (cd runtime && sha256sum -c "$archive.sha256" && tar -xf "$archive")
    runtime/rust-1.91.1-x86_64-unknown-linux-gnu/install.sh --prefix="$repo_dir/runtime/rust" --without=rust-docs --disable-ldconfig
fi
CARGO_HOME="$repo_dir/runtime/cargo" CARGO_TARGET_DIR="$repo_dir/runtime/tfhe-build" \
    RUSTC="$repo_dir/runtime/rust/bin/rustc" runtime/rust/bin/cargo build --release --locked \
    --manifest-path training/expanded/rust/Cargo.toml -j 4
python3 training/expanded/build_dataset.py
python3 training/expanded/validate_dataset.py
