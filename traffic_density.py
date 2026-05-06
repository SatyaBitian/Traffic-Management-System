import pygame
import random
import sys
import time
import math

# --- ARDUINO SETUP ---
try:
    import serial
    ser = serial.Serial('COM12', 9600, timeout=0.1)
    time.sleep(2)
    print("Arduino Connected!")
except:
    ser = None
    print("Arduino NOT connected (serial library or port unavailable).")

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
WIDTH, HEIGHT = 800, 800
FPS = 60

# Road geometry
ROAD_W = 240          # total road width for each axis (4 lanes × 60 px)
LANE_W = 60           # one lane width
CENTER = WIDTH // 2   # 450

# Stop-line distance from centre (vehicles stop here when red)
STOP_DIST = ROAD_W // 2 + 10   # 130 px from centre

# Colours – realistic palette
C_GRASS       = (62,  120,  62)
C_ROAD        = (45,   45,  45)
C_LANE_MARK   = (255, 255, 255)
C_DASHED      = (220, 220,   0)
C_SIDEWALK    = (180, 160, 130)
C_CROSSING    = (240, 240, 240)
C_CAR_NORMAL  = (30,  100, 220)   # blue
C_CAR_EMERG   = (220,  30,  30)   # red
C_CAR_SHADOW  = (0,     0,   0)
C_LIGHT_RED   = (220,  30,  30)
C_LIGHT_YEL   = (220, 200,  30)
C_LIGHT_GRN   = ( 30, 200,  80)
C_LIGHT_OFF   = ( 60,  60,  60)
C_POLE        = (80,   80,  80)
C_TEXT_BG     = (0,     0,   0, 180)
C_WHITE       = (255, 255, 255)
C_BLACK       = (0,     0,   0)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Traffic Management System")
clock = pygame.time.Clock()
font_main  = pygame.font.SysFont('Consolas', 17, bold=True)
font_small = pygame.font.SysFont('Consolas', 13)
font_big   = pygame.font.SysFont('Consolas', 22, bold=True)

# ─────────────────────────────────────────────
#  PRE-RENDER ROAD SURFACE (drawn once)
# ─────────────────────────────────────────────
road_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
road_surf.fill(C_GRASS)

