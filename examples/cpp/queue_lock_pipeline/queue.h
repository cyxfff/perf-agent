#pragma once

#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <mutex>

struct QueueTask {
    std::uint32_t seed;
    std::uint32_t payload_size;
    std::uint32_t compute_rounds;
};

class BoundedQueue {
public:
    explicit BoundedQueue(std::size_t capacity);

    void push(QueueTask task);
    bool pop(QueueTask* task);
    void close();

private:
    std::size_t capacity_;
    bool closed_ = false;
    std::mutex mutex_;
    std::condition_variable not_empty_;
    std::condition_variable not_full_;
    std::deque<QueueTask> queue_;
};
