#pragma once

#include <cstddef>

double run_queue_lock_pipeline(
    std::size_t task_count,
    std::size_t worker_count,
    std::size_t payload_size,
    std::size_t compute_rounds,
    std::size_t queue_capacity
);
