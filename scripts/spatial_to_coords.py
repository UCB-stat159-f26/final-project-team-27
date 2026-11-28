import pandas as pd
import json, math, re, time, requests

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

# prepare location data from each row, then query unique locations in batches
# keep row positions s.t. the coordinates still line up with the original data
# a lot of time spent on https://docs.python.org/3/library/re.html#special-characters

# expected output columns after processing
OUTPUT_COLUMNS = ["location_type", "normalized_location", "city", "latitude", "longitude"]

# Geocoder database for city of Berkeley 
GEOCODER = (
    "https://gis.cityofberkeley.info/arcgis3/rest/services/Geocode/"
    "Locator_StreetCenterline/GeocodeServer/findAddressCandidates"
)

### PUBLIC FUNCTION(S) ###
def convert_to_coords(data, min_score=90, batch_size=1000, max_workers=4):
    """
    Converts a raw dataset's spatial location information into normalized location text, classifies the location type,
    and provides approximate latitude and longitude coordinates in EPSG:4326 format.
    Keeps all rows; only text geocoding is restricted to the Berkeley city label.
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
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be an integer between 1 and 1000")
    if not isinstance(max_workers, int) or max_workers < 1:
        raise ValueError("max_workers must be a positive integer")

    df = prepare_df(data)

    rows = df.to_dict("records") # one dictionary for each input row
    texts = pd.Series([location_text(row) for row in rows], dtype="string").fillna("").tolist() # extract location text in row order
    parsed = {text : normalize_location(text) for text in dict.fromkeys(texts)} # classify each distinct text once

    # extract recognized text coordinates once per distinct location string
    embedded_pairs = {
        text: embedded_coordinate_pair(text)
        for text in parsed
        if parsed[text][1] == "coordinates"
    }

    # clean each distinct city, then put the names back in the original row order
    raw_cities = pd.Series([row.get("city") for row in rows], dtype="string").fillna("").tolist()
    city_names = {city : clean_string(city) for city in dict.fromkeys(raw_cities)}
    cities = [city_names[city] for city in raw_cities]

    # construct one query for each distinct location and city combination
    queries = {(text, city) : location_query(text, city) for text, city in dict.fromkeys(zip(texts, cities))}
    has_coords = {"latitude", "longitude"}.issubset(df.columns)

    # make list containing one dictionary with output columns per input row
    records, pending = [], {}
    for position, row in enumerate(rows):
        text, city = texts[position], cities[position]
        normalized, location_type = parsed[text] # reuse the result when location text is repeated
        pair = None
        if has_coords: # keep usable coordinates already supplied by the dataset
            pair = coordinate_pair(row.get("latitude"), row.get("longitude"))

        if pair is None and city == "BERKELEY":
            pair = embedded_pairs.get(text) # use text coordinates when supplied columns did not give a usable pair

        if pair is not None and location_type == "missing": location_type = "coordinates"

        records.append({
            "location_type": location_type,
            "normalized_location": normalized,
            "city": city,
            "latitude": pair[0] if pair is not None else None,
            "longitude": pair[1] if pair is not None else None,
        })

        if pair is None: # only query rows without a usable coordinate pair
            query, query_type = queries[(text, city)]
            if query: pending.setdefault((query, query_type), []).append(position)

    # group queries by location type s.t. each batch uses one geocoder category
    grouped = {}
    for query, location_type in pending:
        grouped.setdefault(location_type, []).append((query, location_type))
    # divide each group into batches of at most batch_size queries
    batches = [group[start:start + batch_size] for group in grouped.values() for start in range(0, len(group), batch_size)]

    if batches: # no requests needed when there are no supported queries
        with ThreadPoolExecutor(max_workers=min(max_workers, len(batches))) as executor:
            # start requests together and keep each submitted batch with its request
            futures = [(batch, executor.submit(fetch_candidates, [query for query, kind in batch], batch[0][1]),) for batch in batches]

            for batch, future in futures:
                for candidate in future.result():
                    # ResultID is the query position inside this batch; returned order can change
                    key = batch[candidate["attributes"]["ResultID"]]
                    pair = rank_select_coordinates([candidate], key[1], min_score) # check this query's selected result

                    if pair is not None:
                        for position in pending[key]: # fill every row that used this same query
                            records[position]["latitude"], records[position]["longitude"] = pair[0], pair[1]

    # keep every input row and its index, including rows without coordinates
    result = pd.DataFrame(records, index=data.index, columns=OUTPUT_COLUMNS)

    result[OUTPUT_COLUMNS[:3]] = (result[OUTPUT_COLUMNS[:3]].astype("string"))
    result[["latitude", "longitude"]] = (result[["latitude", "longitude"]].astype("Float64")) # allow missing coordinates

    return result

def rejected_mask(processed):
    """
    Returns: Boolean series where True means the row has no accepted coordinate pair.
    """
    return processed[["latitude", "longitude"]].isna().any(axis=1)

def rejected_rows(data, processed):
    """
    Returns: DataFrame containing the rejected original rows of the dataset. 
    """
    if len(data) != len(processed) or not data.index.equals(processed.index):
        raise ValueError("The input and processed rows are not aligned")
    mask = rejected_mask(processed)
    return data.iloc[mask.to_numpy()].copy() # select original rows by position


### HELPER FUNCTIONS ###
# check source data columns, clean
def prepare_df(data):
    """
    Normalizes column names in the data. 
    Returns: DataFrame
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    names = [re.sub(r"[\s_]+", "", str(column)).lower() for column in data.columns] # treat spaces and underscores the same

    if len(names) != len(set(names)): # two source columns cannot become the same normalized name
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
        return "" # do this before converting to text s.t. missing values do not become "NAN"
    return " ".join(str(value).upper().split())  

