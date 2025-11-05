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
            # {"trigger": 17, "echo": 27},  # Sensor 1
            # {"trigger": 22, "echo": 10},  # Sensor 2
            # {"trigger": 9, "echo": 11},   # Sensor 3
            # {"trigger": 5, "echo": 6},    # Sensor 4
            # {"trigger": 13, "echo": 19},  # Sensor 5
            # {"trigger": 26, "echo": 21},  # Sensor 6
            # {"trigger": 20, "echo": 16},  # Sensor 7
            # {"trigger": 12, "echo": 7},   # Sensor 8
            # {"trigger": 8, "echo": 25},   # Sensor 9
        ]
        self.chip = gpiod.Chip('4')  # For Raspberry Pi 5
        self.sensors = []
        self.running = False
        self.threads = []
        self.lock = Lock()
        self.debounce_time = 0.5  # Debounce time in seconds (reduced for faster re-triggering)
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
        import sys
        import traceback

        print(f"Started monitoring thread for sensor {sensor.sensor_id}")
        print(f"  Thread ID: {id(sensor)}")
        print(f"  self.running = {self.running}")

        loop_count = 0
        try:
            while self.running:
                loop_count += 1
                # Heartbeat every 100 loops (5 seconds at 0.05s sleep)
                if loop_count % 100 == 0:
                    print(f"[HEARTBEAT] Sensor {sensor.sensor_id} thread alive, loop #{loop_count}, self.running={self.running}")

                try:
                    current_distance = sensor.measure_distance()
                    # Use 1cm threshold for ping pong ball detection
                    # This is sensitive enough to detect a ball dropping into a cup
                    threshold = 1.0
                    current_time = time.time()

                    # Add distance debugging continuously for debugging
                    if sensor.sensor_id == 0:
                        # Print every 10 measurements (once per second at 0.1s sleep)
                        if hasattr(sensor, 'measurement_count'):
                            sensor.measurement_count += 1
                        else:
                            sensor.measurement_count = 0

                        if sensor.measurement_count % 10 == 0:
                            print(f"[SENSOR DEBUG] Sensor 0: {current_distance:.2f}cm (baseline: {sensor.baseline:.2f}cm, change: {sensor.baseline - current_distance:.2f}cm, threshold: {threshold:.2f}cm, loop={loop_count})")
                            sys.stdout.flush()

                    # Detect when distance gets SMALLER (ball/hand moves closer)
                    distance_change = sensor.baseline - current_distance

                    # Check debounce: has enough time passed since last trigger?
                    time_since_last_trigger = current_time - sensor.last_trigger_time
                    can_trigger = time_since_last_trigger > self.debounce_time

                    if distance_change > threshold and can_trigger:
                        with self.lock:
                            print(f"\n🎯 Motion detected on sensor {sensor.sensor_id}!")
                            print(f"   Distance: {current_distance:.2f} cm (baseline: {sensor.baseline:.2f} cm)")
                            print(f"   Change: {distance_change:.2f} cm (threshold: {threshold:.2f} cm)")
                            print(f"   Time since last trigger: {time_since_last_trigger:.2f}s\n")

                            if self.hit_callback:
                                print(f"   ✅ Calling hit callback for sensor {sensor.sensor_id}\n")
                                self.hit_callback(sensor.sensor_id)
                            else:
                                print("   ⚠️ Warning: No callback function set!\n")

                            sensor.last_trigger_time = current_time
                    elif distance_change > threshold:
                        # Would trigger but still in debounce period - only log occasionally
                        if sensor.measurement_count % 5 == 0:  # Only print every 0.5 seconds
                            print(f"[DEBOUNCE] Sensor {sensor.sensor_id} blocked: {distance_change:.2f}cm change, waiting {self.debounce_time - time_since_last_trigger:.2f}s more")
                except Exception as e:
                    print(f"❌ Error in sensor {sensor.sensor_id} measurement: {e}")
                    traceback.print_exc()

                time.sleep(0.05)  # Reduced from 0.1s to 0.05s for faster detection (20Hz polling)

        except Exception as e:
            print(f"💥 FATAL ERROR in sensor {sensor.sensor_id} thread: {e}")
            traceback.print_exc()
            sys.stdout.flush()
        finally:
            print(f"🛑 Stopped monitoring thread for sensor {sensor.sensor_id} (loop_count={loop_count}, self.running={self.running})")

    def start_monitoring(self):
        print("Starting sensor monitoring...")
        self.running = True
        self.threads = []

        for sensor in self.sensors:
            # Remove daemon=True to prevent premature thread termination
            thread = Thread(target=self.monitor_sensor, args=(sensor,))
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