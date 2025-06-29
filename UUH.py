import pygame
import sys
import random
pygame.init()
WIDTH, HEIGHT = 600, 400
win = pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Шутер на Python")

WHITE = (255, 255, 255)
GREEN = (0, 225, 0)
RED = (255, 0, 0)

plaer_width = 40
plaer_height = 20

plaer_x = WIDTH //2 - plaer_width // 2
plaer_y = HEIGHT - plaer_height - 10 
plaer_speed = 5

bullets =[]
bullet_speed = 7
bullet_width = 2
bullet_heigt = 4

enemies = []
enemy_speed = 3
enemy_size = 30

clock = pygame.time.Clock()
FPS = 60


running = True

while running:
    clock.tick(FPS)
    if random.randint(1,60) == 1:
        enemy_x = random.randint(0, WIDTH - enemy_size)
        enemy_y = -enemy_size
        enemies.append({'x': enemy_x, 'y': enemy_y})
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False    
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                bullet_x = plaer_x + plaer_width // 2 - bullet_width//2
                bullet_y = plaer_y 
                bullets.append({'x': bullet_x, 'y': bullet_y})               
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and plaer_x > 0:
        plaer_x -= plaer_speed
    if keys[pygame.K_RIGHT] and plaer_x < WIDTH - plaer_width:
        plaer_x += plaer_speed
    for bullet in bullets:
        bullet['y'] -= bullet_speed
    bullets = [b for b in bullets if b['y'] > 0]
    for enemy in enemies:
        enemy['y'] += enemy_speed
    enemies = [e for e in enemies if e['y'] < HEIGHT]    
    win.fill(WHITE)
    
    pygame.draw.rect(win, GREEN, ( plaer_x, plaer_y, plaer_width, plaer_height))
    
    for enemy in enemies:
        x = enemy['x']
        y = enemy['y']
        pygame.draw.polygon(win, (0, 0, 255), [(x + enemy_size//2,y),(x,y + enemy_size),(x + enemy_size, y + enemy_size)])
    
    for bullet in bullets:
        pygame.draw.rect(win, RED, ( bullet['x'], bullet['y'], bullet_width, bullet_heigt))
    
    pygame.display.update()
    
pygame.quit()
sys.exit()
