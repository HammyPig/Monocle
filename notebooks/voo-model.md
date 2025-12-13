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

# VOO ETF Model

This notebook models the performance of VOO (Vanguard S&P 500 ETF, a 1x ETF) by applying an expense ratio to the S&P 500 Total Return index.

## Setup

Import required libraries and configure plotting.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import pandas as pd
from utils.stocks import apply_expense_ratio, get_rebased_stocks, rebase_dataframe

%matplotlib inline
```

## Data Download

Download historical data for the S&P 500 Total Return index and VOO ETF, then rebase them to a common starting date for comparison.

```{code-cell} ipython3
df = get_rebased_stocks(["^SP500TR", "VOO"])
```

## Baseline Comparison

Visualize the historical performance of the S&P 500 Total Return index and VOO on a logarithmic scale. VOO should track the S&P 500 closely, minus its expense ratio.

```{code-cell} ipython3
fig, ax = plt.subplots()
ax.plot(df["^SP500TR"], label="SP500TR")
ax.plot(df["VOO"], label="VOO")
ax.set_yscale("log")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Return (Log Scale)")
ax.set_title("S&P 500 Total Return vs VOO")
ax.legend()
plt.show()
```

## Model Application

Apply the expense ratio model to the S&P 500 Total Return index. VOO has an expense ratio of approximately 0.03% (0.0003).

```{code-cell} ipython3
df["VOO_model"] = apply_expense_ratio(df["^SP500TR"], expense_ratio=0.0003)

df = rebase_dataframe(df)
```

### Model Statistics

Calculate key statistics to quantify the model's accuracy.

```{code-cell} ipython3
ratio = df["VOO_model"] / df["VOO"]
difference_pct = (df["VOO_model"] - df["VOO"]) / df["VOO"] * 100

print("Model Performance Statistics:")
print(f"  Mean ratio (Model/Actual): {ratio.mean():.4f}")
print(f"  Std deviation of ratio: {ratio.std():.4f}")
print(f"  Mean absolute error: {abs(difference_pct).mean():.2f}%")
print(f"  Max over-prediction: {difference_pct.max():.2f}%")
print(f"  Max under-prediction: {difference_pct.min():.2f}%")
print(f"  Correlation coefficient: {df['VOO'].corr(df['VOO_model']):.4f}")
```

## Model Validation

Compare the model's output to the actual VOO performance using multiple visualization approaches.

### Scatter Plot

A scatter plot of model vs actual values. Points along the diagonal line (y=x) indicate perfect agreement.

```{code-cell} ipython3
fig, ax = plt.subplots(figsize=(4, 4))
ax.scatter(df["VOO"], df["VOO_model"], s=0.1, alpha=0.5)
# Add diagonal reference line
min_val = min(df["VOO"].min(), df["VOO_model"].min())
max_val = max(df["VOO"].max(), df["VOO_model"].max())
ax.plot([min_val, max_val], [min_val, max_val], "r--", label="Perfect match", linewidth=1)
ax.set_xlabel("VOO (Actual)")
ax.set_ylabel("VOO_model (Model)")
ax.set_title("Model vs Actual: Scatter Plot")
ax.legend()
plt.show()
```

### Model Accuracy Over Time

Visualize the percentage difference between model and actual values over time. A value of 0% indicates perfect agreement, with positive values showing where the model over-predicts and negative values showing under-prediction.

**Note:** The model error is near zero until approximately 2015, after which it stabilizes around ~0.6%. The cause of this is unknown.

```{code-cell} ipython3
difference = (df["VOO_model"] - df["VOO"]) / df["VOO"] * 100

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

Overlay the actual VOO performance with the model on a logarithmic scale. Because the model so closely matches VOO's performance, the two lines overlap and appear as one.

```{code-cell} ipython3
fig, ax = plt.subplots()
ax.plot(df["VOO"], label="VOO (Actual)")
ax.plot(df["VOO_model"], label="VOO_model (Model)")
ax.set_yscale("log")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Return (Log Scale)")
ax.set_title("Model vs Actual: Overlay Comparison")
ax.legend(loc="upper left")
plt.show()
```
