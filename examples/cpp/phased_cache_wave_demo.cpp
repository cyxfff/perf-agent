#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

double hot_compute_phase(std::chrono::milliseconds duration, std::size_t working_set) {
    std::vector<double> values(working_set, 1.0);
    const auto deadline = Clock::now() + duration;
    double checksum = 0.0;
    std::size_t round = 1;
    while (Clock::now() < deadline) {
        for (std::size_t i = 0; i < values.size(); ++i) {
            const double x = static_cast<double>((round + 1) * (i + 17));
            values[i] = std::sin(x * 0.001) + std::cos(x * 0.00031) + std::sqrt(x + 3.0);
            checksum += values[i];
        }
        ++round;
    }
    return checksum;
}

double cache_pressure_phase(std::chrono::milliseconds duration, std::size_t large_elements) {
    std::vector<std::uint64_t> values(large_elements, 0x9e3779b97f4a7c15ULL);
    const auto deadline = Clock::now() + duration;
    std::uint64_t checksum = 0;
    std::size_t index = 0;
    while (Clock::now() < deadline) {
        for (std::size_t step = 0; step < values.size(); ++step) {
            index = (index + 4099) % values.size();
            values[index] ^= static_cast<std::uint64_t>(step + checksum);
            checksum += values[index];
        }
    }
    return static_cast<double>(checksum);
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t rounds = 10;
    std::size_t phase_ms = 180;
    std::size_t working_set = 4096;
    std::size_t large_mb = 96;

    if (argc > 1) {
        rounds = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        phase_ms = static_cast<std::size_t>(std::stoull(argv[2]));
    }
    if (argc > 3) {
        large_mb = static_cast<std::size_t>(std::stoull(argv[3]));
    }

    const std::size_t large_elements = (large_mb * 1024 * 1024) / sizeof(std::uint64_t);
    double checksum = 0.0;
    for (std::size_t round = 0; round < rounds; ++round) {
        checksum += hot_compute_phase(std::chrono::milliseconds(phase_ms), working_set);
        checksum += cache_pressure_phase(std::chrono::milliseconds(phase_ms), large_elements);
    }

    std::cout << "phased_cache_wave_demo checksum=" << checksum << std::endl;
    return 0;
}
