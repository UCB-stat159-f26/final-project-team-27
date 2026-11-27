#' @title Get unique values from a column in the Stop Data dataset
#' @description Some of the columns in this dataset include multiple values in a single row, separated by a | character
#' @param df Dataframe containing data to be analyzed
#' @param col Character vector of length 1 containing name of the column to be analyzed
#' @return Character vector containing a list of unique values in the column
#' @examples
#' unique_stop_data_column(df_stop_data, "ForceActionsTaken")
unique_stop_data_column = function(df, col) {
    df |>
        filter(.data[[col]] != "None") |>
        dplyr::pull(.data[[col]]) |>
        stringr::str_split("\\|") |>
        unlist() |>
        stringr::str_trim() |> # strip whitespaces
        unique()
}