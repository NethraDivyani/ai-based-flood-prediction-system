from datetime import timedelta

STATIONS = ["Norwood", "Kithulgala", "Holombuwa", "Deraniyagala", "Glencourse", "Hanwella"]

def next_day(date_value):
    return date_value + timedelta(days=1)

