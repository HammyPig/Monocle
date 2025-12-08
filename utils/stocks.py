"""Stock data utilities for financial analysis."""

import pandas as pd
import yfinance as yf


def ffill_between(series: pd.Series) -> pd.Series:
    """
    Forward fill NaN values only between first and last valid data points.

    Unlike ffill(), this preserves leading and trailing NaNs, only filling
    gaps between the first and last valid values.

    Args:
        series: Series with potential NaN values

    Returns:
        Series with NaNs filled only between first and last valid values
    """
    first_valid = series.first_valid_index()
    last_valid = series.last_valid_index()

    if first_valid is None or last_valid is None:
        return series

    # Forward fill only between first and last valid indices
    result = series.copy()
    result.loc[first_valid:last_valid] = result.loc[first_valid:last_valid].ffill()
    return result


def series_to_cumulative_returns(series: pd.Series) -> pd.Series:
    """
    Convert a price series to cumulative returns.

    Steps:
    1. Forward fill missing values (only between first and last valid values)
    2. Drop remaining NaN values
    3. Divide by first value to normalize to 1.0

    Args:
        series: Price series to normalize

    Returns:
        Series with cumulative returns, starting at 1.0
    """
    series = ffill_between(series).dropna()
    first_value = series.iloc[0]
    return series / first_value


def rebase_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rebase DataFrame columns to a common starting date.

    Each column is first normalized to cumulative returns, then all columns
    are scaled to start at 1.0 on the latest common starting date.

    Args:
        df: DataFrame with datetime index and numeric columns

    Returns:
        DataFrame with all columns rebased to common starting date
    """
    result = df.copy()

    # Normalize each column to cumulative returns
    for column in result.columns:
        result[column] = series_to_cumulative_returns(result[column])

    # Find the latest start date (common starting point)
    rebase_date = result.apply(lambda x: x.first_valid_index()).max()

    # Scale stocks based on latest start date (vectorized)
    rebase_values = result.loc[rebase_date]
    result = result / rebase_values

    return result


def download_yf_stocks(tickers, period="max", auto_adjust=False):
    """
    Download stock data from Yahoo Finance.

    Args:
        tickers: Single ticker string or list of ticker strings
        period: Period to download (default: "max")
        auto_adjust: Whether to auto-adjust prices (default: False)

    Returns:
        MultiIndex DataFrame with columns grouped by ticker
    """
    return yf.download(
        tickers, period=period, group_by="ticker", auto_adjust=auto_adjust
    )


def extract_yf_adj_close(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Adj Close column from yfinance MultiIndex DataFrame.

    Args:
        df: MultiIndex DataFrame from yfinance download

    Returns:
        DataFrame with Adj Close columns only
    """
    return df.xs("Adj Close", axis=1, level=1)


def get_rebased_stocks(tickers, period="max", auto_adjust=False):
    """
    Download stocks from Yahoo Finance and rebase for comparison.

    Pipeline:
    1. Download stock data from Yahoo Finance
    2. Extract Adj Close prices
    3. Rebase all stocks to common starting date

    Args:
        tickers: Single ticker string or list of ticker strings
        period: Period to download (default: "max")
        auto_adjust: Whether to auto-adjust prices (default: False)

    Returns:
        DataFrame with rebased stock prices, ready for comparison
    """
    df = download_yf_stocks(tickers, period=period, auto_adjust=auto_adjust)
    df = extract_yf_adj_close(df)
    df = rebase_dataframe(df)
    return df
