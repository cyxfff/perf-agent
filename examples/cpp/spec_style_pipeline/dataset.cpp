#include "dataset.h"

#include <algorithm>

namespace {

std::uint32_t next_value(std::uint32_t state) {
    return state * 1664525u + 1013904223u;
}

}  // namespace

std::vector<PipelineRecord> build_records(std::size_t record_count, std::uint32_t seed) {
    std::vector<PipelineRecord> records;
    records.reserve(record_count);

    std::uint32_t state = seed;
    for (std::size_t i = 0; i < record_count; ++i) {
        state = next_value(state);
        const std::uint32_t stride = 1u + (state & 255u);
        const std::uint32_t branch_mask = (state >> 8) & 15u;
        const std::uint32_t index = (state >> 12) ^ static_cast<std::uint32_t>(i * 131u);
        const double weight = 0.25 + static_cast<double>((state >> 20) & 1023u) / 512.0;
        records.push_back(PipelineRecord{
            .index = index,
            .branch_mask = branch_mask,
            .stride = stride,
            .weight = weight,
        });
    }
    return records;
}

std::vector<std::uint32_t> build_gather_indices(std::size_t table_size, std::uint32_t seed) {
    std::vector<std::uint32_t> gather(table_size);
    for (std::size_t i = 0; i < table_size; ++i) {
        gather[i] = static_cast<std::uint32_t>(i);
    }

    std::uint32_t state = seed;
    for (std::size_t i = 0; i < table_size; ++i) {
        state = next_value(state);
        const std::size_t j = static_cast<std::size_t>(state) % table_size;
        std::swap(gather[i], gather[j]);
    }
    return gather;
}
