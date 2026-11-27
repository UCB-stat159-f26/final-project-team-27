import pandas as pd
import json, math, re, time, requests

from datetime import datetime, timezone

# plan is to have all the functions only work one row at a time
# s.t. it reduces chance of encountering an error

# clean individual strings
def clean_string(value):
    """
    Remove whitespace and drop missing data in a string.
    Return: string 
    """
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().split())  

# block numbers


# get data


# normalize data


# construct query for geocoder


# fetch  coordinates


# check valid coordinates and return coordinate pair
def coordinate_pair(latitude, longitude):
    """
    Checks and returns coordinate as a pair. 
    Return: tuple (latitude::float, longitude::float).
    """
    try: 
        latitude, longitude = float(latitude), float(longitude)
    except (TypeError, ValueError): 
        return None

    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    if not (latitude, longitude) == (0, 0): 
        return None

    return latitude, longitude


