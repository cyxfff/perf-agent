#include "queue.h"

#include <chrono>
#include <thread>

BoundedQueue::BoundedQueue(std::size_t capacity) : capacity_(capacity) {}

void BoundedQueue::push(QueueTask task) {
    std::unique_lock<std::mutex> lock(mutex_);
    not_full_.wait(lock, [&]() { return queue_.size() < capacity_ || closed_; });
    if (closed_) {
        return;
    }
    if ((queue_.size() % 4u) == 0u) {
        std::this_thread::sleep_for(std::chrono::microseconds(12));
    }
    queue_.push_back(task);
    lock.unlock();
    not_empty_.notify_one();
}

bool BoundedQueue::pop(QueueTask* task) {
    std::unique_lock<std::mutex> lock(mutex_);
    not_empty_.wait(lock, [&]() { return !queue_.empty() || closed_; });
    if (queue_.empty()) {
        return false;
    }
    if ((queue_.size() % 4u) == 1u) {
        std::this_thread::sleep_for(std::chrono::microseconds(10));
    }
    *task = queue_.front();
    queue_.pop_front();
    lock.unlock();
    not_full_.notify_one();
    return true;
}

void BoundedQueue::close() {
    std::lock_guard<std::mutex> lock(mutex_);
    closed_ = true;
    not_empty_.notify_all();
    not_full_.notify_all();
}
