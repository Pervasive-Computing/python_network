import datetime


def calc_cost(light_levels, delta_time):
    
    print(delta_time)
    count1 = 0
    count0 = 0
    for level in light_levels.values():
        if level == 1.0:
            count1 += 1
        elif level < 1.0:
            count0 += 1

    print(count1, count0)
    
    return [delta_time, count1, count0]