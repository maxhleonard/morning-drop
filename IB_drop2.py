from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ContractDetails
from ibapi.scanner import ScannerSubscription, ScanData
from ibapi.tag_value import TagValue
from ibapi.ticktype import TickTypeEnum
from ibapi.order import *
from ibapi.order_condition import TimeCondition
import time
import threading
import datetime
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import bs4
import urllib3


def setup_screener(driver):

	driver.get("https://finance.yahoo.com/losers")
	filters = driver.find_element_by_id("screener-criteria")
	buttons = filters.find_elements_by_tag_name("button")
	for edit in buttons:
		if edit.text == "Edit":
			break
	edit.click()
	time.sleep(1)
	fields = filters.find_elements_by_css_selector("div[data-test=field-section]")

	intra_volume = fields[3]
	remove_button = intra_volume.find_element_by_css_selector("button.removeFilter")
	remove_button.click()
	time.sleep(1)

	caps = fields[2]
	remove_button = caps.find_element_by_css_selector("button.removeFilter")
	remove_button.click()
	time.sleep(1)

	add_filter = filters.find_element_by_css_selector("button.addFilter")
	add_filter.click()
	time.sleep(1)

	menu = filters.find_element_by_css_selector("div[data-test=filter-menu]")
	cats = menu.find_elements_by_css_selector("div[data-test=filter-cat]")

	avg_vol_checkbox = cats[1].find_elements_by_tag_name("li")[1].find_element_by_tag_name("svg")
	avg_vol_checkbox.click()
	time.sleep(1)

	price_checkbox = cats[1].find_elements_by_tag_name("li")[12].find_element_by_tag_name("svg")
	price_checkbox.click()
	time.sleep(1)

	close_button = menu.find_element_by_tag_name("button").find_element_by_tag_name("svg")
	driver.execute_script("window.scroll(0, 0);")
	time.sleep(1)
	close_button.click()
	time.sleep(1)


	while True:
		fields = filters.find_elements_by_css_selector("div[data-test=field-section]")
		not_found = True
		for field in fields:
			found = False
			for t in ["% Change in Price (Intraday)less than", "RegionisUnited States", "Avg Vol (3 month)greater than", "Price (Intraday)greater than"]:
				if t in field.text:
					found = True
					break

			if not found:
				remove_button = field.find_element_by_css_selector("button.removeFilter")
				remove_button.click()
				time.sleep(1)
				not_found = False
				break

		if not_found:
			break

	fields = filters.find_elements_by_css_selector("div[data-test=field-section]")

	correct = 0
	for field in fields:

		if "% Change in Price (Intraday)less than" in field.text:

			correct += 1
			perc_input = field.find_element_by_tag_name("input")
			perc_input.clear()
			perc_input.send_keys("-10")
			time.sleep(1)

		elif "RegionisUnited States" in field.text:
			correct += 1
			continue

		elif "Avg Vol (3 month)greater than" in field.text:
			correct += 1
			vol_input = field.find_element_by_tag_name("input")
			vol_input.clear()
			vol_input.send_keys("20000")
			time.sleep(1)

		elif "Price (Intraday)greater than" in field.text:
			'''
			price_button = field.find_element_by_tag_name("svg")
			price_button.click()
			time.sleep(0.5)

			select_menu = field.find_element_by_css_selector("div[data-test=intradayprice-select-menu]")
			between = select_menu.find_element_by_css_selector("div[data-value=btwn]")
			between.click()
			time.sleep(1)

			price_inputs = field.find_elements_by_tag_name("input")
			price_inputs[0].send_keys("1")
			price_inputs[1].send_keys("40")
			time.sleep(1)
			'''
			correct += 1
			price_input = field.find_element_by_tag_name("input")
			price_input.clear()
			price_input.send_keys("1")
			time.sleep(1)
	if correct != 4:
		return False

	return True
def get_results(driver):

	global pm
	stocks = {}

	find_button = driver.find_element_by_css_selector("button[data-test=find-stock]")
	driver.execute_script("window.scroll(0, 0);")
	find_button.click()
	time.sleep(3)

	results = driver.find_element_by_id("scr-res-table")
	results_button = results.find_element_by_css_selector("div[data-test=select-container]").find_element_by_tag_name("svg")
	results_button.click()
	time.sleep(1)

	results_menu = results.find_element_by_css_selector("div[data-test=showRows-select-menu]")
	hundred = results_menu.find_elements_by_tag_name("div")[-1]
	hundred.click()
	time.sleep(3)

	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
	time.sleep(1)
	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
	time.sleep(1)

	results_list = results.find_element_by_tag_name("tbody").find_elements_by_tag_name("tr")
	
	for res in results_list:
		anchor = res.find_element_by_tag_name("td").find_element_by_tag_name("a")
		stocks[anchor.text] = anchor.get_attribute("href")

	return stocks

