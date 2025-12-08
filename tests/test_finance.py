"""Tests for finance utility functions."""

import pandas as pd

from utils.stocks import ffill_between, rebase_dataframe, series_to_cumulative_returns


class TestFfillBetween:
    """Tests for ffill_between function."""

    def test_ffill_between_basic(self):
        """Test basic forward fill between valid values."""
        series = pd.Series([None, 1, None, None, 2, None, None])
        result = ffill_between(series)
        expected = pd.Series([None, 1, 1, 1, 2, None, None])
        pd.testing.assert_series_equal(result, expected)

    def test_ffill_between_preserves_leading_nans(self):
        """Test that leading NaNs are preserved."""
        series = pd.Series([None, None, 1, None, 2])
        result = ffill_between(series)
        expected = pd.Series([None, None, 1, 1, 2])
        pd.testing.assert_series_equal(result, expected)

    def test_ffill_between_preserves_trailing_nans(self):
        """Test that trailing NaNs are preserved."""
        series = pd.Series([1, None, 2, None, None])
        result = ffill_between(series)
        expected = pd.Series([1, 1, 2, None, None])
        pd.testing.assert_series_equal(result, expected)

    def test_ffill_between_no_nans(self):
        """Test with no NaNs - should return unchanged."""
        series = pd.Series([1, 2, 3, 4])
        result = ffill_between(series)
        pd.testing.assert_series_equal(result, series)

    def test_ffill_between_all_nans(self):
        """Test with all NaNs - should return unchanged."""
        series = pd.Series([None, None, None])
        result = ffill_between(series)
        pd.testing.assert_series_equal(result, series)

    def test_ffill_between_does_not_modify_original(self):
        """Test that original series is not modified."""
        series = pd.Series([None, 1, None, 2, None])
        original = series.copy()
        ffill_between(series)
        pd.testing.assert_series_equal(series, original)


class TestSeriesToCumulativeReturns:
    """Tests for series_to_cumulative_returns function."""

    def test_series_to_cumulative_returns_basic(self):
        """Test basic conversion to cumulative returns."""
        series = pd.Series([100, 200, 400])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1.0, 2.0, 4.0])
        pd.testing.assert_series_equal(result, expected)

    def test_series_to_cumulative_returns_different_starting_price(self):
        """Test that normalization works regardless of starting price."""
        series = pd.Series([50, 100, 200])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1.0, 2.0, 4.0])
        pd.testing.assert_series_equal(result, expected)

    def test_series_to_cumulative_returns_with_nans(self):
        """Test with NaNs that should be filled."""
        series = pd.Series([100, None, None, 200, 400])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1.0, 1.0, 1.0, 2.0, 4.0])
        pd.testing.assert_series_equal(result, expected)

    def test_series_to_cumulative_returns_negative_returns(self):
        """Test with negative returns."""
        series = pd.Series([100, 50, 25])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1.0, 0.5, 0.25])
        pd.testing.assert_series_equal(result, expected)

    def test_series_to_cumulative_returns_zero_change(self):
        """Test with no price changes."""
        series = pd.Series([100, 100, 100])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1.0, 1.0, 1.0])
        pd.testing.assert_series_equal(result, expected)

    def test_series_to_cumulative_returns_does_not_modify_original(self):
        """Test that original series is not modified."""
        series = pd.Series([100, 200, 400])
        original = series.copy()
        series_to_cumulative_returns(series)
        pd.testing.assert_series_equal(series, original)

    def test_series_to_cumulative_returns_realistic_stock_data(self):
        """Test with realistic stock price pattern."""
        series = pd.Series([100, 105, 102, 108])
        result = series_to_cumulative_returns(series)
        expected = pd.Series([1, 1.05, 1.02, 1.08])
        pd.testing.assert_series_equal(result, expected)


class TestRebaseDataframe:
    """Tests for rebase_dataframe function."""

    def test_rebase_dataframe_basic(self):
        """Test basic rebase with columns starting at same date."""
        df = pd.DataFrame(
            {"A": [100, 200, 400], "B": [200, 400, 800], "C": [50, 100, 200]}
        )
        result = rebase_dataframe(df)
        expected = pd.DataFrame(
            {"A": [1.0, 2.0, 4.0], "B": [1.0, 2.0, 4.0], "C": [1.0, 2.0, 4.0]}
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_rebase_dataframe_different_start_dates(self):
        """Test rebase when columns start at different dates."""
        df = pd.DataFrame(
            {
                "A": [None, 100, 200, 400],
                "B": [200, 400, 800, None],
                "C": [50, 100, 200, 400],
            }
        )
        result = rebase_dataframe(df)
        expected = pd.DataFrame(
            {
                "A": [None, 1.0, 2.0, 4.0],
                "B": [0.5, 1.0, 2.0, None],
                "C": [0.5, 1.0, 2.0, 4.0],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_rebase_dataframe_with_nans(self):
        """Test rebase with NaNs in columns."""
        df = pd.DataFrame(
            {"A": [100, None, None, 200, 400], "B": [200, 400, None, 800, None]}
        )
        result = rebase_dataframe(df)
        expected = pd.DataFrame(
            {"A": [1.0, 1.0, 1.0, 2.0, 4.0], "B": [1.0, 2.0, 2.0, 4.0, None]}
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_rebase_dataframe_single_column(self):
        """Test rebase with single column."""
        df = pd.DataFrame({"A": [100, 200, 400]})
        result = rebase_dataframe(df)
        expected = pd.Series([1.0, 2.0, 4.0], name="A")
        pd.testing.assert_series_equal(result["A"], expected)

    def test_rebase_dataframe_does_not_modify_original(self):
        """Test that original DataFrame is not modified."""
        df = pd.DataFrame({"A": [100, 200, 400], "B": [200, 400, 800]})
        original = df.copy()
        rebase_dataframe(df)
        pd.testing.assert_frame_equal(df, original)

    def test_rebase_dataframe_different_returns(self):
        """Test rebase with columns having different returns."""
        df = pd.DataFrame(
            {
                "A": [100, 200, 400],
                "B": [100, 400, 1600],
                "C": [100, 800, 6400],
            }
        )
        result = rebase_dataframe(df)
        expected = pd.DataFrame(
            {
                "A": [1.0, 2.0, 4.0],
                "B": [1.0, 4.0, 16.0],
                "C": [1.0, 8.0, 64.0],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_rebase_dataframe_different_returns_and_start_dates(self):
        """Test rebase with columns having different returns and start dates."""
        df = pd.DataFrame(
            {
                "A": [None, 100, 200, 400],
                "B": [200, 400, 1600, None],
                "C": [50, 100, 400, 3200],
            }
        )
        result = rebase_dataframe(df)
        expected = pd.DataFrame(
            {
                "A": [None, 1.0, 2.0, 4.0],
                "B": [0.5, 1.0, 4.0, None],
                "C": [0.5, 1.0, 4.0, 32.0],
            }
        )
        pd.testing.assert_frame_equal(result, expected)
