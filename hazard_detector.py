# ============================================================
# SMART VISION - HAZARD DETECTION MODULE
# ============================================================

HAZARD_OBJECTS = {
    "car": "Vehicle",
    "truck": "Vehicle",
    "bus": "Vehicle",
    "motorcycle": "Vehicle"
}


def check_hazard(object_name, position):

    if object_name in HAZARD_OBJECTS:

        if position == "left":
            return "Warning! Vehicle on your left"

        elif position == "right":
            return "Warning! Vehicle on your right"

        else:
            return "Warning! Vehicle ahead"

    return None