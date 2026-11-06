# Vigia de promocoes: le canais publicos t.me/s/<canal>, filtra por palavra e preco e posta no grupo via bot.
# Uso: python vigia_promos.py  (token em variavel de ambiente TG_TOKEN, chat em TG_CHAT; nunca gravar no arquivo)
import os, re, json, html, urllib.request, urllib.parse
CANAIS = ["cjpromos","BenchPromos","Fraguas84Oficial","juaocupons","LaPromotion","souzzatechpromos","placasdevideoparaosbetinha"]
# palavra-chave -> preco maximo (alvo). Ajustar com a lista_cacada_promos.html
ALVOS = {"ugreen":45,"f75":260,"aula":260,"easysmx":110,"hyperx":220,"echo dot":260,"gamesir":120,"8bitdo":260,"fifine":200,"controle":150,"gamepad":150,"joystick":150,"cabo":25,"carregador":60,"fone":120,"teclado":200,"mouse":120,"headset":200,"microfone":200,"ssd":300,"placa de v":99999,"rtx":99999,"action figure":60,"fonte":500,"placa m":99999,"processador":99999,"ryzen":99999,"memória":400,"memoria":400,"ddr4":400,"ddr5":600,"monitor":99999,"water cooler":400,"gabinete":300,"rádio":150,"radio":150,"walkie":200,"smartwatch":200,"caixa de som":150,"webcam":150,"roteador":150,"tv box":200,"gtx":99999,"radeon":99999,"nvme":300,"hd externo":300,"powerbank":100,"power bank":100}
VISTO = os.path.join(os.path.dirname(__file__), "vigia_visto.json")
visto = set(json.load(open(VISTO))) if os.path.exists(VISTO) else set()
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=20).read().decode("utf-8","ignore")

LUCRO=0.12
def _venda(custo, canal):
    if canal=="shopee":
        extra = 0.05 if __import__("datetime").date.today() <= __import__("datetime").date(2026,12,1) else 0
        faixas=[(0,79.99,.20+extra,4.5),(80,99.99,.14+extra,16),(100,199.99,.14+extra,20),(200,1e9,.14+extra,26)]
    else:
        faixas=[(0,49.99,.10,4),(50,1e9,.06,4)]
    for lo,hi,pc,fx in faixas:
        p=(custo+fx)/(1-pc-LUCRO)
        if p<=hi: return max(p,lo)
    return p
try:
    _P = json.load(open(r"C:\Users\Asus TUF F15\Documents\You Diamond Precificador\dados.json", encoding="utf-8"))["produtos"]
except Exception: _P = []
def _meu(k, low):
    for p in _P:
        if k.rstrip("s") in p.get("nome", "").lower():
            try: return p["nome"][:40], float(str(p["custo"]).replace(",", "."))
            except Exception: pass
    return None
achados = []
for c in CANAIS:
    try: pg = get(f"https://t.me/s/{c}")
    except Exception as e: continue
    for post, txt in re.findall(r'data-post="([^"]+)".*?tgme_widget_message_text[^>]*>(.*?)</div>', pg, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", " ", txt)); low = t.lower()
        if post in visto: continue
        precos = [float(p.replace(".","").replace(",",".")) for p in re.findall(r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)", t)]
        for k, mx in ALVOS.items():
            if re.search(r"\b"+re.escape(k)+r"s?\b", low) and not re.search(r"controle de |hidratante|facial|creme|shampoo|perfume", low) and precos and min(precos) <= mx:
                m = min(precos)
                msg = "\n".join([" ".join(t.split())[:90], f"Achado: R$ {m:.2f}", (f"Seu custo hoje: R$ {_meu(k,low)[1]:.2f} ({_meu(k,low)[0]})" if _meu(k,low) else "Produto novo na sua loja"), f"Vender na Shopee por R$ {_venda(m,'shopee'):.2f}", f"Vender no TikTok por R$ {_venda(m,'tiktok'):.2f}", f"(taxas incluidas, lucro liquido {int(LUCRO*100)}%)", f"https://t.me/{post}"])
                achados.append((post, msg)); break
_tf=os.path.join(os.path.dirname(__file__),"..","memoria","tg_bot_token.txt")
tok = os.environ.get("TG_TOKEN") or (open(_tf).read().strip() if os.path.exists(_tf) else None)
tok = tok.replace("﻿","").strip() if tok else tok
chat = (os.environ.get("TG_CHAT") or "-5259574389").replace("﻿","").strip()
import time
print("achados:", len(achados), "| vistos:", len(visto))
for post,a in achados[:8]:
    if not (tok and chat): print(a); continue
    try:
        get(f"https://api.telegram.org/bot{tok}/sendMessage?" + urllib.parse.urlencode({"chat_id":chat,"text":a}))
        visto.add(post); json.dump(sorted(visto), open(VISTO,"w")); time.sleep(4)
    except Exception as e:
        print("erro envio", e); break
