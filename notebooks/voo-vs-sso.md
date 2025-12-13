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

# VOO vs SSO Analysis

This notebook compares the VOO ETF model (1x S&P 500 with expense ratio) against the SSO leveraged ETF model (2x S&P 500 with leverage and fees) across different timeframes.

## Setup

Import required libraries and configure plotting.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import pandas as pd
import pandas_datareader.data as web
from utils.stocks import (
    apply_expense_ratio,
    apply_leverage,
    forward_return_ratio,
    get_rebased_stocks,
)

%matplotlib inline
```

## Data Download

Download historical data for the S&P 500 Total Return index, and the Federal Funds Rate (DFF) from FRED, which will be used to model the dynamic borrowing costs for leveraged positions.

```{code-cell} ipython3
df = get_rebased_stocks(["^SP500TR"])
fed_funds = web.DataReader("DFF", "fred", start=df.index.min())
fed_funds = fed_funds["DFF"] / 100
```

## Model Application

Apply both the VOO model (1x with expense ratio) and SSO model (2x leveraged) to the S&P 500 Total Return index.

**VOO Model Parameters:**
- **Expense ratio**: 0.03% (VOO's annual expense ratio)

**SSO Model Parameters:**
- **Leverage**: 2x
- **Expense ratio**: 0.87% (SSO's annual expense ratio)
- **Borrowing multiplier**: 1.1 (estimated markup on the risk-free rate)
- **Borrowing spread**: 0.5% (estimated additional costs)

The SSO model uses the Federal Funds Rate as the base interest rate, scaled to daily using 252 trading days per year.

```{code-cell} ipython3
# Create VOO model (1x with expense ratio)
df["VOO_model"] = apply_expense_ratio(df["^SP500TR"], expense_ratio=0.0003)

# Create SSO model (2x leveraged)
df["SSO_model"] = apply_leverage(
    df["^SP500TR"],
    leverage=2,
    interest_rate_series=fed_funds,
    expense_ratio=0.0087,
    borrowing_multiplier=1.1,
    borrowing_spread=0.005,
)

df = df[["VOO_model", "SSO_model"]]
```

## Forward Return Analysis

Compare SSO model performance vs VOO model across different timeframes. Calculate forward returns and analyze probabilities of over/under performance.

```{code-cell} ipython3
# Define timeframes to analyze (in years)
timeframes = [1, 3, 5, 10, 20]
trading_days_per_year = 252

# Calculate forward return ratios for each timeframe
results = {}
for years in timeframes:
    days = trading_days_per_year * years
    results[years] = forward_return_ratio(
        df, "SSO_model", "VOO_model", days
    )
```

## Summary Statistics

Calculate probabilities and average amounts of over/under performance for each timeframe.

```{code-cell} ipython3
summary_data = []

for timeframe, return_ratios in results.items():
    # Probabilities
    prob_over = (return_ratios > 1.0).mean() * 100
    prob_under = (return_ratios < 1.0).mean() * 100
    prob_equal = (return_ratios == 1.0).mean() * 100
    
    # Average amounts (as percentage)
    avg_over = ((return_ratios[return_ratios > 1.0] - 1.0) * 100).mean() if (return_ratios > 1.0).any() else 0
    avg_under = ((1.0 - return_ratios[return_ratios < 1.0]) * 100).mean() if (return_ratios < 1.0).any() else 0
    
    # Overall statistics
    mean_ratio = return_ratios.mean()
    median_ratio = return_ratios.median()
    
    # Percentiles
    p5 = return_ratios.quantile(0.05)
    p95 = return_ratios.quantile(0.95)
    
    summary_data.append({
        "Timeframe": f"{timeframe}y",
        "Prob Overperform (%)": prob_over,
        "Prob Underperform (%)": prob_under,
        "Avg Overperform (%)": avg_over,
        "Avg Underperform (%)": avg_under,
        "Mean Ratio": mean_ratio,
        "5th Percentile": p5,
        "Median Ratio": median_ratio,
        "95th Percentile": p95,
        "Observations": len(return_ratios)
    })

summary_df = pd.DataFrame(summary_data)
summary_df
```

## Visualization: Probabilities and Amounts

Visualize the probability of over/under performance and the average amounts across timeframes.

```{code-cell} ipython3
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Probability comparison
timeframe_labels = summary_df["Timeframe"].values
x = range(len(timeframe_labels))
width = 0.35

axes[0].bar([i - width/2 for i in x], summary_df["Prob Overperform (%)"], 
            width, label="Overperform", color="green", alpha=0.7)
