from sensor_controller import SensorSystem

def start_sensor_system():
    """Initialize and start the sensor system"""
    system = SensorSystem()
    system.setup_sensors()
    system.calibrate_all_sensors()
    print("Starting sensor monitoring...")
    system.start_monitoring()
    return system

# This part is only used for testing the sensors independently
if __name__ == '__main__':
    try:
        # Test function to print when a sensor is triggered
        def test_hit(sensor_id):
            print(f"Test hit on sensor {sensor_id}")

        system = start_sensor_system()
        system.set_hit_callback(test_hit)

        # Keep the main thread running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        system.stop_monitoring()
        print("Cleanup complete")