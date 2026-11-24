import pygame, math, random, sys, struct

WORLD_MAP = [
    "1111111111111111",
    "1000000000000001",
    "1022000000002201",
    "1020000110000201",
    "1000000110000001",
    "1000220000220001",
    "1000200000020001",
    "1000000110000001",
    "1022000000002201",
    "1111111111111111",
]
MAP_H, MAP_W = len(WORLD_MAP), len(WORLD_MAP[0])
FOV, HALF_FOV, NUM_RAYS, MAX_DEPTH = math.pi / 3, math.pi / 6, 180, 22

WEAPONS = [
    {"name": "PULSE RIFLE", "dmg": 35, "cd": 12, "col": (80, 245, 255), "spark": (255, 215, 90), "body": (48, 58, 76)},
    {"name": "CYBER SMG", "dmg": 18, "cd": 6, "col": (255, 95, 220), "spark": (255, 165, 75), "body": (54, 46, 72)},
    {"name": "HEAVY PLASMA", "dmg": 80, "cd": 24, "col": (90, 255, 150), "spark": (150, 255, 220), "body": (42, 72, 80)},
]

class SoundEngine:
    def __init__(self):
        self.enabled, self.volume, self.sounds = True, 0.8, {}
        try:
            mix = pygame.mixer.get_init()
            if mix:
                self.rate, _, self.chans = mix
                for k in ["shoot0", "shoot1", "shoot2", "kill", "hurt", "click"]:
                    self.sounds[k] = self._make_sfx(k)
                self.sounds["attack"] = self._make_voice([(150, 0.11), (195, 0.14), (135, 0.16)])
                self.sounds["pain"] = self._make_voice([(260, 0.12), (170, 0.18)])
                self.sounds["laugh"] = self._make_voice([(180, 0.09), (160, 0.09), (140, 0.12)])
        except Exception:
            self.enabled = False

    def _build_wave(self, samples):
        buf = bytearray()
        for v in samples:
            buf += struct.pack('<h', int(max(-1.0, min(1.0, v)) * 30000)) * self.chans
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _make_sfx(self, kind):
        durs = {"click": 0.05, "shoot0": 0.14, "shoot1": 0.08, "shoot2": 0.24, "kill": 0.28}
        dur = durs.get(kind, 0.15)
        n, out = int(self.rate * dur), []
        for i in range(n):
            env = (1.0 - i / n) ** 1.5
            if kind == "click": v = math.sin(i * 0.35) * env * 0.5
            elif kind == "shoot0": v = (random.uniform(-1, 1) * 0.75 + math.sin(i * 0.12) * 0.45) * env
            elif kind == "shoot1": v = (random.uniform(-1, 1) * 0.85 + math.sin(i * 0.18) * 0.35) * env
            elif kind == "shoot2": v = (math.sin(i * (0.20 - i * 0.00002)) * 0.8 + random.uniform(-0.3, 0.3)) * env
            elif kind == "kill": v = (random.uniform(-1, 1) * 0.6 + math.sin(i * 0.03) * 0.6) * env
            else: v = (math.sin(i * 0.025) * 0.8 + random.uniform(-0.25, 0.25)) * env
            out.append(v)
        return self._build_wave(out)

    def _make_voice(self, syllables):
        out = []
        for freq, dur in syllables:
            n = int(self.rate * dur)
            for i in range(n):
                t = i / self.rate
                env = math.sin(math.pi * (i / n))
                c = math.sin(2 * math.pi * freq * t)
                f = math.sin(2 * math.pi * (freq * 2.3) * t) * 0.45
                r = 1.0 if math.sin(2 * math.pi * 55 * t) > 0 else 0.5
                out.append((c + f) * r * env * 0.85)
            out.extend([0.0] * int(self.rate * 0.03))
        return self._build_wave(out)

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].set_volume(self.volume)
                self.sounds[name].play()
            except Exception:
                pass
