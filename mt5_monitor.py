import MetaTrader5 as mt5
import requests
import time
from datetime import datetime, timezone

TELEGRAM_BOT_TOKEN = "8688072039:AAGTGewnqZq9AR_zS5_iVTS_IQbdf9OVOgI"
TELEGRAM_CHAT_ID   = "-1003830307981"

CHECK_INTERVAL = 3

ORDER_TYPE_NAMES = {
    mt5.ORDER_TYPE_BUY:             "BUY",
    mt5.ORDER_TYPE_SELL:            "SELL",
    mt5.ORDER_TYPE_BUY_LIMIT:       "BUY LIMIT",
    mt5.ORDER_TYPE_SELL_LIMIT:      "SELL LIMIT",
    mt5.ORDER_TYPE_BUY_STOP:        "BUY STOP",
    mt5.ORDER_TYPE_SELL_STOP:       "SELL STOP",
    mt5.ORDER_TYPE_BUY_STOP_LIMIT:  "BUY STOP LIMIT",
    mt5.ORDER_TYPE_SELL_STOP_LIMIT: "SELL STOP LIMIT",
}

MARKET_TYPES = {mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL}


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if not r.ok:
            print(f"[TELEGRAM ERROR] {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[TELEGRAM EXCEPTION] {e}")


def calc_risk_percent(account_info, order) -> str:
    if order.sl == 0.0:
        return "N/A (no SL)"

    symbol_info = mt5.symbol_info(order.symbol)
    if symbol_info is None:
        return "N/A"

    tick_size  = symbol_info.trade_tick_size
    tick_value = symbol_info.trade_tick_value
    volume     = order.volume if hasattr(order, "volume") else order.volume_initial

    if tick_size == 0:
        return "N/A"

    sl_distance_ticks = abs(order.price_open - order.sl) / tick_size
    sl_value_money    = sl_distance_ticks * tick_value * volume

    if account_info.balance == 0:
        return "N/A"

    return f"{(sl_value_money / account_info.balance) * 100:.2f}%"


