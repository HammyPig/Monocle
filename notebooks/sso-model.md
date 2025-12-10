---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.18.1
kernelspec:
  name: python3
  display_name: Python 3 (ipykernel)
  language: python
---

# SSO Leveraged ETF Model

This notebook models the performance of SSO (ProShares Ultra S&P500, a 2x leveraged ETF) by applying leverage to the S&P 500 Total Return index and accounting for realistic borrowing costs and fees.

## Setup

Import required libraries and configure plotting.

```{code-cell} ipython3
import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import pandas_datareader.data as web
from utils.stocks import apply_leverage, get_rebased_stocks, rebase_dataframe

%matplotlib inline
```

## Data Download

Download historical data for the S&P 500 Total Return index and SSO ETF, then rebase them to a common starting date for comparison. Also download the Federal Funds Rate (DFF) from FRED, which will be used to model the dynamic borrowing costs for leveraged positions.

```{code-cell} ipython3
df = get_rebased_stocks(["^SP500TR", "SSO"])
fed_funds = web.DataReader("DFF", "fred", start=df.index.min())
fed_funds = fed_funds["DFF"] / 100
```

## Baseline Comparison

Visualize the historical performance of the S&P 500 Total Return index and SSO on a logarithmic scale. SSO should approximately track 2x the daily returns of the S&P 500, minus fees.

```{code-cell} ipython3
fig, ax = plt.subplots()
ax.plot(df["^SP500TR"], label="SP500TR")
ax.plot(df["SSO"], label="SSO (SP500 x2)")
ax.set_yscale("log")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Return (Log Scale)")
ax.set_title("S&P 500 Total Return vs SSO")
ax.legend()
plt.show()
```

## Model Application

Apply the leverage model to the S&P 500 Total Return index with the following parameters:
- **Leverage**: 2x
- **Expense ratio**: 0.87% (SSO's annual expense ratio)
- **Borrowing multiplier**: 1.1 (10% markup on the risk-free rate)
- **Borrowing spread**: 0.5% (additional costs for counterparty risk and operational fees)

The model uses the Federal Funds Rate as the base interest rate, scaled to daily using 252 trading days per year.

```{code-cell} ipython3
df["SP500TR_x2"] = apply_leverage(
    df["^SP500TR"],
    leverage=2,
    interest_rate_series=fed_funds,
    expense_ratio=0.0087,
    borrowing_multiplier=1.1,
    borrowing_spread=0.005,
)

df = rebase_dataframe(df)
```

### Model Statistics

Calculate key statistics to quantify the model's accuracy.

```{code-cell} ipython3
ratio = df["SP500TR_x2"] / df["SSO"]
difference_pct = (df["SP500TR_x2"] - df["SSO"]) / df["SSO"] * 100

print("Model Performance Statistics:")
print(f"  Mean ratio (Model/Actual): {ratio.mean():.4f}")
print(f"  Std deviation of ratio: {ratio.std():.4f}")
print(f"  Mean absolute error: {abs(difference_pct).mean():.2f}%")
print(f"  Max over-prediction: {difference_pct.max():.2f}%")
print(f"  Max under-prediction: {difference_pct.min():.2f}%")
print(f"  Correlation coefficient: {df['SSO'].corr(df['SP500TR_x2']):.4f}")
```

## Model Validation

Compare the model's output to the actual SSO performance using multiple visualization approaches.

### Scatter Plot

A scatter plot of model vs actual values. Points along the diagonal line (y=x) indicate perfect agreement.

```{code-cell} ipython3
fig, ax = plt.subplots(figsize=(4, 4))
ax.scatter(df["SSO"], df["SP500TR_x2"], s=0.1, alpha=0.5)
# Add diagonal reference line
min_val = min(df["SSO"].min(), df["SP500TR_x2"].min())
max_val = max(df["SSO"].max(), df["SP500TR_x2"].max())
ax.plot([min_val, max_val], [min_val, max_val], "r--", label="Perfect match", linewidth=1)
ax.set_xlabel("SSO (Actual)")
ax.set_ylabel("SP500TR_x2 (Model)")
ax.set_title("Model vs Actual: Scatter Plot")
ax.legend()
plt.show()
```

### Model Accuracy Over Time

Visualize the percentage difference between model and actual values over time. A value of 0% indicates perfect agreement, with positive values showing where the model over-predicts and negative values showing under-prediction.

```{code-cell} ipython3
difference = (df["SP500TR_x2"] - df["SSO"]) / df["SSO"] * 100

fig, ax = plt.subplots()
ax.plot(difference, linewidth=0.8)
ax.axhline(y=0, color="r", linestyle="--", linewidth=1, label="Perfect match")
ax.set_xlabel("Date")
ax.set_ylabel("Percentage Difference (%)")
ax.set_title("Model Accuracy Over Time")
ax.legend()
ax.grid(True, alpha=0.3)
plt.show()
```

## Visual Comparison

Overlay the actual SSO performance with the model on a logarithmic scale. Because the model so closely matches SSO's performance, the two lines overlap and appear as one.

```{code-cell} ipython3
fig, ax = plt.subplots()
ax.plot(df["SSO"], label="SSO (Actual)")
ax.plot(df["SP500TR_x2"], label="SP500TR_x2 (Model)")
ax.set_yscale("log")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Return (Log Scale)")
ax.set_title("Model vs Actual: Overlay Comparison")
ax.legend(loc="upper left")
plt.show()
```
