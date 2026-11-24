import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tagging import DOMAIN_ORDER, TAG_TO_DOMAINS, assign_domains, assign_tags
from fetch_emails_msg import _build_entry


class ClassificationTests(unittest.TestCase):
    def test_primary_domains(self):
        cases = {
            "Generative AI for Excel": "AI",
            "AI Agent Memory Management Bootcamp": "AI",
            "Machine Learning from Scratch": "AI",
            "Harness Engineering for Browser Agents": "AI",
            "Hands-On Microsoft Foundry": "AI",
            "PyTorch for Beginners": "AI",
            "Microsoft Fabric Data Engineer Associate Bootcamp (DP-700)": "Data",
            "Mastering pandas": "Data",
            "Introduction to Statistics for Data Analysis with Python": "Data",
            "Data Design for Microservices": "Data",
            "Azure Architecture: Best Practices": "Cloud",
            "Google Professional Cloud Architect Certification Crash Course": "Cloud",
            "Certified Kubernetes Administrator (CKA) Exam Prep": "DevOps",
            "Hands-on Policy as Code": "DevOps",
            "Modern Frontend Web Development in 5 Weeks": "Frontend",
            "Creating Angular Applications with GraphQL": "Frontend",
            "Backend (Web) Development in 4 Weeks": "Backend",
            "C# and .NET in 3 Weeks": "Languages",
            "Asynchronous Programming with Node.js": "Backend",
            "Advanced JavaScript": "Languages",
            "Design Patterns with TypeScript": "Software Engineering",
            "Python Web Development in 4 Weeks": "Backend",
            "ASP.NET Core 3.0, Web API and EF Core Fundamentals": "Backend",
            "Getting Started with Java: From Core Concepts to Real Code in 4 Hours": "Languages",
            "Graphs and Network Algorithms for Everyone": "Software Engineering",
            "Modular Monoliths": "Software Engineering",
            "Linux Under the Hood": "Systems & Networking",
            "TCP/IP Deep Dive with Wireshark for NetOps and SecOps": "Systems & Networking",
            "Certified Ethical Hacker (CEH) Bootcamp": "Security",
            "The Zero Trust Security Framework": "Security",
            "Building Your LinkedIn Network": "Career & Soft Skills",
            "Build Your Critical Thinking Skills": "Career & Soft Skills",
            "Basic Introduction to Quantum Computing": "Emerging Technology",
            "Blockchain and Cryptocurrency Essentials": "Emerging Technology",
            "O'Reilly Demo Day": "O'Reilly Events",
        }
        for event, expected in cases.items():
            with self.subTest(event=event):
                self.assertEqual(assign_domains(assign_tags(event), event), [expected])

    def test_false_positive_tags(self):
        for event, forbidden in [
            ("Digital strategy", {"Git", "AI"}),
            ("Paragraph editing", {"RAG", "AI"}),
            ("The Zero Trust Security Framework", {"Rust"}),
            ("Reactive Spring Boot", {"React", "Frontend"}),
            ("AI Agent Memory Management Bootcamp", {"Career", "Management"}),
            ("Machine Learning from Scratch", {"Learning", "Career"}),
            ("Hands-on GitHub Copilot", {"Git", "Version Control"}),
            ("Graphs and Network Algorithms for Everyone", {"Networking"}),
        ]:
            with self.subTest(event=event):
                self.assertFalse(forbidden.intersection(assign_tags(event)))

    def test_unmatched_titles_fail_explicitly(self):
        for event in ["", "A previously unknown course", "Certification"]:
            with self.subTest(event=event):
                with self.assertRaisesRegex(ValueError, "No domain classification"):
                    assign_domains(assign_tags(event), event)

    def test_domain_mappings_are_known(self):
        for domains in TAG_TO_DOMAINS.values():
            self.assertTrue(set(domains).issubset(DOMAIN_ORDER))

    def test_ingestion_uses_the_same_primary_domain(self):
        body = '<a href="https://learning.oreilly.com/recording">Watch the recording</a>'
        event = "Communicating Software Architecture"
        entry, reason = _build_entry("Recording: " + event, "", "2026-01-01", body, "course.eml")
        self.assertEqual(reason, "kept")
        self.assertEqual(entry["domains"], ["Career & Soft Skills"])
        with self.assertRaisesRegex(ValueError, "No domain classification"):
            _build_entry("Recording: A previously unknown course", "", "2026-01-01", body, "course.eml")

    def test_catalog_coverage(self):
        for name in ["data.json", "data.sample.json"]:
            path = ROOT / "data" / name
            if not path.exists():
                continue
            entries = json.loads(path.read_text(encoding="utf-8"))
            domain_count = 0
            for entry in entries:
                with self.subTest(dataset=name, event=entry["event"]):
                    tags = assign_tags(entry["event"])
                    domains = assign_domains(tags, entry["event"])
                    self.assertNotIn("Uncategorized", tags)
                    self.assertNotIn("Other", domains)
                    self.assertEqual(entry["tags"], tags)
                    self.assertEqual(entry["domains"], domains)
                    self.assertEqual(len(domains), 1)
                    self.assertIn(domains[0], DOMAIN_ORDER)
                    domain_count += len(domains)
            self.assertEqual(domain_count, len(entries))

    def test_retag_preserves_fields_and_rejects_unmatched_before_writing(self):
        entry = {
            "event": "Linux Fundamentals", "tags": [], "domains": [],
            "received": "2026-01-01T10:00:00Z", "recording_url": "https://example.test/",
            "custom": {"keep": True},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(json.dumps([entry]), encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "scripts" / "retag.py"), "--file", str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(path.read_text(encoding="utf-8"))[0]
            self.assertEqual(
                {k: v for k, v in updated.items() if k not in ("tags", "domains")},
                {k: v for k, v in entry.items() if k not in ("tags", "domains")},
            )
            path.write_text(json.dumps([entry, {"event": "A previously unknown course"}]), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
