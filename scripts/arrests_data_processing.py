import pandas as pd

INPUT_DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S%z"
OUTPUT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"
START = pd.Timestamp("2021-03-01", tz="America/Los_Angeles")
END_EXCLUSIVE = pd.Timestamp("2026-05-01", tz="America/Los_Angeles")

def preprocess_arrests(data):
    occurred = pd.to_datetime(
        data["Occurred_Datetime"],
        format=INPUT_DATETIME_FORMAT,
        errors="coerce",
        utc=True
    ).dt.tz_convert("America/Los_Angeles")

    city = data["City"].astype("string").str.strip().str.upper()
    keep = (city.eq("BERKELEY") & occurred.ge(START) & occurred.lt(END_EXCLUSIVE))

    cleaned = data.loc[keep].copy()

    cleaned["Occurred_Datetime"] = (occurred.loc[keep].dt.strftime(OUTPUT_DATETIME_FORMAT))
    return cleaned

def main():
    PATH_TO_DATA = "data/raw/"
    PATH_TO_OUTPUT = "data/clean/arrests_data.csv"
    
    raw_data = pd.read_csv(PATH_TO_DATA + "arrests_2016_current.csv", 
                           dtype="string", keep_default_na=False, na_values="")

    process_data = preprocess_arrests(raw_data)
    process_data.to_csv(PATH_TO_OUTPUT, index=False)

if __name__ == "__main__":
    main()