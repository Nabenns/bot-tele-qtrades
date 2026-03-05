import os
import MetaTrader5 as mt5
import requests
import time
from datetime import datetime, timezone

TELEGRAM_BOT_TOKEN = "8703917049:AAEImdlrAiZgqVB6sCRGoXvjvcirMpxkoHE"

CHANNELS = [
    "-1001732290104",   # Channel 1
    "-1002220295876",   # Channel 2
    # "-100XXXXXXXXXX", # Channel 3
]

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

BUY_TYPES  = {mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT,
              mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_BUY_STOP_LIMIT}
SELL_TYPES = {mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT,
              mt5.ORDER_TYPE_SELL_STOP, mt5.ORDER_TYPE_SELL_STOP_LIMIT}


def direction(order_type: int) -> str:
    return "BUYNOW" if order_type in BUY_TYPES else "SELLNOW"


def fmt_price(symbol: str, price: float) -> str:
    info = mt5.symbol_info(symbol)
    digits = info.digits if info else 5
    return f"{price:.{digits}f}"


# ─────────────────────────────────────────────
#  CHANNEL 1  —  Gaya kasual / hype
# ─────────────────────────────────────────────

def ch1_open(order, label="NEW") -> str:
    symbol = order.symbol
    entry  = fmt_price(symbol, order.price_open)
    sl     = fmt_price(symbol, order.sl) if order.sl != 0.0 else None
    tp     = fmt_price(symbol, order.tp) if order.tp != 0.0 else None
    action = direction(order.type)

    if label == "UPDATE SL/TP":
        prefix = "UPDATE ‼️\n"
    elif label == "UPDATE PENDING":
        prefix = "ORDER DIUPDATE ✏️\n"
    else:
        prefix = ""

    lines = [
        f"{prefix}🏁 {symbol} {action}",
        "",
        f"HARGA : {entry}",
        "",
        f"SL : {sl if sl is not None else '-'}",
        f"TP : {tp if tp is not None else '-'}",
        "",
        "JAGA RISK KALIAN GUYS ‼️",
    ]
    return "\n".join(lines)


def ch1_close(deal, label: str) -> str:
    symbol = deal.symbol
    if label == "HIT TP":
        return f"YOOOOOO TAKE PROFIT ✅\n{symbol}"
    elif label == "HIT SL":
        return f"SL GUYS, NT ❌\n{symbol}"
    else:
        return f"CLOSED MANUAL ⚪\n{symbol}"


def ch1_cancel(hist_order) -> str:
    order_type = ORDER_TYPE_NAMES.get(hist_order.type, "ORDER")
    return (
        f"❌ ORDER CANCEL\n"
        f"{hist_order.symbol} {order_type}\n"
        f"HARGA : {fmt_price(hist_order.symbol, hist_order.price_open)}"
    )


# ─────────────────────────────────────────────
#  CHANNEL 2  —  (tambah nanti)
# ─────────────────────────────────────────────

def ch2_open(order, label="NEW") -> str:
    symbol = order.symbol
    entry  = fmt_price(symbol, order.price_open)
    sl     = fmt_price(symbol, order.sl) if order.sl != 0.0 else None
    tp     = fmt_price(symbol, order.tp) if order.tp != 0.0 else None
    action = direction(order.type)

    if label == "UPDATE SL/TP":
        prefix = "UPDATE ORDER\n"
    elif label == "UPDATE PENDING":
        prefix = "UPDATE ORDER\n"
    else:
        prefix = ""

    lines = [
        f"{prefix}{symbol} {action}",
        "",
        f"PRICE : {entry}",
        "",
        f"STOPLOSS : {sl if sl is not None else '-'}",
        f"TAKEPROFIT : {tp if tp is not None else '-'}",
        "",
        "DISCLAIMER : TRADING MEMILIK RESIKO TINGGI!",
    ]
    return "\n".join(lines)


