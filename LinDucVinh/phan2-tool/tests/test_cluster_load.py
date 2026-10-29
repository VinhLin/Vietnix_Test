import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cluster_load import analyze, main


class AnalyzeTests(unittest.TestCase):
    def test_overloaded_source_gets_safe_move(self):
        data = {
            "cluster": "test",
            "nodes": [
                {"node": "a", "status": "online", "cpu_cores": 4, "mem_total": 8 * 1024**3},
                {"node": "b", "status": "online", "cpu_cores": 8, "mem_total": 16 * 1024**3},
            ],
            "vms": [
                {"vmid": 1, "name": "large", "node": "a", "status": "running", "vcpus": 4,
                 "cpu_usage": 1.0, "mem_max": 7 * 1024**3, "mem_used": 7 * 1024**3},
            ],
        }
        result = analyze(data)
        self.assertEqual(result["overloaded_nodes"], [])
        self.assertTrue(result["migration_complete"])
        self.assertEqual(len(result["migration_plan"]), 1)
        move = result["migration_plan"][0]
        self.assertEqual((move["vmid"], move["from"], move["to"]), (1, "a", "b"))
        self.assertLessEqual(move["target_after"]["cpu_percent"], 80)
        self.assertLessEqual(move["target_after"]["memory_percent"], 85)
        self.assertLessEqual(move["target_after"]["vcpu_per_core"], 2.5)
        self.assertLessEqual(move["source_after"]["cpu_percent"], 80)

    def test_invalid_records_warn_without_crashing_and_block_unsafe_move(self):
        data = {
            "nodes": [{"node": "a", "status": "online", "cpu_cores": 4, "mem_total": 8 * 1024**3},
                      {"node": "b", "status": "online", "cpu_cores": 4, "mem_total": 256 * 1024}],
            "vms": [{"vmid": 1, "name": "badcpu", "node": "a", "status": "running", "vcpus": 2,
                     "cpu_usage": 31, "mem_max": 6 * 1024**3, "mem_used": 6 * 1024**3},
                    {"vmid": 2, "name": "orphan", "node": "missing", "status": "running", "vcpus": 1,
                     "cpu_usage": 0.2, "mem_max": 1, "mem_used": 1}]
        }
        result = analyze(data)
        self.assertEqual(result["migration_plan"], [])
        joined = " ".join(w["message"] for w in result["warnings"])
        self.assertIn("outside documented range", joined)
        self.assertIn("absent from nodes[]", joined)
        self.assertIn("implausibly small", joined)

    def test_duplicate_id_is_not_double_counted(self):
        node = {"node": "a", "status": "online", "cpu_cores": 8, "mem_total": 16 * 1024**3}
        vm = {"vmid": 7, "node": "a", "status": "running", "vcpus": 2, "cpu_usage": 0.5,
              "mem_max": 2 * 1024**3, "mem_used": 1 * 1024**3}
        result = analyze({"nodes": [node], "vms": [vm, dict(vm, name="duplicate")]})
        self.assertEqual(result["nodes"][0]["running_vms"], 1)
        self.assertTrue(any("duplicate vmid" in w["message"] for w in result["warnings"]))

    def test_invalid_document_type_raises_clear_value_error(self):
        with self.assertRaisesRegex(ValueError, "top-level JSON"):
            analyze([])

    def test_cli_malformed_json_returns_error_code_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
