# Monocle

# Documentation

## Stock transactions

A class which is responsible for parsing stock transactions from various sources into a unified format.

The end product is a list of transactions, each with the transaction date, action (buy or sell), stock, units, and amount.

## Tax calculation

A class which given a list of stock transactions, calculates the total gain or loss (for tax purposes) for a specified time period.

This works by keeping track of every individual share. Each share has its base cost recorded (the amount needed to buy the individual share), and when sold, records its individual capital proceeds (the amount gained from the sale of the individual share). These two values are then used to calculate the capital gain or loss on the individual share. These gains or losses are then summed up during a financial period to come up with the final taxable amount.
