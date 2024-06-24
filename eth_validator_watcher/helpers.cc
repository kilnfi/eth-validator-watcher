#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(eth_validator_watcher_ext, m) {
  // This is a helper function that aims to be parallelized and fast,
  // this is the main bottleneck of the validator watcher.
  
  m.def("fast_compute_validator_metrics", [](const py::dict& validators) {
    py::dict metrics;

    return metrics;
  });
}
