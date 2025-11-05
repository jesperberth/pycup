# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an interactive beer pong game built with Pygame that integrates physical ultrasonic sensors via GPIO on a Raspberry Pi 5. The game features a full-screen UI with player name input, scoring system, countdown timer, and persistent high scores stored in SQLite.

## Running the Application

**Main game with sensor integration:**
```bash
# With sensors (default fullscreen)
python3 pycup.py

# Test mode (mouse/keyboard control)
python3 pycup.py --test

# Windowed mode (half screen)
python3 pycup.py --nofullscreen

# Combined: windowed test mode
python3 pycup.py --test --nofullscreen
```

**Test sensors independently:**
```bash
# Test mode with visual feedback
python3 test_sensor_simple.py

# Standalone sensor integration test
python3 sensor_integration.py
```

## Architecture

### Core Components

**pycup.py** - Main game with sensor integration
- Full Pygame-based UI with game states: start_screen, input_name, countdown, playing, game_over
- Supports both sensor mode (default) and test mode (--test flag for mouse/keyboard)
- Threading: Main pygame loop + 10 individual sensor threads (one per ultrasonic sensor)
- Scoring: 1 point (first hit, green), 3 points (second hit within 3s, blue), 5 points (third hit within 2s, red + cooldown)
- Game mechanics: 30-second timed rounds, 10 cups in triangular formation
- Keyboard shortcuts: 0-9 keys trigger corresponding cups (for testing), ESC exits

**sensor_controller.py** - Low-level sensor management
- `SensorSystem` class manages HC-SR04 ultrasonic sensors via gpiod (Raspberry Pi 5)
- Pin mappings defined in `sensor_pins` list at [sensor_controller.py:63-74](sensor_controller.py#L63-L74)
- Currently only sensor 0 is enabled (sensors 1-9 commented out for testing)
- Calibration: Takes baseline measurements, then monitors for 1cm threshold deviations
- Multi-threaded: One thread per sensor for continuous monitoring (20Hz polling at 0.05s intervals)
- Debounce: 0.5-second cooldown between triggers
- Callback mechanism: `set_hit_callback()` to register hit handlers

**sensor_integration.py** - Bridge between sensors and game
- `start_sensor_system()` - Initializes and calibrates sensors (does NOT start monitoring)
- Returns configured `SensorSystem` instance ready for callback registration
- Monitoring must be started manually with `system.start_monitoring()` after `set_hit_callback()`

**test_sensor_simple.py** - Standalone sensor testing utility
- Real-time distance monitoring with visual feedback
- Shows baseline calibration and trigger detection
- Useful for debugging sensor hardware and detection thresholds

**depricated_sensors.py** - Legacy sensor implementation
- Deprecated implementation kept for reference
- Not used by current codebase

### Threading Model

1. Main Pygame thread (game loop, rendering, event handling)
2. 10 individual sensor threads (one per ultrasonic sensor in `SensorSystem`)
3. Thread safety: `game_lock` protects shared state during `hit_cup()` calls from sensor threads

### Sensor-Game Integration Flow

1. Game initializes `SensorSystem` in [pycup.py:281-295](pycup.py#L281-L295)
2. Calls `setup_sensors()` to configure GPIO pins
3. Calls `calibrate_all_sensors()` to establish baseline distances
4. Registers `hit_cup()` callback via `set_hit_callback()`
5. Calls `start_monitoring()` to begin sensor threads
6. Sensor threads detect distance changes and call `hit_cup(cup_number)`
7. `hit_cup()` only processes hits when `game_state == "playing"` ([pycup.py:189](pycup.py#L189))
8. Cup numbering: 0-9 maps directly to sensor IDs
9. On cleanup, `stop_monitoring()` joins threads and releases GPIO

### Database

- SQLite database: `beer_pong_scores.db`
- Schema: `high_scores` table with columns: id, player_name, score, date_time
- Functions in [pycup.py:54-81](pycup.py#L54-L81): `setup_database()`, `save_score()`, `get_high_scores(limit=10)`

## Hardware Configuration

**GPIO Setup:**
- Raspberry Pi 5 using gpiod chip '4'
- 10 HC-SR04 ultrasonic sensors, each requiring trigger and echo pins
- Pin mappings defined at [sensor_controller.py:63-74](sensor_controller.py#L63-L74)
- Currently only sensor 0 enabled (pins: trigger=23, echo=24)
- Uncomment sensors 1-9 in sensor_pins list to enable additional sensors

**Detection Parameters:**
- Baseline calibration: 10 measurements, median value used
- Detection threshold: 1.0cm distance decrease (object moving closer)
- Polling rate: 20Hz (0.05s interval)
- Debounce: 0.5s cooldown between triggers per sensor

## Dependencies

- `pygame` - Game UI and event handling
- `gpiod` - GPIO control for Raspberry Pi 5
- `sqlite3` - Score persistence (standard library)
- `threading` - Concurrent sensor monitoring (standard library)
- `statistics` - Sensor calibration (standard library)
- `argparse` - Command-line argument parsing (standard library)

## Key Implementation Details

**Sensor Detection Logic:**
- Sensors measure distance continuously and compare to calibrated baseline
- Detection triggers when distance decreases by >1cm (ball/hand enters cup)
- Each sensor thread runs independently with its own debounce timer
- Thread-safe callback execution protected by `game_lock`

**Game Scoring System:**
- First hit within window: +1 point (cup turns green, 3s window opens)
- Second hit within 3s: +3 points (cup turns blue, 2s window opens)
- Third hit within 2s: +5 points (cup turns red, 1s cooldown begins)
- Cooldown prevents rapid re-triggering

**Testing Without Hardware:**
- Use `--test` flag to run without sensors
- Mouse clicks on cups or keyboard 0-9 keys trigger hits
- Mode indicator shows "Test (Mouse/Keyboard)" or "Sensors Active"

**Required Assets:**
- Background image: `images/ArrowTechHubTransparentLightMode.png` (1200x1200)
