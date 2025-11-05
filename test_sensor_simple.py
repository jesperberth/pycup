#!/usr/bin/env python3
"""
Simple sensor test script - shows real-time distance readings
and triggers when a ping pong ball is detected.

Usage: python3 test_sensor_simple.py
"""

from sensor_controller import SensorSystem
import time

def test_callback(sensor_id):
    print(f"🎯 HIT DETECTED on sensor {sensor_id}!")

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("SENSOR TEST - Real-time distance monitoring")
        print("=" * 60)

        # Initialize sensor system
        print("\n1. Initializing sensor system...")
        system = SensorSystem()
        system.setup_sensors()

        print("\n2. Calibrating (measuring baseline distance)...")
        print("   Make sure cups are empty!")
        system.calibrate_all_sensors()

        print("\n3. Starting monitoring...")
        system.set_hit_callback(test_callback)
        system.start_monitoring()

        print("\n" + "=" * 60)
        print("✅ Sensor system running!")
        print("=" * 60)
        print("\nInstructions:")
        print("  - Watch the distance readings scroll by")
        print("  - Drop a ping pong ball into cup 0")
        print("  - You should see '🎯 HIT DETECTED' message")
        print("  - Press Ctrl+C to exit")
        print("\n" + "=" * 60 + "\n")

        # Monitor continuously
        while True:
            if not system.is_running():
                print("⚠️ WARNING: Sensor system stopped running!")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Stopping sensor system...")
        print("=" * 60)
        system.stop_monitoring()
        print("✅ Cleanup complete!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
