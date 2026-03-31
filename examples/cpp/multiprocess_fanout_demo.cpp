#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace {

double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
    double checksum = 0.0;
    for (std::size_t round = 0; round < outer_loops; ++round) {
        for (std::size_t i = 0; i < inner_loops; ++i) {
            const double x = static_cast<double>((round + seed + 3) * (i + 11));
            checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
        }
    }
    return checksum;
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t process_count = 3;
    std::size_t outer_loops = 250;
    std::size_t inner_loops = 24000;
    if (argc > 1) {
        process_count = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        outer_loops = static_cast<std::size_t>(std::stoull(argv[2]));
    }
    if (argc > 3) {
        inner_loops = static_cast<std::size_t>(std::stoull(argv[3]));
    }

    std::vector<int> read_fds;
    std::vector<pid_t> children;
    read_fds.reserve(process_count);
    children.reserve(process_count);

    for (std::size_t i = 0; i < process_count; ++i) {
        int pipefd[2];
        if (pipe(pipefd) != 0) {
            std::perror("pipe");
            return 1;
        }

        pid_t pid = fork();
        if (pid < 0) {
            std::perror("fork");
            return 1;
        }
        if (pid == 0) {
            close(pipefd[0]);
            const double checksum = worker(outer_loops, inner_loops, i + 1);
            const std::string payload = std::to_string(checksum);
            const ssize_t written = write(pipefd[1], payload.data(), payload.size());
            (void)written;
            close(pipefd[1]);
            _exit(0);
        }

        close(pipefd[1]);
        read_fds.push_back(pipefd[0]);
        children.push_back(pid);
    }

    double total = 0.0;
    for (int fd : read_fds) {
        std::string buffer(128, '\0');
        const ssize_t count = read(fd, buffer.data(), buffer.size());
        if (count > 0) {
            total += std::stod(buffer.substr(0, static_cast<std::size_t>(count)));
        }
        close(fd);
    }

    for (pid_t child : children) {
        int status = 0;
        waitpid(child, &status, 0);
    }

    std::cout << "multiprocess_fanout_demo checksum=" << total << std::endl;
    return 0;
}