def draw_road_base():
    s = road_surf

    # --- sidewalks (slightly lighter band around roads) ---
    SW = 14   # sidewalk width
    # vertical road sidewalks
    pygame.draw.rect(s, C_SIDEWALK, (CENTER - ROAD_W//2 - SW, 0, SW, HEIGHT))
    pygame.draw.rect(s, C_SIDEWALK, (CENTER + ROAD_W//2,      0, SW, HEIGHT))
    # horizontal road sidewalks
    pygame.draw.rect(s, C_SIDEWALK, (0, CENTER - ROAD_W//2 - SW, WIDTH, SW))
    pygame.draw.rect(s, C_SIDEWALK, (0, CENTER + ROAD_W//2,      WIDTH, SW))

    # --- main road rectangles ---
    pygame.draw.rect(s, C_ROAD, (CENTER - ROAD_W//2, 0, ROAD_W, HEIGHT))
    pygame.draw.rect(s, C_ROAD, (0, CENTER - ROAD_W//2, WIDTH, ROAD_W))

    # --- zebra crossings (8 stripes, 8 px each with 8 gap) ---
    stripe_w, stripe_gap = 8, 8
    stripe_len = ROAD_W - 4
    num_stripes = 8
    cross_off = ROAD_W//2 + SW + 2   # how far from centre the crossing starts

    for i in range(num_stripes):
        ox = i * (stripe_w + stripe_gap)
        # top crossing (horizontal road, top of intersection)
        pygame.draw.rect(s, C_CROSSING,
            (CENTER - stripe_len//2,
             CENTER - cross_off - stripe_w - ox,
             stripe_len, stripe_w))
        # bottom crossing
        pygame.draw.rect(s, C_CROSSING,
            (CENTER - stripe_len//2,
             CENTER + cross_off + ox,
             stripe_len, stripe_w))
        # left crossing (vertical road, left of intersection)
        pygame.draw.rect(s, C_CROSSING,
            (CENTER - cross_off - stripe_w - ox,
             CENTER - stripe_len//2,
             stripe_w, stripe_len))
        # right crossing
        pygame.draw.rect(s, C_CROSSING,
            (CENTER + cross_off + ox,
             CENTER - stripe_len//2,
             stripe_w, stripe_len))

    # --- lane markings ---
    dash_len, dash_gap = 28, 18

    def draw_dashes_v(x, y0, y1):
        """dashed vertical line"""
        y = y0
        while y < y1:
            pygame.draw.line(s, C_DASHED, (x, y), (x, min(y + dash_len, y1)), 2)
            y += dash_len + dash_gap

    def draw_dashes_h(y, x0, x1):
        x = x0
        while x < x1:
            pygame.draw.line(s, C_DASHED, (x, y), (min(x + dash_len, x1), y), 2)
            x += dash_len + dash_gap

    # Vertical road: 4 lanes (2 up, 2 down) – centre divider solid white, others dashed yellow
    vx0 = CENTER - ROAD_W//2
    # solid centre line
    pygame.draw.line(s, C_LANE_MARK, (CENTER, 0), (CENTER, HEIGHT), 2)
    # dashed lane lines left half
    draw_dashes_v(vx0 + LANE_W,   0, CENTER - ROAD_W//2)
    draw_dashes_v(vx0 + LANE_W,   CENTER + ROAD_W//2, HEIGHT)
    # dashed lane lines right half
    draw_dashes_v(vx0 + 3*LANE_W, 0, CENTER - ROAD_W//2)
    draw_dashes_v(vx0 + 3*LANE_W, CENTER + ROAD_W//2, HEIGHT)

    # Horizontal road
    hy0 = CENTER - ROAD_W//2
    # solid centre line
    pygame.draw.line(s, C_LANE_MARK, (0, CENTER), (WIDTH, CENTER), 2)
    # dashed lane lines
    draw_dashes_h(hy0 + LANE_W,   0, CENTER - ROAD_W//2)
    draw_dashes_h(hy0 + LANE_W,   CENTER + ROAD_W//2, WIDTH)
    draw_dashes_h(hy0 + 3*LANE_W, 0, CENTER - ROAD_W//2)
    draw_dashes_h(hy0 + 3*LANE_W, CENTER + ROAD_W//2, WIDTH)

    # --- stop lines (thick white, just outside intersection box) ---
    sl = ROAD_W//2 + 2
    lw = 4
    # Lane 1 (coming from bottom, stops just south of intersection)
    pygame.draw.line(s, C_LANE_MARK,
        (CENTER - ROAD_W//2, CENTER + sl), (CENTER + ROAD_W//2, CENTER + sl), lw)
    # Lane 3 (from top)
    pygame.draw.line(s, C_LANE_MARK,
        (CENTER - ROAD_W//2, CENTER - sl), (CENTER + ROAD_W//2, CENTER - sl), lw)
    # Lane 2 (from right)
    pygame.draw.line(s, C_LANE_MARK,
        (CENTER + sl, CENTER - ROAD_W//2), (CENTER + sl, CENTER + ROAD_W//2), lw)
    # Lane 4 (from left)
    pygame.draw.line(s, C_LANE_MARK,
        (CENTER - sl, CENTER - ROAD_W//2), (CENTER - sl, CENTER + ROAD_W//2), lw)

draw_road_base()

# ─────────────────────────────────────────────
#  TRAFFIC LIGHT DRAWING
# ─────────────────────────────────────────────
# Pole + 3-light housing positions (per lane)
# Each entry: (pole_x, pole_y, box_x, box_y, orientation)
# orientation: 'v' = vertical box, 'h' = horizontal box
TL_CONFIG = {
    "Lane_1": (CENTER + ROAD_W//2 + 4,  CENTER + STOP_DIST - 20,  'right'),
    "Lane_2": (CENTER + STOP_DIST - 20, CENTER - ROAD_W//2 - 4,   'top'),
    "Lane_3": (CENTER - ROAD_W//2 - 4,  CENTER - STOP_DIST + 20,  'left'),
    "Lane_4": (CENTER - STOP_DIST + 20, CENTER + ROAD_W//2 + 4,   'bottom'),
}

def draw_traffic_light(surf, lane, signal):
    """signal: 'red' | 'yellow' | 'green'"""
    px, py, side = TL_CONFIG[lane]

    # Which bulbs are lit
    if signal == 'green':
        r, y, g = C_LIGHT_OFF, C_LIGHT_OFF, C_LIGHT_GRN
    elif signal == 'yellow':
        r, y, g = C_LIGHT_OFF, C_LIGHT_YEL, C_LIGHT_OFF
    else:  # red
        r, y, g = C_LIGHT_RED, C_LIGHT_OFF, C_LIGHT_OFF

    # Box dimensions
    bw, bh = 22, 62
    if side in ('top', 'bottom'):
        bw, bh = 62, 22

    # Draw pole
    if side == 'right':
        pole_x1, pole_y1 = px,      py
        pole_x2, pole_y2 = px + 16, py
        box_x = px + 16
        box_y = py - bh // 2
        pygame.draw.line(surf, C_POLE, (px, py), (px + 16, py), 4)
    elif side == 'left':
        pole_x1, pole_y1 = px,      py
        pygame.draw.line(surf, C_POLE, (px, py), (px - 16, py), 4)
        box_x = px - 16 - bw
        box_y = py - bh // 2
    elif side == 'top':
        pygame.draw.line(surf, C_POLE, (px, py), (px, py - 16), 4)
        box_x = px - bw // 2
        box_y = py - 16 - bh
    else:  # bottom
        pygame.draw.line(surf, C_POLE, (px, py), (px, py + 16), 4)
        box_x = px - bw // 2
        box_y = py + 16

    # Housing background
    pygame.draw.rect(surf, C_BLACK, (box_x - 2, box_y - 2, bw + 4, bh + 4), border_radius=4)

    # Draw 3 lights
    if side in ('right', 'left'):
        bulb_r = 8
        cx = box_x + bw // 2
        positions = [(cx, box_y + 9), (cx, box_y + 31), (cx, box_y + 53)]
        colours   = [r, y, g]
    else:
        bulb_r = 8
        cy = box_y + bh // 2
        positions = [(box_x + 9, cy), (box_x + 31, cy), (box_x + 53, cy)]
        colours   = [r, y, g]

    for (bx, by), col in zip(positions, colours):
        pygame.draw.circle(surf, col, (bx, by), bulb_r)
        if col != C_LIGHT_OFF:
            glow = pygame.Surface((bulb_r*4, bulb_r*4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, 60), (bulb_r*2, bulb_r*2), bulb_r*2)
            surf.blit(glow, (bx - bulb_r*2, by - bulb_r*2))

# ─────────────────────────────────────────────
#  VEHICLE CLASS
# ─────────────────────────────────────────────
CAR_BODIES = [
    (30, 100, 220),  # blue
    (30, 150, 200),  # teal
    (100, 180, 60),  # green
    (180, 160, 30),  # gold
    (160,  60, 200), # purple
    (60,  160, 100), # sea-green
]

# Lane travel directions and spawn/exit info
# Lane 1: bottom → top  (going north), right lane of vertical road (x = CENTER + LANE_W//2)
# Lane 2: right  → left (going west),  top lane of horizontal road  (y = CENTER - LANE_W//2)
# Lane 3: top   → bottom (going south), left lane of vertical road  (x = CENTER - LANE_W//2)
# Lane 4: left  → right (going east),  bottom lane of horizontal road (y = CENTER + LANE_W//2)

LANE_META = {
    #        axis  travel  spawn coord       exit coord   vehicle centre x/y offsets
    "Lane_1": dict(axis='y', dir=-1,
                   spawn_coord=HEIGHT + 30,
                   exit_coord=-80,
                   lane_coord=CENTER + LANE_W + LANE_W//2,   # x centre
                   stop_coord=CENTER + STOP_DIST),            # stops when pos[1] <= this
    "Lane_2": dict(axis='x', dir=-1,
                   spawn_coord=WIDTH + 30,
                   exit_coord=-80,
                   lane_coord=CENTER - LANE_W - LANE_W//2,   # y centre
                   stop_coord=CENTER + STOP_DIST),
    "Lane_3": dict(axis='y', dir=+1,
                   spawn_coord=-30,
                   exit_coord=HEIGHT + 80,
                   lane_coord=CENTER - LANE_W - LANE_W//2,
                   stop_coord=CENTER - STOP_DIST),
    "Lane_4": dict(axis='x', dir=+1,
                   spawn_coord=-30,
                   exit_coord=WIDTH + 80,
                   lane_coord=CENTER + LANE_W + LANE_W//2,
                   stop_coord=CENTER - STOP_DIST),
}

# Minimum gap between vehicles (front-bumper to rear-bumper)
MIN_GAP = 8
CAR_LEN = 44   # along travel axis
CAR_WID = 26   # across travel axis

class Vehicle:
    _id_counter = 0

    def __init__(self, lane):
        Vehicle._id_counter += 1
        self.id    = Vehicle._id_counter
        self.lane  = lane
        meta       = LANE_META[lane]
        self.axis  = meta['axis']          # 'x' or 'y'
        self.dir   = meta['dir']           # +1 or -1
        self.lane_coord  = meta['lane_coord']
        self.stop_coord  = meta['stop_coord']
        self.exit_coord  = meta['exit_coord']

        # is_emergency: ~5% chance
        self.is_emergency = random.random() < 0.05
        if self.is_emergency:
            self.color = C_CAR_EMERG
            self.roof_color = (255, 80, 80)
        else:
            self.color = random.choice(CAR_BODIES)
            self.roof_color = tuple(max(0, c - 50) for c in self.color)

        self.speed = random.uniform(1.8, 2.5)
        self.base_speed = self.speed

        # Position: coord along travel axis
        self.travel = float(meta['spawn_coord'])

        # Has this vehicle crossed the stop line already?
        self.has_crossed = False

        # Build rect for collision queries
        self._update_rect()

    def _update_rect(self):
        if self.axis == 'y':
            x = self.lane_coord - CAR_WID // 2
            y = int(self.travel) - CAR_LEN // 2
            self.rect = pygame.Rect(x, y, CAR_WID, CAR_LEN)
        else:
            x = int(self.travel) - CAR_LEN // 2
            y = self.lane_coord - CAR_WID // 2
            self.rect = pygame.Rect(x, x if False else x, CAR_LEN, CAR_WID)
            # redo properly
            self.rect = pygame.Rect(int(self.travel) - CAR_LEN // 2,
                                    self.lane_coord - CAR_WID // 2,
                                    CAR_LEN, CAR_WID)

    def _front(self):
        """Position of the front bumper along the travel axis."""
        if self.dir == -1:
            return self.travel - CAR_LEN // 2
        else:
            return self.travel + CAR_LEN // 2

    def _back(self):
        if self.dir == -1:
            return self.travel + CAR_LEN // 2
        else:
            return self.travel - CAR_LEN // 2

    def update_crossed(self, is_green):
        """
        Mark has_crossed=True only when the vehicle's FRONT BUMPER passes the stop line
        AND the signal was green (so it legitimately crossed, not ran a red).
        Once crossed, the vehicle is inside/past the intersection and never stops again.
        """
        if self.has_crossed:
            return
        if not is_green:
            return   # never mark crossed on a red/yellow — vehicle must be stopped
        if self.dir == -1:
            # front bumper = travel - half_length; crosses when it goes below stop_coord
            if (self.travel - CAR_LEN // 2) <= self.stop_coord:
                self.has_crossed = True
        else:
            # front bumper = travel + half_length; crosses when it goes above stop_coord
            if (self.travel + CAR_LEN // 2) >= self.stop_coord:
                self.has_crossed = True

    def should_stop(self, is_green):
        """
        Returns True if vehicle must hold at (or approach) the stop line.
        Rules:
          - Already crossed → never stop (free passage through intersection)
          - Green signal    → never stop
          - Red/yellow + not yet crossed → stop before the stop line
        """
        if self.has_crossed:
            return False
        if is_green:
            return False
        return True   # red or yellow AND haven't crossed → must stop

    def gap_to_vehicle_ahead(self, others):
        """
        Returns bumper-to-bumper gap (px) to the nearest vehicle directly ahead.
        'Ahead' means in the direction of travel (smaller travel for dir=-1, larger for dir=+1).
        Returns None if no vehicle is close ahead.
        """
        best = None
        for o in others:
            if o is self or o.lane != self.lane:
                continue
            if self.dir == -1:
                # self moving toward smaller values; other is ahead if o.travel < self.travel
                # gap = self front edge minus other back edge
                # self front (lowest point) = self.travel - CAR_LEN//2
                # other back  (highest point) = o.travel + CAR_LEN//2
                gap = (self.travel - CAR_LEN // 2) - (o.travel + CAR_LEN // 2)
            else:
                # self moving toward larger values; other is ahead if o.travel > self.travel
                # self front (highest point) = self.travel + CAR_LEN//2
                # other back  (lowest point) = o.travel - CAR_LEN//2
                gap = (o.travel - CAR_LEN // 2) - (self.travel + CAR_LEN // 2)
            if 0 < gap < 350:
                best = gap if best is None else min(best, gap)
        return best

    def move(self, is_green, others):
        self.update_crossed(is_green)

        if self.should_stop(is_green):
            # Approach and hold at stop line.
            # The FRONT BUMPER must not cross stop_coord.
            # So vehicle centre (self.travel) must stay at stop_coord ± (CAR_LEN//2 + margin).
            MARGIN = 6
            if self.dir == -1:
                # Travelling north (decreasing travel).
                # Front bumper = self.travel - CAR_LEN//2 must stay >= stop_coord.
                # So self.travel must stay >= stop_coord + CAR_LEN//2.
                hold = self.stop_coord + CAR_LEN // 2 + MARGIN
                if self.travel > hold + 0.5:
                    gap = self.gap_to_vehicle_ahead(others)
                    if gap is None or gap > MIN_GAP:
                        self.travel = max(hold, self.travel - self.speed)
            else:
                # Travelling south (increasing travel).
                # Front bumper = self.travel + CAR_LEN//2 must stay <= stop_coord.
                hold = self.stop_coord - CAR_LEN // 2 - MARGIN
                if self.travel < hold - 0.5:
                    gap = self.gap_to_vehicle_ahead(others)
                    if gap is None or gap > MIN_GAP:
                        self.travel = min(hold, self.travel + self.speed)
            self._update_rect()
            return

        # Green or already crossed — move freely, respect gap to car ahead
        gap = self.gap_to_vehicle_ahead(others)
        if gap is not None and gap < MIN_GAP + CAR_LEN * 0.6:
            factor = max(0.0, gap / (MIN_GAP + CAR_LEN * 0.6))
            move_speed = self.speed * factor
        else:
            move_speed = self.speed

        self.travel += self.dir * move_speed
        self._update_rect()

    def is_offscreen(self):
        if self.dir == -1:
            return self.travel < self.exit_coord
        else:
            return self.travel > self.exit_coord

    def draw(self, surf):
        rx, ry, rw, rh = self.rect

        # Shadow
        shadow = pygame.Surface((rw + 4, rh + 4), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        surf.blit(shadow, (rx + 3, ry + 3))

        # Body
        pygame.draw.rect(surf, self.color, self.rect, border_radius=5)

        # Roof (smaller inner rectangle)
        roof_inset = 5
        if self.axis == 'y':
            roof = pygame.Rect(rx + roof_inset, ry + 10, rw - roof_inset*2, rh - 20)
        else:
            roof = pygame.Rect(rx + 10, ry + roof_inset, rw - 20, rh - roof_inset*2)
        pygame.draw.rect(surf, self.roof_color, roof, border_radius=3)

        # Windshield (lighter strip at front)
        ws_col = (200, 220, 255)
        if self.axis == 'y':
            if self.dir == -1:  # going north, front is top
                ws = pygame.Rect(rx + 4, ry + 3, rw - 8, 7)
            else:
                ws = pygame.Rect(rx + 4, ry + rh - 10, rw - 8, 7)
        else:
            if self.dir == -1:  # going west, front is left
                ws = pygame.Rect(rx + 3, ry + 4, 7, rh - 8)
            else:
                ws = pygame.Rect(rx + rw - 10, ry + 4, 7, rh - 8)
        pygame.draw.rect(surf, ws_col, ws, border_radius=2)

        # Headlights (front) and taillights (back)
        hl_col = (255, 255, 200)
        tl_col = (200, 30, 30)
        hl_sz  = 4
        if self.axis == 'y':
            if self.dir == -1:
                hl_y, tl_y = ry + 2, ry + rh - 2 - hl_sz
            else:
                hl_y, tl_y = ry + rh - 2 - hl_sz, ry + 2
            hl_x1, hl_x2 = rx + 3, rx + rw - 3 - hl_sz
            pygame.draw.rect(surf, hl_col, (hl_x1, hl_y, hl_sz, hl_sz))
            pygame.draw.rect(surf, hl_col, (hl_x2, hl_y, hl_sz, hl_sz))
            pygame.draw.rect(surf, tl_col, (hl_x1, tl_y, hl_sz, hl_sz))
            pygame.draw.rect(surf, tl_col, (hl_x2, tl_y, hl_sz, hl_sz))
        else:
            if self.dir == -1:
                hl_x, tl_x = rx + 2, rx + rw - 2 - hl_sz
            else:
                hl_x, tl_x = rx + rw - 2 - hl_sz, rx + 2
            hl_y1, hl_y2 = ry + 3, ry + rh - 3 - hl_sz
            pygame.draw.rect(surf, hl_col, (hl_x, hl_y1, hl_sz, hl_sz))
            pygame.draw.rect(surf, hl_col, (hl_x, hl_y2, hl_sz, hl_sz))
            pygame.draw.rect(surf, tl_col, (tl_x, hl_y1, hl_sz, hl_sz))
            pygame.draw.rect(surf, tl_col, (tl_x, hl_y2, hl_sz, hl_sz))

        # Emergency siren flash (alternating blue/red rectangle on roof)
        if self.is_emergency:
            t = time.time()
            siren_col = (0, 80, 255) if int(t * 4) % 2 == 0 else (255, 30, 30)
            if self.axis == 'y':
                siren = pygame.Rect(rx + rw//2 - 4, ry + rh//2 - 3, 8, 6)
            else:
                siren = pygame.Rect(rx + rw//2 - 3, ry + rh//2 - 4, 6, 8)
            pygame.draw.rect(surf, siren_col, siren, border_radius=2)

# ─────────────────────────────────────────────
#  SPAWN GUARD: ensure new vehicles don't overlap existing ones
# ─────────────────────────────────────────────
def safe_to_spawn(lane, vehicles):
    meta = LANE_META[lane]
    spawn = float(meta['spawn_coord'])
    for v in vehicles:
        if v.lane != lane:
            continue
        gap = abs(v.travel - spawn)
        if gap < CAR_LEN + MIN_GAP + 20:
            return False
    return True

# ─────────────────────────────────────────────
#  HUD PANEL
# ─────────────────────────────────────────────
def draw_hud(surf, counts, emergency, current_green, next_winner, elapsed, green_time, is_yellow):
    panel_w, panel_h = 225, 215
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 165))
    surf.blit(panel, (10, 10))

    title = font_big.render("SMART TRAFFIC", True, (80, 200, 255))
    surf.blit(title, (18, 16))
    sub = font_small.render("Management System", True, (160, 200, 160))
    surf.blit(sub, (18, 40))

    lane_names = {"Lane_1": "Lane 1 (N)", "Lane_2": "Lane 2 (W)",
                  "Lane_3": "Lane 3 (S)", "Lane_4": "Lane 4 (E)"}
    y = 62
    for lane in LANES:
        if lane == current_green and not is_yellow:
            col = C_LIGHT_GRN;  sym = "● GREEN "
        elif lane == current_green and is_yellow:
            col = C_LIGHT_YEL;  sym = "● YELLOW"
        else:
            col = (200, 60, 60); sym = "● RED   "

        em  = " 🚨" if emergency[lane] else ""
        lbl = f"{lane_names[lane]}: {counts[lane]:2d}{em}"
        surf.blit(font_small.render(sym, True, col),      (18, y))
        surf.blit(font_small.render(lbl, True, C_WHITE),  (92, y))
        y += 20

    # Progress bar
    bar_w        = panel_w - 20
    bar_x, bar_y = 18, y + 6
    pygame.draw.rect(surf, (55, 55, 55), (bar_x, bar_y, bar_w, 10), border_radius=4)
    fill    = int(bar_w * min(elapsed / green_time, 1.0))
    bar_col = C_LIGHT_YEL if is_yellow else C_LIGHT_GRN
    pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill, 10), border_radius=4)

    rem = max(0.0, green_time - elapsed)
    surf.blit(font_small.render(f"Phase: {rem:.1f}s", True, C_WHITE), (18, bar_y + 14))

# ─────────────────────────────────────────────
#  PHASE STATE MACHINE
#
#  States per phase:
#    GREEN_PHASE  → current_green lane is green, all others red
#    YELLOW_PHASE → current_green lane turns yellow (0.5 s), all others stay red
#                   vehicles treat yellow same as red (do not enter intersection)
#    (after yellow) → switch current_green to next_winner, restart
#
#  Emergency override:
#    If any RED lane contains an emergency vehicle that hasn't crossed yet,
#    ALL lanes immediately go red, that emergency lane goes green.
#    This overrides the normal phase timer instantly.
# ─────────────────────────────────────────────
LANES = ["Lane_1", "Lane_2", "Lane_3", "Lane_4"]

vehicles         = []
current_green    = "Lane_1"
FIXED_GREEN_TIME = 6.0      # seconds a lane stays green
YELLOW_DURATION  = 0.5      # seconds yellow is shown before switching
phase            = 'green'  # 'green' | 'yellow'
phase_start      = time.time()
next_winner      = "Lane_1"
emergency_override = False  # True while handling an emergency

SPAWN_RATE = 0.022

while True:
    clock.tick(FPS)
    now = time.time()

    # ── Events ──────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

    # ── Spawn ────────────────────────────────────────────────────────────
    if random.random() < SPAWN_RATE:
        lane = random.choice(LANES)
        if safe_to_spawn(lane, vehicles):
            vehicles.append(Vehicle(lane))

    # ── Count vehicles & detect emergency vehicles waiting at red ────────
    counts    = {l: 0     for l in LANES}
    emergency = {l: False for l in LANES}

    for v in vehicles:
        # Count only vehicles that are still waiting (haven't crossed yet)
        if not v.has_crossed:
            counts[v.lane] += 1
            if v.is_emergency:
                emergency[v.lane] = True

    # ── Emergency override check ─────────────────────────────────────────
    #    If any lane that is currently RED has an uncrossed emergency vehicle,
    #    immediately switch to that lane (all others red).
    em_lane = None
    for l in LANES:
        if l != current_green and emergency[l]:
            em_lane = l
            break

    if em_lane is not None and phase == 'green':
        # Trigger yellow on current_green first, then switch instantly
        phase       = 'yellow'
        phase_start = now
        next_winner = em_lane
        emergency_override = True

    # ── Phase state machine ──────────────────────────────────────────────
    elapsed = now - phase_start

    if phase == 'green':
        if elapsed >= FIXED_GREEN_TIME:
            # Time to switch — enter yellow phase
            phase       = 'yellow'
            phase_start = now
            # Decide next winner now
            waiting = {l: counts[l] for l in counts if l != current_green}
            # Check emergency in waiting lanes (non-current)
            em_next = None
            for l in LANES:
                if l != current_green and emergency[l]:
                    em_next = l
                    break
            if em_next:
                next_winner = em_next
            elif any(c > 0 for c in waiting.values()):
                next_winner = max(waiting, key=waiting.get)
            else:
                next_winner = LANES[(LANES.index(current_green) + 1) % 4]
            emergency_override = False

    elif phase == 'yellow':
        if elapsed >= YELLOW_DURATION:
            # Switch to next winner
            current_green      = next_winner
            phase              = 'green'
            phase_start        = now
            emergency_override = False
            if ser:
                idx = LANES.index(current_green)
                try:
                    ser.write(f"{idx}\n".encode())
                except:
                    pass

    # ── Build per-lane signal dict ───────────────────────────────────────
    #    green  → that lane's vehicles may go
    #    yellow → current_green is about to turn red (vehicles treat as red)
    #    red    → vehicles must stop
    signals = {}
    for l in LANES:
        if l == current_green:
            signals[l] = 'yellow' if phase == 'yellow' else 'green'
        else:
            signals[l] = 'red'

    # ── Which lanes are actually "go" for vehicle movement ───────────────
    #    Only green signal → vehicles may move freely past stop line.
    #    Yellow / red → vehicles must stop before the stop line.
    def lane_is_go(lane):
        return signals[lane] == 'green'

    # ── Move vehicles ────────────────────────────────────────────────────
    for v in vehicles:
        v.move(lane_is_go(v.lane), vehicles)

    # ── Remove off-screen ────────────────────────────────────────────────
    vehicles = [v for v in vehicles if not v.is_offscreen()]

    # ── Draw road ────────────────────────────────────────────────────────
    screen.blit(road_surf, (0, 0))

    # ── Draw vehicles ────────────────────────────────────────────────────
    for v in vehicles:
        v.draw(screen)

    # ── Draw traffic lights ───────────────────────────────────────────────
    for lane in LANES:
        draw_traffic_light(screen, lane, signals[lane])

    # ── Emergency flash overlay ───────────────────────────────────────────
    for lane in LANES:
        if emergency[lane] and signals[lane] != 'green':
            px, py, _ = TL_CONFIG[lane]
            if int(now * 4) % 2 == 0:
                em_surf = pygame.Surface((136, 24), pygame.SRCALPHA)
                em_surf.fill((220, 30, 30, 190))
                screen.blit(em_surf, (px - 68, py - 36))
                em_txt = font_small.render("⚡ EMERGENCY ⚡", True, C_WHITE)
                screen.blit(em_txt, (px - 64, py - 33))

    # ── HUD ──────────────────────────────────────────────────────────────
    # Recompute elapsed for HUD (green phase elapsed)
    hud_elapsed = now - phase_start if phase == 'green' else FIXED_GREEN_TIME
    hud_yellow  = (phase == 'yellow')
    draw_hud(screen, counts, emergency, current_green, next_winner,
             hud_elapsed, FIXED_GREEN_TIME, hud_yellow)

    pygame.display.flip()
