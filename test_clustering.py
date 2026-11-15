"""
Unit tests for SignalBrief clustering and briefing pipeline.
"""
import unittest
import json
import os
from briefing_engine import run_pipeline, cluster_articles, calculate_similarity

class TestBriefingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_dir, "sample_data.json")
        with open(data_path, "r", encoding="utf-8") as f:
            cls.articles = json.load(f)

    def test_sample_dataset_loaded(self):
        self.assertEqual(len(self.articles), 13)

    def test_clustering_reduces_noise(self):
        clusters = cluster_articles(self.articles, threshold=0.25)
        # 13 articles should group into 4 key developments
        self.assertEqual(len(clusters), 4)

    def test_pipeline_metrics(self):
        res = run_pipeline(self.articles, threshold=0.25)
        metrics = res["metrics"]
        self.assertEqual(metrics["total_articles"], 13)
        self.assertEqual(metrics["key_developments"], 4)
        self.assertGreaterEqual(metrics["noise_reduction_pct"], 60)

if __name__ == "__main__":
    unittest.main()
