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
        self.consecutive_detections = 0  # Track consecutive readings above threshold
        self.setup_gpio()

    def setup_gpio(self):
        self.trigger_line = self.chip.get_line(self.trigger_pin)
        self.echo_line = self.chip.get_line(self.echo_pin)
        self.trigger_line.request(consumer=f"sensor_{self.sensor_id}_trigger", type=gpiod.LINE_REQ_DIR_OUT)
        self.echo_line.request(consumer=f"sensor_{self.sensor_id}_echo", type=gpiod.LINE_REQ_DIR_IN)

    def measure_distance(self):
        # Send trigger pulse
        self.trigger_line.set_value(1)
        time.sleep(0.00001)
        self.trigger_line.set_value(0)

        # Wait for echo to go high (with proper timeout)
        timeout_start = time.time()
        start_time = time.time()
        while self.echo_line.get_value() == 0:
            if time.time() - timeout_start > 0.1:
                # Timeout - return baseline or safe default
                return self.baseline if self.baseline else 100.0
            start_time = time.time()

        # Wait for echo to go low (with proper timeout)
        stop_time = start_time
        while self.echo_line.get_value() == 1:
            if time.time() - start_time > 0.1:
                # Timeout - return baseline or safe default
                return self.baseline if self.baseline else 100.0
            stop_time = time.time()

        # Calculate distance
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
    def __init__(self, debug=False):
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
        self.debug = debug  # Enable/disable verbose debug output
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

                # Debug: Print at the very start of loop to confirm we're entering
                if self.debug and (loop_count <= 5 or loop_count % 20 == 0):
                    print(f"[LOOP START] Sensor {sensor.sensor_id}: Beginning loop {loop_count}, self.running={self.running}", flush=True)

                # Heartbeat every 100 loops (5 seconds at 0.05s sleep / 20Hz)
                if self.debug and loop_count % 100 == 0:
                    print(f"[HEARTBEAT] Sensor {sensor.sensor_id} thread alive, loop #{loop_count}, self.running={self.running}", flush=True)

                try:
                    if self.debug and (loop_count <= 5 or loop_count % 20 == 0):
                        print(f"[LOOP] Sensor {sensor.sensor_id}: About to call measure_distance(), loop {loop_count}", flush=True)

                    current_distance = sensor.measure_distance()

                    if self.debug and (loop_count <= 5 or loop_count % 20 == 0):
                        print(f"[LOOP] Sensor {sensor.sensor_id}: measure_distance() returned {current_distance:.2f}cm, loop {loop_count}", flush=True)
                    # Use 2.5cm threshold for ping pong ball detection
                    # Ping pong ball is ~4cm diameter, so this reduces false positives
                    # while still reliably detecting a ball entering the cup
                    threshold = 1.5
                    current_time = time.time()

                    # Add distance debugging continuously for debugging
                    if self.debug and sensor.sensor_id == 0:
                        # Print every 20 measurements (once per second at 0.05s sleep / 20Hz)
                        if hasattr(sensor, 'measurement_count'):
                            sensor.measurement_count += 1
                        else:
                            sensor.measurement_count = 0

                        if sensor.measurement_count % 20 == 0:
                            print(f"[SENSOR DEBUG] Sensor 0: {current_distance:.2f}cm (baseline: {sensor.baseline:.2f}cm, change: {sensor.baseline - current_distance:.2f}cm, threshold: {threshold:.2f}cm, loop={loop_count})", flush=True)

                    # Detect when distance gets SMALLER (ball/hand moves closer)
                    distance_change = sensor.baseline - current_distance

                    # Check debounce: has enough time passed since last trigger?
                    time_since_last_trigger = current_time - sensor.last_trigger_time
                    can_trigger = time_since_last_trigger > self.debounce_time

                    # Consecutive detection logic to filter noise
                    REQUIRED_CONSECUTIVE = 1  # Number of consecutive readings required (1=instant, 2=0.1s, 3=0.15s at 20Hz)

                    if distance_change > threshold and can_trigger:
                        # If REQUIRED_CONSECUTIVE is 1, trigger immediately (bypass consecutive logic)
                        if REQUIRED_CONSECUTIVE == 1:
                            with self.lock:
                                print(f"\n🎯 Motion detected on sensor {sensor.sensor_id}!")
                                print(f"   Distance: {current_distance:.2f} cm (baseline: {sensor.baseline:.2f} cm)")
                                print(f"   Change: {distance_change:.2f} cm (threshold: {threshold:.2f} cm)")
                                print(f"   Time since last trigger: {time_since_last_trigger:.2f}s\n", flush=True)

                                if self.hit_callback:
                                    print(f"   ✅ Calling hit callback for sensor {sensor.sensor_id}\n", flush=True)
                                    self.hit_callback(sensor.sensor_id)
                                else:
                                    print("   ⚠️ Warning: No callback function set!\n", flush=True)

                                sensor.last_trigger_time = current_time
                        else:
                            # Use consecutive detection filtering
                            sensor.consecutive_detections += 1

                            # Debug logging for consecutive detections
                            if sensor.sensor_id == 0 and sensor.consecutive_detections > 0:
                                print(f"[CONSECUTIVE] Sensor 0: detection {sensor.consecutive_detections}/{REQUIRED_CONSECUTIVE}, change={distance_change:.2f}cm", flush=True)

                            # Only trigger callback after required consecutive detections
                            if sensor.consecutive_detections >= REQUIRED_CONSECUTIVE:
                                with self.lock:
                                    print(f"\n🎯 Motion detected on sensor {sensor.sensor_id}!")
                                    print(f"   Distance: {current_distance:.2f} cm (baseline: {sensor.baseline:.2f} cm)")
                                    print(f"   Change: {distance_change:.2f} cm (threshold: {threshold:.2f} cm)")
                                    print(f"   Consecutive detections: {sensor.consecutive_detections}")
                                    print(f"   Time since last trigger: {time_since_last_trigger:.2f}s\n", flush=True)

                                    if self.hit_callback:
                                        print(f"   ✅ Calling hit callback for sensor {sensor.sensor_id}\n", flush=True)
                                        self.hit_callback(sensor.sensor_id)
                                    else:
                                        print("   ⚠️ Warning: No callback function set!\n", flush=True)

                                    # Reset for next detection
                                    sensor.last_trigger_time = current_time
                                    sensor.consecutive_detections = 0
                    elif distance_change > threshold and not can_trigger:
                        # In debounce period - reset consecutive counter (only if using consecutive logic)
                        if REQUIRED_CONSECUTIVE > 1:
                            sensor.consecutive_detections = 0
                    else:
                        # Distance change below threshold - reset consecutive counter (only if using consecutive logic)
                        if REQUIRED_CONSECUTIVE > 1:
                            if sensor.consecutive_detections > 0 and sensor.sensor_id == 0:
                                print(f"[CONSECUTIVE RESET] Sensor 0: was at {sensor.consecutive_detections}, resetting (change={distance_change:.2f}cm < {threshold}cm)", flush=True)
                            sensor.consecutive_detections = 0
                except Exception as e:
                    print(f"❌ Error in sensor {sensor.sensor_id} measurement: {e}", flush=True)
                    traceback.print_exc()

                # Add debug to confirm we reach end of loop
                if self.debug and sensor.sensor_id == 0 and loop_count % 20 == 0:
                    print(f"[LOOP END] Sensor 0: Completed loop {loop_count}, sleeping 0.05s...", flush=True)

                time.sleep(0.05)  # 20Hz polling - fast enough to catch falling ping pong balls

        except Exception as e:
            print(f"💥 FATAL ERROR in sensor {sensor.sensor_id} thread: {e}", flush=True)
            traceback.print_exc()
            sys.stdout.flush()
        finally:
            print(f"🛑 Stopped monitoring thread for sensor {sensor.sensor_id} (loop_count={loop_count}, self.running={self.running})", flush=True)

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