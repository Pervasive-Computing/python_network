import datetime
from datetime import time as t
from loguru import logger

#define a python function that takes a certain JSON form as input, {'date': int}:
def is_time_between(target, time_start, time_end):
    # If the end time is less than the start time, it means the interval wraps around midnight

    if time_end < time_start:
        # If the target time is greater than the start time, it's between start and midnight
        # Or if the target time is less than the end time, it's between midnight and end
        return target >= time_start or target <= time_end
    else:
        # If the interval doesn't wrap around midnight, it's a simple comparison
        print("Checkpoint3")
        return time_start <= target <= time_end



class lightController():
    def __init__(self, timeout_time):
        self.timeout_time = timeout_time
        self.logic_time = t(22,00)

    def parse_json(self, json_inp):
        expected_format = {'date': datetime.datetime, 
                        'sunset_time': t,
                        'sunrise_time': t,
                        'lux_number': float,
                        'current_level': float,
                        'sensor_input': bool,
                        }     
        for key, expected_item in expected_format.items():
            if key not in json_inp:
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
        early_evening_logic = True

        try: 
            date, sunset_time, sunrise_time, light_level, current_level, sensor_input = self.parse_json(json_obj)
        except ValueError as e:
            print("Value error: ", e)
            return 0.0, 0
        except TypeError as e:
            print("Typerror: ", e)
            return 0.0, 0

        if(last_change > 0 and current_level > 0.5):
            if sensor_input:
                return 1.0, self.timeout_time
            return current_level, (last_change - 1)


        if(not is_time_between(date.time(), sunset_time, sunrise_time)):
            logger.warning("Time is not bewteen sunset and sunrise. No light required")
            # print("Time is not bewteen sunset and sunrise. No light required")
            return 0.0, 0
        
        #Early time logic
        if(self.logic_time > sunset_time):
            early_evening_logic = False
        elif is_time_between(date.time(), sunset_time, self.logic_time):
            early_evening_logic = True
        else:
            early_evening_logic = False


        if sensor_input:
            return 1.0, self.timeout_time  

        return (0.5, 0) if early_evening_logic else (0.0, 0)
    