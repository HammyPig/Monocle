"""Stock data utilities for financial analysis."""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.ticker import MaxNLocator
from numba import jit


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


def lump_sum_return_ratio_distribution(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    days: int,
) -> pd.Series:
    """
    Calculate the lump sum return ratio distribution between two series.

    For each day in the series, calculates the forward return ratio (column1/column2)
    over the specified number of days. This creates a distribution of return ratios
    showing the probability of outperformance. A ratio > 1.0 means column1
    outperformed column2 over that timeframe.

    Args:
        df: DataFrame that contains column1 and column2 as columns
        column1: First column name (numerator in ratio)
        column2: Second column name (denominator in ratio)
        days: Number of days to look forward

    Returns:
        Series with the lump sum return ratio distribution. Each value represents
        the ratio of forward returns (column1/column2) for a given starting date.
        A ratio > 1.0 means column1 outperformed column2 over that timeframe.
    """
    forward1 = df[column1].shift(-days) / df[column1]
    forward2 = df[column2].shift(-days) / df[column2]

    return forward1 / forward2


def lump_sum_return_ratio_distributions_by_timeframe(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    timeframes: list[int],
    trading_days_per_year: int = 252,
) -> dict[int, pd.Series]:
    """
    Calculate lump sum return ratio distributions for multiple timeframes.

    For each timeframe in years, calculates the lump sum return ratio distribution
    between two columns. Returns a dictionary with years as keys and lump sum return
    ratio distribution series as values.

    Args:
        df: DataFrame that contains column1 and column2 as columns
        column1: First column name (numerator in ratio)
        column2: Second column name (denominator in ratio)
        timeframes: List of timeframes in years (e.g., [1, 3, 5, 10, 20])
        trading_days_per_year: Number of trading days per year (default: 252)

    Returns:
        Dictionary with years as keys and lump sum return ratio distribution
        Series as values. Each Series contains the distribution of return ratios
        (column1/column2) for that timeframe. A ratio > 1.0 means column1
        outperformed column2 over that timeframe.
    """
    results = {}
    for years in timeframes:
        days = trading_days_per_year * years
        results[years] = lump_sum_return_ratio_distribution(df, column1, column2, days)
    return results


def dca_return_ratio_distribution(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    days: int,
    buy_period: int = 20,
) -> pd.Series:
    """
    Calculate the DCA (Dollar Cost Averaging) return ratio distribution between two series.

    For each possible starting date, calculates the DCA return ratio (column1/column2)
    over the specified number of days. DCA returns are calculated by averaging
    purchase prices at regular intervals (buy_period) and comparing to the starting price.
    This creates a distribution of return ratios showing the probability of outperformance.
    A ratio > 1.0 means column1 outperformed column2 over that timeframe.

    Args:
        df: DataFrame that contains column1 and column2 as columns
        column1: First column name (numerator in ratio)
        column2: Second column name (denominator in ratio)
        days: Number of days to look forward
        buy_period: Number of trading days between purchases (default: 20)

    Returns:
        Series with the DCA return ratio distribution. Each value represents
        the ratio of DCA returns (column1/column2) for a given starting date.
        A ratio > 1.0 means column1 outperformed column2 over that timeframe.
    """
    n = len(df) - days + 1
    ratios = np.zeros(n)

    series1 = df[column1].values
    series2 = df[column2].values

    for i in range(n):
        # Get prices at buy_period intervals within the timeframe
        end_idx = i + days
        buy_indices = np.arange(i, end_idx, buy_period)

        if len(buy_indices) == 0:
            ratios[i] = np.nan
            continue

        # Calculate mean purchase price for each series
        buy_prices1 = series1[buy_indices]
        buy_prices2 = series2[buy_indices]

        mean_price1 = buy_prices1.mean()
        mean_price2 = buy_prices2.mean()

        # Starting prices
        start_price1 = series1[i]
        start_price2 = series2[i]

        # DCA return = mean purchase price / starting price
        dca_return1 = mean_price1 / start_price1
        dca_return2 = mean_price2 / start_price2

        # Return ratio
        ratios[i] = dca_return1 / dca_return2

    # Create Series with same index as original DataFrame (for first n values)
    result_index = df.index[:n] if n > 0 else df.index[:0]
    return pd.Series(ratios, index=result_index)


