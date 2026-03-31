#include <cmath>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

namespace {

double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
    std::vector<double> values(inner_loops, 0.0);
    double checksum = 0.0;
    for (std::size_t round = 0; round < outer_loops; ++round) {
        for (std::size_t i = 0; i < inner_loops; ++i) {
            const double x = static_cast<double>((round + seed + 1) * (i + 7));
            values[i] = std::sin(x) + std::cos(x / 5.0) + std::sqrt(x + 17.0);
            checksum += values[i];
        }
    }
    return checksum;
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t thread_count = 4;
    std::size_t outer_loops = 400;
    std::size_t inner_loops = 18000;
    if (argc > 1) {
        thread_count = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        outer_loops = static_cast<std::size_t>(std::stoull(argv[2]));
    }
    if (argc > 3) {
        inner_loops = static_cast<std::size_t>(std::stoull(argv[3]));
    }

    std::vector<std::thread> threads;
    std::vector<double> partial(thread_count, 0.0);
    threads.reserve(thread_count);
    for (std::size_t i = 0; i < thread_count; ++i) {
        threads.emplace_back([&, i]() { partial[i] = worker(outer_loops, inner_loops, i + 1); });
    }
    for (auto& thread : threads) {
        thread.join();
    }

    double checksum = 0.0;
    for (double value : partial) {
        checksum += value;
    }
    std::cout << "multithread_cpu_demo checksum=" << checksum << std::endl;
    return 0;
}