# block numbers
def block_number_string(value):
    match = re.fullmatch(r"([0-9]+)(?:\.0+)?", clean_string(value)) # allow block numbers imported as 1800.0
    return match.group(1) if match else ""
def location_text(row):
    """
    Extracts location text from a row. 
    Returns: location description :: string
    """
    if "locationtype" in row: # newer stop data uses separate fields for each location type
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

    if "blockaddress" in row: # cases and force use this name after column normalization
        return row.get("blockaddress")

    return row.get("locationdescription") # older stop data keeps the location in one text field

# normalize data
def normalize_location(value):
    """
    Normalizes raw string text into a common format and classifies the location type.
    Returns: tuple (normalized address :: string, location class :: string). 
    """
    text = clean_string(value)
    if not text: return "", "missing" # precaution check in case failed

    pair = embedded_coordinate_pair(text)
    if pair is not None:
        return f"{pair[0]};{pair[1]}", "coordinates" # keep just the coordinate pair in the normalized location

    # flagging "other" class for descriptions with proximity, freeways, obscured names
    review_pattern = ( # text patterns 
        r"\b(?:NEAR|BETWEEN|IFO|FWY|EXIT|RAMP)\b"
        r"|\bI-?\d+\b|[A-Z]00\b"
    )
    if re.search(review_pattern, text): return text, "other" 

    # remove supplementary wording only from descriptions starting with a number
    if re.match(r"^[0-9]+\s+", text):
        if re.search(r"\([^()]*\(", text):
            return text, "other" # nested parentheses remain for review

        text = re.sub(r"\([^()]*\)", " ", text) # remove complete annotations like (REAR)
        text = re.sub(r"\([^()]*$", " ", text) # remove an unclosed trailing annotation
        text = clean_string(text) # collapse whitespace left by the removed wording

    if re.search(r"[()]", text):
        return text, "other" # remaining parentheses mean the description is still unresolved

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
    # also, if the number ends in `00` (multiple of 100), address is treated as a block
    if desc != street or int(num) % 100 == 0: 
        return f"{num} BLOCK OF {street}", "block"

    return text, "address" # finally, all other pass as class "address"

# construct a text query only when the event city label is Berkeley
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
    except (TypeError, ValueError): return None
    if not (math.isfinite(latitude) and math.isfinite(longitude)): return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180): return None
    if (latitude, longitude) == (0, 0): return None

    return latitude, longitude # both values passed the numeric checks

def embedded_coordinate_pair(value):
    text = clean_string(value)

    # allow latitude;longitude, optionally preceded by an integer and whitespace
    match = re.fullmatch(
        r"(?:[0-9]+\s+)?([+-]?[0-9]+\.[0-9]+)\s*;\s*"
        r"([+-]?[0-9]+\.[0-9]+)",
        text,
    )
    if not match:
        return None

    # first number is latitude, second is longitude; apply the existing numeric checks
    return coordinate_pair(match.group(1), match.group(2))


