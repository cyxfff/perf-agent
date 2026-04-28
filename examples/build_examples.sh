#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CPP_DIR="${SCRIPT_DIR}/cpp"
BIN_DIR="${SCRIPT_DIR}/bin"

CXX=${CXX:-g++}
CXXFLAGS=(-std=c++17 -O2 -g -fno-omit-frame-pointer -Wall -Wextra -pthread)

mkdir -p "${BIN_DIR}"

build_single() {
  local source_file=$1
  local output_file=$2
  echo "[build] ${output_file}"
  "${CXX}" "${CXXFLAGS[@]}" "${source_file}" -o "${output_file}"
}

build_multi() {
  local output_file=$1
  shift
  echo "[build] ${output_file}"
  "${CXX}" "${CXXFLAGS[@]}" "$@" -o "${output_file}"
}

build_single "${CPP_DIR}/cpu_bound_demo.cpp" "${BIN_DIR}/cpu_bound_demo"
build_single "${CPP_DIR}/lock_contention_demo.cpp" "${BIN_DIR}/lock_contention_demo"
build_single "${CPP_DIR}/multithread_cpu_demo.cpp" "${BIN_DIR}/multithread_cpu_demo"
build_single "${CPP_DIR}/multiprocess_fanout_demo.cpp" "${BIN_DIR}/multiprocess_fanout_demo"
build_single "${CPP_DIR}/phased_cache_wave_demo.cpp" "${BIN_DIR}/phased_cache_wave_demo"

build_multi \
  "${BIN_DIR}/spec_style_pipeline_demo" \
  "${CPP_DIR}/spec_style_pipeline/main.cpp" \
  "${CPP_DIR}/spec_style_pipeline/dataset.cpp" \
  "${CPP_DIR}/spec_style_pipeline/pipeline.cpp"

build_multi \
  "${BIN_DIR}/queue_lock_pipeline_demo" \
  "${CPP_DIR}/queue_lock_pipeline/main.cpp" \
  "${CPP_DIR}/queue_lock_pipeline/queue.cpp" \
  "${CPP_DIR}/queue_lock_pipeline/workers.cpp"