axes[0].bar([i + width/2 for i in x], summary_df["Prob Underperform (%)"], 
            width, label="Underperform", color="red", alpha=0.7)
axes[0].set_xlabel("Timeframe")
axes[0].set_ylabel("Probability (%)")
axes[0].set_title("Probability of Over/Under Performance")
axes[0].set_xticks(x)
axes[0].set_xticklabels(timeframe_labels)
axes[0].legend()
axes[0].grid(True, alpha=0.3, axis="y")
axes[0].axhline(y=50, color="red", linestyle="dashed")

# Average amount comparison
axes[1].bar([i - width/2 for i in x], summary_df["Avg Overperform (%)"], 
            width, label="Avg Overperform", color="green", alpha=0.7)
axes[1].bar([i + width/2 for i in x], summary_df["Avg Underperform (%)"], 
            width, label="Avg Underperform", color="red", alpha=0.7)
axes[1].set_xlabel("Timeframe")
axes[1].set_ylabel("Average Amount (%)")
axes[1].set_title("Average Over/Under Performance Amount")
axes[1].set_xticks(x)
axes[1].set_xticklabels(timeframe_labels)
axes[1].legend()
axes[1].grid(True, alpha=0.3, axis="y")

plt.tight_layout()
plt.show()
```

## Percentile Analysis Over Timeframes

Visualize how different percentiles of the return ratio distribution change across timeframes. This shows the spread and distribution shape at different investment horizons.

```{code-cell} ipython3
# Define percentiles to plot
percentiles = [0, 5, 10, 25, 50, 75, 90, 95, 100]

# Calculate percentile values for each timeframe
percentile_data = []
for timeframe in timeframes:
    ratio = results[timeframe].dropna()
    percentile_values = [ratio.quantile(p / 100) for p in percentiles]
    percentile_data.append(percentile_values)

# Convert to DataFrame for easier plotting
percentile_df = pd.DataFrame(percentile_data, index=[f"{t}y" for t in timeframes], 
                             columns=[f"{p}th" for p in percentiles])

# Create line plot
fig, ax = plt.subplots(figsize=(12, 6))

# Plot each percentile as a line
for percentile in percentiles:
    label = f"{percentile}th percentile"
    if percentile == 50:
        label = "Median (50th)"
    elif percentile == 0:
        label = "Min (0th)"
    elif percentile == 100:
        label = "Max (100th)"
    
    # Color: green for 50th and above, red for below 50th
    color = "green" if percentile >= 50 else "red"
    
    ax.plot(percentile_df.index, percentile_df[f"{percentile}th"], 
            marker="o", label=label, linewidth=1.5, markersize=4, color=color)

# Add reference line at ratio = 1.0
ax.axhline(y=1.0, color="red", linestyle="dashed", linewidth=1.5, 
           label="Equal performance", alpha=0.7)

ax.set_xlabel("Timeframe")
ax.set_ylabel("Return Ratio")
ax.set_title("Return Ratio Percentiles Across Timeframes")
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

## Distribution Comparison

Compare the distribution of ratios across different timeframes.

```{code-cell} ipython3
fig, axes = plt.subplots(len(timeframes), 1, figsize=(12, 4*len(timeframes)), sharex=True)

for idx, year in enumerate(timeframes):
    ratio = results[year]
    
    axes[idx].hist(ratio, bins="auto", edgecolor="black", alpha=0.7)
    axes[idx].axvline(x=1.0, color="red", linestyle="dashed", linewidth=2, label="Equal performance")
    axes[idx].axvline(x=ratio.mean(), color="blue", linestyle="--", linewidth=1, 
                      label=f"Mean: {ratio.mean():.3f}")
    p5 = ratio.quantile(0.05)
    p95 = ratio.quantile(0.95)
    axes[idx].axvline(x=p5, color="gray", linestyle=":", linewidth=1.5, 
                      label=f"5th percentile: {p5:.3f}")
    axes[idx].axvline(x=p95, color="gray", linestyle=":", linewidth=1.5, 
                      label=f"95th percentile: {p95:.3f}")
    axes[idx].set_ylabel("Frequency")
    axes[idx].set_title(f"{year}y Forward Return Ratio Distribution")
    axes[idx].legend()
    axes[idx].grid(True, alpha=0.3, axis="x")
    axes[idx].set_xlabel("SSO Model / VOO Model Ratio")
    axes[idx].tick_params(labelbottom=True)
    
plt.tight_layout()
plt.show()
```
