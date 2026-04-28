#include "pipeline.h"

#include <cmath>
#include <vector>

namespace {

double mix_lane(double value, double weight, std::uint32_t selector) {
    if ((selector & 1u) == 0u) {
        return std::fma(value + weight, 1.0003 + static_cast<double>(selector & 7u) * 0.01, std::sqrt(weight + 3.0));
    }
    if ((selector & 2u) != 0u) {
        return std::sin(value + weight) + std::cos(weight * 0.35) + std::sqrt(value + 9.0);
    }
    if ((selector & 4u) != 0u) {
        return (value * 0.75 + weight * 1.2) / (1.0 + static_cast<double>((selector & 3u) + 1u));
    }
    return std::sqrt(value + 11.0) * 0.55 + weight * 1.8;
}

}  // namespace

double run_pipeline(
    const std::vector<PipelineRecord>& records,
    const std::vector<std::uint32_t>& gather_indices,
    std::size_t passes,
    std::size_t scratch_size
) {
    std::vector<double> scratch(scratch_size, 1.0);
    std::vector<double> reduction(32, 0.0);
    double checksum = 0.0;

    for (std::size_t pass = 0; pass < passes; ++pass) {
        const std::uint32_t phase_bias = static_cast<std::uint32_t>(pass * 1315423911u);
        for (std::size_t i = 0; i < records.size(); ++i) {
            const PipelineRecord& record = records[i];
            const std::size_t gather_index = (static_cast<std::size_t>(record.index ^ phase_bias) + i * 17u) % gather_indices.size();
            const std::size_t primary = gather_indices[gather_index] % scratch.size();
            const std::size_t secondary = (primary + record.stride + pass * 3u) % scratch.size();
            const std::size_t reduce_lane = (record.branch_mask + pass + i) & 31u;

            const double base = scratch[primary] + scratch[secondary] * 0.03125 + reduction[reduce_lane] * 0.005;
            const double mixed = mix_lane(base, record.weight, record.branch_mask + static_cast<std::uint32_t>(pass));

            scratch[primary] = mixed + scratch[(secondary + 7u) % scratch.size()] * 0.02;
            reduction[reduce_lane] += scratch[primary] * 0.001 + mixed * 0.0003;
            checksum += scratch[primary];
        }
    }

    for (double lane : reduction) {
        checksum += lane;
    }
    return checksum;
}
