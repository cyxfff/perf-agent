#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {

double hot_loop(std::size_t outer_loops, std::size_t inner_loops) {
    std::vector<double> values(inner_loops, 0.0);
    double checksum = 0.0;
    for (std::size_t round = 0; round < outer_loops; ++round) {
        for (std::size_t i = 0; i < inner_loops; ++i) {
            const double x = static_cast<double>((round + 1) * (i + 3));
            values[i] = std::sin(x) * std::cos(x / 3.0) + std::sqrt(x + 11.0);
            checksum += values[i];
        }
    }
    return checksum;
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t outer_loops = 1200;
    std::size_t inner_loops = 24000;
    if (argc > 1) {
        outer_loops = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        inner_loops = static_cast<std::size_t>(std::stoull(argv[2]));
    }

    const double checksum = hot_loop(outer_loops, inner_loops);
    std::cout << "cpu_bound_demo checksum=" << checksum << std::endl;
    return 0;
}
