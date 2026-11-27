def unique_stop_data_column(df, col):
    """
    Get unique values from a column in the Stop Data dataset.

    Some of the columns in this dataset include multiple values in a single row, separated by a | character.

    Args:
        df (pandas DataFrame): Dataframe containing data to be analyzed.
        col (str): Name of the column to be analyzed.

    Returns:
        list[str]: List of unique values in the column.

    Example:
        unique_stop_data_column(df_stop_data, "NonForceActionsTaken")
    """
    col_all = list(df[col])
    col_all = [x for x in col_all if x == x] # strip nans

    col_split = []
    for i in col_all:
        current = i.split("|")
        col_split.extend(current)
    col_split = [i.lstrip() for i in col_split] # strip whitespaces
    col_unique = list(set(col_split))

    return(col_unique)