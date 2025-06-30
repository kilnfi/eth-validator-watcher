#include <iostream>
#include <vector>
#include <thread>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

static constexpr int kMaxLogging = 5;
static constexpr char kLogLabel[] = "scope:watched";

using float64_t = double;

// Flat structure to allow stupid simple conversions to Python without
// having too-many levels of mental indirections. Processing is shared
// between python (convenience) and cpp (fast).
struct Validator {
  // Updated data from the config processing
  std::vector<std::string> labels;

  // Updated data from the rewards processing
  bool missed_attestation = false;
  bool previous_missed_attestation = false;
  bool suboptimal_source = false;
  bool suboptimal_target = false;
  bool suboptimal_head = false;
  float64_t ideal_consensus_reward = 0;
  float64_t actual_consensus_reward = 0;

  // Updated data from the duties processing
  uint64_t duties_slot = 0;
  bool duties_performed_at_slot = false;

  // Updated data from the blocks processing
  std::vector<uint64_t> missed_blocks;
  std::vector<uint64_t> missed_blocks_finalized;
  std::vector<uint64_t> proposed_blocks;
  std::vector<uint64_t> proposed_blocks_finalized;
  std::vector<uint64_t> future_blocks_proposal;

  // Updated data from the beacon state processing
  std::string consensus_pubkey;
  uint64_t consensus_effective_balance = 0;
  bool consensus_slashed = false;
  uint64_t consensus_index = 0;
  std::string consensus_status;
  uint64_t consensus_type = 0;
  uint64_t consensus_activation_epoch = 0;

  // This is the weight of the validator compared to a 32 ETH 0x01
  // validator.
  float64_t weight = 0;
};

// Same, flat structure approach. This is used to aggregate data from
// all validators by labels.
struct MetricsByLabel {
  std::map<std::string, uint64_t> validator_status_count;
  std::map<std::string, double> validator_status_scaled_count;
  std::map<int, uint64_t> validator_type_count;
  std::map<int, uint64_t> validator_type_scaled_count;

  uint64_t suboptimal_source_count = 0;
  uint64_t suboptimal_target_count = 0;
  uint64_t suboptimal_head_count = 0;
  uint64_t optimal_source_count = 0;
  uint64_t optimal_target_count = 0;
  uint64_t optimal_head_count = 0;
  uint64_t validator_slashes = 0;
  uint64_t missed_duties_at_slot_count = 0;
  float64_t missed_duties_at_slot_scaled_count = 0.0f;
  uint64_t performed_duties_at_slot_count = 0;
  float64_t performed_duties_at_slot_scaled_count = 0.0f;
  float64_t duties_rate = 0.0f;
  float64_t duties_rate_scaled = 0.0f;

  float64_t ideal_consensus_reward = 0;
  float64_t actual_consensus_reward = 0;
  uint64_t missed_attestations_count = 0;
  float64_t missed_attestations_scaled_count = 0.0f;
  uint64_t missed_consecutive_attestations_count = 0;
  float64_t missed_consecutive_attestations_scaled_count = 0.0f;

  uint64_t proposed_blocks = 0;
  uint64_t missed_blocks = 0;
  uint64_t proposed_blocks_finalized = 0;
  uint64_t missed_blocks_finalized = 0;
  uint64_t future_blocks_proposal = 0;

  std::vector<std::pair<uint64_t, std::string>> details_proposed_blocks;
  std::vector<std::pair<uint64_t, std::string>> details_missed_blocks;
  std::vector<std::pair<uint64_t, std::string>> details_missed_blocks_finalized;
  std::vector<std::pair<uint64_t, std::string>> details_future_blocks;
  std::vector<std::string> details_missed_attestations;
};

namespace {
  void process_details(const std::string &validator, std::vector<uint64_t> slots, std::vector<std::pair<uint64_t, std::string>> *out) {
    for (const auto& slot: slots) {
      if (out->size() >= kMaxLogging) {
        break;
      }
      out->push_back({slot, validator});
    }
  }
  
