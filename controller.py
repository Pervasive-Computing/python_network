import numpy as np
import datetime
from datetime import time
import time as t

#define a python function that takes a certain JSON form as input, {'date': int}:
def is_time_between(target, time_start, time_end):
    # If the end time is less than the start time, it means the interval wraps around midnight
    if time_end < time_start:
        # If the target time is greater than the start time, it's between start and midnight
        # Or if the target time is less than the end time, it's between midnight and end
        return target >= time_start or target <= time_end
    else:
        # If the interval doesn't wrap around midnight, it's a simple comparison
        return time_start <= target <= time_end

def get_time():
    return datetime.datetime.now()


class lightController():
    def __init__(self):
        pass

    def parse_json(self, json_inp):
        expected_format = {'date': datetime.datetime, 
                        'sunset_time': time,
                        'sunrise_time': time,
                        'lux_number': float,
                        'current_level': float,
                        'sensor_input': bool,
                        }
                            
        for key, expected_item in expected_format.items():
            if key not in json_inp:
                print(json_inp)
                raise ValueError("Key not in expected format: " + key)
            if not isinstance(json_inp[key], expected_item):
                raise TypeError("Value not in expected format: " + key)

        date = json_inp['date']
        sunset_time = json_inp['sunset_time']
        sunrise_time = json_inp['sunrise_time']
        light_level = json_inp['lux_number']
        current_level = json_inp['current_level']
        sensor_input = json_inp['sensor_input']

        return date, sunset_time, sunrise_time, light_level, current_level, sensor_input    

    def control(self, json_obj, last_change):
        # if(last_change > 0)
        # res = self.make_light_decision(json_obj)
        # return res
        
        try: 
            date, sunset_time, sunrise_time, light_level, current_level, sensor_input = self.parse_json(json_obj)
        except ValueError as e:
            print("Value error: ", e)
            return 0.0, 0
        except TypeError as e:
            print("Typerror: ", e)
            return 0.0, 0

        if(last_change > 0 and current_level > 0.5):
            return current_level, (last_change - 1)

        
        if(not is_time_between(date.time(), sunset_time, sunrise_time)):
            print("Time is not bewteen sunset and sunrise. No light required")
            return 0.0, 0
        
        if sensor_input:
            return 1.0, 60
        

        return 0.5, 0
    