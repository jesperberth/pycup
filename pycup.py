import pygame
import sys
import time

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
high_scores = []
game_state = "input_name"  # States: "input_name", "start_screen", "countdown", "playing", "game_over"
start_time = 0
game_duration = 10  # seconds

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
    for i, (name, score) in enumerate(high_scores[:10]):
        draw_text(surface, f"{name}: {score}", font, BLACK, width * 5 // 6, height // 6 + (i + 1) * 40)

def handle_events():
    global player_name, game_state, score, start_time
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            return False
        elif game_state == "input_name":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and player_name:
                    game_state = "start_screen"
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    player_name += event.unicode
        elif game_state == "start_screen":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button_rect.collidepoint(event.pos):
                    game_state = "countdown"
                    start_time = time.time()
        elif game_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_cup_click(event.pos)
    return True

def handle_cup_click(pos):
    global score
    current_time = time.time()
    for cup in cups:
        if pygame.math.Vector2(cup["pos"]).distance_to(pos) < cup["radius"]:
            if current_time - cup["cooldown"] >= 1:
                if cup["hits"] == 2 and current_time - cup["hit_time"] < 2:
                    score += 5
                    cup["cooldown"] = current_time
                elif cup["hits"] == 1 and current_time - cup["hit_time"] < 3:
                    cup["hits"] = 2
                    score += 3
                else:
                    cup["hits"] = 1
                    score += 1
                cup["hit_time"] = current_time

def main():
    global game_state, start_time, score

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

    # Create start button
    global start_button_rect
    start_button_rect = pygame.Rect(width // 2 - 100, height * 3 // 4, 200, 50)

    running = True
    while running:
        running = handle_events()

        screen.fill(WHITE)

        if game_state == "input_name":
            draw_text(screen, "Enter your name:", font, BLACK, width // 2, height // 2 - 50)
            draw_text(screen, player_name, font, BLACK, width // 2, height // 2)
        elif game_state == "start_screen":
            background_x = (screen.get_width() - image_rect.width) // 2   # Center horizontally
            background_y = (screen.get_height() - image_rect.height) // 2  # Center vertically
            #draw_text(screen, "Arrow Tech Hub", large_font, BLACK, width // 2, 150)
            screen.blit(background_image, (background_x, background_y))
            #draw_text(screen, "Presents", medium_font, BLACK, width // 2, 300)
            draw_text(screen, "Beer Pong", large_font, BLACK, width // 2, 450)
            pygame.draw.rect(screen, RED, start_button_rect)
            draw_text(screen, "Start Game", font, WHITE, start_button_rect.centerx, start_button_rect.centery)
        elif game_state == "countdown":
            countdown = 3 - int(time.time() - start_time)
            if countdown > 0:
                draw_text(screen, str(countdown), large_font, BLACK, width // 2, height // 2)
            else:
                game_state = "playing"
                start_time = time.time()
                score = 0
        elif game_state == "playing":
            # Draw cup formation
            draw_cup_formation(screen)

            # Draw player info and timer
            elapsed_time = int(time.time() - start_time)
            remaining_time = max(0, game_duration - elapsed_time)
            draw_text(screen, f"Player: {player_name} - Points {score} - Time: {remaining_time}", font, BLACK, 10, 10, False)

            # Draw high scores
            draw_high_scores(screen)

            if remaining_time == 0:
                game_state = "game_over"
                high_scores.append((player_name, score))
                high_scores.sort(key=lambda x: x[1], reverse=True)
        elif game_state == "game_over":
            draw_text(screen, "Game Over", large_font, BLACK, width // 2, height // 2 - 50)
            draw_text(screen, f"Your score: {score}", font, BLACK, width // 2, height // 2 + 50)
            draw_text(screen, "Click to play again", font, BLACK, width // 2, height // 2 + 100)
            draw_high_scores(screen)
            if pygame.mouse.get_pressed()[0]:
                game_state = "start_screen"

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()