### GEOCODER FETCHING TO MATCH COORDINATES AND ADDRESSES
def retry_delay(response, attempt):
    """
    Helper function for fetch_candidates(), delays attempts between querying geocoder
    """
    delay = 0.5 * 2 ** attempt # wait longer after each temporary request failure

    if response is None: return delay

    value = response.headers.get("Retry-After") # use the server's requested wait when supplied
    if not value: return delay

    try:
        seconds = float(value) # Retry-After can be a number of seconds
    except ValueError:
        try:
            deadline = parsedate_to_datetime(value) # or a date and time to wait until
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            seconds = (deadline - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return delay

    return max(delay, seconds) if math.isfinite(seconds) else delay # respect the longer wait

def fetch_candidates(queries, location_type):
    """
    Fetches one selected geocoder result per submitted query, including unmatched results.
    Follows documentation from Geocode Services https://developers.arcgis.com/rest/services-reference/enterprise/geocode-addresses/.
    Returns: list of geocoder locations :: List
    """
    if not queries: return []
    if len(queries) > 1000: raise ValueError("A batch cannot contain more than 1000 queries")

    # give each query its position within this batch as OBJECTID
    addresses = {"records": [
            {"attributes": {"OBJECTID": position, "SingleLine": query}}
            for position, query in enumerate(queries)
        ]
    }

    # request one location category per batch and coordinates in EPSG:4326
    parameters = {
        "addresses": json.dumps(addresses),
        "category": {"block": "Street Midblock", "intersection": "Intersection", "address": "Street Address"}[location_type],
        "outSR": 4326, "outFields": "Status,Addr_type,City", "f": "json"}

    url = GEOCODER.rsplit("/", 1)[0] + "/geocodeAddresses"
    temporary_statuses = {403, 408, 429, 500, 502, 503, 504}

    with requests.Session() as session: # each concurrent batch uses its own session
        for attempt in range(3): # stop after three unsuccessful attempts
            response = None

            try:
                response = session.post(url, data=parameters, headers={"User-Agent": "STAT259-final-project-team-27-spatial-fn"}, timeout=(10, 60))
                response.raise_for_status() # raise when the HTTP request failed
                payload = response.json()

                if not isinstance(payload, dict): raise ValueError("Expected a geocoder response dictionary")

            except requests.HTTPError as error:
                if (
                    error.response is None
                    or error.response.status_code not in temporary_statuses
                    or attempt == 2
                ):
                    raise

            except (requests.Timeout, requests.ConnectionError, ValueError):
                if attempt == 2: raise

            else:
                if "error" not in payload: break # successful HTTP responses can still contain an API error

                error = payload["error"]
                status = error.get("code") if isinstance(error, dict) else None

                if status not in temporary_statuses or attempt == 2: raise RuntimeError(error)

            time.sleep(retry_delay(response, attempt)) # only wait after a temporary failure

    locations = payload["locations"]
    if not isinstance(locations, list):
        raise ValueError("Expected a list of batch locations")

    ids = [record["attributes"]["ResultID"] for record in locations] # returned OBJECTIDs identify the submitted queries

    # every submitted query must have exactly one result with a valid ID
    if (
        any(type(identity) is not int for identity in ids)
        or len(ids) != len(set(ids))
        or set(ids) != set(range(len(queries)))
    ):
        raise ValueError("Batch result IDs do not match the submitted queries")

    if any(record.get("location") for record in locations): # check the returned coordinate system
        reference = payload.get("spatialReference", {})
        outSR = reference.get("latestWkid", reference.get("wkid"))

        if outSR != 4326:
            raise ValueError("Wrong geocoder coordinate system")

    return locations

def rank_select_coordinates(candidates, location_type, min_score=90):
    """
    Checks selected batch results against the location type, city, coordinates, and score rules.
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
        status = attributes["Status"]
        if status == "U": continue # the request succeeded but this query had no match
        # M is matched; T keeps the geocoder's selected point among tied matches
        if status not in {"M", "T"}: raise ValueError(f"Unkown batch match status: {status}")

        point = candidate.get("location") or {}
        pair = coordinate_pair(point.get("y"), point.get("x")) # geocoder y is latitude, x is longitude
        score = float(candidate["score"])

        if (
            pair is not None
            and attributes.get("Addr_type") in location_types
            and clean_string(attributes.get("City")) == "BERKELEY"
            and math.isfinite(score)
            and score >= min_score
        ):
            matches.append((score, pair))

    if not matches: return None # leave coordinates missing when no result passes all checks

    return max(matches, key=lambda match: match[0])[1] # return the pair from the highest-scoring accepted result

