import pandas as pd
import json, math, re, time, requests

from datetime import datetime, timezone

# plan is to have all the functions only work one row at a time
# s.t. it reduces chance of encountering an error
# a lot of time spent on https://docs.python.org/3/library/re.html#special-characters

# expected output columns after processing
OUTPUT_COLUMNS = ["location_type", "normalized_location", "city", "latitude", "longitude"]

# Geocoder database for city of Berkeley 
GEOCODER = (
    "https://gis.cityofberkeley.info/arcgis3/rest/services/Geocode/"
    "Locator_StreetCenterline/GeocodeServer/findAddressCandidates"
)

### PUBLIC FUNCTION(S) ###
def convert_to_coords(data, cache=None, min_score=90, pause=1.0):
    """
    Converts a raw dataset's spatial location information into normalized location text, constrains city to 
    only Berkeley, classify the location type, and provides approximate latitude and longitude coordinates in EPSG:4326 format. 
    Returns: 
        DataFrame with columns
            "location_type"::string, 
            "normalized_location"::string, 
            "city"::string, 
            "latitude"::float, 
            "longitude"::float
    """
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")
    if not math.isfinite(pause) or pause < 0:
        raise ValueError("pause must be a finite nonnegative number")

    df = prepare_df(data)

    if cache is None: cache = {}

    # make list containing one dictionary with output columns per input row
    records, pending = [], {}
    for position, row in enumerate(df.to_dict("records")):
        text = location_text(row)
        normalized, location_type = normalize_location(text)
        city = clean_string(row.get("city"))
        pair = coordinate_pair(row.get("latitude"), row.get("longitude"))

        if pair is not None and location_type == "missing": location_type = "coordinates"

        records.append({
            "location_type": location_type,
            "normalized_location": normalized,
            "city": city,
            "latitude": pair[0] if pair is not None else None,
            "longitude": pair[1] if pair is not None else None,
        })

        if pair is None:
            query, query_type = location_query(text, city)
            if query: pending.setdefault((query, query_type), []).append(position)

    # query the rows integer position, indepdnent of its index label
    # map unique query and location type to the positions needing that query 
    for (query, location_type), positions in pending.items():
        if query not in cache:
            cache[query] = fetch_candidates(query) # tracks the mapping of query strings to candidate lists
            time.sleep(pause)

        pair = rank_select_coordinates(cache[query], location_type, min_score)

        if pair is not None:
            for position in positions:
                records[position]["latitude"] = pair[0]
                records[position]["longitude"] = pair[1]

    result = pd.DataFrame(records, index=data.index, columns=OUTPUT_COLUMNS)

    result[OUTPUT_COLUMNS[:3]] = (result[OUTPUT_COLUMNS[:3]].astype("string"))
    result[["latitude", "longitude"]] = (result[["latitude", "longitude"]].astype("Float64"))

    return result

def rejected_mask(processed):
    """
    Returns: Boolean series where True means the row conversion failed for a dataset.
    """
    return processed[["latitude", "longitude"]].isna().any(axis=1)

def rejected_rows(data, processed):
    """
    Returns: DataFrame containing the rejected original rows of the dataset. 
    """
    if len(data) != len(processed) or not data.index.equals(processed.index):
        raise ValueError("The input and processed rows are not aligned")
    mask = rejected_mask(processed)
    return data.iloc[mask.to_numpy()].copy()


### HELPER FUNCTIONS ###
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

### GEOCODER FETCHING TO MATCH COORDINATES AND ADDRESSES
def fetch_candidates(query):
    """
    Fetches candidate locations given a address query. 
    Follows documentation from Geocode Services https://developers.arcgis.com/rest/services-reference/enterprise/find-address-candidates/.
    Returns: list of geocoder candidates :: List
    """
    response = requests.get(
        GEOCODER, 
        params={
        "SingleLine" : query, 
        "outSR" : 4326, 
        "outFields" : "Addr_type,City",
        "maxLocations" : 5,
        "f" : "json"
    }, 
    headers={"User-Agent" : "STAT259-final-project-team-27-spatial-fn"}, 
    timeout=30)
    response.raise_for_status()
    payload = response.json()

    # checking over the payload output from the response query
    if "error" in payload: raise RuntimeError(payload["error"])

    candidates = payload["candidates"] # returns a list 
    if not isinstance(candidates, list): raise ValueError("Expected list of geocoder candidates")

    if candidates: # if we got the candidates, need to check the geocoder json data to match coordinate system
        spatial_reference = payload.get("spatialReference", {})
        outSR = spatial_reference.get("latestWkid", spatial_reference.get("wkid"))
        if outSR != 4326: raise ValueError("Wrong geocoder coordinate system")
    return candidates

def rank_select_coordinates(candidates, location_type, min_score=90):
    """
    Given a list of candidate locations of a query, coordinates are selected according to a rank and score system. 
    The scores are calculated and provided by Geocoder's match score.
    Return: Coordinate pair :: (float, float) or None
    """
    # matching my location class names to Geocoder's JSON names
    location_types = {"block" : {"StreetMidBlock"}, 
                      "intersection" : {"StreetInt"}, 
                      "address" : {"PointAddress", "StreetAddress"}}[location_type]

    matches = []
    for candidate in candidates: 
        attributes = candidate["attributes"]
        point = candidate["location"]
        pair = coordinate_pair(point.get("y"), point.get("x"))
        score = float(candidate["score"])

        if (
            pair is not None
            and attributes.get("Addr_type") in location_types
            and clean_string(attributes.get("City")) == "BERKELEY"
            and math.isfinite(score)
            and score >= min_score
        ):
            matches.append((score, pair))

    if not matches: return None

    best_score = max(score for score, pair in matches)
    best_points = {pair for score, pair in matches if score == best_score}

    if len(best_points) != 1: return None
    return next(iter(best_points))