  void process(uint64_t slot, std::size_t from, std::size_t to, const std::vector<Validator> &vals, std::map<std::string, MetricsByLabel> &out) {
    for (std::size_t i = from; i < to; i++) {
      auto &v = vals[i];

      for (const auto& label: v.labels) {
        MetricsByLabel & m = out[label];

        m.validator_status_count[v.consensus_status] += 1;
        m.validator_status_scaled_count[v.consensus_status] += 1.0 * v.weight;
        m.validator_type_count[v.consensus_type] += 1;
        m.validator_type_scaled_count[v.consensus_type] += 1.0 * v.weight;

        m.validator_slashes += (v.consensus_slashed == true);

        // Everything below implies to have a validator that is active
        // on the beacon chain, this prevents miscounting missed
        // attestation for instance.
        if (v.consensus_status.find("active") == std::string::npos) {
          continue;
        }

        m.suboptimal_source_count += int(v.suboptimal_source == true);
        m.suboptimal_target_count += int(v.suboptimal_target == true);
        m.suboptimal_head_count += int(v.suboptimal_head == true);
        m.optimal_source_count += int(v.suboptimal_source == false);
        m.optimal_target_count += int(v.suboptimal_target == false);
        m.optimal_head_count += int(v.suboptimal_head == false);

        if (slot == v.duties_slot) {
          m.performed_duties_at_slot_count += int(v.duties_performed_at_slot == true);
          m.performed_duties_at_slot_scaled_count += int(v.duties_performed_at_slot == true) * v.weight;
          m.missed_duties_at_slot_count += int(v.duties_performed_at_slot == false);
          m.missed_duties_at_slot_scaled_count += int(v.duties_performed_at_slot == false) * v.weight;
        }

        m.ideal_consensus_reward += v.ideal_consensus_reward;
        m.actual_consensus_reward += v.actual_consensus_reward;

        m.missed_attestations_count += int(v.missed_attestation == true);
        m.missed_attestations_scaled_count += int(v.missed_attestation == true) * v.weight;
        m.missed_consecutive_attestations_count += int(v.previous_missed_attestation == true && v.missed_attestation == true);
        m.missed_consecutive_attestations_scaled_count += int(v.previous_missed_attestation == true && v.missed_attestation == true) * v.weight;

        m.proposed_blocks += v.proposed_blocks.size();
        m.missed_blocks += v.missed_blocks.size();
        m.proposed_blocks_finalized += v.proposed_blocks_finalized.size();
        m.missed_blocks_finalized += v.missed_blocks_finalized.size();
        m.future_blocks_proposal += v.future_blocks_proposal.size();

        process_details(v.consensus_pubkey, v.proposed_blocks, &m.details_proposed_blocks);
        process_details(v.consensus_pubkey, v.missed_blocks, &m.details_missed_blocks);
        process_details(v.consensus_pubkey, v.missed_blocks_finalized, &m.details_missed_blocks_finalized);
        process_details(v.consensus_pubkey, v.future_blocks_proposal, &m.details_future_blocks);
        if (v.missed_attestation && m.details_missed_attestations.size() < kMaxLogging) {
          m.details_missed_attestations.push_back(v.consensus_pubkey);
        }
      }
    }
  }

  void merge_details(const std::vector<std::pair<uint64_t, std::string>> &details, std::vector<std::pair<uint64_t, std::string>> *out) {
    for (const auto& detail: details) {
      if (out->size() >= kMaxLogging) {
        break;
      }
      out->push_back(detail);
    }
  }

