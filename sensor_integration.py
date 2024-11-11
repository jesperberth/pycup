from sensor_controller import SensorSystem
import time

def start_sensor_system():
    """Initialize and start the sensor system"""
    system = SensorSystem()
    system.setup_sensors()
    system.calibrate_all_sensors()
    print("Starting sensor monitoring...")
    system.start_monitoring()
    return system

# Add a debug version of hit_cup to verify the sensor triggers
def debug_hit_cup(cup_number):
    print(f"DEBUG: hit_cup called for cup {cup_number}")

if __name__ == '__main__':
    try:
        system = start_sensor_system()
        system.set_hit_callback(debug_hit_cup)

        print("Sensor system running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        system.stop_monitoring()
        print("Cleanup complete")