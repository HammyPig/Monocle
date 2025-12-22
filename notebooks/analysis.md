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

```{code-cell} ipython3
import pickle
from pathlib import Path
import pandas_datareader.data as web
from utils.stocks import comprehensive_comparison, get_rebased_stocks, apply_expense_ratio, apply_leverage, rebase_dataframe
from utils.paths import get_project_root
```

```{code-cell} ipython3
# Set up cache directory
cache_dir = get_project_root() / "data" / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)

# Create cache file paths
symbols = ["^SP500TR", "EFA", "EEM", "QQQ", "SSO", "TLT", "VOO", "SHY", "IJH", "IJR", "IVV"]
symbols_str = "_".join(sorted(symbols))
df_cache_file = cache_dir / f"df_orig_{symbols_str}.pkl"
fed_funds_cache_file = cache_dir / "fed_funds.pkl"

# Try to load from cache
use_cache = True  # Set to False to force fresh download
try:
    if use_cache and df_cache_file.exists() and fed_funds_cache_file.exists():
        with open(df_cache_file, "rb") as f:
            df_orig = pickle.load(f)
        with open(fed_funds_cache_file, "rb") as f:
            fed_funds = pickle.load(f)
        print("Loaded data from cache")
    else:
        raise FileNotFoundError("Cache not found, downloading fresh data")
except Exception as e:
    # Download fresh data
    print(f"Downloading fresh data: {e}")
    df_orig = get_rebased_stocks(symbols)
    fed_funds = web.DataReader("DFF", "fred", start=df_orig.index.min())
    fed_funds = fed_funds["DFF"] / 100
    
    # Save to cache
    if use_cache:
        try:
            with open(df_cache_file, "wb") as f:
                pickle.dump(df_orig, f)
            with open(fed_funds_cache_file, "wb") as f:
                pickle.dump(fed_funds, f)
            print("Saved data to cache")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

df_orig.apply(lambda x: x.first_valid_index()).sort_values()
```

```{code-cell} ipython3
# Calculate models
df = df_orig.copy()

# Get market cap (in trillions) from wiki pages to calculate total US proportions
sp500_market_cap = 61 # https://en.wikipedia.org/wiki/S%26P_500
sp400_market_cap = 3.1 # https://en.wikipedia.org/wiki/S%26P_400
sp600_market_cap = 1.5 # https://en.wikipedia.org/wiki/S%26P_600
total_us_market_cap = sp500_market_cap + sp400_market_cap + sp600_market_cap

df["VTI"] = (
    (sp500_market_cap / total_us_market_cap) * df["IVV"] +
    (sp400_market_cap / total_us_market_cap) * df["IJH"] +
    (sp600_market_cap / total_us_market_cap) * df["IJR"]
)

developed_ratio = 0.9 # https://www.msci.com/indexes/group/developed-markets-indexes
emerging_ratio = 0.1 # https://www.msci.com/indexes/group/emerging-markets-indexes
developed_us_ratio = 0.713 / developed_ratio # https://www.msci.com/indexes/index/664185
developed_ex_us_ratio = developed_ratio - developed_us_ratio

df["world"] = (
    developed_us_ratio * df["VTI"] +
    developed_ex_us_ratio * df["EFA"] +
    emerging_ratio * df["EEM"]
)

df["VOO"] = apply_expense_ratio(df["^SP500TR"], expense_ratio=0.0003)

# Align Fed Funds data with the dataframe
fed_funds_aligned = fed_funds.reindex(df.index, method="ffill")

# Convert annual rate to daily rate
daily_returns = (1 + fed_funds_aligned) ** (1 / 252) - 1

# Create cash model using cumulative product
df["cash"] = (1 + daily_returns).cumprod()

# Rebase to start at 1.0
df["cash"] = df["cash"] / df["cash"].iloc[0]

df
```

```{code-cell} ipython3
comprehensive_comparison(df[["world", "cash"]])
```

```{code-cell} ipython3
comprehensive_comparison(df[["world", "TLT"]])
```

```{code-cell} ipython3
comprehensive_comparison(df[["VTI", "world"]])
```

```{code-cell} ipython3
comprehensive_comparison(df[["VOO", "VTI"]])
```

```{code-cell} ipython3
comprehensive_comparison(df[["QQQ", "VOO"]])
```
