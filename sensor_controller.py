import gpiod
import time
import statistics
from threading import Thread, Lock
from datetime import datetime

class UltrasonicSensor:
    def __init__(self, chip, trigger_pin, echo_pin, sensor_id):
        self.chip = chip
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.sensor_id = sensor_id
        self.baseline = None
        self.trigger_line = None
        self.echo_line = None
        self.last_trigger_time = 0
        self.setup_gpio()

    def setup_gpio(self):
        self.trigger_line = self.chip.get_line(self.trigger_pin)
        self.echo_line = self.chip.get_line(self.echo_pin)
        self.trigger_line.request(consumer=f"sensor_{self.sensor_id}_trigger", type=gpiod.LINE_REQ_DIR_OUT)
        self.echo_line.request(consumer=f"sensor_{self.sensor_id}_echo", type=gpiod.LINE_REQ_DIR_IN)

    def measure_distance(self):
        self.trigger_line.set_value(1)
        time.sleep(0.00001)
        self.trigger_line.set_value(0)

        start_time = time.time()
        stop_time = time.time()

        while self.echo_line.get_value() == 0 and time.time() - start_time < 0.1:
            start_time = time.time()

        while self.echo_line.get_value() == 1 and time.time() - start_time < 0.1:
            stop_time = time.time()

        time_elapsed = stop_time - start_time
        distance = (time_elapsed * 34300) / 2
        return distance

    def calibrate(self, num_measurements=10):
        measurements = []
        for _ in range(num_measurements):
            dist = self.measure_distance()
            measurements.append(dist)
            time.sleep(0.1)
        
        self.baseline = statistics.median(measurements)
        print(f"Sensor {self.sensor_id} baseline: {self.baseline:.2f} cm")
        return self.baseline

    def cleanup(self):
        if self.trigger_line:
            self.trigger_line.release()
        if self.echo_line:
            self.echo_line.release()

class SensorSystem:
    def __init__(self):
        # Define pin mappings for 10 sensors
        self.sensor_pins = [
            {"trigger": 23, "echo": 24},  # Sensor 0
            {"trigger": 17, "echo": 27},  # Sensor 1
            {"trigger": 22, "echo": 10},  # Sensor 2
            {"trigger": 9, "echo": 11},   # Sensor 3
            {"trigger": 5, "echo": 6},    # Sensor 4
            {"trigger": 13, "echo": 19},  # Sensor 5
            {"trigger": 26, "echo": 21},  # Sensor 6
            {"trigger": 20, "echo": 16},  # Sensor 7
            {"trigger": 12, "echo": 7},   # Sensor 8
            {"trigger": 8, "echo": 25},   # Sensor 9
        ]
        self.chip = gpiod.Chip('4')  # For Raspberry Pi 5
        self.sensors = []
        self.running = False
        self.threads = []
        self.lock = Lock()
        self.debounce_time = 1.0  # Debounce time in seconds
        self.hit_callback = None
        print("SensorSystem initialized")

    def set_hit_callback(self, callback):
        """Set the callback function to be called when a sensor is triggered"""
        self.hit_callback = callback
        print("Callback function set")

    def setup_sensors(self):
        for i, pins in enumerate(self.sensor_pins):
            sensor = UltrasonicSensor(
                self.chip,
                pins["trigger"],
                pins["echo"],
                i
            )
            self.sensors.append(sensor)
        print(f"Setup completed for {len(self.sensors)} sensors")

    def calibrate_all_sensors(self):
        print("Starting sensor calibration...")
        for sensor in self.sensors:
            sensor.calibrate()
        print("Calibration complete!")

    def monitor_sensor(self, sensor):
        print(f"Started monitoring thread for sensor {sensor.sensor_id}")
        while self.running:
            try:
                current_distance = sensor.measure_distance()
                threshold = sensor.baseline * 0.10  # 10% threshold
                current_time = time.time()

                # Add distance debugging every few seconds
                if sensor.sensor_id == 0 and int(current_time) % 5 == 0:
                    print(f"Sensor 0 distance: {current_distance:.2f} cm (baseline: {sensor.baseline:.2f} cm)")

                if (abs(current_distance - sensor.baseline) > threshold and 
                    current_time - sensor.last_trigger_time > self.debounce_time):
                    with self.lock:
                        print(f"Motion detected on sensor {sensor.sensor_id}!")
                        print(f"Distance: {current_distance:.2f} cm (baseline: {sensor.baseline:.2f} cm)")
                        if self.hit_callback:
                            print(f"Calling hit callback for sensor {sensor.sensor_id}")
                            self.hit_callback(sensor.sensor_id)
                        else:
                            print("Warning: No callback function set!")
                        sensor.last_trigger_time = current_time
            except Exception as e:
                print(f"Error in sensor {sensor.sensor_id} monitoring: {e}")
            
            time.sleep(0.1)
        
        print(f"Stopped monitoring thread for sensor {sensor.sensor_id}")

    def start_monitoring(self):
        print("Starting sensor monitoring...")
        self.running = True
        self.threads = []
        
        for sensor in self.sensors:
            thread = Thread(target=self.monitor_sensor, args=(sensor,), daemon=True)
            thread.start()
            self.threads.append(thread)
        print(f"Started {len(self.threads)} monitoring threads")

    def stop_monitoring(self):
        print("Stopping sensor monitoring...")
        self.running = False
        for thread in self.threads:
            thread.join()
        
        for sensor in self.sensors:
            sensor.cleanup()
        
        self.chip.close()
        print("Sensor monitoring stopped and cleaned up")

    def is_running(self):
        """Check if the sensor system is running"""
        return self.running and all(thread.is_alive() for thread in self.threads)