def format_open_message(order, account_info, label="NEW") -> str:
    order_type  = ORDER_TYPE_NAMES.get(order.type, f"TYPE_{order.type}")
    is_market   = order.type in MARKET_TYPES
    volume      = order.volume if hasattr(order, "volume") else order.volume_initial
    sl          = order.sl if order.sl != 0.0 else None
    tp          = order.tp if order.tp != 0.0 else None
    entry_label = "Price Entry" if is_market else "Price Entry (Pending)"
    order_label = "MARKET ORDER" if is_market else "LIMIT/STOP ORDER"

    lines = [
        f"<b>📊 {label} {order_type} — {order.symbol}</b>",
        f"<i>{order_label}</i>",
        f"Ticket: <code>{order.ticket}</code>",
        "",
        f"<b>Equity:</b>  {account_info.equity:.2f}",
        f"<b>Lotsize:</b> {volume}",
        f"<b>Risk:</b>    {calc_risk_percent(account_info, order)}",
        "",
        f"<b>{entry_label}:</b> {order.price_open}",
        f"<b>Price SL:</b>     {sl if sl is not None else '—'}",
        f"<b>Price TP:</b>     {tp if tp is not None else '—'}",
        "",
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(lines)


def format_close_message(deal, account_info, label: str, emoji: str) -> str:
    lines = [
        f"<b>{emoji} {label} — {deal.symbol}</b>",
        f"Ticket: <code>{deal.position_id}</code>",
        "",
        f"<b>Equity:</b>   {account_info.equity:.2f}",
        f"<b>Balance:</b>  {account_info.balance:.2f}",
        f"<b>Lotsize:</b>  {deal.volume}",
        "",
        f"<b>Close Price:</b> {deal.price}",
        f"<b>Profit:</b>      {deal.profit:+.2f}",
        "",
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(lines)


def format_cancel_message(hist_order, account_info) -> str:
    order_type = ORDER_TYPE_NAMES.get(hist_order.type, f"TYPE_{hist_order.type}")
    lines = [
        f"<b>🚫 CANCELLED {order_type} — {hist_order.symbol}</b>",
        f"Ticket: <code>{hist_order.ticket}</code>",
        "",
        f"<b>Equity:</b>  {account_info.equity:.2f}",
        f"<b>Lotsize:</b> {hist_order.volume_initial}",
        "",
        f"<b>Price Entry (Pending):</b> {hist_order.price_open}",
        f"<b>Price SL:</b>             {hist_order.sl if hist_order.sl != 0.0 else '—'}",
        f"<b>Price TP:</b>             {hist_order.tp if hist_order.tp != 0.0 else '—'}",
        "",
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(lines)


def get_pending_tickets() -> set:
    orders = mt5.orders_get()
    return {o.ticket for o in orders} if orders else set()


def get_position_tickets() -> set:
    positions = mt5.positions_get()
    return {p.ticket for p in positions} if positions else set()


def snapshot_positions() -> dict:
    result = {}
    positions = mt5.positions_get()
    if positions:
        for p in positions:
            result[p.ticket] = (p.sl, p.tp)
    return result


def snapshot_pending() -> dict:
    """Simpan snapshot price_open, sl, tp semua pending order. {ticket: (price_open, sl, tp)}"""
    result = {}
    orders = mt5.orders_get()
    if orders:
        for o in orders:
            result[o.ticket] = (o.price_open, o.sl, o.tp)
    return result


def get_close_deal(position_ticket: int):
    deals = mt5.history_deals_get(position=position_ticket)
    if not deals:
        return None
    for d in reversed(deals):
        if d.entry == mt5.DEAL_ENTRY_OUT:
            return d
    return None


def main():
    print("[MT5 Monitor] Starting...")

    if not mt5.initialize():
        print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
        return

    print(f"[MT5] Connected. Terminal: {mt5.terminal_info().name}")

    account = mt5.account_info()
    print(f"[MT5] Account: {account.login} | Balance: {account.balance} | Equity: {account.equity}")

    known_pending      = get_pending_tickets()
    known_positions    = get_position_tickets()
    position_sltp      = snapshot_positions()
    pending_snapshot   = snapshot_pending()
    pending_type_cache = {t: v[0] for t, v in pending_snapshot.items()} if pending_snapshot else {}
    existing_orders = mt5.orders_get()
    if existing_orders:
        for o in existing_orders:
            pending_type_cache[o.ticket] = o.type

    send_telegram(
        f"<b>✅ MT5 Monitor aktif</b>\n"
        f"Account: <code>{account.login}</code>\n"
        f"Balance: {account.balance:.2f} | Equity: {account.equity:.2f}"
    )

    print(f"[MT5] Monitoring started. Interval: {CHECK_INTERVAL}s\n")

    while True:
        try:
            cur_pending   = get_pending_tickets()
            cur_positions = get_position_tickets()
            acct          = mt5.account_info()

            # --- Order pending baru ---
            for ticket in cur_pending - known_pending:
                orders = mt5.orders_get(ticket=ticket)
                if orders:
                    pending_type_cache[ticket] = orders[0].type
                    print(f"[NEW PENDING] Ticket {ticket}")
                    send_telegram(format_open_message(orders[0], acct, label="NEW"))

            # --- Posisi baru (market order / pending yang ke-fill) ---
            for ticket in cur_positions - known_positions:
                positions = mt5.positions_get(ticket=ticket)
                if not positions:
                    continue
                pos = positions[0]
                if ticket in pending_type_cache:
                    orig_type = ORDER_TYPE_NAMES.get(pending_type_cache[ticket], "LIMIT")
                    print(f"[FILLED] Ticket {ticket} ({orig_type})")
                    send_telegram(format_open_message(pos, acct, label=f"FILLED {orig_type}"))
                    del pending_type_cache[ticket]
                else:
                    print(f"[NEW POSITION] Ticket {ticket}")
                    send_telegram(format_open_message(pos, acct, label="NEW"))

            # --- Pending order hilang (cancelled atau filled) ---
            for ticket in known_pending - cur_pending:
                if ticket in cur_positions:
                    pass  # sudah jadi posisi, sudah dihandle di atas
                else:
                    hist = mt5.history_orders_get(ticket=ticket)
                    if hist:
                        h = hist[0]
                        if h.state == mt5.ORDER_STATE_CANCELED:
                            print(f"[CANCELLED] Ticket {ticket}")
                            send_telegram(format_cancel_message(h, acct))

            # --- Posisi hilang (closed: SL / TP / manual) ---
            for ticket in known_positions - cur_positions:
                deal = get_close_deal(ticket)
                if deal is None:
                    continue

                if deal.reason == mt5.DEAL_REASON_SL:
                    label, emoji = "HIT SL", "🔴"
                elif deal.reason == mt5.DEAL_REASON_TP:
                    label, emoji = "HIT TP", "🟢"
                else:
                    label, emoji = "CLOSED MANUAL", "⚪"

                print(f"[{label}] Ticket {ticket} | Profit: {deal.profit:+.2f}")
                send_telegram(format_close_message(deal, acct, label, emoji))

            # --- Perubahan SL/TP pada posisi existing ---
            cur_sltp = snapshot_positions()
            for ticket, (new_sl, new_tp) in cur_sltp.items():
                if ticket not in position_sltp:
                    continue
                old_sl, old_tp = position_sltp[ticket]
                if new_sl != old_sl or new_tp != old_tp:
                    positions = mt5.positions_get(ticket=ticket)
                    if positions:
                        what = []
                        if new_sl != old_sl:
                            what.append(f"SL: {old_sl} → {new_sl}")
                        if new_tp != old_tp:
                            what.append(f"TP: {old_tp} → {new_tp}")
                        print(f"[SL/TP UPDATE] Ticket {ticket} — {', '.join(what)}")
                        send_telegram(format_open_message(positions[0], acct, label="UPDATE SL/TP"))

            # --- Perubahan price/SL/TP pada pending order existing ---
            cur_pending_snap = snapshot_pending()
            for ticket, (new_price, new_sl, new_tp) in cur_pending_snap.items():
                if ticket not in pending_snapshot:
                    continue
                old_price, old_sl, old_tp = pending_snapshot[ticket]
                if new_price != old_price or new_sl != old_sl or new_tp != old_tp:
                    orders = mt5.orders_get(ticket=ticket)
                    if orders:
                        what = []
                        if new_price != old_price:
                            what.append(f"Entry: {old_price} → {new_price}")
                        if new_sl != old_sl:
                            what.append(f"SL: {old_sl} → {new_sl}")
                        if new_tp != old_tp:
                            what.append(f"TP: {old_tp} → {new_tp}")
                        print(f"[PENDING UPDATE] Ticket {ticket} — {', '.join(what)}")
                        send_telegram(format_open_message(orders[0], acct, label="UPDATE PENDING"))

            known_pending    = cur_pending
            known_positions  = cur_positions
            position_sltp    = cur_sltp
            pending_snapshot = cur_pending_snap
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[MT5 Monitor] Stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(CHECK_INTERVAL)

    mt5.shutdown()


if __name__ == "__main__":
    main()
