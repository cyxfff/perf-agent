#include "workers.h"

#include "queue.h"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <mutex>
#include <thread>
#include <vector>

namespace {

double execute_task(const QueueTask& task) {
    std::vector<double> scratch(task.payload_size, 0.0);
    double checksum = 0.0;
    for (std::size_t round = 0; round < task.compute_rounds; ++round) {
        for (std::size_t i = 0; i < scratch.size(); ++i) {
            const double x = static_cast<double>((task.seed + round + 1u) * (i + 5u));
            scratch[i] = std::sin(x * 0.00015) + std::cos(x * 0.00007) + std::sqrt(x + 9.0);
            checksum += scratch[i];
        }
    }
    return checksum;
}

}  // namespace

double run_queue_lock_pipeline(
    std::size_t task_count,
    std::size_t worker_count,
    std::size_t payload_size,
    std::size_t compute_rounds,
    std::size_t queue_capacity
) {
    BoundedQueue queue(queue_capacity);
    std::mutex reduction_mutex;
    double checksum = 0.0;

    std::vector<std::thread> workers;
    workers.reserve(worker_count);
    for (std::size_t worker_id = 0; worker_id < worker_count; ++worker_id) {
        workers.emplace_back([&, worker_id]() {
            QueueTask task{};
            double local_checksum = 0.0;
            std::size_t completed = 0;
            while (queue.pop(&task)) {
                local_checksum += execute_task(task);
                ++completed;
                if ((completed % 2u) == 0u) {
                    std::lock_guard<std::mutex> lock(reduction_mutex);
                    std::this_thread::sleep_for(std::chrono::microseconds(8));
                    checksum += local_checksum * 0.15;
                }
                if (((completed + worker_id) % 24u) == 0u) {
                    std::this_thread::sleep_for(std::chrono::microseconds(20));
                }
            }
            std::lock_guard<std::mutex> lock(reduction_mutex);
            checksum += local_checksum;
        });
    }

    for (std::size_t i = 0; i < task_count; ++i) {
        queue.push(QueueTask{
            .seed = static_cast<std::uint32_t>(i * 97u + 13u),
            .payload_size = static_cast<std::uint32_t>(payload_size),
            .compute_rounds = static_cast<std::uint32_t>(compute_rounds + (i % 3u)),
        });
        if ((i % 16u) == 0u) {
            std::this_thread::sleep_for(std::chrono::microseconds(6));
        }
    }
    queue.close();

    for (auto& worker : workers) {
        worker.join();
    }
    return checksum;
}
