from global_macro_scanner.config.criteria import STOCK_CRITERIA, MACRO_CRITERIA
from global_macro_scanner.config.markets import MARKETS
from global_macro_scanner.screener.core import screen_equities
from global_macro_scanner.screener.macro import screen_macro
from global_macro_scanner.storage.csv import log_catches
from global_macro_scanner.alerts.telegram import send_alerts

def daily_scan():
    equity_catches = screen_equities(STOCK_CRITERIA, MARKETS['equities'])
    macro_catches = screen_macro(MACRO_CRITERIA, MARKETS['macro'])
    all_catches = equity_catches + macro_catches
    log_catches(all_catches)
    send_alerts(all_catches)

if __name__ == '__main__':
    daily_scan()
