#include "dataset.h"
#include "pipeline.h"

#include <cstddef>
#include <iostream>

int main(int argc, char** argv) {
    std::size_t record_count = 180000;
    std::size_t passes = 16;
    std::size_t scratch_size = 65536;
    if (argc > 1) {
        record_count = static_cast<std::size_t>(std::stoull(argv[1]));
    }
    if (argc > 2) {
        passes = static_cast<std::size_t>(std::stoull(argv[2]));
    }
    if (argc > 3) {
        scratch_size = static_cast<std::size_t>(std::stoull(argv[3]));
    }

    const std::vector<PipelineRecord> records = build_records(record_count, 1337u);
    const std::vector<std::uint32_t> gather_indices = build_gather_indices(scratch_size, 4242u);
    const double checksum = run_pipeline(records, gather_indices, passes, scratch_size);
    std::cout << "spec_style_pipeline_demo checksum=" << checksum << std::endl;
    return 0;
}