  void merge(const std::vector<std::map<std::string, MetricsByLabel>> &thread_metrics, std::map<std::string, MetricsByLabel> *out) {
    for (const auto& thread_metric: thread_metrics) {
      for (const auto& [label, metric]: thread_metric) {
        MetricsByLabel & m = (*out)[label];

        for (const auto& [status, count]: metric.validator_status_count) {
          m.validator_status_count[status] += count;
        }
        for (const auto& [status, count]: metric.validator_status_scaled_count) {
          m.validator_status_scaled_count[status] += count;
        }
        for (const auto& [type, count]: metric.validator_type_count) {
          m.validator_type_count[type] += count;
        }
        for (const auto& [type, count]: metric.validator_type_scaled_count) {
          m.validator_type_scaled_count[type] += count;
        }

        m.suboptimal_source_count += metric.suboptimal_source_count;
        m.suboptimal_target_count += metric.suboptimal_target_count;
        m.suboptimal_head_count += metric.suboptimal_head_count;
        m.optimal_source_count += metric.optimal_source_count;
        m.optimal_target_count += metric.optimal_target_count;
        m.optimal_head_count += metric.optimal_head_count;
        m.validator_slashes += metric.validator_slashes;
        m.missed_duties_at_slot_count += metric.missed_duties_at_slot_count;
        m.missed_duties_at_slot_scaled_count += metric.missed_duties_at_slot_scaled_count;
        m.performed_duties_at_slot_count += metric.performed_duties_at_slot_count;
        m.performed_duties_at_slot_scaled_count += metric.performed_duties_at_slot_scaled_count;

        m.ideal_consensus_reward += metric.ideal_consensus_reward;
        m.actual_consensus_reward += metric.actual_consensus_reward;
        m.missed_attestations_count += metric.missed_attestations_count;
        m.missed_attestations_scaled_count += metric.missed_attestations_scaled_count;
        m.missed_consecutive_attestations_count += metric.missed_consecutive_attestations_count;
        m.missed_consecutive_attestations_scaled_count += metric.missed_consecutive_attestations_scaled_count;

        m.proposed_blocks += metric.proposed_blocks;
        m.missed_blocks += metric.missed_blocks;
        m.proposed_blocks_finalized += metric.proposed_blocks_finalized;
        m.missed_blocks_finalized += metric.missed_blocks_finalized;
        m.future_blocks_proposal += metric.future_blocks_proposal;

        merge_details(metric.details_proposed_blocks, &m.details_proposed_blocks);
        merge_details(metric.details_missed_blocks, &m.details_missed_blocks);
        merge_details(metric.details_missed_blocks_finalized, &m.details_missed_blocks_finalized);
        merge_details(metric.details_future_blocks, &m.details_future_blocks);

        for (const auto& missed_attestation: metric.details_missed_attestations) {
          if (m.details_missed_attestations.size() < kMaxLogging) {
            m.details_missed_attestations.push_back(missed_attestation);
          }
        }
      }
    }

    // Compute the duties rate once per label.
    for (auto& [label, o]: *out) {
      const float64_t total = o.missed_duties_at_slot_count + o.performed_duties_at_slot_count;
      const float64_t total_scaled = o.missed_duties_at_slot_scaled_count + o.performed_duties_at_slot_scaled_count;

      // Here we assume that if we don't have any duties process, the
      // duties were performed.
      o.duties_rate = total ? float64_t(o.performed_duties_at_slot_count) / total : 1.0f;
      o.duties_rate_scaled = total_scaled ? float64_t(o.performed_duties_at_slot_scaled_count) / total_scaled : 1.0f;
    }
    
  }

} // anonymous namespace

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
    .def_readwrite("duties_slot", &Validator::duties_slot)
    .def_readwrite("duties_performed_at_slot", &Validator::duties_performed_at_slot)
    .def_readwrite("missed_blocks", &Validator::missed_blocks)
    .def_readwrite("missed_blocks_finalized", &Validator::missed_blocks_finalized)
    .def_readwrite("proposed_blocks", &Validator::proposed_blocks)
    .def_readwrite("proposed_blocks_finalized", &Validator::proposed_blocks_finalized)
    .def_readwrite("future_blocks_proposal", &Validator::future_blocks_proposal)
    .def_readwrite("consensus_pubkey", &Validator::consensus_pubkey)
    .def_readwrite("consensus_effective_balance", &Validator::consensus_effective_balance)
    .def_readwrite("consensus_slashed", &Validator::consensus_slashed)
    .def_readwrite("consensus_index", &Validator::consensus_index)
    .def_readwrite("consensus_status", &Validator::consensus_status)
    .def_readwrite("consensus_activation_epoch", &Validator::consensus_activation_epoch)
    .def_readwrite("consensus_type", &Validator::consensus_type)
    .def_readwrite("weight", &Validator::weight);

  py::class_<MetricsByLabel>(m, "MetricsByLabel")
    .def(py::init<>())
    .def_readwrite("validator_status_count", &MetricsByLabel::validator_status_count)
    .def_readwrite("validator_status_scaled_count", &MetricsByLabel::validator_status_scaled_count)
    .def_readwrite("validator_type_count", &MetricsByLabel::validator_type_count)
    .def_readwrite("validator_type_scaled_count", &MetricsByLabel::validator_type_scaled_count)
    .def_readwrite("suboptimal_source_count", &MetricsByLabel::suboptimal_source_count)
    .def_readwrite("suboptimal_target_count", &MetricsByLabel::suboptimal_target_count)
    .def_readwrite("suboptimal_head_count", &MetricsByLabel::suboptimal_head_count)
    .def_readwrite("missed_duties_at_slot_count", &MetricsByLabel::missed_duties_at_slot_count)
    .def_readwrite("missed_duties_at_slot_scaled_count", &MetricsByLabel::missed_duties_at_slot_scaled_count)
    .def_readwrite("performed_duties_at_slot_count", &MetricsByLabel::performed_duties_at_slot_count)
    .def_readwrite("performed_duties_at_slot_scaled_count", &MetricsByLabel::performed_duties_at_slot_scaled_count)
    .def_readwrite("duties_rate", &MetricsByLabel::duties_rate)
    .def_readwrite("duties_rate_scaled", &MetricsByLabel::duties_rate_scaled)
    .def_readwrite("suboptimal_head_count", &MetricsByLabel::suboptimal_head_count)
    .def_readwrite("optimal_source_count", &MetricsByLabel::optimal_source_count)
    .def_readwrite("optimal_target_count", &MetricsByLabel::optimal_target_count)
    .def_readwrite("optimal_head_count", &MetricsByLabel::optimal_head_count)
    .def_readwrite("validator_slashes", &MetricsByLabel::validator_slashes)
    .def_readwrite("ideal_consensus_reward", &MetricsByLabel::ideal_consensus_reward)
    .def_readwrite("actual_consensus_reward", &MetricsByLabel::actual_consensus_reward)
    .def_readwrite("missed_attestations_count", &MetricsByLabel::missed_attestations_count)
    .def_readwrite("missed_attestations_scaled_count", &MetricsByLabel::missed_attestations_scaled_count)
    .def_readwrite("missed_consecutive_attestations_count", &MetricsByLabel::missed_consecutive_attestations_count)
    .def_readwrite("missed_consecutive_attestations_scaled_count", &MetricsByLabel::missed_consecutive_attestations_scaled_count)
    .def_readwrite("proposed_blocks", &MetricsByLabel::proposed_blocks)
    .def_readwrite("missed_blocks", &MetricsByLabel::missed_blocks)
    .def_readwrite("proposed_blocks_finalized", &MetricsByLabel::proposed_blocks_finalized)
    .def_readwrite("missed_blocks_finalized", &MetricsByLabel::missed_blocks_finalized)
    .def_readwrite("future_blocks_proposal", &MetricsByLabel::future_blocks_proposal)
    .def_readwrite("details_proposed_blocks", &MetricsByLabel::details_proposed_blocks)
    .def_readwrite("details_missed_blocks", &MetricsByLabel::details_missed_blocks)
    .def_readwrite("details_missed_blocks_finalized", &MetricsByLabel::details_missed_blocks_finalized)
    .def_readwrite("details_future_blocks", &MetricsByLabel::details_future_blocks)
    .def_readwrite("details_missed_attestations", &MetricsByLabel::details_missed_attestations);
    
  m.def("fast_compute_validator_metrics", [](const py::dict& pyvals, uint64_t slot) {
    std::vector<Validator> vals;
    vals.reserve(pyvals.size());
    for (auto& pyval: pyvals) {
      vals.push_back(pyval.second.attr("_v").cast<Validator>());
    }

    auto n = std::thread::hardware_concurrency();

    std::size_t chunk = (vals.size() / n) + 1;
    std::vector<std::thread> threads;
    std::vector<std::map<std::string, MetricsByLabel>> thread_metrics(n);
    std::map<std::string, MetricsByLabel> metrics;

    {
      py::gil_scoped_release release;
      for (size_t i = 0; i < n; i++) {
        threads.push_back(std::thread([slot, i, chunk, &vals, &thread_metrics] {
            std::size_t from = i * chunk;
            std::size_t to = std::min(from + chunk, vals.size());
            process(slot, from, to, vals, thread_metrics[i]);
        }));
      }

      for (auto& thread: threads) {
        thread.join();
      }

      merge(thread_metrics, &metrics);
    }

    py::dict pymetrics;
    for (const auto& [label, metric]: metrics) {
      pymetrics[py::str(label)] = metric;
    }

    return pymetrics;
  });
}
