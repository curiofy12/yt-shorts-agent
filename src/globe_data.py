"""
Shared lists for the "Every Second on Earth" (globe) style: the map views
the camera can fly to, and the icons that can pop onto the map.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ICONS_DIR

# name: (longitude, latitude, zoom). zoom 1 = whole map height on screen.
REGIONS = {
    "world":          (15, 15, 1.0),
    "world_west":     (-75, 15, 1.0),
    "north_america":  (-100, 45, 1.7),
    "usa":            (-97, 39, 2.6),
    "south_america":  (-60, -18, 1.8),
    "europe":         (12, 50, 2.6),
    "africa":         (20, 3, 1.6),
    "middle_east":    (45, 27, 2.8),
    "russia":         (90, 60, 1.9),
    "asia":           (95, 32, 1.6),
    "india":          (79, 22, 3.0),
    "china":          (105, 35, 2.5),
    "japan":          (138, 37, 4.0),
    "southeast_asia": (110, 5, 2.5),
    "australia":      (134, -25, 2.4),
    "arctic":         (-40, 72, 2.2),
    "antarctica":     (40, -75, 1.8),
    "atlantic":       (-35, 20, 1.6),
    "pacific":        (-160, 5, 1.4),
    "indian_ocean":   (75, -15, 1.7),
    "space":          (0, 0, 1.0),   # starry sky instead of the map
}

# Icons that belong in the water rather than on land
SEA_ICONS = {"fish", "whale", "shark", "turtle", "ship", "wave", "water_drop", "plastic_bottle", "oil_barrel_sea"}


def icon_names():
    if not os.path.isdir(ICONS_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(ICONS_DIR) if f.endswith(".webp"))
