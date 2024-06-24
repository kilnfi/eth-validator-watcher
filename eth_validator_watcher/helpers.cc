#include <vector>
#include <thread>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// Flat structure to allow stupid simple conversions to Python without
// having too-many levels of mental indirections. Processing is shared
// between python (convenience) and cpp (fast).
struct WatchedValidator {
  // Updated data from the config processing
  std::vector<std::string> labels;

  // Updated data from the rewards processing
  bool missed_attestation;
  bool previous_missed_attestation;
  bool suboptimal_source;
  bool suboptimal_target;
  bool suboptimal_head;
  uint64_t ideal_consensus_reward;
  uint64_t actual_consensus_reward;

  // Updated data from the blocks processing
  std::vector<uint64_t> missed_blocks;
  std::vector<uint64_t> missed_blocks_finalized;
  std::vector<uint64_t> proposed_blocks;
  std::vector<uint64_t> proposed_blocks_finalized;
  std::vector<uint64_t> future_blocks_proposal;

  // Updated data from the beacon state processing
  std::string consensus_pubkey;
  uint64_t consensus_effective_balance;
  bool consensus_slashed;
  uint64_t consensus_index;
  std::string consensus_status;
};

PYBIND11_MODULE(eth_validator_watcher_ext, m) {

  py::class_<WatchedValidator>(m, "Validator")
    .def(py::init<>())
    .def_readwrite("labels", &WatchedValidator::labels)
    .def_readwrite("missed_attestation", &WatchedValidator::missed_attestation)
    .def_readwrite("previous_missed_attestation", &WatchedValidator::previous_missed_attestation)
    .def_readwrite("suboptimal_source", &WatchedValidator::suboptimal_source)
    .def_readwrite("suboptimal_target", &WatchedValidator::suboptimal_target)
    .def_readwrite("suboptimal_head", &WatchedValidator::suboptimal_head)
    .def_readwrite("ideal_consensus_reward", &WatchedValidator::ideal_consensus_reward)
    .def_readwrite("actual_consensus_reward", &WatchedValidator::actual_consensus_reward)
    .def_readwrite("missed_blocks", &WatchedValidator::missed_blocks)
    .def_readwrite("missed_blocks_finalized", &WatchedValidator::missed_blocks_finalized)
    .def_readwrite("proposed_blocks", &WatchedValidator::proposed_blocks)
    .def_readwrite("proposed_blocks_finalized", &WatchedValidator::proposed_blocks_finalized)
    .def_readwrite("future_blocks_proposal", &WatchedValidator::future_blocks_proposal)
    .def_readwrite("consensus_pubkey", &WatchedValidator::consensus_pubkey)
    .def_readwrite("consensus_effective_balance", &WatchedValidator::consensus_effective_balance)
    .def_readwrite("consensus_slashed", &WatchedValidator::consensus_slashed)
    .def_readwrite("consensus_index", &WatchedValidator::consensus_index)
    .def_readwrite("consensus_status", &WatchedValidator::consensus_status);
    
  m.def("fast_compute_validator_metrics", [](const py::list& validators) {
    py::dict metrics;

    // No parallelization here for now, let's see how it performs with
    // a single thread for now.
    for (const auto& v : validators) {

    }
    
    return metrics;
  });
}