def ch2_close(deal, label: str) -> str:
    symbol = deal.symbol
    if label == "HIT TP":
        return f"TEPEEEE ✅\n{symbol}"
    elif label == "HIT SL":
        return f"SORRY SL ❌\n{symbol}"
    else:
        return f"CLOSED\n{symbol}"


def ch2_cancel(hist_order) -> str:
    order_type = ORDER_TYPE_NAMES.get(hist_order.type, "ORDER")
    return (
        f"ORDER CANCEL\n"
        f"{hist_order.symbol} {order_type}\n"
        f"PRICE : {fmt_price(hist_order.symbol, hist_order.price_open)}"
    )


# ─────────────────────────────────────────────
#  CHANNEL 3  —  (tambah nanti)
# ─────────────────────────────────────────────

def ch3_open(order, label="NEW") -> str:
    return ""  # TODO

def ch3_close(deal, label: str) -> str:
    return ""  # TODO

def ch3_cancel(hist_order) -> str:
    return ""  # TODO


# ─────────────────────────────────────────────
#  Mapping channel index → formatter
# ─────────────────────────────────────────────

FORMATTERS = [
    {"open": ch1_open, "close": ch1_close, "cancel": ch1_cancel},
    {"open": ch2_open, "close": ch2_close, "cancel": ch2_cancel},
    {"open": ch3_open, "close": ch3_close, "cancel": ch3_cancel},
]


# ─────────────────────────────────────────────
#  Telegram
# ─────────────────────────────────────────────

def send_telegram(chat_id: str, message: str, reply_to: int = None) -> int:
    if not message.strip():
        return None
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.ok:
            return r.json().get("result", {}).get("message_id")
        else:
            print(f"[TELEGRAM ERROR] {chat_id}: {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[TELEGRAM EXCEPTION] {e}")
    return None


ticket_msg_ids = {}


def broadcast_open(order, label="NEW"):
    ticket  = order.ticket
    is_new  = label == "NEW"
    msg_ids = []

    for i, chat_id in enumerate(CHANNELS):
        fmt      = FORMATTERS[i]
        msg      = fmt["open"](order, label)
        reply_to = None
        if not is_new and ticket in ticket_msg_ids and i < len(ticket_msg_ids[ticket]):
            reply_to = ticket_msg_ids[ticket][i]
        msg_id = send_telegram(chat_id, msg, reply_to=reply_to)
        msg_ids.append(msg_id)

    if is_new:
        ticket_msg_ids[ticket] = msg_ids


def broadcast_close(deal, label: str):
    ticket = deal.position_id
    for i, chat_id in enumerate(CHANNELS):
        fmt      = FORMATTERS[i]
        msg      = fmt["close"](deal, label)
        reply_to = None
        if ticket in ticket_msg_ids and i < len(ticket_msg_ids[ticket]):
            reply_to = ticket_msg_ids[ticket][i]
        send_telegram(chat_id, msg, reply_to=reply_to)
    ticket_msg_ids.pop(ticket, None)


def broadcast_cancel(hist_order):
    ticket = hist_order.ticket
    for i, chat_id in enumerate(CHANNELS):
        fmt      = FORMATTERS[i]
        msg      = fmt["cancel"](hist_order)
        reply_to = None
        if ticket in ticket_msg_ids and i < len(ticket_msg_ids[ticket]):
            reply_to = ticket_msg_ids[ticket][i]
        send_telegram(chat_id, msg, reply_to=reply_to)
    ticket_msg_ids.pop(ticket, None)


