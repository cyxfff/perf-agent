#include "workers.h"

#include <cstddef>
#include <iostream>

int main(int argc, char** argv) {
    std::size_t task_count = 16000;
    std::size_t worker_count = 8;
    std::size_t payload_size = 72;
    std::size_t compute_rounds = 14;
    std::size_t queue_capacity = 8;
    if (argc > 1) {
        task_count = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        worker_count = static_cast<std::size_t>(std::stoull(argv[2]));
    }
    if (argc > 3) {
        payload_size = static_cast<std::size_t>(std::stoull(argv[3]));
    }
    if (argc > 4) {
        compute_rounds = static_cast<std::size_t>(std::stoull(argv[4]));
    }
    if (argc > 5) {
        queue_capacity = static_cast<std::size_t>(std::stoull(argv[5]));
    }

    const double checksum = run_queue_lock_pipeline(
        task_count,
        worker_count,
        payload_size,
        compute_rounds,
        queue_capacity
    );
    std::cout << "queue_lock_pipeline_demo checksum=" << checksum << std::endl;
    return 0;
}
