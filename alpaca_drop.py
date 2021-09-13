import os
import time
import datetime
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.rest import REST

API_KEY = os.getenv("ALPACA_PAPER_API_KEY")
SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET_KEY")

NUM_TRADES = 15


def main():

	rest = REST(API_KEY, SECRET_KEY, base_url='https://paper-api.alpaca.markets')
	all_assets = rest.list_assets()
	working_symbols = [x.symbol for x in all_assets if x.tradable and x.status == 'active']

	positions = {}
	trading = False
	today = datetime.datetime.today()
	start = datetime.datetime(today.year, today.month, today.day, 6, 30, 30)
	end = datetime.datetime(today.year, today.month, today.day, 7, 0, 0)

	total_cash = float(rest.get_account().equity)
	cash_per_trade = (total_cash - 25000) / NUM_TRADES
	current_trades = 0

	while True:
		now = datetime.datetime.today()
		if now > start:
			trading = True
		if now > end:
			break
		if trading and current_trades < NUM_TRADES:
			snapshots = rest.get_snapshots(working_symbols)
			for stock, data in snapshots.items():
				try:
					prev_close = float(data.prev_daily_bar.c)
					today_open = float(data.daily_bar.o)
					current = float(data.daily_bar.c)
				except:
					continue
				if (today_open - prev_close) / prev_close > 0.15:
					working_symbols.remove(stock)
					continue
				if current < today_open * 0.9 and current < 40 and current_trades < NUM_TRADES:
					qty = cash_per_trade // (today_open * 0.9)
					order = rest.submit_order(symbol=stock, side="buy", qty=qty, type="limit", time_in_force="gtc", limit_price=today_open*0.9, order_class="bracket", stop_loss={"stop_price":today_open*0.6}, take_profit={"limit_price":today_open*0.95})
					print(order)
					if order.status in ["new", "accepted", "filled", "partially_filled"]:
						positions[stock] = order.id
						working_symbols.remove(stock)
						current_trades += 1
		time.sleep(20)

	actual_positions = [x.symbol for x in rest.list_positions()]
	for stock, order_id in positions.items():
		if stock not in actual_positions:
			rest.cancel_order(order_id)


if __name__ == '__main__':
	main()
