# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an interactive beer pong game built with Pygame that integrates physical ultrasonic sensors via GPIO on a Raspberry Pi 5. The game features a full-screen UI with player name input, scoring system, countdown timer, and persistent high scores stored in SQLite.

## Running the Application

**Main game (with sensors):**
```bash
python3 beer_pong_game.py
```

**pycup.py - Enhanced version with sensor integration:**
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
python3 sensor_integration.py
```

**Test sensor system directly:**
```bash
python3 sensor_controller.py
```

## Architecture

### Core Components

**beer_pong_game.py** - Main integrated game with sensor support
- Full Pygame-based UI with game states: start_screen, input_name, countdown, playing, game_over
- Integrates sensor system via `sensor_integration.start_sensor_system()`
- Threading: Main pygame loop + sensor monitoring thread + individual sensor threads
- Scoring: 1 point (first hit, green), 3 points (second hit within 3s, blue), 5 points (third hit within 2s, red + cooldown)
- Game mechanics: 10-second timed rounds, 10 cups in triangular formation

**pycup.py** - Original standalone game
- Same game logic but uses mouse clicks and keyboard (0-9 keys) instead of sensors
- Useful for testing game mechanics without hardware

**sensor_controller.py** - Low-level sensor management
- `SensorSystem` class manages 10 HC-SR04 ultrasonic sensors via gpiod (Raspberry Pi 5)
- Pin mappings defined in `sensor_pins` list (sensors 0-9)
- Calibration: Takes baseline measurements, then monitors for 10% threshold deviations
- Multi-threaded: One thread per sensor for continuous monitoring
- Debounce: 1-second cooldown between triggers
- Callback mechanism: `set_hit_callback()` to register hit handlers

**sensor_integration.py** - Bridge between sensors and game
- `start_sensor_system()` - Initializes, calibrates, and starts monitoring
- Provides clean interface for game to interact with sensors
- Handles sensor system lifecycle (setup, start, stop)

**sensors.py** - Deprecated/alternative sensor implementation
- Similar functionality to sensor_controller.py
- Uses `write_sensor_trigger()` function for logging
- Kept for reference but not actively used by beer_pong_game.py

### Threading Model

1. Main Pygame thread (game loop, rendering, event handling)
2. Sensor monitoring thread (`monitor_sensors()`) - checks system health
3. 10 individual sensor threads (one per ultrasonic sensor in `SensorSystem`)
4. Thread safety: `game_lock` protects shared state, especially during `hit_cup()` calls

### Sensor-Game Integration

- Sensors trigger `hit_cup(cup_number)` via callback when motion detected
- Only processes hits when `game_state == "playing"`
- Cup numbering: 0-9 maps directly to sensor IDs
- GPIO chip: 'gpiod.Chip('4')' for Raspberry Pi 5

### Database

- SQLite database: `beer_pong_scores.db`
- Schema: `high_scores` table with player_name, score, date_time
- Functions: `setup_database()`, `save_score()`, `get_high_scores(limit=10)`

## Hardware Configuration

The project expects 10 HC-SR04 ultrasonic sensors connected to a Raspberry Pi 5 with specific GPIO pin mappings defined in `sensor_controller.py:68-79`. Each sensor requires a trigger pin and echo pin. The system uses the gpiod library (chip '4') for GPIO access.

## Dependencies

- pygame - Game UI and event handling
- gpiod - GPIO control for Raspberry Pi 5
- sqlite3 - Score persistence
- threading - Concurrent sensor monitoring
- statistics - Sensor calibration

## Development Notes

- The game requires the `images/ArrowTechHubTransparentLightMode.png` background image
- Sensors currently only use sensor 0 for testing (see commented sensors in `sensor_controller.py:65-73`)
- When testing without hardware, use `pycup.py` or the keyboard shortcuts (0-9) in `beer_pong_game.py`
- ESC key exits fullscreen mode
- Sensor calibration happens on startup and measures baseline distances for each sensor
