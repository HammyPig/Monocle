# Monocle

# Documentation

## Portfolio

Imports and holds transaction and dividend data.

### Transactions

Able to parse stock transactions from various sources into a unified format. The end result is a list of transactions, each with the transaction date, action (buy or sell), stock, units, and amount.

### Dividends

Does not offer functionality in parsing dividend data as providers do not offer sufficient data. Takes a csv file assumed to be formatted as date, amount, type (Direct Credit or DRP), security code, and DRP shares (amount of units received).

If the entry is labelled as a direct credit, the date and amount are stored in a dividend object, which is then stored in the portfolio dividends list.

Otherwise, if the entry is labelled as part of a DRP, an additional transaction is also added to mimick an individual receiving the direct credit, and then spending it manually to purchase the amount of shares.

However, it is important to note that the total amount is not added in the dividend object, but rather, the DRP price of the share multiplied by the amount of units received. This is because if you did not receive an amount divisible by the DRP share price, it would not make sense to tax any amount leftover (since any leftover amount is kept with the dividend distributor, and not yourself.)

## Tax calculation

A class which given a portfolio, calculates the capital gains or losses for a specified time period.

This works by keeping track of every individual share purchased (either manually, or through DRP). Each share has its base cost recorded (the amount needed to buy the individual share), and when sold, records its individual capital proceeds (the amount gained from the sale of the individual share).

These two values are then used to calculate the capital gain or loss on the individual share. These gains or losses are then summed up during a financial period to come up with the final taxable amount.

Non-DRP dividends are also included in the capital gains calculation by simply adding the credit amount on after the fact.