def get_prices(link):

	soup = bs4.BeautifulSoup(pm.request("GET", link).data, "html.parser")
	price = float(soup.find("div", id="quote-header-info").findChildren("div", recursive=False)[-1].find("span").text)
	exhange = soup.find("div", id="quote-header-info").findChildren("div", recursive=False)[1].find("div").findChildren("div", recursive=False)[1].find("span").text
	data_rows = soup.find("div", attrs={"data-test":"left-summary-table"}).find("tbody").find_all("tr")
	previous_close = float(data_rows[0].find_all("td")[1].find("span").text)
	today_open = float(data_rows[1].find_all("td")[1].find("span").text)
	ask = data_rows[3].find_all("td")[1].find("span").text
	ask = float(ask.split(" x ")[0])
	return {"last":price, "close":previous_close, "open":today_open, "exchange":exhange, "ask":ask}

class IBapi(EWrapper, EClient):

	def __init__(self):
		EClient.__init__(self, self)
		self.stocks = {}
		self.nextOrderId = -1

	def nextValidId(self, orderId: int):

		super().nextValidId(orderId)
		self.nextOrderId = orderId

	def contractDetails(self, reqId : int, contractDetails : ContractDetails):

		this_symbol = contractDetails.contract.symbol
		if this_symbol in self.stocks.keys():

			info = self.stocks[this_symbol]

			parentOrder = Order()
			parentOrder.tif = "GTD"
			parentOrder.action = "BUY"
			parentOrder.orderType = "MKT"
			parentOrder.totalQuantity = 1
			parentOrder.transmit = False
			parentOrder.goodTillDate = "20210311 07:00:00"

			takeProfitOrder = Order()
			takeProfitOrder.tif = "GTC"
			takeProfitOrder.action = "SELL"
			takeProfitOrder.orderType = "LMT"
			takeProfitOrder.totalQuantity = 1
			takeProfitOrder.lmtPrice = round(info["open"] * 0.95, 2)
			takeProfitOrder.parentId = self.nextOrderId
			takeProfitOrder.transmit = False

			stopLossOrder = Order()
			stopLossOrder.tif= "GTC"
			stopLossOrder.action = "SELL"
			stopLossOrder.orderType = "STP"
			stopLossOrder.auxPrice = round(info["open"] * 0.6, 2)
			stopLossOrder.totalQuantity = 1
			stopLossOrder.parentId = self.nextOrderId
			stopLossOrder.transmit = True

			self.placeOrder(self.nextOrderId, contractDetails.contract, parentOrder)
			self.nextOrderId += 1
			self.placeOrder(self.nextOrderId, contractDetails.contract, takeProfitOrder)
			self.nextOrderId += 1
			self.placeOrder(self.nextOrderId, contractDetails.contract, stopLossOrder)
			self.nextOrderId += 1

	def new_stock(self, symbol, data):

		if symbol in self.stocks.keys():
			return

		if data["last"] > 0.9 * data["open"]:
			return

		if data["ask"] > 0.9 * data["open"]:
			return

		overnight = (data["open"] - data["close"]) / data["close"]
		if abs(overnight) > 0.1:
			return 

		self.stocks[symbol] = data

		contract = Contract()
		contract.symbol = symbol
		contract.currency = "USD"
		contract.secType = "STK"
		contract.exchange = "SMART"
		self.reqContractDetails(0, contract)


TIMER_DONE = False

def ib_loop():

	app.run()

def time_loop():

	global TIMER_DONE
	time.sleep(60)
	TIMER_DONE = True

pm = urllib3.PoolManager()

options = Options()
options.headless = True
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(options=options)

while True:
	if setup_screener(driver):
		break
	time.sleep(5)

print("YAHOO SCREENER SETUP FINISHED")

app = IBapi()

app.connect('127.0.0.1', 7497, 62)
time.sleep(5)

thread1 = threading.Thread(target=ib_loop)
thread2 = threading.Thread(target=time_loop)

thread1.start()
thread2.start()

while True:
	if TIMER_DONE:
		break
	to_check = get_results(driver)
	for ticker, link in to_check.items():

		if ticker in app.stocks.keys():
			continue
		try:
			data = get_prices(link)
		except:
			continue
		if data["last"] <= 40 and "OTC" not in data["exchange"]:
			app.new_stock(ticker, data)

	time.sleep(10)

app.disconnect()
driver.quit()


