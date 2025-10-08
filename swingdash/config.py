# -----------------------------
# Config
# -----------------------------
KEY_METRICS = [
    "Club Speed", "Ball Speed", "Smash Factor",
    "Launch Angle", "Spin Rate", "Apex Height",
    "Carry Distance", "Total Distance",
    "Carry Deviation Distance", "Total Deviation Distance",
    "Attack Angle", "Club Path", "Club Face", "Face to Path", "Spin Axis"
]

BETTER_DIRECTION = {
    "Club Speed": +1,
    "Ball Speed": +1,
    "Smash Factor": +1,
    "Launch Angle": 0,
    "Spin Rate": 0,
    "Apex Height": 0,
    "Carry Distance": +1,
    "Total Distance": +1,
    "Carry Deviation Distance": -1,
    "Total Deviation Distance": -1,
    "Attack Angle": 0,
    "Club Path": 0,
    "Club Face": 0,
    "Face to Path": 0,
    "Spin Axis": 0,
}

CANDIDATE_NUMERIC = [
    "Club Speed", "Attack Angle", "Club Path", "Club Face", "Face to Path",
    "Ball Speed", "Smash Factor", "Launch Angle", "Launch Direction",
    "Backspin", "Sidespin", "Spin Rate", "Spin Rate Type", "Spin Axis",
    "Apex Height", "Carry Distance", "Carry Deviation Angle",
    "Carry Deviation Distance", "Total Distance", "Total Deviation Angle",
    "Total Deviation Distance", "Air Density", "Temperature", "Air Pressure",
    "Relative Humidity"
]

UNIT_PATTERNS = [
    r"mph", r"km/h", r"kph", r"m/s", r"rpm",
    r"°", r"deg", r"degrees?",
    r"yds?", r"yards?", r"m", r"cm",
    r"kPa", r"Pa", r"bar", r"psi",
    r"%", r","
]