def dca_return_ratio_distributions_by_timeframe(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    timeframes: list[int],
    buy_period: int = 20,
    trading_days_per_year: int = 252,
) -> dict[int, pd.Series]:
    """
    Calculate DCA return ratio distributions for multiple timeframes.

    For each timeframe in years, calculates the DCA return ratio distribution
    between two columns. Returns a dictionary with years as keys and DCA return
    ratio distribution series as values.

    Args:
        df: DataFrame that contains column1 and column2 as columns
        column1: First column name (numerator in ratio)
        column2: Second column name (denominator in ratio)
        timeframes: List of timeframes in years (e.g., [1, 3, 5, 10, 20])
        buy_period: Number of trading days between purchases (default: 20)
        trading_days_per_year: Number of trading days per year (default: 252)

    Returns:
        Dictionary with years as keys and DCA return ratio distribution
        Series as values. Each Series contains the distribution of return ratios
        (column1/column2) for that timeframe. A ratio > 1.0 means column1
        outperformed column2 over that timeframe.
    """
    results = {}
    for years in timeframes:
        days = trading_days_per_year * years
        results[years] = dca_return_ratio_distribution(
            df, column1, column2, days, buy_period
        )
    return results


def plot_comparison(
    df: pd.DataFrame,
    columns: list[str],
    labels: list[str] = None,
    title: str = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Create a comparison plot of multiple series from a DataFrame.

    Args:
        df: DataFrame containing the series to plot
        columns: List of column names to plot
        labels: Optional list of labels for the legend (defaults to column names)
        title: Optional title for the plot

    Returns:
        Tuple containing the figure and axes objects
    """
    if labels is None or len(labels) != len(columns):
        labels = columns

    fig, ax = plt.subplots(figsize=(10, 5))

    for col, label in zip(columns, labels):
        ax.plot(df[col], label=label)

    # Set log scale
    ax.set_yscale("log")
    # Fix log scale tick frequency
    ax.yaxis.set_major_locator(MaxNLocator(steps=[1, 2, 5, 10]))

    # Format as percentage
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{100 * x:.0f}%"))

    ax.set_xlabel("Date", fontsize=12, fontweight="bold")
    ax.set_ylabel("Total Return (Log Scale)", fontsize=12, fontweight="bold")
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend()

    plt.tight_layout()

    return fig, ax


def plot_percentile_comparison(
    results: dict[int, pd.Series],
    column1_label: str,
    column2_label: str,
    percentiles: list[int] = None,
    figsize: tuple = (16, 6),
    show: bool = True,
) -> tuple[plt.Figure, list[plt.Axes]]:
    """
    Create a side-by-side percentile comparison plot showing both ratio and inverse ratio.

    Creates two subplots: one showing column1/column2 percentiles, and another showing
    column2/column1 (inverse) percentiles. Each plot shows filled bands for different
    percentile ranges and a median line. Bands are automatically created from symmetric
    percentile pairs around the median.

    Args:
        results: Dictionary with timeframes (years) as keys and return ratio Series as values.
                 Output from lump_sum_return_ratio_distributions_by_timeframe.
        column1_label: Label for the first column (numerator in ratio)
        column2_label: Label for the second column (denominator in ratio)
        percentiles: List of percentiles to plot (default: [1, 5, 10, 25, 50, 75, 90, 95, 99]).
                     Must include 50 for median line. Bands are created from symmetric pairs.
        figsize: Figure size tuple (width, height)
        show: Whether to display the plot immediately (default: True). If False, returns fig and axes.

    Returns:
        Tuple containing the figure and list of axes objects. If show=True, displays the plot.
    """
    timeframes = list(results.keys())
    timeframes.sort()  # Ensure timeframes are sorted

    if percentiles is None:
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]

    # Find symmetric percentile pairs around the median (50th percentile)
    # and create bands with decreasing opacity from outer to inner
    percentile_pairs = []
    if 50 in percentiles:
        # Get percentiles below and above 50
        below_50 = sorted([p for p in percentiles if p < 50], reverse=True)
        above_50 = sorted([p for p in percentiles if p > 50])

        # Create symmetric pairs
        for i, (low, high) in enumerate(zip(below_50, above_50)):
            if 100 - high == low:  # Only create symmetric pairs
                percentile_pairs.append((low, high))

        # Sort pairs by width (outermost first)
        percentile_pairs.sort(key=lambda x: x[1] - x[0], reverse=True)

    # Calculate opacity for each band (decreasing from outer to inner)
    num_bands = len(percentile_pairs)
    if num_bands > 0:
        # Opacity range: 0.15 (outermost) to 0.35 (innermost)
        opacity_step = (0.35 - 0.15) / max(1, num_bands - 1) if num_bands > 1 else 0
        band_opacities = [0.15 + i * opacity_step for i in range(num_bands)]
    else:
        band_opacities = []

    # Calculate percentile values for each timeframe (column1/column2)
    percentile_data = []
    for timeframe in timeframes:
        ratio = results[timeframe].dropna()
        percentile_values = [ratio.quantile(p / 100) for p in percentiles]
        percentile_data.append(percentile_values)

    # Convert to DataFrame for easier plotting (column1/column2)
    percentile_df = pd.DataFrame(
        percentile_data,
        index=[f"{t}y" for t in timeframes],
        columns=[f"{p}th" for p in percentiles],
    )

    # Calculate percentile values for inverse ratio (column2/column1)
    percentile_data_inverse = []
    for timeframe in timeframes:
        ratio = results[timeframe].dropna()
        inverse_ratio = 1 / ratio  # column2/column1 = 1 / (column1/column2)
        percentile_values = [inverse_ratio.quantile(p / 100) for p in percentiles]
        percentile_data_inverse.append(percentile_values)

    # Convert to DataFrame for inverse ratio (column2/column1)
    percentile_df_inverse = pd.DataFrame(
        percentile_data_inverse,
        index=[f"{t}y" for t in timeframes],
        columns=[f"{p}th" for p in percentiles],
    )

    # Create plot with side-by-side subplots
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    x_positions = range(len(timeframes))

    # Left plot: column1/column2
    ax_left = axes[0]

    # Plot filled bands for column1/column2 (gray) - automatically from percentile pairs
    for (low_p, high_p), opacity in zip(percentile_pairs, band_opacities):
        low_col = f"{low_p}th"
        high_col = f"{high_p}th"
        if low_col in percentile_df.columns and high_col in percentile_df.columns:
            ax_left.fill_between(
                x_positions,
                percentile_df[low_col],
                percentile_df[high_col],
                alpha=opacity,
                color="gray",
                label=f"{low_p}th-{high_p}th percentile",
            )

    # Plot median line for column1/column2 (if 50th percentile exists)
    if "50th" in percentile_df.columns:
        ax_left.plot(
            x_positions,
            percentile_df["50th"],
            marker="o",
            linewidth=2.5,
            markersize=8,
            color="blue",
            label="Median (50th percentile)",
            zorder=5,
        )

    # Set x-axis labels
    ax_left.set_xticks(x_positions)
    ax_left.set_xticklabels([f"{t}y" for t in timeframes])

    # Add reference line at ratio = 1.0
    ax_left.axhline(
        y=1.0,
        color="red",
        linestyle="dashed",
        linewidth=1.5,
        label="Equal performance",
        alpha=0.7,
        zorder=4,
    )

    ax_left.set_xlabel("Timeframe", fontsize=12)
    ax_left.set_ylabel("Return Ratio", fontsize=12)
    ax_left.set_title(
        f"{column1_label} / {column2_label} Percentiles",
        fontsize=14,
        fontweight="bold",
    )
    ax_left.legend()
    ax_left.grid(True, alpha=0.3)

    # Set log scale
    ax_left.set_yscale("log")
    ax_left.yaxis.set_major_locator(MaxNLocator())
    ax_left.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax_left.yaxis.set_minor_locator(ticker.NullLocator())

    # Right plot: column2/column1
    ax_right = axes[1]

    # Plot filled bands for column2/column1 (orange) - automatically from percentile pairs
    for (low_p, high_p), opacity in zip(percentile_pairs, band_opacities):
        low_col = f"{low_p}th"
        high_col = f"{high_p}th"
        if (
            low_col in percentile_df_inverse.columns
            and high_col in percentile_df_inverse.columns
        ):
            ax_right.fill_between(
                x_positions,
                percentile_df_inverse[low_col],
                percentile_df_inverse[high_col],
                alpha=opacity,
                color="orange",
                label=f"{low_p}th-{high_p}th percentile",
            )

    # Plot median line for column2/column1 (if 50th percentile exists)
    if "50th" in percentile_df_inverse.columns:
        ax_right.plot(
            x_positions,
            percentile_df_inverse["50th"],
            marker="s",
            linewidth=2.5,
            markersize=8,
            color="red",
            label="Median (50th percentile)",
            zorder=5,
        )

    # Set x-axis labels
    ax_right.set_xticks(x_positions)
    ax_right.set_xticklabels([f"{t}y" for t in timeframes])

    # Add reference line at ratio = 1.0
    ax_right.axhline(
        y=1.0,
        color="red",
        linestyle="dashed",
        linewidth=1.5,
        label="Equal performance",
        alpha=0.7,
        zorder=4,
    )

    ax_right.set_xlabel("Timeframe", fontsize=12)
    ax_right.set_ylabel("Return Ratio", fontsize=12)
    ax_right.set_title(
        f"{column2_label} / {column1_label} Percentiles",
        fontsize=14,
        fontweight="bold",
    )
    ax_right.legend()
    ax_right.grid(True, alpha=0.3)

    # Set log scale
    ax_right.set_yscale("log")
    ax_right.yaxis.set_major_locator(MaxNLocator())
    ax_right.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax_right.yaxis.set_minor_locator(ticker.NullLocator())

    plt.tight_layout()

    if show:
        plt.show()

    return fig, axes


@jit(nopython=True)
def lump_sum_with_withdrawals(
    pct_change: np.ndarray,
    n_days: int,
    withdrawal_period: int,
    withdrawal_amount: float,
) -> np.ndarray:
    """
    Simulate portfolio returns with periodic withdrawals over n_days.

    For each possible starting date, calculates the final portfolio value
    after applying periodic withdrawals. If the portfolio depletes to zero,
    it remains at zero.

    Args:
        pct_change: Array of period-over-period returns (1 + pct_change)
        n_days: Number of days to simulate
        withdrawal_period: Days between withdrawals
        withdrawal_amount: Fixed amount to withdraw each period

    Returns:
        Array of final portfolio values for each starting date
    """
    # Calculate possible timeframes given total time and n_days
    n = len(pct_change) - n_days + 1
    results = np.zeros(n)

    # For each possible starting date
    for i in range(n):
        # Calculate the return with withdrawals
        cumprod = 1.0
        for j in range(i, i + n_days):
            cumprod *= pct_change[j]

            # Apply withdrawal at regular intervals
            if j % withdrawal_period == 0:
                cumprod -= withdrawal_amount
                if cumprod <= 0:
                    cumprod = 0.0
                    break

        results[i] = cumprod

    return results


def lump_sum_with_withdrawals_distribution(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    withdrawal_pcts: list[float],
    withdrawal_period: int = 20,
    retirement_years: int = 10,
    trading_days_per_year: int = 252,
) -> pd.DataFrame:
    """
    Calculate retirement feasibility by testing different withdrawal rates.

    For each withdrawal rate, simulates portfolio performance with periodic withdrawals
    over the retirement period and calculates the success probability (ending value > initial value).

    Args:
        df: DataFrame containing the two series to compare
        column1: First column name
        column2: Second column name
        withdrawal_period: Days between withdrawals (default: 20, ~monthly)
        retirement_years: Number of years to simulate (default: 10)
        trading_days_per_year: Number of trading days per year (default: 252)

    Returns:
        DataFrame with columns: withdrawal_pct, column1_label, column2_label
        Each row contains the withdrawal rate and success probabilities for both series.
    """
    results = []

    # Prepare return series (convert to 1 + pct_change format)
    series1 = df[column1].pct_change(fill_method=None) + 1
    series1.iloc[0] = 1.0
    series1 = np.array(series1)

    series2 = df[column2].pct_change(fill_method=None) + 1
    series2.iloc[0] = 1.0
    series2 = np.array(series2)

    # Calculate success probability for each withdrawal rate
    for withdrawal_pct in withdrawal_pcts:
        # Convert annual withdrawal rate to per-period amount
        # withdrawal_pct is annual rate, so per-period = annual / periods_per_year
        withdrawal_amount = withdrawal_pct / (trading_days_per_year / withdrawal_period)

        # Simulate retirement periods
        result1 = lump_sum_with_withdrawals(
            series1,
            retirement_years * trading_days_per_year,
            withdrawal_period,
            withdrawal_amount,
        )

        result2 = lump_sum_with_withdrawals(
            series2,
            retirement_years * trading_days_per_year,
            withdrawal_period,
            withdrawal_amount,
        )

        # Calculate success probability (ending value > initial value = 1.0)
        success_prob1 = (result1 > 1.0).sum() / len(result1)
        success_prob2 = (result2 > 1.0).sum() / len(result2)

        results.append(
            {
                "withdrawal_pct": withdrawal_pct,
                column1: success_prob1,
                column2: success_prob2,
            }
        )

    return pd.DataFrame(results)


def _forward_transform_stretch_near_one(
    y: np.ndarray, power: float = 3.0
) -> np.ndarray:
    """
    Transform that stretches values near 1.
    Uses: y_transformed = 1 - (1-y)^(1/power)
    This makes small differences near 1 become larger visual differences.

    Args:
        y: Array of values in [0, 1]
        power: Power parameter controlling stretch amount (higher = more stretching)

    Returns:
        Transformed array
    """
    y = np.clip(y, 0, 1)
    # Avoid division by zero and handle edge cases
    result = np.where(y == 1, 1.0, 1 - np.power(1 - y, 1 / power))
    return result


def _inverse_transform_stretch_near_one(
    y_transformed: np.ndarray, power: float = 3.0
) -> np.ndarray:
    """
    Inverse transformation for stretch_near_one.
    Uses: y = 1 - (1-y_transformed)^power

    Args:
        y_transformed: Array of transformed values in [0, 1]
        power: Power parameter (must match forward transform)

    Returns:
        Original array values
    """
    y_transformed = np.clip(y_transformed, 0, 1)
    result = np.where(y_transformed == 1, 1.0, 1 - np.power(1 - y_transformed, power))
    return result


def plot_retirement_feasibility(
    retirement_df: pd.DataFrame,
    columns: list[str] = None,
    labels: list[str] = None,
    title: str = "Retirement Feasibility: Probability of Maintaining Portfolio Value Over 20 Years",
    xlabel: str = "Annual Withdrawal Rate",
    ylabel: str = "Probability of Successful Retirement",
    thresholds: dict[float, dict] = None,
    figsize: tuple = (10, 5),
    power: float = 3.0,
    invert_xaxis: bool = True,
    show: bool = True,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot retirement feasibility with probability of success on a y-axis that stretches near 1.

    The y-axis uses a custom transformation that increases visual spacing as values
    approach 1, making it easier to distinguish high-probability scenarios.

    Args:
        retirement_df: DataFrame with 'withdrawal_pct' column and probability columns
        columns: List of column names to plot (defaults to all columns except 'withdrawal_pct')
        labels: Optional list of labels for the legend (defaults to column names)
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        thresholds: Dictionary mapping threshold values to styling dicts.
                   Example: {0.99: {'color': 'green', 'linestyle': '--', 'label': '99% Threshold'}}
                   Defaults to 0.99, 0.95, and 0.90 thresholds.
        figsize: Figure size tuple (width, height)
        power: Power parameter for y-axis transformation (higher = more stretching near 1)
        invert_xaxis: Whether to invert the x-axis (default: True)
        show: Whether to display the plot immediately (default: True)

    Returns:
        Tuple containing the figure and axes objects
    """
    # Default columns (all except withdrawal_pct)
    if columns is None:
        columns = [col for col in retirement_df.columns if col != "withdrawal_pct"]

    if labels is None:
        labels = columns

    if len(labels) != len(columns):
        labels = columns

    # Default thresholds
    if thresholds is None:
        thresholds = {
            0.99: {
                "color": "green",
                "linestyle": "--",
                "alpha": 0.5,
                "label": "99% Success Threshold",
            },
            0.95: {
                "color": "orange",
                "linestyle": "--",
                "alpha": 0.5,
                "label": "95% Success Threshold",
            },
            0.90: {
                "color": "red",
                "linestyle": ":",
                "alpha": 0.5,
                "label": "90% Success Threshold",
            },
        }

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Plot each column
    markers = ["o", "s", "^", "v", "D", "p", "*", "h"]
    for i, (col, label) in enumerate(zip(columns, labels)):
        marker = markers[i % len(markers)]
        ax.plot(
            retirement_df["withdrawal_pct"],
            retirement_df[col],
            label=label,
            marker=marker,
            linewidth=2,
            markersize=6,
        )

    # Add threshold lines
    for threshold_value, style in thresholds.items():
        ax.axhline(y=threshold_value, linewidth=1, **style)

    # Set labels and title
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    if invert_xaxis:
        ax.invert_xaxis()

    # Apply the function scale - this stretches values near 1
    ax.set_yscale(
        "function",
        functions=(
            lambda y: _forward_transform_stretch_near_one(y, power),
            lambda y: _inverse_transform_stretch_near_one(y, power),
        ),
    )

    # Format y-axis as percentage
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.set_ylim(0, 1)

    plt.tight_layout()

    if show:
        plt.show()

    return fig, ax


def find_withdrawal_rates_by_threshold(
    retirement_df: pd.DataFrame,
    columns: list[str],
    column_labels: list[str] = None,
    thresholds: list[float] = None,
    withdrawal_pct_col: str = "withdrawal_pct",
) -> pd.DataFrame:
    """
    Find maximum withdrawal rates that achieve specified success probability thresholds.

    For each threshold, finds the highest withdrawal rate where each model/column
    achieves at least that success probability. Also calculates the advantage
    (difference in percentage points) between models.

    Args:
        retirement_df: DataFrame with withdrawal_pct column and probability columns
        columns: List of column names to analyze (probability columns)
        column_labels: Optional list of labels for columns (defaults to column names)
        thresholds: List of success probability thresholds (default: [0.99, 0.95, 0.90, 0.75, 0.50])
        withdrawal_pct_col: Name of the withdrawal percentage column (default: "withdrawal_pct")

    Returns:
        DataFrame with columns:
        - Success Threshold: The probability threshold
        - For each column: Max withdrawal rate achieving that threshold
        - For each pair: Advantage (difference in percentage points)
    """
    if thresholds is None:
        thresholds = [0.99, 0.95, 0.90, 0.75, 0.50]

    if column_labels is None:
        column_labels = columns

    if len(column_labels) != len(columns):
        column_labels = columns

    insights = []

    for threshold in thresholds:
        row_data = {"Success Threshold": f"{threshold:.0%}"}

        # Find max withdrawal rate for each column
        max_rates = {}
        for col, label in zip(columns, column_labels):
            above_threshold = retirement_df[retirement_df[col] >= threshold]
            max_rate = (
                above_threshold[withdrawal_pct_col].max()
                if len(above_threshold) > 0
                else None
            )
            max_rates[col] = max_rate
            row_data[f"{label} Max Withdrawal Rate"] = (
                f"{max_rate:.2%}" if max_rate is not None else "N/A"
            )

        # Calculate advantages between pairs
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                col1, label1 = columns[i], column_labels[i]
                col2, label2 = columns[j], column_labels[j]
                max1 = max_rates[col1]
                max2 = max_rates[col2]

                advantage_name = f"{label1} vs {label2} Advantage"
                if max1 is not None and max2 is not None:
                    advantage = (max1 - max2) * 100
                    row_data[advantage_name] = f"{advantage:.1f}pp"
                else:
                    row_data[advantage_name] = "N/A"

        insights.append(row_data)

    return pd.DataFrame(insights)


def comprehensive_comparison(
    df: pd.DataFrame,
    column1_label: str = None,
    column2_label: str = None,
    timeframes: list[int] = None,
    percentiles: list[int] = None,
    n_withdrawal_rates: int = 20,
    retirement_years: int = 10,
    withdrawal_period: int = 20,
    trading_days_per_year: int = 252,
    show: bool = True,
) -> None:
    """
    Perform a comprehensive comparison between two columns with 3 plots and 1 table.

    This function performs a complete analysis comparing two investment strategies:
    1. Creates 3 plots:
       - Basic comparison plot
       - Lump sum percentile comparison
       - DCA percentile comparison
       - Retirement feasibility plot
    2. Displays withdrawal rate insights table

    Args:
        df: DataFrame containing exactly two columns to compare
        column1_label: Optional label for first column (defaults to column name)
        column2_label: Optional label for second column (defaults to column name)
        timeframes: List of timeframes in years (default: [1, 3, 5, 10, 20])
        percentiles: List of percentiles for percentile plots (default: [1, 5, 10, 25, 50, 75, 90, 95, 99])
        n_withdrawal_rates: Number of withdrawal rates to test (default: 20)
        retirement_years: Number of years for retirement simulation (default: 10)
        withdrawal_period: Days between withdrawals (default: 20)
        trading_days_per_year: Number of trading days per year (default: 252)
        show: Whether to display plots immediately (default: True)
    """
    # Drop rows with any NaN values
    df = df.dropna(how="any")

    df = rebase_dataframe(df)

    # Get the two column names
    if len(df.columns) != 2:
        raise ValueError(
            f"DataFrame must have exactly 2 columns, got {len(df.columns)}"
        )

    column1, column2 = df.columns[0], df.columns[1]

    # Set defaults
    if timeframes is None:
        timeframes = [1, 3, 5, 10, 20]
    if percentiles is None:
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    if column1_label is None:
        column1_label = column1
    if column2_label is None:
        column2_label = column2

    # Calculate withdrawal rates (same pattern as notebook)
    withdrawal_pcts = np.zeros(n_withdrawal_rates)
    x = 0.2
    for i in range(n_withdrawal_rates):
        withdrawal_pcts[i] = x
        x /= 1.2

    # Calculate the 3 results
    lump_sum_results = lump_sum_return_ratio_distributions_by_timeframe(
        df, column1, column2, timeframes, trading_days_per_year
    )
    dca_results = dca_return_ratio_distributions_by_timeframe(
        df,
        column1,
        column2,
        timeframes,
        buy_period=withdrawal_period,
        trading_days_per_year=trading_days_per_year,
    )
    retirement_results = lump_sum_with_withdrawals_distribution(
        df,
        column1,
        column2,
        withdrawal_pcts,
        withdrawal_period=withdrawal_period,
        retirement_years=retirement_years,
        trading_days_per_year=trading_days_per_year,
    )

    # Calculate insights
    insights = find_withdrawal_rates_by_threshold(
        retirement_results,
        columns=[column1, column2],
        column_labels=[column1_label, column2_label],
    )

    # Create the plots
    # Plot 1: Basic comparison
    plot_comparison(
        df,
        [column1, column2],
        labels=[column1_label, column2_label],
        title=f"{column1_label} vs {column2_label}",
    )
    if show:
        plt.show()

    # Plot 2: Lump sum percentile comparison
    plot_percentile_comparison(
        lump_sum_results,
        column1_label,
        column2_label,
        percentiles=percentiles,
        show=show,
    )

    # Plot 3: DCA percentile comparison
    plot_percentile_comparison(
        dca_results, column1_label, column2_label, percentiles=percentiles, show=show
    )

    # Plot 4: Retirement feasibility
    plot_retirement_feasibility(
        retirement_results,
        columns=[column1, column2],
        labels=[column1_label, column2_label],
        show=show,
    )

    # Display insights table at the end
    if show:
        try:
            from IPython.display import display

            print("\nWithdrawal Rate Insights by Success Threshold:")
            display(insights)
        except ImportError:
            # Fallback for non-Jupyter environments
            print("\nWithdrawal Rate Insights by Success Threshold:")
            print(insights.to_string(index=False))
            print()
