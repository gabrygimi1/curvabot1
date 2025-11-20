import requests
import time
import json
import concurrent.futures
import random
import os

# =========================================
# CONFIG
# =========================================

WEBHOOK = "https://discord.com/api/webhooks/1441088068802318347/2h9ChK1MH23WR6665v3CKPQ4g2Q5j8ETaqCguqv0sPAC6NEZbDETaERG_ed2C0rYd9P7"

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; ultrafast-bot)",
    "accept": "*/*",
}

SETTORI_CURVA = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"]

INTERVALLO = 0.8  # secondi

session = requests.Session()

# =========================================
# FUNZIONI
# =========================================

def send_discord(msg: str):
    try:
        session.post(WEBHOOK, json={"content": msg}, timeout=5)
        print("🔔 Notifica inviata!")
    except Exception as e:
        print("❌ Errore invio webhook:", e)


def estrai_match_info(url: str):
    after = url.split("/match/")[1]
    evento, progressivo = after.split("/")[:2]
    return evento, progressivo


def parse_variable(html: str, varname: str):
    marker = f"var {varname} ="
    i = html.find(marker)
    if i == -1:
        return None

    start = i + len(marker)
    end = html.find("};", start)
    if end == -1:
        return None

    try:
        raw = html[start:end + 1].strip()
        return json.loads(raw)
    except:
        return None


def check_settore(evento: str, progressivo: str, settore: str):
    url = f"https://tickets.acffiorentina.com/tickets/match/{evento}/{progressivo}/G_CS/{settore}/0"

    try:
        r = session.get(url, headers=HEADERS, timeout=4)
    except:
        return settore, None, None, url

    if r.status_code != 200:
        return settore, None, None, url

    data = parse_variable(r.text, "settore")
    if not data:
        return settore, None, None, url

    disponibili = data.get("totalePostiLiberi", 0)
    capienza = data.get("capienza", 0)

    return settore, disponibili, capienza, url


# =========================================
# MAIN
# =========================================

def main():

    print("============================")
    print("   AVVIO BOT CURVA FERROVIA ")
    print("============================\n")

    # Legge MATCH_URL da variabili ambiente (Railway)
    match_url = os.getenv("MATCH_URL")

    if not match_url:
        print("❌ ERRORE: Devi impostare MATCH_URL nelle variabili ambiente Railway!")
        print("Esempio MATCH_URL = https://tickets.acffiorentina.com/tickets/match/M30339/002")
        return

    evento, progressivo = estrai_match_info(match_url)

    print("\n==============================")
    print("   MONITOR CURVA FERROVIA (ULTRA)")
    print("==============================\n")

    print(f"📌 Evento: {evento} / {progressivo}")
    print("📡 Monitor parallelo su S01 → S10 (ULTRA FAST MODE)\n")

    notificati = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while True:

            futures = {
                executor.submit(check_settore, evento, progressivo, settore): settore
                for settore in SETTORI_CURVA
            }

            for future in concurrent.futures.as_completed(futures):
                settore = futures[future]

                try:
                    s, disponibili, capienza, link = future.result()
                except:
                    print(f"❌ Errore settore {settore}")
                    continue

                if disponibili is None:
                    print(f"⚠️ {settore} offline…")
                    continue

                if disponibili > 0:
                    print(f"🔥 {settore} → {disponibili} disponibili!")

                    if settore not in notificati:
                        msg = (
                            f"🔥 **POSTI DISPONIBILI — CURVA FERROVIA** 🔥\n"
                            f"🎯 Settore **{settore}**\n"
                            f"📌 Disponibili: **{disponibili}** su {capienza}\n"
                            f"🔗 {link}"
                        )
                        send_discord(msg)
                        notificati.add(settore)

                else:
                    print(f"⏳ {settore}: 0 posti")

            time.sleep(INTERVALLO)


if __name__ == "__main__":
    main()
