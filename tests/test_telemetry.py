import unittest
import sys
import os

# Adjust path to find app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.telemetry_bridge import TelemetryBridge

class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.bridge = TelemetryBridge()

    def test_empty_telemetry(self):
        struct = self.bridge.get_empty_telemetry()
        self.assertIn("battery", struct)
        self.assertIn("imu", struct)
        self.assertEqual(len(struct["motors"]), 12)
        self.assertEqual(struct["battery"]["percentage"], 100)

    def test_mock_telemetry(self):
        struct = self.bridge.generate_mock_telemetry()
        self.assertIn("system", struct)
        self.assertGreaterEqual(struct["battery"]["percentage"], 10)
        self.assertLessEqual(struct["battery"]["percentage"], 100)
        self.assertEqual(len(struct["motors"]), 12)
        # Verify motor 0 has target positions
        self.assertIn("target_pos", struct["motors"][0])

    def test_mock_pointcloud(self):
        pc = self.bridge.generate_mock_pointcloud()
        self.assertEqual(pc.ndim, 2)
        self.assertEqual(pc.shape[1], 5) # x, y, z, time, density
        self.assertGreater(pc.shape[0], 0)

if __name__ == '__main__':
    unittest.main()
