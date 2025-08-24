# This cell overwrites the game with improved, more responsive controls:
# - Single unified event loop (no double event polling)
# - Edge-triggered inputs (jump_pressed, jump_released)
# - Jump buffer + coyote time for forgiving jumps
# - Variable jump height (early release cuts jump)
# - Ground movement smoothing + stronger air control
# - Pause/resume fixed; restart reliable
# - Minor tweaks to difficulty and collisions

import pathlib

code = r'''#!/usr/bin/env python3
# Neon Dash (v2) — tighter controls, buffered jumps, single event loop
'''
import math, random, sys, time
import pygame

pygame.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
FPS = 120

# Colors
BLACK = (10, 10, 18)
WHITE = (240, 240, 255)
NEON_PINK = (255, 70, 165)
NEON_CYAN = (40, 245, 240)
NEON_PURPLE = (168, 85, 247)
NEON_YELLOW = (255, 234, 94)
NEON_GREEN = (50, 255, 170)
GRAY = (60, 60, 80)

pygame.init()
try:
    pygame.mixer.init()
    SOUND_ON = True
except Exception:
    SOUND_ON = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neon Dash — GenZ Runner (v2)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 22)
big_font = pygame.font.SysFont("Verdana", 48, bold=True)
tiny_font = pygame.font.SysFont("Verdana", 16)

def play_beep(freq=440, dur=80, vol=0.25):
    if not SOUND_ON: return
    sample_rate = 22050
    n_samples = int(dur * sample_rate / 1000)
    buf = bytearray()
    phase = 0.0
    inc = 2*math.pi*freq/sample_rate
    for _ in range(n_samples):
        s = int(127 * math.sin(phase))
        phase += inc
        buf += (s + 128).to_bytes(1, 'little', signed=False)
    snd = pygame.mixer.Sound(buffer=bytes(buf))
    snd.set_volume(vol)
    snd.play()

class Particle:
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = life
        self.max_life = life
        self.color = color
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 40 * dt
        self.life -= dt
    def draw(self, s):
        if self.life <= 0: return
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        surf = pygame.Surface((4,4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (2,2), 2)
        s.blit(surf, (self.x, self.y))

class Star:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.z = random.uniform(0.3, 1.0)
        self.tw = random.uniform(0.0, 1.0)
    def update(self, speed, dt):
        self.x -= speed * self.z * dt
        if self.x < -2:
            self.x = WIDTH + random.uniform(0, WIDTH*0.2)
            self.y = random.uniform(0, HEIGHT)
            self.z = random.uniform(0.3, 1.0)
            self.tw = random.uniform(0.0, 1.0)
        self.tw += dt
    def draw(self, s):
        size = int(self.z*2)+1
        glow = int(150 + 105*abs(math.sin(self.tw*3)))
        pygame.draw.circle(s, (glow, glow, 255), (int(self.x), int(self.y)), size)

def draw_ground(s, t, ground_y):
    for i in range(0, WIDTH, 24):
        yy = ground_y + int(math.sin((i*0.05) + t*4)*2)
        pygame.draw.line(s, GRAY, (i, yy), (i+12, yy))
    pygame.draw.line(s, WHITE, (0, ground_y), (WIDTH, ground_y), 2)

def aabb_circle_collision(rect, cx, cy, cr):
    rx, ry, rw, rh = rect
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dx = cx - closest_x
    dy = cy - closest_y
    return dx*dx + dy*dy <= cr*cr

def screen_shake(intensity):
    return (random.randint(-intensity, intensity),
            random.randint(-intensity, intensity))

class Input:
    def __init__(self):
        self.reset()
    def reset(self):
        self.left = self.right = self.down = False
        self.jump = False
        self.jump_pressed = False
        self.jump_released = False
        self.pause_pressed = False
        self.restart_pressed = False
        self.quit_pressed = False
    def poll(self):
        # Reset edge flags each frame
        self.jump_pressed = False
        self.jump_released = False
        self.pause_pressed = False
        self.restart_pressed = False
        self.quit_pressed = False

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit_pressed = True
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_a, pygame.K_LEFT): self.left = True
                if e.key in (pygame.K_d, pygame.K_RIGHT): self.right = True
                if e.key in (pygame.K_s, pygame.K_DOWN): self.down = True
                if e.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if not self.jump:
                        self.jump_pressed = True
                    self.jump = True
                if e.key == pygame.K_p: self.pause_pressed = True
                if e.key == pygame.K_r: self.restart_pressed = True
                if e.key == pygame.K_ESCAPE: self.quit_pressed = True
            elif e.type == pygame.KEYUP:
                if e.key in (pygame.K_a, pygame.K_LEFT): self.left = False
                if e.key in (pygame.K_d, pygame.K_RIGHT): self.right = False
                if e.key in (pygame.K_s, pygame.K_DOWN): self.down = False
                if e.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if self.jump:
                        self.jump_released = True
                    self.jump = False

