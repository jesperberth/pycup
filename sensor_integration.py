from sensor_controller import SensorSystem
import time

def start_sensor_system():
    """Initialize and start the sensor system

    Note: Monitoring is NOT started automatically. Call system.start_monitoring()
    after setting the hit callback with system.set_hit_callback(callback_function)
    """
    system = SensorSystem()
    system.setup_sensors()
    system.calibrate_all_sensors()

    # Add a small delay to let things stabilize before monitoring
    print("Waiting 0.5 seconds for sensors to stabilize...")
    time.sleep(0.5)

    return system

if __name__ == '__main__':
    try:
        # Test function to print when a sensor is triggered
        def test_hit(sensor_id):
            print(f"Test hit on sensor {sensor_id}")

        system = start_sensor_system()

        # Set callback BEFORE starting monitoring
        system.set_hit_callback(test_hit)
        system.start_monitoring()

        # Verify the system is running
        if system.is_running():
            print("Sensor system is running and monitoring")
        else:
            print("Warning: Sensor system may not be running properly")

        print("Running sensor test. Press Ctrl+C to exit.")
        # Monitor the system status
        while True:
            if not system.is_running():
                print("Warning: Sensor system stopped running!")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        system.stop_monitoring()
        print("Cleanup complete")