class Button:
    def __init__(self, x, y, w, h, text, font, bg=(24, 32, 48), bd=(90, 225, 255), alpha=215, round_btn=False):
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.text, self.font, self.bg, self.bd, self.alpha, self.round_btn = text, font, bg, bd, alpha, round_btn

    def draw(self, surf):
        w, h = self.rect.w, self.rect.h
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        if self.round_btn:
            r = min(w, h) // 2
            pygame.draw.circle(s, (*self.bg, self.alpha), (r, r), r)
            pygame.draw.circle(s, (*self.bd, 90), (r, r), max(4, r - 8), 3)
            pygame.draw.circle(s, (*self.bd, 245), (r, r), r - 1, 3)
        else:
            cut = min(16, w // 5, h // 3)
            pts = [(cut, 0), (w - cut, 0), (w, cut), (w, h - cut), (w - cut, h), (cut, h), (0, h - cut), (0, cut)]
            pygame.draw.polygon(s, (*self.bg, self.alpha), pts)
            top_pts = [(cut, 0), (w - cut, 0), (w - 2, cut), (2, cut)]
            pygame.draw.polygon(s, (255, 255, 255, 28), top_pts)
            pygame.draw.polygon(s, (*self.bd, 240), pts, 2)
            pygame.draw.line(s, (*self.bd, 255), (cut, 3), (cut + 14, 3), 3)
            pygame.draw.line(s, (*self.bd, 255), (w - cut - 14, h - 4), (w - cut, h - 4), 3)
        surf.blit(s, self.rect.topleft)
        if self.text:
            t = self.font.render(self.text, True, (245, 252, 255))
            surf.blit(t, t.get_rect(center=self.rect.center))

    def contains(self, pos):
        return self.rect.inflate(16, 16).collidepoint(pos)

class Joystick:
    def __init__(self, cx, cy, r):
        self.cx, self.cy, self.r = int(cx), int(cy), int(r)
        self.kx, self.ky = self.cx, self.cy
        self.dx, self.dy = 0.0, 0.0
        self.finger = None

    def contains(self, pos):
        return math.dist(pos, (self.cx, self.cy)) <= self.r * 1.5

    def update(self, pos):
        px, py = pos
        vx, vy = px - self.cx, py - self.cy
        d = math.hypot(vx, vy)
        if d > self.r:
            vx, vy = (vx / d) * self.r, (vy / d) * self.r
        self.kx, self.ky = int(self.cx + vx), int(self.cy + vy)
        self.dx, self.dy = vx / self.r, vy / self.r

    def reset(self):
        self.kx, self.ky = self.cx, self.cy
        self.dx, self.dy = 0.0, 0.0
        self.finger = None

    def draw(self, surf):
        s = pygame.Surface((self.r * 2 + 4, self.r * 2 + 4), pygame.SRCALPHA)
        c = self.r + 2
        pygame.draw.circle(s, (16, 22, 34, 130), (c, c), self.r)
        pygame.draw.circle(s, (80, 220, 255, 70), (c, c), int(self.r * 0.65), 1)
        pygame.draw.circle(s, (90, 225, 255, 210), (c, c), self.r, 2)
        surf.blit(s, (self.cx - c, self.cy - c))
        kr = max(18, int(self.r * 0.42))
        pygame.draw.circle(surf, (40, 140, 190), (self.kx, self.ky), kr)
        pygame.draw.circle(surf, (110, 235, 255), (self.kx, self.ky), kr - 4)
        pygame.draw.circle(surf, (240, 252, 255), (self.kx, self.ky), kr, 2)

class Enemy:
    def __init__(self, x, y, kind="normal"):
        self.x, self.y, self.kind = x, y, kind
        self.max_hp = 150 if kind == "tank" else 80
        self.hp = self.max_hp
        self.speed = 0.018 if kind == "tank" else 0.032
        self.hit_timer = self.attack_anim = 0

    def update(self, px, py):
        if self.hit_timer > 0: self.hit_timer -= 1
        if self.attack_anim > 0: self.attack_anim -= 1
        dx, dy = px - self.x, py - self.y
        dist = math.hypot(dx, dy)
        if 0.8 < dist < 12.0:
            vx, vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            if WORLD_MAP[int(self.y)][int(self.x + vx * 3)] == '0': self.x += vx
            if WORLD_MAP[int(self.y + vy * 3)][int(self.x)] == '0': self.y += vy
        return dist
    def draw_sprite(self, surf, sx, sy, size):
        if size < 8: return
        w, h = int(size * 0.74), int(size)
        x, y = int(sx - w // 2), int(sy - h // 2)
        dark = (28, 32, 42) if self.hit_timer == 0 else (210, 220, 235)
        armor = (255, 255, 255) if self.hit_timer > 0 else ((58, 52, 78) if self.kind == "tank" else (55, 64, 78))
        plate = (230, 240, 255) if self.hit_timer > 0 else ((92, 78, 128) if self.kind == "tank" else (88, 102, 124))
        neon = (220, 90, 255) if self.kind == "tank" else (80, 245, 255)
        eye_col = (255, 70, 90) if self.kind == "tank" else (255, 230, 65)

        pygame.draw.rect(surf, dark, (int(x + w * 0.23), int(y + h * 0.56), int(w * 0.20), int(h * 0.40)), border_radius=4)
        pygame.draw.rect(surf, dark, (int(x + w * 0.57), int(y + h * 0.56), int(w * 0.20), int(h * 0.40)), border_radius=4)
        pygame.draw.rect(surf, plate, (int(x + w * 0.21), int(y + h * 0.68), int(w * 0.24), int(h * 0.12)), border_radius=3)
        pygame.draw.rect(surf, plate, (int(x + w * 0.55), int(y + h * 0.68), int(w * 0.24), int(h * 0.12)), border_radius=3)

        pygame.draw.rect(surf, plate, (int(x + w * 0.03), int(y + h * 0.24), int(w * 0.18), int(h * 0.16)), border_radius=5)
        pygame.draw.rect(surf, plate, (int(x + w * 0.79), int(y + h * 0.24), int(w * 0.18), int(h * 0.16)), border_radius=5)
        pygame.draw.rect(surf, dark, (int(x + w * 0.05), int(y + h * 0.38), int(w * 0.13), int(h * 0.26)), border_radius=4)
        pygame.draw.rect(surf, dark, (int(x + w * 0.82), int(y + h * 0.38), int(w * 0.13), int(h * 0.26)), border_radius=4)

        pygame.draw.rect(surf, armor, (int(x + w * 0.17), int(y + h * 0.25), int(w * 0.66), int(h * 0.35)), border_radius=6)
        pygame.draw.rect(surf, plate, (int(x + w * 0.23), int(y + h * 0.28), int(w * 0.54), int(h * 0.22)), border_radius=5)

        core_r = max(2, int(w * 0.07))
        pygame.draw.circle(surf, neon, (int(sx), int(y + h * 0.39)), core_r)
        pygame.draw.circle(surf, (255, 255, 255), (int(sx), int(y + h * 0.39)), max(1, core_r // 2))

        pygame.draw.rect(surf, armor, (int(x + w * 0.29), int(y + h * 0.06), int(w * 0.42), int(h * 0.21)), border_radius=7)
        pygame.draw.rect(surf, plate, (int(x + w * 0.33), int(y + h * 0.08), int(w * 0.34), int(h * 0.13)), border_radius=5)
        pygame.draw.rect(surf, dark, (int(x + w * 0.37), int(y + h * 0.19), int(w * 0.26), max(2, int(h * 0.06))), border_radius=3)

        er = max(2, int(w * 0.055))
        ey = int(y + h * 0.14)
        pygame.draw.circle(surf, eye_col, (int(x + w * 0.41), ey), er)
        pygame.draw.circle(surf, eye_col, (int(x + w * 0.59), ey), er)
        pygame.draw.circle(surf, (255, 255, 255), (int(x + w * 0.41), ey), max(1, er // 2))
        pygame.draw.circle(surf, (255, 255, 255), (int(x + w * 0.59), ey), max(1, er // 2))

        if self.hp < self.max_hp:
            bw, bh = max(12, int(w * 0.8)), max(4, int(h * 0.04))
            pygame.draw.rect(surf, (20, 10, 15), (int(sx - bw // 2), int(y - bh - 6), bw, bh))
            pygame.draw.rect(surf, (70, 250, 130), (int(sx - bw // 2), int(y - bh - 6), max(0, int(bw * (self.hp / self.max_hp))), bh))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        rw, rh = self.screen.get_size()
        if rw < rh:
            self.W, self.H = rh, rw
            self.screen = pygame.display.set_mode((self.W, self.H))
        else:
            self.W, self.H = rw, rh
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, max(32, self.H // 14))
        self.small_font = pygame.font.SysFont(None, max(24, self.H // 20))
        self.big_font = pygame.font.SysFont(None, max(60, self.H // 7))
        self.sound = SoundEngine()
        self.state, self.click_cd, self.touches = "MENU", 0, {}
        self.look_finger, self.mouse_looking = None, False
        self.rot_speed, self.show_minimap, self.weapon_idx = 0.045, True, 0
        self.tracer_timer, self.sparks = 0, []
        self.vx = self.vy = self.bob_phase = 0.0
        self._init_ui()
        self.reset_game()

    def _init_ui(self):
        cx, cy = self.W // 2, self.H // 2
        bw, bh = min(350, int(self.W * 0.40)), max(60, int(self.H * 0.12))
        self.btn_play = Button(cx - bw // 2, cy - int(bh * 0.6), bw, bh, "START GAME", self.font, (25, 115, 85), (85, 255, 175))
        self.btn_set = Button(cx - bw // 2, cy + int(bh * 0.7), bw, bh, "SETTINGS", self.font)
        self.btn_quit = Button(cx - bw // 2, cy + int(bh * 2.0), bw, bh, "EXIT", self.font, (135, 35, 50), (255, 110, 130))

        margin = max(20, int(self.W * 0.03))
        bw_set = max(96, int(self.W * 0.14))
        bh_set = max(72, int(self.H * 0.15))
        lx = margin
        rx = self.W - margin - bw_set

        y1 = int(self.H * 0.16)
        y2 = int(self.H * 0.36)
        y3 = int(self.H * 0.57)
        y4 = int(self.H * 0.80)

        self.b_sd = Button(lx, y1, bw_set, bh_set, "-", self.big_font)
        self.b_su = Button(rx, y1, bw_set, bh_set, "+", self.big_font)
        self.b_vd = Button(lx, y2, bw_set, bh_set, "-", self.big_font)
        self.b_vu = Button(rx, y2, bw_set, bh_set, "+", self.big_font)
        self.b_wd = Button(lx, y3, bw_set, int(bh_set * 1.15), "<", self.big_font, (45, 65, 105), (120, 210, 255))
        self.b_wu = Button(rx, y3, bw_set, int(bh_set * 1.15), ">", self.big_font, (45, 65, 105), (120, 210, 255))

        bot_w = (self.W - margin * 2 - 30) // 2
        self.b_mp = Button(lx, y4, bot_w, bh_set, "MINIMAP: ON", self.font)
        self.b_bk = Button(lx + bot_w + 30, y4, bot_w, bh_set, "SAVE & BACK", self.font, (25, 115, 85), (85, 255, 175))

        pad = max(25, int(self.H * 0.05))
        jr = max(60, int(self.H * 0.14))
        self.joy = Joystick(pad + jr, self.H - pad - jr, jr)
        fs = int(jr * 1.48)
        self.c_fr = Button(self.W - pad - fs, self.H - pad - fs, fs, fs, "FIRE", self.font, (200, 30, 45), (255, 120, 140), 225, round_btn=True)
        self.c_ps = Button(self.W - 125, 20, 105, 46, "MENU", self.small_font, (24, 32, 48), (90, 225, 255), 195)
          def _is_on_hud(self, pos):
        return self.joy.contains(pos) or self.c_fr.contains(pos) or self.c_ps.contains(pos)

    def reset_game(self):
        self.px, self.py, self.pa = 1.5, 1.5, 0.0
        self.vx = self.vy = self.bob_phase = 0.0
        self.hp, self.score = 100, 0
        self.muzzle = self.shoot_cd = self.hurt_fl = self.voice_cd = self.tracer_timer = 0
        self.sparks.clear()
        self.touches.clear()
        self.look_finger = None
        self.joy.reset()
        self.enemies = [Enemy(8.5, 2.5), Enemy(13.5, 4.5, "tank"), Enemy(6.5, 7.5), Enemy(12.5, 7.5)]

    def shoot(self):
        if self.shoot_cd > 0: return
        wpn = WEAPONS[self.weapon_idx]
        self.shoot_cd = wpn["cd"]
        self.muzzle = 4
        self.tracer_timer = 4
        self.sound.play(f"shoot{self.weapon_idx}")

        mx, my = int(self.W * 0.65), int(self.H * 0.65)
        for _ in range(12):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(4, 14)
            self.sparks.append((mx, my, math.cos(ang) * spd, math.sin(ang) * spd, random.randint(6, 12)))

        best, best_d = None, MAX_DEPTH
        for e in self.enemies:
            dx, dy = e.x - self.px, e.y - self.py
            d = math.hypot(dx, dy)
            ang = (math.atan2(dy, dx) - self.pa + math.pi) % (2 * math.pi) - math.pi
            if abs(ang) < 0.16 and d < best_d and not self._wall(self.px, self.py, e.x, e.y):
                best_d, best = d, e
        if best:
            best.hp -= wpn["dmg"]
            best.hit_timer = 6
            for _ in range(10):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(3, 11)
                self.sparks.append((self.W // 2, self.H // 2, math.cos(ang) * spd, math.sin(ang) * spd, random.randint(6, 11)))
            if best.hp <= 0:
                self.enemies.remove(best)
                self.score += 150 if best.kind == "tank" else 100
                self.sound.play("kill")
                spots = [(13.5, 2.5), (2.5, 7.5), (13.5, 7.5), (8.5, 5.0)]
                random.shuffle(spots)
                for sx, sy in spots:
                    if math.hypot(sx - self.px, sy - self.py) > 4.0:
                        self.enemies.append(Enemy(sx, sy, "tank" if random.random() < 0.3 else "normal"))
                        break
            else:
                self.sound.play("pain")

    def _wall(self, x1, y1, x2, y2):
        steps = max(2, int(math.hypot(x2 - x1, y2 - y1) * 5))
        for i in range(1, steps):
            t = i / steps
            cx, cy = int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)
            if 0 <= cy < MAP_H and 0 <= cx < MAP_W and WORLD_MAP[cy][cx] != '0': return True
        return False

    def move(self):
        keys = pygame.key.get_pressed()
        pts = [pos for fid, pos in self.touches.items() if fid not in (self.look_finger, self.joy.finger)]
        if any(pygame.mouse.get_pressed()) and not self.mouse_looking and self.joy.finger != "MOUSE":
            pts.append(pygame.mouse.get_pos())

        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.pa -= self.rot_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.pa += self.rot_speed

        fwd = -self.joy.dy
        strafe = self.joy.dx
        if keys[pygame.K_w] or keys[pygame.K_UP]: fwd = 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: fwd = -1.0

        spd = 0.072
        tx = (math.cos(self.pa) * fwd - math.sin(self.pa) * strafe) * spd
        ty = (math.sin(self.pa) * fwd + math.cos(self.pa) * strafe) * spd
        self.vx += (tx - self.vx) * 0.25
        self.vy += (ty - self.vy) * 0.25

        if WORLD_MAP[int(self.py)][int(self.px + self.vx * 3.5)] == '0': self.px += self.vx
        else: self.vx = 0.0
        if WORLD_MAP[int(self.py + self.vy * 3.5)][int(self.px)] == '0': self.py += self.vy
        else: self.vy = 0.0

        vel = math.hypot(self.vx, self.vy)
        if vel > 0.005: self.bob_phase += vel * 3.2

        if keys[pygame.K_SPACE] or any(self.c_fr.contains(p) for p in pts):
            self.shoot()

    def _draw_weapon_art(self, surf, idx, cx, cy, scale=1.0, recoil=0):
        wpn = WEAPONS[idx]
        col, body = wpn["col"], wpn["body"]
        s = scale
        gx, gy = int(cx + recoil * 0.5), int(cy + recoil * 0.5)

        if idx == 0:
            pygame.draw.polygon(surf, (20, 24, 34), [
                (gx - int(115 * s), gy - int(68 * s)), (gx + int(90 * s), gy + int(85 * s)),
                (gx + int(35 * s), gy + int(142 * s)), (gx - int(148 * s), gy - int(22 * s))
            ])
            pygame.draw.polygon(surf, body, [
                (gx - int(98 * s), gy - int(84 * s)), (gx + int(118 * s), gy + int(72 * s)),
                (gx + int(76 * s), gy + int(126 * s)), (gx - int(132 * s), gy - int(34 * s))
            ])
            pygame.draw.polygon(surf, (78, 92, 114), [
                (gx - int(82 * s), gy - int(104 * s)), (gx + int(56 * s), gy - int(4 * s)),
                (gx + int(36 * s), gy + int(22 * s)), (gx - int(102 * s), gy - int(78 * s))
            ])
            pygame.draw.rect(surf, (28, 34, 46), (gx - int(14 * s), gy - int(66 * s), int(36 * s), int(26 * s)), border_radius=4)
            pygame.draw.rect(surf, col, (gx - int(10 * s), gy - int(62 * s), int(28 * s), int(18 * s)), 2, border_radius=3)
            pygame.draw.line(surf, col, (gx - int(96 * s), gy - int(68 * s)), (gx + int(66 * s), gy + int(48 * s)), max(2, int(4 * s)))

        elif idx == 1:
            pygame.draw.polygon(surf, (22, 18, 32), [
                (gx - int(105 * s), gy - int(55 * s)), (gx + int(85 * s), gy + int(80 * s)),
                (gx + int(30 * s), gy + int(135 * s)), (gx - int(135 * s), gy - int(15 * s))
            ])
            pygame.draw.polygon(surf, (38, 32, 52), [
                (gx - int(45 * s), gy - int(15 * s)), (gx - int(85 * s), gy + int(35 * s)),
                (gx - int(62 * s), gy + int(52 * s)), (gx - int(22 * s), gy + int(2 * s))
            ])
            pygame.draw.line(surf, col, (gx - int(72 * s), gy + int(28 * s)), (gx - int(34 * s), gy - int(10 * s)), max(2, int(3 * s)))
            pygame.draw.polygon(surf, body, [
                (gx - int(90 * s), gy - int(72 * s)), (gx + int(105 * s), gy + int(68 * s)),
                (gx + int(68 * s), gy + int(118 * s)), (gx - int(122 * s), gy - int(26 * s))
            ])
            pygame.draw.line(surf, col, (gx - int(95 * s), gy - int(58 * s)), (gx + int(55 * s), gy + int(50 * s)), max(2, int(5 * s)))
            pygame.draw.circle(surf, col, (gx - int(104 * s), gy - int(62 * s)), max(3, int(6 * s)))

        else:
            pygame.draw.polygon(surf, (18, 28, 34), [
                (gx - int(125 * s), gy - int(75 * s)), (gx + int(105 * s), gy + int(95 * s)),
                (gx + int(45 * s), gy + int(150 * s)), (gx - int(155 * s), gy - int(20 * s))
            ])
            pygame.draw.polygon(surf, body, [
                (gx - int(112 * s), gy - int(92 * s)), (gx + int(125 * s), gy + int(80 * s)),
                (gx + int(80 * s), gy + int(136 * s)), (gx - int(142 * s), gy - int(32 * s))
            ])
            for k in range(3):
                ox = gx - int((82 - k * 34) * s)
                oy = gy - int((58 - k * 25) * s)
                pygame.draw.circle(surf, col, (ox, oy), max(5, int(13 * s)))
                pygame.draw.circle(surf, (240, 255, 250), (ox, oy), max(2, int(6 * s)))

        pygame.draw.rect(surf, (15, 22, 32), (gx + int(34 * s), gy + int(54 * s), int(30 * s), int(22 * s)), border_radius=4)
        pygame.draw.rect(surf, col, (gx + int(38 * s), gy + int(58 * s), int(22 * s), int(14 * s)), border_radius=2)
          def _draw_health_bar(self):
        bx, by, bw, bh = 22, 20, max(210, int(self.W * 0.28)), 34
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(s, (15, 30, 22, 185), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(s, (75, 245, 130, 230), (0, 0, bw, bh), 2, border_radius=8)
        self.screen.blit(s, (bx, by))

        pygame.draw.rect(self.screen, (85, 255, 140), (bx + 14, by + 9, 6, 16))
        pygame.draw.rect(self.screen, (85, 255, 140), (bx + 9, by + 14, 16, 6))

        segs = 16
        active = int(math.ceil((max(0, self.hp) / 100.0) * segs))
        sx_start = bx + 36
        seg_w = max(5, (bw - 48) // segs - 3)
        for i in range(segs):
            col = (80, 255, 135) if i < active else (25, 55, 38)
            pygame.draw.rect(self.screen, col, (sx_start + i * (seg_w + 3), by + 7, seg_w, bh - 14), border_radius=2)

    def draw_3d(self):
        hh = self.H // 2
        pygame.draw.rect(self.screen, (10, 14, 22), (0, 0, self.W, hh))
        pygame.draw.rect(self.screen, (14, 18, 28), (0, hh, self.W, hh))

        for i in range(1, 7):
            t = (i / 7.0) ** 1.7
            y_c = int(hh * (1.0 - t))
            c_glow = (16 + i * 3, 26 + i * 6, 44 + i * 9)
            pygame.draw.rect(self.screen, c_glow, (0, y_c, self.W, max(2, int(t * 14))))

        pygame.draw.polygon(self.screen, (130, 235, 255), [
            (self.W // 2 - 12, hh - 8), (self.W // 2 + 12, hh - 8),
            (int(self.W * 0.35), 0), (int(self.W * 0.65), 0)
        ])

        ca, sa = math.cos(self.pa), math.sin(self.pa)
        for row_y in range(hh + 6, self.H, 6):
            p = row_y - hh
            row_dist = (0.5 * self.H) / p
            shade = max(0.15, min(1.0, 1.35 / (row_dist + 0.4)))
            phase_z = (row_dist + (self.px * ca + self.py * sa)) % 1.0
            is_h_line = phase_z < 0.08
            base_c = (int(42 * shade), int(85 * shade), int(115 * shade)) if is_h_line else (int(18 * shade), int(24 * shade), int(36 * shade))
            pygame.draw.rect(self.screen, base_c, (0, row_y, self.W, 6))

            if row_dist < 14.0:
                strafe_off = (-self.px * sa + self.py * ca + self.pa * 1.8) % 1.0
                tile_w = max(24, int(self.W / (row_dist * 1.1)))
                start_x = int(-strafe_off * tile_w)
                line_c = (int(38 * shade), int(95 * shade), int(130 * shade))
                for gx in range(start_x, self.W, tile_w):
                    pygame.draw.line(self.screen, line_c, (gx, row_y), (gx, row_y + 5), 2)

        zbuf = [MAX_DEPTH] * NUM_RAYS
        ang = self.pa - HALF_FOV
        step = FOV / NUM_RAYS
        sc = self.W / NUM_RAYS
        for r in range(NUM_RAYS):
            ray_x, ray_y = math.cos(ang), math.sin(ang)
            map_x, map_y = int(self.px), int(self.py)
            ddx = abs(1.0 / (ray_x if abs(ray_x) > 1e-6 else 1e-6))
            ddy = abs(1.0 / (ray_y if abs(ray_y) > 1e-6 else 1e-6))
            if ray_x < 0: step_x, sdx = -1, (self.px - map_x) * ddx
            else: step_x, sdx = 1, (map_x + 1.0 - self.px) * ddx
            if ray_y < 0: step_y, sdy = -1, (self.py - map_y) * ddy
            else: step_y, sdy = 1, (map_y + 1.0 - self.py) * ddy

            hit, side, wall_type = False, 0, '1'
            for _ in range(MAX_DEPTH * 2):
                if sdx < sdy:
                    sdx += ddx; map_x += step_x; side = 0
                else:
                    sdy += ddy; map_y += step_y; side = 1
                if 0 <= map_y < MAP_H and 0 <= map_x < MAP_W:
                    if WORLD_MAP[map_y][map_x] != '0':
                        hit, wall_type = True, WORLD_MAP[map_y][map_x]
                        break
                else:
                    break

            if hit:
                raw_dist = (sdx - ddx) if side == 0 else (sdy - ddy)
                perp = max(0.05, raw_dist * math.cos(self.pa - ang))
                zbuf[r] = perp
                ph = min(self.H * 1.65, self.H / perp)
                wx = (self.py + raw_dist * ray_y) if side == 0 else (self.px + raw_dist * ray_x)
                wx -= math.floor(wx)

                sh = max(0.18, 1.0 - perp / MAX_DEPTH) * (0.78 if side == 1 else 1.0)
                is_rib = (wx < 0.05 or wx > 0.95) or (0.47 < wx < 0.53)
                if is_rib: sh *= 0.45

                col = (int(42 * sh), int(52 * sh), int(72 * sh))
                rx_pos = int(r * sc)
                ry_pos = int(hh - ph // 2)
                rw_px = int(sc + 2)
                rh_px = int(ph)
                pygame.draw.rect(self.screen, col, (rx_pos, ry_pos, rw_px, rh_px))

                if ph > 16:
                    c_cyan = (int(90 * sh), int(245 * sh), int(255 * sh))
                    c_purp = (int(225 * sh), int(85 * sh), int(255 * sh))
                    pygame.draw.rect(self.screen, c_cyan, (rx_pos, ry_pos + int(ph * 0.14), rw_px, max(2, int(ph * 0.035))))
                    pygame.draw.rect(self.screen, c_cyan, (rx_pos, ry_pos + int(ph * 0.88), rw_px, max(2, int(ph * 0.035))))
                    if not is_rib:
                        n_col = c_purp if wall_type == '2' or side == 1 else c_cyan
                        pygame.draw.rect(self.screen, n_col, (rx_pos, int(hh - ph * 0.02), rw_px, max(2, int(ph * 0.04))))
            ang += step

        for e in sorted(self.enemies, key=lambda x: math.hypot(x.x - self.px, x.y - self.py), reverse=True):
            dx, dy = e.x - self.px, e.y - self.py
            dist = math.hypot(dx, dy)
            a = (math.atan2(dy, dx) - self.pa + math.pi) % (2 * math.pi) - math.pi
            if abs(a) < HALF_FOV + 0.3 and dist > 0.3:
                sx = (0.5 + a / FOV) * self.W
                idx = int(sx / sc)
                if 0 <= idx < NUM_RAYS and dist < zbuf[idx]:
                    sz = min(self.H * 1.2, self.H / dist)
                    e.draw_sprite(self.screen, sx, hh + sz * 0.1, sz)
              def draw_hud(self):
        wpn = WEAPONS[self.weapon_idx]
        recoil = 16 if self.shoot_cd > (wpn["cd"] - 4) else 0
        bob_x = int(math.cos(self.bob_phase) * 8)
        bob_y = int(abs(math.sin(self.bob_phase)) * 6)

        gx = int(self.W * 0.74) + bob_x
        gy = int(self.H * 0.78) + bob_y
        mz_x, mz_y = gx - int(95 * 1.15), gy - int(92 * 1.15)

        if self.tracer_timer > 0:
            tx = self.W // 2 + random.randint(-8, 8)
            ty = self.H // 2 + random.randint(-8, 8)
            pygame.draw.line(self.screen, wpn["col"], (mz_x, mz_y), (tx, ty), 4 if self.weapon_idx == 2 else 3)

        if self.muzzle > 0:
            pygame.draw.circle(self.screen, wpn["col"], (mz_x, mz_y), 34)
            pygame.draw.circle(self.screen, (255, 255, 255), (mz_x, mz_y), 16)

        self._draw_weapon_art(self.screen, self.weapon_idx, gx, gy, 1.15, recoil)

        new_sparks = []
        for sx, sy, svx, svy, life in self.sparks:
            if life > 1:
                nx, ny = sx + svx, sy + svy
                pygame.draw.line(self.screen, wpn["spark"], (int(nx), int(ny)), (int(sx), int(sy)), 2)
                new_sparks.append((nx, ny, svx, svy + 0.45, life - 1))
        self.sparks = new_sparks

        pygame.draw.circle(self.screen, wpn["col"], (self.W // 2, self.H // 2), 7, 2)
        self._draw_health_bar()
        self.screen.blit(self.small_font.render(f"SCORE: {self.score}  |  {wpn['name']}", True, (220, 240, 255)), (24, 62))

        if self.show_minimap:
            my_off = 92
            for r, row in enumerate(WORLD_MAP):
                for c, v in enumerate(row):
                    col_m = (60, 175, 235) if v == '1' else ((185, 75, 235) if v == '2' else (18, 22, 34))
                    pygame.draw.rect(self.screen, col_m, (22 + c * 8, my_off + r * 8, 7, 7))
            pygame.draw.circle(self.screen, (80, 255, 140), (int(22 + self.px * 8), int(my_off + self.py * 8)), 3)
            for e in self.enemies:
                pygame.draw.circle(self.screen, (255, 75, 90), (int(22 + e.x * 8), int(my_off + e.y * 8)), 3)

        self.joy.draw(self.screen)
        self.c_fr.draw(self.screen)
        self.c_ps.draw(self.screen)
        if self.hurt_fl > 0:
            pygame.draw.rect(self.screen, (230, 40, 50), (0, 0, self.W, self.H), 10)

    def tap(self, pos):
        if self.click_cd > 0: return
        if self.state == "MENU":
            if self.btn_play.contains(pos): self.sound.play("click"); self.reset_game(); self.state = "PLAYING"; self.click_cd = 10
            elif self.btn_set.contains(pos): self.sound.play("click"); self.state = "SETTINGS"; self.click_cd = 10
            elif self.btn_quit.contains(pos): pygame.quit(); sys.exit()
        elif self.state == "SETTINGS":
            if self.b_sd.contains(pos): self.rot_speed = max(0.015, round(self.rot_speed - 0.01, 3)); self.click_cd = 4
            elif self.b_su.contains(pos): self.rot_speed = min(0.10, round(self.rot_speed + 0.01, 3)); self.click_cd = 4
            elif self.b_vd.contains(pos): self.sound.volume = max(0.0, round(self.sound.volume - 0.1, 1)); self.click_cd = 4
            elif self.b_vu.contains(pos): self.sound.volume = min(1.0, round(self.sound.volume + 0.1, 1)); self.click_cd = 4
            elif self.b_wd.contains(pos): self.weapon_idx = (self.weapon_idx - 1) % len(WEAPONS); self.click_cd = 5
            elif self.b_wu.contains(pos): self.weapon_idx = (self.weapon_idx + 1) % len(WEAPONS); self.click_cd = 5
            elif self.b_mp.contains(pos): self.show_minimap = not self.show_minimap; self.click_cd = 6
            elif self.b_bk.contains(pos): self.state = "MENU"; self.click_cd = 10
            self.sound.play("click")
        elif self.state == "PLAYING" and self.c_ps.contains(pos):
            self.sound.play("click"); self.state = "MENU"; self.click_cd = 10
        elif self.state == "GAMEOVER":
            if self.btn_play.contains(pos): self.reset_game(); self.state = "PLAYING"; self.click_cd = 10
            elif self.btn_quit.contains(pos): pygame.quit(); sys.exit()

    def _draw_bar(self, cx, y, w, h, ratio, col):
        pygame.draw.rect(self.screen, (16, 20, 32), (cx - w // 2, y, w, h), border_radius=6)
        pygame.draw.rect(self.screen, col, (cx - w // 2, y, max(6, int(w * ratio)), h), border_radius=6)
          def run(self):
        while True:
            if self.click_cd > 0: self.click_cd -= 1
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.tap(ev.pos)
                    if self.state == "PLAYING":
                        if self.joy.contains(ev.pos):
                            self.joy.finger = "MOUSE"; self.joy.update(ev.pos)
                        elif not self._is_on_hud(ev.pos):
                            self.mouse_looking = True
                elif ev.type == pygame.MOUSEMOTION and self.state == "PLAYING":
                    if self.joy.finger == "MOUSE": self.joy.update(ev.pos)
                    elif self.mouse_looking:
                        rx_rel, _ = ev.rel
                        self.pa += rx_rel * (self.rot_speed * 0.12)
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    if self.joy.finger == "MOUSE": self.joy.reset()
                    self.mouse_looking = False
                elif ev.type == pygame.FINGERDOWN:
                    p = (int(ev.x * self.W), int(ev.y * self.H))
                    self.touches[ev.finger_id] = p
                    self.tap(p)
                    if self.state == "PLAYING":
                        if self.joy.finger is None and self.joy.contains(p):
                            self.joy.finger = ev.finger_id; self.joy.update(p)
                        elif self.look_finger is None and not self._is_on_hud(p):
                            self.look_finger = ev.finger_id
                elif ev.type == pygame.FINGERMOTION:
                    p = (int(ev.x * self.W), int(ev.y * self.H))
                    self.touches[ev.finger_id] = p
                    if self.state == "PLAYING":
                        if ev.finger_id == self.joy.finger: self.joy.update(p)
                        elif ev.finger_id == self.look_finger: self.pa += ev.dx * (self.rot_speed * 85.0)
                elif ev.type == pygame.FINGERUP:
                    self.touches.pop(ev.finger_id, None)
                    if ev.finger_id == self.joy.finger: self.joy.reset()
                    if ev.finger_id == self.look_finger: self.look_finger = None

            if self.state == "MENU":
                self.screen.fill((14, 18, 28))
                t = self.big_font.render("CYBER DOOM 3D", True, (80, 240, 255))
                self.screen.blit(t, t.get_rect(center=(self.W // 2, self.H // 2 - 130)))
                self.btn_play.text = "START GAME"
                for b in [self.btn_play, self.btn_set, self.btn_quit]: b.draw(self.screen)

            elif self.state == "SETTINGS":
                self.screen.fill((14, 18, 28))
                cx = self.W // 2
                bar_w = max(220, int(self.W * 0.42))
                title = self.big_font.render("SETTINGS & ARMORY", True, (80, 240, 255))
                self.screen.blit(title, title.get_rect(center=(cx, int(self.H * 0.08))))

                y1 = self.b_sd.rect.centery
                t1 = self.font.render(f"SENSITIVITY: {int(self.rot_speed * 1000)}", True, (255, 255, 255))
                self.screen.blit(t1, t1.get_rect(center=(cx, y1 - 18)))
                self._draw_bar(cx, y1 + 12, bar_w, 14, self.rot_speed / 0.10, (80, 240, 255))

                y2 = self.b_vd.rect.centery
                t2 = self.font.render(f"VOLUME: {int(self.sound.volume * 100)}%", True, (255, 255, 255))
                self.screen.blit(t2, t2.get_rect(center=(cx, y2 - 18)))
                self._draw_bar(cx, y2 + 12, bar_w, 14, self.sound.volume, (85, 255, 140))

                wpn = WEAPONS[self.weapon_idx]
                y3 = self.b_wd.rect.centery
                box_w = self.b_wu.rect.left - self.b_wd.rect.right - 30
                box = pygame.Rect(self.b_wd.rect.right + 15, self.b_wd.rect.top, box_w, self.b_wd.rect.h)
                pygame.draw.rect(self.screen, (22, 28, 44), box, border_radius=16)
                pygame.draw.rect(self.screen, wpn["col"], box, 2, border_radius=16)

                self._draw_weapon_art(self.screen, self.weapon_idx, box.left + int(box_w * 0.22), y3 + 6, 0.42)

                info_x = box.left + int(box_w * 0.44)
                s_bar_w = int(box_w * 0.36)
                t3 = self.font.render(wpn["name"], True, wpn["col"])
                self.screen.blit(t3, (info_x, box.top + 8))
                self.screen.blit(self.small_font.render("DMG", True, (200, 210, 230)), (info_x, box.top + int(box.h * 0.45)))
                self._draw_bar(info_x + 65 + s_bar_w // 2, box.top + int(box.h * 0.49), s_bar_w, 10, wpn["dmg"] / 85.0, (255, 95, 110))
                self.screen.blit(self.small_font.render("SPD", True, (200, 210, 230)), (info_x, box.top + int(box.h * 0.72)))
                self._draw_bar(info_x + 65 + s_bar_w // 2, box.top + int(box.h * 0.76), s_bar_w, 10, (30 - wpn["cd"]) / 26.0, (255, 215, 80))

                self.b_mp.text = f"MINIMAP: {'ON' if self.show_minimap else 'OFF'}"
                for b in [self.b_sd, self.b_su, self.b_vd, self.b_vu, self.b_wd, self.b_wu, self.b_mp, self.b_bk]:
                    b.draw(self.screen)

            elif self.state == "PLAYING":
                if self.shoot_cd > 0: self.shoot_cd -= 1
                if self.muzzle > 0: self.muzzle -= 1
                if self.tracer_timer > 0: self.tracer_timer -= 1
                if self.hurt_fl > 0: self.hurt_fl -= 1
                if self.voice_cd > 0: self.voice_cd -= 1
                self.move()
                for e in self.enemies:
                    if e.update(self.px, self.py) < 1.1:
                        e.attack_anim = 10
                        if self.hurt_fl == 0:
                            self.hp -= 10; self.hurt_fl = 25; self.sound.play("hurt")
                            if self.voice_cd == 0: self.sound.play("attack"); self.voice_cd = 90
                            if self.hp <= 0: self.sound.play("laugh"); self.state = "GAMEOVER"
                self.draw_3d(); self.draw_hud()

            elif self.state == "GAMEOVER":
                self.screen.fill((28, 16, 28))
                t = self.big_font.render("GAME OVER", True, (255, 85, 110))
                s = self.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
                self.screen.blit(t, t.get_rect(center=(self.W // 2, self.H // 2 - 120)))
                self.screen.blit(s, s.get_rect(center=(self.W // 2, self.H // 2 - 60)))
                self.btn_play.text = "PLAY AGAIN"
                for b in [self.btn_play, self.btn_quit]: b.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    Game().run()
              