class Player:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x = WIDTH * 0.2
        self.y = HEIGHT * 0.7
        self.vx = 0.0
        self.vy = 0.0
        self.r = 16
        self.on_ground = False
        self.coyote = 0.0          # time after falling where jump is allowed
        self.jump_buffer = 0.0     # time before landing where jump is queued
        self.hover = 0.0
        self.shield = 0.0
        self.slowmo = 0.0
        self.combo_time = 0.0
        self.combo = 0
        self.alive = True
    def update(self, inp: Input, dt, ground_y):
        accel_ground = 1400
        accel_air = 900
        max_speed_x = 260
        friction_ground = 0.86
        friction_air = 0.98
        jump_v = -420
        gravity = 1200
        max_fall = 950
        hover_grav = 300

        # Slow-mo halves dt for the player only (world still moves — feels powerful)
        local_dt = dt * (0.5 if self.slowmo > 0 else 1.0)

        # Timers
        self.coyote = max(0.0, self.coyote - local_dt)
        self.jump_buffer = max(0.0, self.jump_buffer - local_dt)
        self.hover = max(0.0, self.hover - local_dt)
        self.slowmo = max(0.0, self.slowmo - local_dt)
        self.shield = max(0.0, self.shield - local_dt) if self.shield>0 else 0.0

        # Queue jump on press
        if inp.jump_pressed:
            self.jump_buffer = 0.12

        # Horizontal
        ax = 0.0
        if inp.left: ax -= (accel_air if not self.on_ground else accel_ground)
        if inp.right: ax += (accel_air if not self.on_ground else accel_ground)
        self.vx += ax * local_dt
        # Clamp & friction
        self.vx = max(-max_speed_x, min(max_speed_x, self.vx))
        self.vx *= (friction_ground if self.on_ground else friction_air)

        # Jump if buffered and allowed (ground or coyote)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote > 0.0):
            self.vy = jump_v
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buffer = 0.0
            self.hover = 0.18
            play_beep(620, 70, 0.25)

        # Variable jump height: early release trims upward velocity
        if inp.jump_released and self.vy < -140:
            self.vy = -140

        # Hover (hold jump briefly after the jump)
        if inp.jump and not self.on_ground and self.hover > 0:
            self.vy += (hover_grav - gravity) * local_dt

        # Fast fall
        if inp.down and not self.on_ground:
            self.vy += gravity * local_dt * 0.8

        # Gravity
        self.vy += gravity * local_dt
        if self.vy > max_fall: self.vy = max_fall

        # Integrate
        self.x += self.vx * local_dt
        self.y += self.vy * local_dt

        # Ground collision
        if self.y + self.r >= ground_y:
            if not self.on_ground and self.vy > 200:
                play_beep(220, 40, 0.15)
            self.y = ground_y - self.r
            self.vy = 0.0
            self.on_ground = True
            self.coyote = 0.12
        else:
            # left the ground
            if self.on_ground and self.vy > 0:
                self.coyote = 0.12
            self.on_ground = False

        # Combo timer
        self.combo_time = max(0.0, self.combo_time - dt)
        if self.combo_time <= 0 and self.combo > 0:
            self.combo = 0
    def draw(self, s):
        glow = pygame.Surface((self.r*6, self.r*6), pygame.SRCALPHA)
        col = NEON_CYAN if self.shield>0 else NEON_PINK
        pygame.draw.circle(glow, (*col, 40), (self.r*3, self.r*3), self.r*3)
        s.blit(glow, (self.x - self.r*3, self.y - self.r*3))
        pygame.draw.circle(s, col, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(s, WHITE, (int(self.x), int(self.y)), self.r, 2)

class Obstacle:
    def __init__(self, kind, x, y, w, h, speed):
        self.kind = kind
        self.x, self.y, self.w, self.h = x, y, w, h
        self.base_y = y
        self.speed = speed
        self.phase = random.random()*6.28
        self.alive = True
    def update(self, dt, difficulty):
        self.x -= self.speed * dt
        if self.kind == "laser":
            self.y = self.base_y + math.sin(self.phase + pygame.time.get_ticks()*0.002)*30
        elif self.kind == "spikeball":
            self.y = self.base_y + math.sin(self.phase + pygame.time.get_ticks()*0.004)*50
        if self.x + self.w < -120:
            self.alive = False
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)
    def draw(self, s):
        if self.kind == "block":
            pygame.draw.rect(s, NEON_PURPLE, self.rect(), border_radius=8)
            pygame.draw.rect(s, WHITE, self.rect(), 2, border_radius=8)
        elif self.kind == "laser":
            r = self.rect()
            pygame.draw.rect(s, NEON_PINK, r, border_radius=6)
            pygame.draw.rect(s, WHITE, r, 2, border_radius=6)
        elif self.kind == "spikeball":
            r = self.rect()
            cx, cy = r.center
            pygame.draw.circle(s, NEON_YELLOW, (cx, cy), r.width//2)
            for i in range(12):
                ang = i*math.pi/6 + (pygame.time.get_ticks()*0.01)%6.28
                px = int(cx + math.cos(ang)*(r.width//2 + 8))
                py = int(cy + math.sin(ang)*(r.width//2 + 8))
                pygame.draw.circle(s, NEON_YELLOW, (px, py), 3)
            pygame.draw.circle(s, WHITE, (cx, cy), r.width//2, 2)

class Pickup:
    def __init__(self, kind, x, y, speed):
        self.kind = kind
        self.x, self.y = x, y
        self.speed = speed
        self.r = 10
        self.alive = True
        self.phase = random.random()*6.28
    def update(self, dt):
        self.x -= self.speed * dt
        self.y += math.sin(self.phase + pygame.time.get_ticks()*0.003) * 0.2
        if self.x < -50: self.alive = False
    def rect(self):
        return pygame.Rect(self.x-self.r, self.y-self.r, self.r*2, self.r*2)
    def draw(self, s):
        col = NEON_GREEN if self.kind=="shield" else (NEON_CYAN if self.kind=="slow" else NEON_YELLOW)
        pygame.draw.circle(s, col, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(s, WHITE, (int(self.x), int(self.y)), self.r, 2)

def main():
    stars = [Star() for _ in range(120)]
    player = Player()
    particles = []
    obstacles = []
    pickups = []

    t0 = time.time()
    score = 0.0
    best = 0.0
    speed = 240.0
    ground_y = int(HEIGHT * 0.8)
    spawn_timer = 0.0
    pickup_timer = 2.0
    shake = 0.0
    paused = False
    game_over = False
    inp = Input()

    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 1/45.0)

        # ------- Input -------
        inp.poll()
        if inp.quit_pressed:
            pygame.quit(); sys.exit()

        if not game_over and inp.pause_pressed:
            paused = not paused

        if game_over and inp.restart_pressed:
            # reset
            player = Player()
            particles.clear()
            obstacles.clear()
            pickups.clear()
            t0 = time.time()
            score = 0.0
            speed = 240.0
            spawn_timer = 0.0
            pickup_timer = 2.0
            shake = 0.0
            paused = False
            game_over = False

        # ------- Update -------
        # Background always animates
        for st in stars:
            st.update(speed*0.12, dt)

        if not paused and not game_over:
            elapsed = time.time() - t0
            difficulty = 1.0 + min(2.5, elapsed / 45.0)
            speed += dt * (10.0 + difficulty*6.0)
            score += dt * (10.0 * difficulty) * (1 + 0.1*player.combo)
            spawn_rate = 1.15 / difficulty
            spawn_timer -= dt
            pickup_timer -= dt

            # Spawn obstacles
            if spawn_timer <= 0:
                spawn_timer = random.uniform(max(0.32, 0.9*spawn_rate), 1.05*spawn_rate)
                pattern = random.choice(["block", "laser", "spike", "stack", "mix"] if difficulty>1.2 else ["block", "laser"])
                base_x = WIDTH + 30
                if pattern == "block":
                    h = random.randint(16, 60)
                    obstacles.append(Obstacle("block", base_x, ground_y - h, random.randint(24, 48), h, speed))
                elif pattern == "laser":
                    h = random.randint(12, 20)
                    y = random.randint(int(HEIGHT*0.45), ground_y-60)
                    obstacles.append(Obstacle("laser", base_x, y, random.randint(80, 140), h, speed*1.1))
                elif pattern == "spike":
                    sz = random.randint(22, 34)
                    y = random.randint(int(HEIGHT*0.45), ground_y-40)
                    obstacles.append(Obstacle("spikeball", base_x, y, sz, sz, speed*1.05))
                elif pattern == "stack":
                    step = random.randint(18, 28)
                    for i in range(random.randint(2,4)):
                        h = step*(i+1)
                        obstacles.append(Obstacle("block", base_x + i*48, ground_y - h, 36, h, speed))
                else:
                    h = random.randint(16, 48)
                    obstacles.append(Obstacle("block", base_x, ground_y - h, random.randint(24, 48), h, speed))
                    sz = random.randint(20, 28)
                    obstacles.append(Obstacle("spikeball", base_x+120, random.randint(int(HEIGHT*0.45), ground_y-60), sz, sz, speed*1.05))

            if pickup_timer <= 0:
                pickup_timer = random.uniform(3.0/difficulty, 6.0/difficulty)
                kind = random.choices(["shield","slow","score"], weights=[1.2, 1.0, 1.4])[0]
                y = random.randint(int(HEIGHT*0.35), ground_y-80)
                pickups.append(Pickup(kind, WIDTH+20, y, speed*0.9))

            # Entities
            player.update(inp, dt, ground_y)
            for ob in obstacles: ob.update(dt, difficulty)
            for pk in pickups: pk.update(dt)

            obstacles = [o for o in obstacles if o.alive]
            pickups = [p for p in pickups if p.alive]

            # Collisions
            pre_combo = player.combo
            near_miss = False
            for ob in obstacles:
                if aabb_circle_collision(ob.rect(), player.x, player.y, player.r):
                    if player.shield > 0:
                        player.shield = 0.0
                        shake = 10
                        play_beep(180, 60, 0.25)
                        for _ in range(30):
                            particles.append(Particle(player.x, player.y, random.uniform(-120,120), random.uniform(-160, -40), random.uniform(0.2,0.6), NEON_CYAN))
                        ob.alive = False
                    else:
                        game_over = True
                        best = max(best, score)
                        play_beep(120, 150, 0.35)
                        break
                else:
                    r = ob.rect()
                    dx = max(r.left - player.x, 0, player.x - r.right)
                    dy = max(r.top - player.y, 0, player.y - r.bottom)
                    dist = math.hypot(dx, dy)
                    if dist < player.r + 12:
                        near_miss = True
            if near_miss:
                player.combo = min(20, player.combo + 1 if player.combo_time>0 else 1)
                player.combo_time = 1.2
                if player.combo != pre_combo:
                    play_beep(840, 40, 0.18)

            for pk in pickups:
                if aabb_circle_collision(pk.rect(), player.x, player.y, player.r):
                    pk.alive = False
                    if pk.kind == "shield":
                        player.shield = 6.0
                        play_beep(500, 80, 0.25)
                    elif pk.kind == "slow":
                        player.slowmo = 2.1
                        play_beep(300, 80, 0.25)
                    else:
                        score += 80 + 10*player.combo
                        play_beep(760, 60, 0.25)
                        for _ in range(12):
                            particles.append(Particle(pk.x, pk.y, random.uniform(-80,80), random.uniform(-120,-10), random.uniform(0.2,0.5), NEON_YELLOW))

            for pr in particles: pr.update(dt)
            particles[:] = [p for p in particles if p.life>0]
            shake = max(0.0, shake - dt*20)

        # ------- Draw -------
        base = pygame.Surface((WIDTH, HEIGHT))
        base.fill(BLACK)
        for i in range(0, WIDTH, 40):
            pygame.draw.line(base, (30, 30, 60), (i, 0), (i, HEIGHT))
        for j in range(0, HEIGHT, 40):
            pygame.draw.line(base, (30, 30, 60), (0, j), (WIDTH, j))

        for st in stars: st.draw(base)
        draw_ground(base, pygame.time.get_ticks()/1000.0, ground_y)
        for ob in obstacles: ob.draw(base)
        for pk in pickups: pk.draw(base)
        for pr in particles: pr.draw(base)
        player.draw(base)

        info = [f"Score {int(score)}", f"Best {int(best)}"]
        if player.combo>0: info.append(f"STREAK x{player.combo}")
        if player.shield>0: info.append("Shield")
        if player.slowmo>0: info.append("SLOW")
        x, y = 12, 10
        for t in info:
            surf = font.render(t, True, WHITE); base.blit(surf, (x, y)); y += surf.get_height()+2

        if paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,160))
            base.blit(overlay, (0,0))
            txt = big_font.render("Paused — P to resume", True, WHITE)
            base.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - txt.get_height()//2))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180))
            base.blit(overlay, (0,0))
            txt = big_font.render("Game Over", True, WHITE)
            base.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 90))
            sc = font.render(f"Score: {int(score)}   Best: {int(best)}", True, WHITE)
            base.blit(sc, (WIDTH//2 - sc.get_width()//2, HEIGHT//2 - 30))
            hint = font.render("Press R to restart, ESC to quit", True, WHITE)
            base.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 20))

        if player.slowmo>0:
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); tint.fill((40, 255, 240, 30)); base.blit(tint, (0,0))
        if player.shield>0:
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); tint.fill((40, 255, 170, 25)); base.blit(tint, (0,0))

        if shake>0:
            ox, oy = screen_shake(int(shake))
        else:
            ox, oy = 0, 0
        screen.blit(base, (ox, oy))

        if (time.time() - t0) < 6 and not game_over:
            hint = tiny_font.render("SPACE to jump (buffered) • Hold to hover • S/DOWN fast-fall • A/D move • P pause", True, WHITE)
            screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT-28))

        pygame.display.flip()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        print("If pygame isn't installed, run: pip install pygame")
'''
path = pathlib.Path("/mnt/data/neon_dash.py")
path.write_text(code, encoding="utf-8")
print("Updated:", str(path))
'''