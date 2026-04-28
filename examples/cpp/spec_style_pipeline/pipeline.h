#pragma once

#include "dataset.h"

#include <cstddef>
#include <cstdint>
#include <vector>

double run_pipeline(
    const std::vector<PipelineRecord>& records,
    const std::vector<std::uint32_t>& gather_indices,
    std::size_t passes,
    std::size_t scratch_size
);
