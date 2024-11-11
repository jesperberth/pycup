import pygame
import sys
import time
import sqlite3
from datetime import datetime
from sensor_integration import start_sensor_system
import threading

sensor_system = None
sensor_monitor_thread = None
is_running = True
game_lock = threading.Lock()

# Initialize Pygame
pygame.init()

# Set up the display to use full screen
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
width, height = screen.get_size()
pygame.display.set_caption("Interactive Beer Pong")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
DARK_RED = (139, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# Cup data structure
cups = [{"pos": (0, 0), "color": WHITE, "radius": 0, "hit_time": 0, "hits": 0, "cooldown": 0} for _ in range(10)]

# Game variables
player_name = ""
score = 0
game_state = "start_screen"  # Changed initial state to start_screen
start_time = 0
game_duration = 10  # seconds

# Button rectangles
start_button_rect = pygame.Rect(width // 2 - 100, height * 3 // 4, 200, 50)
name_submit_rect = pygame.Rect(width // 2 - 100, height * 2 // 3, 200, 50)
continue_button_rect = pygame.Rect(width // 2 - 100, height * 2 // 3, 200, 50)

# Database setup
def setup_database():
    conn = sqlite3.connect('beer_pong_scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS high_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_score(player_name, score):
    conn = sqlite3.connect('beer_pong_scores.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO high_scores (player_name, score) VALUES (?, ?)', (player_name, score))
    conn.commit()
    conn.close()

def get_high_scores(limit=10):
    conn = sqlite3.connect('beer_pong_scores.db')
    cursor = conn.cursor()
    cursor.execute('SELECT player_name, score, date_time FROM high_scores ORDER BY score DESC LIMIT ?', (limit,))
    scores = cursor.fetchall()
    conn.close()
    return scores

# Initialize database
setup_database()

def monitor_sensors():
    """Dedicated thread for monitoring sensor status"""
    global is_running
    while is_running:
        if sensor_system and sensor_system.is_running():
            # Print status every 5 seconds
            current_time = int(time.time())
            if current_time % 5 == 0:
                print(f"Sensor system active at {current_time}")
        time.sleep(0.1)

def sensor_hit_cup(cup_number):
    """Wrapper function to handle sensor triggers"""
    global game_state
    with game_lock:
        print(f"Sensor triggered cup {cup_number}")
        if game_state == "playing":
            print(f"Calling hit_cup({cup_number})")
            hit_cup(cup_number)
        else:
            print(f"Game not in playing state (current state: {game_state})")

def sensor_triggered(cup_number):
    hit_cup(cup_number)
    print("Cup")
    print(cup_number)

def initialize_sensors():
    """Initialize the sensor system when the game starts"""
    global sensor_system, sensor_monitor_thread
    try:
        sensor_system = start_sensor_system()
        sensor_system.set_hit_callback(lambda cup_number: hit_cup(cup_number))
        print("Sensor system initialized successfully")
        
        # Start the monitoring thread
        sensor_monitor_thread = threading.Thread(target=monitor_sensors, daemon=True)
        sensor_monitor_thread.start()
        print("Sensor monitoring thread started")
        
    except Exception as e:
        print(f"Failed to initialize sensors: {e}")
        sensor_system = None

def cleanup_sensors():
    """Clean up the sensor system when the game exits"""
    global sensor_system, is_running
    is_running = False
    if sensor_system:
        sensor_system.stop_monitoring()
        print("Sensor system stopped")

def draw_cup(surface, x, y, radius, inner_color):
    pygame.draw.circle(surface, RED, (x, y), radius)
    pygame.draw.circle(surface, inner_color, (x, y), radius - 4)
    pygame.draw.circle(surface, DARK_RED, (x, y), radius, 2)
    pygame.draw.circle(surface, DARK_RED, (x, y), radius - 8, 1)

def setup_cup_formation(start_x, start_y, cup_radius, spacing):
    cup_index = 0
    rows = 4
    for row in range(rows):
        for col in range(rows - row):
            x = start_x + col * (cup_radius * 2 + spacing) - (rows - row - 1) * (cup_radius + spacing / 2)
            y = start_y + row * (cup_radius * 2 + spacing) * 0.866
            cups[cup_index]["pos"] = (int(x), int(y))
            cups[cup_index]["radius"] = cup_radius
            cup_index += 1

def draw_cup_formation(surface):
    current_time = time.time()
    for cup in cups:
        if current_time - cup["cooldown"] < 1:
            inner_color = RED
        elif cup["hits"] == 2 and current_time - cup["hit_time"] < 2:
            inner_color = BLUE
        elif cup["hits"] == 1 and current_time - cup["hit_time"] < 3:
            inner_color = GREEN
        else:
            cup["color"] = WHITE
            cup["hits"] = 0
            inner_color = WHITE
        draw_cup(surface, cup["pos"][0], cup["pos"][1], cup["radius"], inner_color)

def draw_text(surface, text, font, color, x, y, center=True):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)

def draw_high_scores(surface):
    font = pygame.font.Font(None, 36)
    draw_text(surface, "High Scores", font, BLACK, width * 5 // 6, height // 6)

    high_scores = get_high_scores()
    for i, (name, score, date) in enumerate(high_scores):
        date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        date_str = date_obj.strftime('%m/%d/%Y')
        score_text = f"{name}: {score} ({date_str})"
        draw_text(surface, score_text, font, BLACK, width * 5 // 6, height // 6 + (i + 1) * 40)

def handle_events():
    global player_name, game_state, score, start_time
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            return False
        elif game_state == "start_screen":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button_rect.collidepoint(event.pos):
                    game_state = "input_name"
                    player_name = ""  # Reset player name when entering name input screen
        elif game_state == "input_name":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif event.key != pygame.K_RETURN:  # Allow typing except Enter key
                    player_name += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if name_submit_rect.collidepoint(event.pos) and player_name.strip():
                    game_state = "countdown"
                    start_time = time.time()
        elif game_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_cup_click(event.pos)
        elif game_state == "game_over":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if continue_button_rect.collidepoint(event.pos):
                    game_state = "start_screen"
    return True

def hit_cup(cup_number):
    """Hit a specific cup by its number (0-9)"""
    global score
    if not 0 <= cup_number < len(cups):
        print(f"Invalid cup number: {cup_number}")
        return

    cup = cups[cup_number]
    current_time = time.time()
    print(f"Processing hit on cup {cup_number}")

    if current_time - cup["cooldown"] >= 1:  # Check if cup is not in cooldown
        if cup["hits"] == 2 and current_time - cup["hit_time"] < 2:
            score += 5
            cup["cooldown"] = current_time
            print(f"Cup {cup_number}: Third hit! +5 points")
        elif cup["hits"] == 1 and current_time - cup["hit_time"] < 3:
            cup["hits"] = 2
            score += 3
            print(f"Cup {cup_number}: Second hit! +3 points")
        else:
            cup["hits"] = 1
            score += 1
            print(f"Cup {cup_number}: First hit! +1 point")
        cup["hit_time"] = current_time
    else:
        print(f"Cup {cup_number} is in cooldown")

def handle_cup_click(pos):
    """
    Modified to handle mouse clicks by finding the closest cup and calling hit_cup()
    """
    for i, cup in enumerate(cups):
        if pygame.math.Vector2(cup["pos"]).distance_to(pos) < cup["radius"]:
            hit_cup(i)
            break

def main():
    global game_state, start_time, score, sensor_system, is_running

    initialize_sensors()

    clock = pygame.time.Clock()

    # Calculate cup size and spacing based on screen size
    cup_radius = min(width, height) // 25
    spacing = cup_radius // 2

    # Calculate starting position to center the formation in the left 2/3 of the screen
    start_x = width // 3
    start_y = height // 2 - (3 * (cup_radius * 2 + spacing) * 0.866) // 2

    # Set up the initial cup formation
    setup_cup_formation(start_x, start_y, cup_radius, spacing)

    # Fonts
    font = pygame.font.Font(None, 36)
    medium_font = pygame.font.Font(None, 128)
    large_font = pygame.font.Font(None, 256)

    # Images
    background_image = pygame.image.load("images/ArrowTechHubTransparentLightMode.png")
    background_image = pygame.transform.scale(background_image, (1200, 1200))
    image_rect = background_image.get_rect()

    running = True
    while running:
        running = handle_events()
        screen.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Example of how to use hit_cup() with keyboard numbers (for testing)
        keys = pygame.key.get_pressed()
        if game_state == "playing":
            for i in range(10):  # 0-9 keys
                if keys[pygame.K_0 + i]:
                    hit_cup(i)

        if game_state == "start_screen":
            # Draw start screen
            background_x = (screen.get_width() - image_rect.width) // 2
            background_y = (screen.get_height() - image_rect.height) // 2
            screen.blit(background_image, (background_x, background_y))
            draw_text(screen, "Beer Pong", large_font, BLACK, width // 2, 450)
            pygame.draw.rect(screen, RED, start_button_rect)
            draw_text(screen, "Start Game", font, WHITE, start_button_rect.centerx, start_button_rect.centery)
            draw_high_scores(screen)

        elif game_state == "input_name":
            # Draw name input screen
            draw_text(screen, "Enter Your Name", medium_font, BLACK, width // 2, height // 3)
            # Draw name input box
            input_box_rect = pygame.Rect(width // 2 - 200, height // 2 - 25, 400, 50)
            pygame.draw.rect(screen, BLACK, input_box_rect, 2)
            draw_text(screen, player_name, font, BLACK, width // 2, height // 2)
            # Draw start button
            pygame.draw.rect(screen, RED, name_submit_rect)
            draw_text(screen, "Start Game", font, WHITE, name_submit_rect.centerx, name_submit_rect.centery)
            draw_high_scores(screen)

        elif game_state == "countdown":
            countdown = 3 - int(time.time() - start_time)
            if countdown > 0:
                draw_text(screen, str(countdown), large_font, BLACK, width // 2, height // 2)
            else:
                game_state = "playing"
                start_time = time.time()
                score = 0

        elif game_state == "playing":
            draw_cup_formation(screen)
            elapsed_time = int(time.time() - start_time)
            remaining_time = max(0, game_duration - elapsed_time)
            draw_text(screen, f"Player: {player_name} - Points {score}", font, BLACK, 10, 10, False)
            draw_text(screen, f"Time: {remaining_time}", medium_font, BLACK, 10, 100, False)
            draw_high_scores(screen)

            if remaining_time == 0:
                game_state = "game_over"
                save_score(player_name, score)

        elif game_state == "game_over":
            draw_text(screen, "Game Over", large_font, BLACK, width // 2, height // 2 - 50)
            draw_text(screen, f"Your score: {score}", font, BLACK, width // 2, height // 2 + 50)
            # Draw continue button
            pygame.draw.rect(screen, RED, continue_button_rect)
            draw_text(screen, "Continue", font, WHITE, continue_button_rect.centerx, continue_button_rect.centery)
            draw_high_scores(screen)
        time.sleep(0.001)
        pygame.display.flip()
        clock.tick(60)

        if not running:
            # Clean up sensors before exiting
            cleanup_sensors()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")
        cleanup_sensors()
    finally:
        cleanup_sensors()
        pygame.quit()
        sys.exit()