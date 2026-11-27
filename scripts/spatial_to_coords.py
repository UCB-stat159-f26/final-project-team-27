import pandas as pd
import json, math, re, time, requests

from datetime import datetime, timezone

# plan is to have all the functions only work one row at a time
# s.t. it reduces chance of encountering an error
# a lot of time spent on https://docs.python.org/3/library/re.html#special-characters

# expected output columns after processing
OUTPUT_COLUMNS = ["location_type", "normalized_location", "city", "latitude", "longitude"]

# check source data columns, clean
def prepare_df(data):
    """
    Normalizes column names in the data. 
    Returns: DataFrame
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    names = [re.sub(r"[\s_]+", "", str(column)).lower() for column in data.columns]

    if len(names) != len(set(names)):
        raise ValueError("Source columns become ambiguous after normalization")

    df = data.copy(deep=False)
    df.columns = names

    return df

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
def block_number_string(value):
    match = re.fullmatch(r"([0-9]+)(?:\.0+)?", clean_string(value))
    return match.group(1) if match else ""
def location_text(row):
    """
    Extracts location text from a row. 
    Returns: location description :: string
    """
    if "locationtype" in row:
        location_type = clean_string(row.get("locationtype"))

        if location_type  == "BLKNUMBER":
            number = block_number_string(row.get("blocknumber"))
            street = clean_string(row.get("streetname"))
            return f"{number} BLOCK OF {street}" if number and street else ""

        if location_type == "INTERSECTION":
            first = clean_string(row.get("crossstreet1"))
            second = clean_string(row.get("crossstreet2"))
            return f"{first} & {second}" if first and second else ""

        if location_type == "HIGHWAYANDEXIT":
            highway = clean_string(row.get("highway"))
            exit_name = clean_string(row.get("closestexit"))
            return f"HIGHWAY {highway} EXIT {exit_name}" if highway or exit_name else ""

        if location_type == "OTHER":
            return row.get("otherlocationdesc")

        return ""

    if "blockaddress" in row:
        return row.get("blockaddress")

    return row.get("locationdescription")

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
    if (latitude, longitude) == (0, 0): 
        return None

    return latitude, longitude

### 