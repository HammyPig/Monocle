# Monocle

# Documentation

## Portfolio

Imports and holds transaction and dividend data.

### Transactions

Able to parse stock transactions from various sources into a unified format. The end result is a list of transactions, each with the transaction date, action (buy or sell), stock, units, and amount.

### Dividends

Does not offer functionality in parsing dividend data as providers do not offer sufficient dividend data. Takes a csv file assumed to be formatted as date, amount, type (Direct Credit or DRP), security code, and DRP price.

If the entry is labelled as 'Direct Credit', the date and amount are stored in the portfolio dividends list.

Otherwise, if the entry is labelled as part of a DRP, this does not happen. Instead, the program tracks the growth of the DRP residual balance, and only when the balance is large enough to purchase shares at the DRP price, the date and only the amount used to purchase the shares are added to the portfolio dividends list. Additionally, a transaction is made for the purchased shares.

## Tax calculation

A class which given a portfolio, calculates the capital gains or losses for a specified time period.

This works by keeping track of every individual share purchased (either manually, or through DRP). Each share has its base cost recorded (the amount needed to buy the individual share), and when sold, records its individual capital proceeds (the amount gained from the sale of the individual share).

These two values are then used to calculate the capital gain or loss on the individual share. These gains or losses are then summed up during a financial period to come up with the final taxable amount.

Non-DRP dividends are also included in the capital gains calculation by simply adding the credit amount on after the fact. For DRP dividends, pnly the functional amount that has been used to purchase shares is included in the capital gains calculation. This is because it would not make sense to tax any residual amount which you cannot access.
