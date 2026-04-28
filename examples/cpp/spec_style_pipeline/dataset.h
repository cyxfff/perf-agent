#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

struct PipelineRecord {
    std::uint32_t index;
    std::uint32_t branch_mask;
    std::uint32_t stride;
    double weight;
};

std::vector<PipelineRecord> build_records(std::size_t record_count, std::uint32_t seed);
std::vector<std::uint32_t> build_gather_indices(std::size_t table_size, std::uint32_t seed);
