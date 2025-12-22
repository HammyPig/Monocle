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


def apply_leverage(
    series: pd.Series,
    leverage: float,
    interest_rate_series: pd.Series,
    expense_ratio: float = 0.0,
    borrowing_multiplier: float = 1.0,
    borrowing_spread: float = 0.0,
) -> pd.Series:
    """
    Apply leverage multiplier to a series (prices or cumulative returns).

    Leverage multiplies the period returns by the leverage factor.
    Fees are calculated from an interest-rate series (scaled to daily using 252
    trading days per year), plus an expense ratio, borrowing multiplier, and spread.

    Args:
        series: Price series or cumulative returns series.
        leverage: Leverage multiplier (e.g., 2 for 2x leverage).
        interest_rate_series: Series of annualized interest rates (as decimals),
                              aligned to the series index. Required.
        expense_ratio: Annual expense ratio as decimal (e.g., 0.0087 for 0.87%).
                       Default 0.0.
        borrowing_multiplier: Multiplier applied to the interest rate
                              (e.g., 1.1 for a 10% markup). Default 1.0.
        borrowing_spread: Annual spread added to the interest rate (e.g., 0.01 for 1%).
                          Default 0.0.

    Returns:
        Series with leveraged returns, starting at 1.0.
    """
    # Convert to period returns
    returns = series.pct_change(fill_method=None)

    # Align interest rates to returns index
    aligned_rates = interest_rate_series.reindex(returns.index, method="ffill")

    # Use 252 trading days per year
    trading_days_per_year = 252

    # Effective annual rate includes multiplier and spread
    effective_rate = (aligned_rates * borrowing_multiplier) + borrowing_spread
    borrowing_cost = (leverage - 1) * effective_rate / trading_days_per_year
    expense_cost = expense_ratio / trading_days_per_year
    fee = borrowing_cost + expense_cost

    # Apply leverage to returns and subtract fee
    leveraged_returns = returns * leverage - fee

    # Convert back to cumulative returns
    result = (leveraged_returns + 1).cumprod()

    # Set the value immediately before the first valid index to 1.0
    first_valid_index = result.first_valid_index()
    if first_valid_index is not None:
        first_valid_position = result.index.get_loc(first_valid_index)

        if first_valid_position > 0:
            prev_idx = result.index[first_valid_position - 1]
            result.loc[prev_idx] = 1.0

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


def apply_expense_ratio(series: pd.Series, expense_ratio: float) -> pd.Series:
    """
    Apply expense ratio to a price series (for non-leveraged ETFs).

    Subtracts the annual expense ratio on a daily basis (252 trading days per year)
    from the period returns.

    Args:
        series: Price series or cumulative returns series
        expense_ratio: Annual expense ratio as decimal (e.g., 0.0003 for 0.03%)

    Returns:
        Series with expense ratio applied, starting at 1.0
    """
    returns = series.pct_change(fill_method=None)
    trading_days_per_year = 252
    daily_fee = expense_ratio / trading_days_per_year

    adjusted_returns = returns - daily_fee
    result = (adjusted_returns + 1).cumprod()
    result.iloc[0] = 1.0

    return result


def forward_return_ratio(
    df: pd.DataFrame, column1: str, column2: str, days: int
) -> pd.Series:
    """
    Calculate a time series of the ratio of forward returns between two columns in a DataFrame.

    Forward returns on any given day shows the performance after x days if invested on that day.
    The time series then is a distribution of forward returns that shows the probability of
    performance. A ratio > 1.0 means column1 outperformed column2.

    Args:
        df: DataFrame that contains column1 and column2 as columns
        column1: First column name
        column2: Second column name
        days: Number of days to look forward

    Returns:
        Series with the forward return ratio.
    """
    df = df[[column1, column2]].copy()
    df = df.dropna()
    df = rebase_dataframe(df)
    forward1 = df[column1].shift(-days) / df[column1]
    forward2 = df[column2].shift(-days) / df[column2]
    return_ratio = forward1 / forward2
    return_ratio = return_ratio.dropna()

    return return_ratio

    return return_ratio
