import re
import MetaTrader5 as mt5
import requests
import time

DISCORD_BOT_TOKEN = "MTQ4MDYyNTUxMjczMTY0NDAyNg.Gi_D2M.huG_wvH6Y-wbk6z5eyKV-apvZ-HJie4j75z1aQ"
DISCORD_CHANNEL_ID = "1480611447225716737"
DISCORD_API = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"

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

BUY_TYPES  = {mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT,
              mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_BUY_STOP_LIMIT}
SELL_TYPES = {mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT,
              mt5.ORDER_TYPE_SELL_STOP, mt5.ORDER_TYPE_SELL_STOP_LIMIT}


def clean_symbol(symbol: str) -> str:
    return re.sub(r'[a-z.+#\-]+$', '', symbol)


def fmt_price(symbol: str, price: float) -> str:
    info = mt5.symbol_info(symbol)
    digits = info.digits if info else 5
    return f"{price:.{digits}f}"


def direction(order_type: int) -> str:
    return "BUY NOW" if order_type in BUY_TYPES else "SELL NOW"


# ─────────────────────────────────────────────
#  Formatters
# ─────────────────────────────────────────────

def fmt_open(order, label="NEW") -> str:
    symbol = clean_symbol(order.symbol)
    entry  = fmt_price(order.symbol, order.price_open)
    sl     = fmt_price(order.symbol, order.sl) if order.sl != 0.0 else None
    tp     = fmt_price(order.symbol, order.tp) if order.tp != 0.0 else None
    action = direction(order.type)

    if label == "UPDATE SL/TP":
        lines = [
            f"SL : {sl if sl is not None else '-'}",
            f"TP : {tp if tp is not None else '-'}",
        ]
    elif label == "UPDATE PENDING":
        lines = [
            f"ORDER DIUPDATE ✏️\n{symbol} {action}",
            "",
            f"HARGA : {entry}",
            "",
            f"SL : {sl if sl is not None else '-'}",
            f"TP : {tp if tp is not None else '-'}",
        ]
    else:
        lines = [
            f"{symbol} {action}",
            "",
            f"HARGA : {entry}",
        ]
    return "\n".join(lines)


def fmt_close(deal, label: str) -> str:
    if label == "HIT TP":
        return "YOOOOOO TAKE PROFIT ✅"
    elif label == "HIT SL":
        return "SL GUYS, SORRY YA NT ❌"
    else:
        return "CLOSE PROFIT ✅"


def fmt_cancel(hist_order) -> str:
    order_type = ORDER_TYPE_NAMES.get(hist_order.type, "ORDER")
    return (
        f"❌ ORDER CANCEL\n"
        f"{clean_symbol(hist_order.symbol)} {order_type}\n"
        f"HARGA : {fmt_price(hist_order.symbol, hist_order.price_open)}"
    )


# ─────────────────────────────────────────────
#  Discord API
# ─────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    "Content-Type": "application/json",
}


def send_discord(message: str, reply_to: int = None) -> int:
    if not message.strip():
        return None
    payload = {"content": message}
    if reply_to:
        payload["message_reference"] = {"message_id": str(reply_to)}
    try:
        r = requests.post(DISCORD_API, json=payload, headers=HEADERS, timeout=10)
        if r.ok:
            return int(r.json().get("id", 0)) or None
        else:
            print(f"[DISCORD ERROR] {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[DISCORD EXCEPTION] {e}")
    return None


def edit_discord(message_id: int, message: str):
    if not message.strip():
        return
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages/{message_id}"
    try:
        r = requests.patch(url, json={"content": message}, headers=HEADERS, timeout=10)
        if not r.ok:
            print(f"[DISCORD EDIT ERROR] {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[DISCORD EDIT EXCEPTION] {e}")


# ─────────────────────────────────────────────
#  State & broadcast
# ─────────────────────────────────────────────

ticket_msg_ids = {}
sltp_msg_ids   = {}


def broadcast_open(order, label="NEW"):
    ticket    = order.ticket
    is_new    = label == "NEW"
    is_sltp   = label == "UPDATE SL/TP"
    is_adjust = is_sltp and ticket in sltp_msg_ids

    msg = fmt_open(order, label)

    if is_sltp and is_adjust:
        edit_discord(sltp_msg_ids[ticket], msg)
    else:
        reply_to = None
        if not is_new and ticket in ticket_msg_ids:
            reply_to = ticket_msg_ids[ticket]
        mid = send_discord(msg, reply_to=reply_to)
        if is_new:
            ticket_msg_ids[ticket] = mid
        elif is_sltp:
            sltp_msg_ids[ticket] = mid


def broadcast_close(deal, label: str):
    ticket   = deal.position_id
    reply_to = ticket_msg_ids.get(ticket)
    send_discord(fmt_close(deal, label), reply_to=reply_to)
    ticket_msg_ids.pop(ticket, None)
    sltp_msg_ids.pop(ticket, None)


def broadcast_cancel(hist_order):
    ticket   = hist_order.ticket
    reply_to = ticket_msg_ids.get(ticket)
    send_discord(fmt_cancel(hist_order), reply_to=reply_to)
    ticket_msg_ids.pop(ticket, None)
    sltp_msg_ids.pop(ticket, None)


# ─────────────────────────────────────────────
#  MT5 helpers
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
    print("[MT5 Monitor v3] Starting...")

    if not mt5.initialize():
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

    print(f"[MT5] Monitoring started. Discord channel: {DISCORD_CHANNEL_ID} | Interval: {CHECK_INTERVAL}s\n")

    while True:
        try:
            cur_pending   = get_pending_tickets()
            cur_positions = get_position_tickets()

            for ticket in cur_pending - known_pending:
                orders = mt5.orders_get(ticket=ticket)
                if orders:
                    pending_type_cache[ticket] = orders[0].type
                    print(f"[NEW PENDING] Ticket {ticket}")
                    broadcast_open(orders[0], label="NEW")

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

            for ticket in known_pending - cur_pending:
                if ticket not in cur_positions:
                    hist = mt5.history_orders_get(ticket=ticket)
                    if hist and hist[0].state == mt5.ORDER_STATE_CANCELED:
                        print(f"[CANCELLED] Ticket {ticket}")
                        broadcast_cancel(hist[0])

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

            cur_sltp = snapshot_positions()
            for ticket, (new_sl, new_tp) in cur_sltp.items():
                if ticket not in position_sltp:
                    continue
                old_sl, old_tp = position_sltp[ticket]
                if new_sl != old_sl or new_tp != old_tp:
                    positions = mt5.positions_get(ticket=ticket)
                    if positions:
                        print(f"[SL/TP UPDATE] Ticket {ticket}")
                        broadcast_open(positions[0], label="UPDATE SL/TP")

            cur_pending_snap = snapshot_pending()
            for ticket, (new_price, new_sl, new_tp) in cur_pending_snap.items():
                if ticket not in pending_snapshot:
                    continue
                old_price, old_sl, old_tp = pending_snapshot[ticket]
                if new_price != old_price or new_sl != old_sl or new_tp != old_tp:
                    orders = mt5.orders_get(ticket=ticket)
                    if orders:
                        print(f"[PENDING UPDATE] Ticket {ticket}")
                        broadcast_open(orders[0], label="UPDATE PENDING")

            known_pending    = cur_pending
            known_positions  = cur_positions
            position_sltp    = cur_sltp
            pending_snapshot = cur_pending_snap
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[MT5 Monitor v3] Stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(CHECK_INTERVAL)

    mt5.shutdown()


if __name__ == "__main__":
    main()
