from dateutil.relativedelta import relativedelta

class Tax:
    class ShareParcel:
        def __init__(self, date_bought, units, cost_base):
            self.date_bought = date_bought
            self.units = units
            self.cost_base = cost_base

    def get_capital_gains(portfolio, start_date, end_date):
        capital_gains = 0
        share_parcels = {}

        for t in portfolio.transactions:
            if t.action == "buy":
                if t.stock not in share_parcels: share_parcels[t.stock] = []
                cost_base = t.amount / t.units
                share_parcel = Tax.ShareParcel(t.date, t.units, cost_base)
                share_parcels[t.stock].insert(0, share_parcel)
            elif t.action == "sell":
                capital_proceeds = t.amount / t.units
                sold_units = t.units

                for i in range(len(share_parcels[t.stock]) - 1, -1, -1):
                    share_parcel = share_parcels[t.stock][i]
                    shares_sold_from_parcel = min(sold_units, share_parcel.units)

                    if t.date >= start_date and t.date <= end_date:
                        capital_gain = shares_sold_from_parcel * (capital_proceeds - share_parcel.cost_base)
                        
                        if capital_gain > 0 and t.date > share_parcel.date_bought + relativedelta(months=12):
                            capital_gain /= 2

                        capital_gains += capital_gain

                    share_parcels[t.stock][i].units -= shares_sold_from_parcel
                    if share_parcels[t.stock][i].units <= 0:
                        share_parcels[t.stock].pop(i)

                    sold_units -= shares_sold_from_parcel
                    if sold_units == 0: break

        for d in portfolio.dividends:
            if d.date >= start_date and d.date <= end_date:
                capital_gains += d.amount

        return capital_gains
