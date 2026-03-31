#include <chrono>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

namespace {

std::mutex global_mutex;
std::uint64_t shared_counter = 0;

void worker(std::size_t iterations) {
    for (std::size_t i = 0; i < iterations; ++i) {
        std::lock_guard<std::mutex> guard(global_mutex);
        shared_counter += static_cast<std::uint64_t>(i % 7);
        if ((i % 128) == 0) {
            std::this_thread::sleep_for(std::chrono::microseconds(30));
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t thread_count = 6;
    std::size_t iterations = 180000;
    if (argc > 1) {
        thread_count = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        iterations = static_cast<std::size_t>(std::stoull(argv[2]));
    }

    std::vector<std::thread> threads;
    threads.reserve(thread_count);
    for (std::size_t i = 0; i < thread_count; ++i) {
        threads.emplace_back(worker, iterations);
    }
    for (auto& thread : threads) {
        thread.join();
    }

    std::cout << "lock_contention_demo counter=" << shared_counter << std::endl;
    return 0;
}
