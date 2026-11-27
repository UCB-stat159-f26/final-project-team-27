import pandas as pd
import json, math, re, time, requests

from datetime import datetime, timezone

# plan is to have all the functions only work one row at a time
# s.t. it reduces chance of encountering an error
# a lot of time spent on https://docs.python.org/3/library/re.html#special-characters

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
def normalize_location(value):
    """
    Normalizes raw string text into a common format and classifies the location type.
    Returns: tuple (normalized address :: string, location class :: string). 
    """
    text = clean_string(value)
    if not text: return "", "missing" # precaution check in case failed

    # flagging "other" class for descriptions with proximity, freeways, obscured names
    review_pattern = ( # text patterns 
        r"[()]|\b(?:NEAR|BETWEEN|IFO|FWY|EXIT|RAMP)\b"
        r"|\bI-?\d+\b|[A-Z]00\b"
    )
    if re.search(review_pattern, text): return text, "other" 

    # flagging "intersection" class
    parts = re.split(r"\s*(?:&|/|\bAND\b)\s*", text)
    if len(parts) > 1:
        if len(parts) == 2 and all(re.search(r"[A-Z]", part) for part in parts):
            return " & ".join(parts), "intersection"
        return text, "other"

    # flagging "address" class with numbers leading 
    match = re.fullmatch(r"([0-9]+)\s+(.+)", text) # check if numbers lead the string fully
    if not match: return text, "other"

    num, desc = match.groups()

    # now we can flag "block" class 
    block_prefix = r"^(?:(?:BLOCK|BLK)\b(?:\s+OF\b)?\s*)+"
    street = re.sub(block_prefix, "", desc).strip()
    if not street or not re.search(r"[A-Z]", street): return text, "other"
    # any changed description means there was an explicit block wording present
    # also, if there was was leading `00` (multiple of 100), address is treated as a block
    if desc != street or int(num) % 100 == 0: 
        return f"{num} BLOCK OF {street}", "block"

    return text, "address" # finally, all other pass as class "address"

# construct query for geocoder, also checks if the address is within Berkeley only
def location_query(text, city):
    """
    Constructs location query address to be sent to the geocoder.
    Returns: tuple (location :: string, location class :: string)
    """
    norm_text, text_class = normalize_location(text)
    if clean_string(city) == "BERKELEY" and text_class in {"block", "intersection", "address"}:
        return f"{norm_text}, BERKELEY, CA", text_class
    return "", text_class # otherwise, return empty string to be checked later

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