# ─────────────────────────────────────────────
#  MT5 Helpers
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    print("[MT5 Monitor v2] Starting...")

    mt5_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\MT5\terminal64.exe",
    ]

    initialized = False
    for path in mt5_paths:
        if os.path.exists(path):
            print(f"[MT5] Trying: {path}")
            if mt5.initialize(path=path):
                initialized = True
                break

    if not initialized:
        if mt5.initialize():
            initialized = True

    if not initialized:
        print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
        print("[INFO] Pastikan MetaTrader 5 sudah dibuka dan login.")
        return

    print(f"[MT5] Connected: {mt5.terminal_info().name}")

    account = mt5.account_info()
    print(f"[MT5] Account: {account.login} | Balance: {account.balance} | Equity: {account.equity}")

    known_pending      = get_pending_tickets()
    known_positions    = get_position_tickets()
    position_sltp      = snapshot_positions()
    pending_snapshot   = snapshot_pending()
    pending_type_cache = {}
    existing_orders    = mt5.orders_get()
    if existing_orders:
        for o in existing_orders:
            pending_type_cache[o.ticket] = o.type

    print(f"[MT5] Monitoring started. Channels: {len(CHANNELS)} | Interval: {CHECK_INTERVAL}s\n")

    while True:
        try:
            cur_pending   = get_pending_tickets()
            cur_positions = get_position_tickets()

            # --- Pending order baru ---
            for ticket in cur_pending - known_pending:
                orders = mt5.orders_get(ticket=ticket)
                if orders:
                    pending_type_cache[ticket] = orders[0].type
                    print(f"[NEW PENDING] Ticket {ticket}")
                    broadcast_open(orders[0], label="NEW")

            # --- Posisi baru (market order / pending ke-fill) ---
            for ticket in cur_positions - known_positions:
                positions = mt5.positions_get(ticket=ticket)
                if not positions:
                    continue
                pos = positions[0]
                if ticket in pending_type_cache:
                    orig = ORDER_TYPE_NAMES.get(pending_type_cache[ticket], "LIMIT")
                    print(f"[FILLED] Ticket {ticket} ({orig})")
                    broadcast_open(pos, label=f"FILLED {orig}")
                    del pending_type_cache[ticket]
                else:
                    print(f"[NEW POSITION] Ticket {ticket}")
                    broadcast_open(pos, label="NEW")

            # --- Pending order hilang (cancel / filled) ---
            for ticket in known_pending - cur_pending:
                if ticket not in cur_positions:
                    hist = mt5.history_orders_get(ticket=ticket)
                    if hist and hist[0].state == mt5.ORDER_STATE_CANCELED:
                        print(f"[CANCELLED] Ticket {ticket}")
                        broadcast_cancel(hist[0])

            # --- Posisi hilang (SL / TP / manual) ---
            for ticket in known_positions - cur_positions:
                deal = get_close_deal(ticket)
                if deal is None:
                    continue
                if deal.reason == mt5.DEAL_REASON_SL:
                    label = "HIT SL"
                elif deal.reason == mt5.DEAL_REASON_TP:
                    label = "HIT TP"
                else:
                    label = "CLOSED MANUAL"
                print(f"[{label}] Ticket {ticket} | Profit: {deal.profit:+.2f}")
                broadcast_close(deal, label)

            # --- Perubahan SL/TP posisi existing ---
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
                            what.append(f"SL: {old_sl}→{new_sl}")
                        if new_tp != old_tp:
                            what.append(f"TP: {old_tp}→{new_tp}")
                        print(f"[SL/TP UPDATE] Ticket {ticket} — {', '.join(what)}")
                        broadcast_open(positions[0], label="UPDATE SL/TP")

            # --- Perubahan harga/SL/TP pending order existing ---
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
                            what.append(f"Entry: {old_price}→{new_price}")
                        if new_sl != old_sl:
                            what.append(f"SL: {old_sl}→{new_sl}")
                        if new_tp != old_tp:
                            what.append(f"TP: {old_tp}→{new_tp}")
                        print(f"[PENDING UPDATE] Ticket {ticket} — {', '.join(what)}")
                        broadcast_open(orders[0], label="UPDATE PENDING")

            known_pending    = cur_pending
            known_positions  = cur_positions
            position_sltp    = cur_sltp
            pending_snapshot = cur_pending_snap
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[MT5 Monitor v2] Stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(CHECK_INTERVAL)

    mt5.shutdown()


if __name__ == "__main__":
    main()
