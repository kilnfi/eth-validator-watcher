#include <vector>
#include <thread>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// Flat structure to allow stupid simple conversions to Python without
// having too-many levels of mental indirections. Processing is shared
// between python (convenience) and cpp (fast).
struct Validator {
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

  py::class_<Validator>(m, "Validator")
    .def(py::init<>())
    .def_readwrite("labels", &Validator::labels)
    .def_readwrite("missed_attestation", &Validator::missed_attestation)
    .def_readwrite("previous_missed_attestation", &Validator::previous_missed_attestation)
    .def_readwrite("suboptimal_source", &Validator::suboptimal_source)
    .def_readwrite("suboptimal_target", &Validator::suboptimal_target)
    .def_readwrite("suboptimal_head", &Validator::suboptimal_head)
    .def_readwrite("ideal_consensus_reward", &Validator::ideal_consensus_reward)
    .def_readwrite("actual_consensus_reward", &Validator::actual_consensus_reward)
    .def_readwrite("missed_blocks", &Validator::missed_blocks)
    .def_readwrite("missed_blocks_finalized", &Validator::missed_blocks_finalized)
    .def_readwrite("proposed_blocks", &Validator::proposed_blocks)
    .def_readwrite("proposed_blocks_finalized", &Validator::proposed_blocks_finalized)
    .def_readwrite("future_blocks_proposal", &Validator::future_blocks_proposal)
    .def_readwrite("consensus_pubkey", &Validator::consensus_pubkey)
    .def_readwrite("consensus_effective_balance", &Validator::consensus_effective_balance)
    .def_readwrite("consensus_slashed", &Validator::consensus_slashed)
    .def_readwrite("consensus_index", &Validator::consensus_index)
    .def_readwrite("consensus_status", &Validator::consensus_status);
    
  m.def("fast_compute_validator_metrics", [](const py::dict& pyvals) {
    py::dict metrics;

    std::vector<Validator> vals;

    vals.reserve(pyvals.size());
    
    for (auto& pyval: pyvals) {
      vals.push_back(pyval.second.attr("_v").cast<Validator>());
    }
 
    return metrics;
  });
}
