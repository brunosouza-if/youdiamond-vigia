# Vigia de promocoes: le canais publicos t.me/s/<canal>, filtra por palavra e preco e posta no grupo via bot.
# Roda no GitHub Actions (TG_TOKEN e TG_CHAT em secrets). Mensagem em HTML: precos de venda em negrito + nota de facilidade de venda.
import os, re, json, html, time, datetime, urllib.request, urllib.parse
CANAIS = ["cjpromos","BenchPromos","Fraguas84Oficial","juaocupons","LaPromotion","souzzatechpromos","placasdevideoparaosbetinha"]
# palavra-chave -> preco maximo (alvo). Ajustar com a lista_cacada_promos.html
ALVOS = {"ugreen":45,"f75":260,"aula":260,"easysmx":110,"hyperx":220,"echo dot":260,"gamesir":120,"8bitdo":260,"fifine":200,"controle":250,"gamepad":250,"joystick":250,"cabo":25,"carregador":60,"fone":120,"teclado":200,"mouse":120,"headset":200,"microfone":200,"ssd":300,"placa de v":99999,"rtx":99999,"action figure":60,"fonte":500,"placa m":99999,"processador":99999,"ryzen":99999,"memória":400,"memoria":400,"ddr4":400,"ddr5":600,"monitor":99999,"water cooler":400,"gabinete":300,"rádio":150,"radio":150,"walkie":200,"smartwatch":200,"caixa de som":150,"webcam":150,"roteador":150,"tv box":200,"gtx":99999,"radeon":99999,"nvme":300,"hd externo":300,"powerbank":100,"power bank":100}
# Demanda base por categoria na Shopee (0-100): giro rapido e ticket baixo pontuam mais.
DEMANDA = {"cabo":85,"carregador":85,"fone":85,"mouse":80,"teclado":75,"headset":75,"controle":75,"gamepad":75,"joystick":75,"ugreen":85,"f75":70,"aula":70,"easysmx":75,"hyperx":75,"echo dot":70,"gamesir":70,"8bitdo":70,"fifine":65,
           "caixa de som":70,"smartwatch":65,"powerbank":70,"power bank":70,"webcam":65,"microfone":65,"ssd":65,"nvme":65,"memória":60,"memoria":60,"ddr4":60,"ddr5":60,"hd externo":60,
           "action figure":55,"tv box":55,"roteador":55,"rádio":50,"radio":50,"walkie":50,"monitor":45,"placa de v":45,"rtx":45,"gtx":45,"radeon":45,"processador":45,"ryzen":45,"fonte":50,"gabinete":45,"water cooler":45,"placa m":45}
MARCAS = ["ugreen","hyperx","baseus","logitech","redragon","kingston","samsung","xiaomi","jbl","echo","amazon","aula","8bitdo","gamesir","fifine","razer","sandisk","wd ","crucial","anker","tp-link","intelbras"]
VISTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vigia_visto.json")
visto = set(json.load(open(VISTO))) if os.path.exists(VISTO) else set()
def get(u, data=None): return urllib.request.urlopen(urllib.request.Request(u, data=data, headers={"User-Agent":"Mozilla/5.0"}), timeout=20).read().decode("utf-8","ignore")

LUCRO=0.12
def _venda(custo, canal):
    if canal=="shopee":
        extra = 0.05 if datetime.date.today() <= datetime.date(2026,12,1) else 0   # Campanha de Destaque ate 01/12
        faixas=[(0,79.99,.20+extra,4.5),(80,99.99,.14+extra,16),(100,199.99,.14+extra,20),(200,1e9,.14+extra,26)]
    else:
        faixas=[(0,49.99,.10,4),(50,1e9,.06,4)]
    for lo,hi,pc,fx in faixas:
        p=(custo+fx)/(1-pc-LUCRO)
        if p<=hi: return max(p,lo)
    return p
def _nota(k, low, m, alvo, venda_shopee):
    """Facilidade de venda 0-100: demanda da categoria + preco de venda + folga ate o alvo + marca + sinais do post. Heuristica, nao dado real de mercado."""
    n = DEMANDA.get(k, 55)
    n += 10 if venda_shopee <= 80 else 5 if venda_shopee <= 200 else -10 if venda_shopee > 500 else 0
    n += 10 if m <= 0.7*alvo else 5 if m <= 0.9*alvo else 0
    n += 5 if any(b in low for b in MARCAS) else 0
    n += min(10, 5*sum(1 for s in ("menor pre","hist","cupom","frete gr") if s in low))
    return max(15, min(95, n))
def _rotulo(n): return "alta" if n >= 75 else "média" if n >= 55 else "baixa"
_RE_PRECO = r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)"
def _precos(t):
    """Preco de compra do produto em primeiro lugar. Ignora parcela ('12x R$ 24,33', 'R$ 24,33/mes'), cupom, frete,
    cashback e desconto; prefere o valor depois de 'por'/'pix'/'a vista' (promo 'de X por Y'); senao o primeiro R$ do post.
    Valor menor que 20% do maior e tratado como parcela/cupom e descartado. (06/11: AULA F75 saiu como R$ 24,33 = parcela.)"""
    low = t.lower()
    vals = []
    for m_ in re.finditer(_RE_PRECO, t):
        a, b = low[max(0, m_.start()-28):m_.start()], low[m_.end():m_.end()+14]
        if re.search(r"\d+\s*x\s*(de\s*)?$|cupom|frete|cashback|desconto|economi|off\b", a) \
           or re.search(r"^\s*(/|por|ao)?\s*m[eê]s|^\s*(de|em)?\s*cashback|^\s*(de\s*)?desconto", b):
            continue
        v = float(m_.group(1).replace(".", "").replace(",", "."))
        pref = bool(re.search(r"(por|pix|[àa] vista|agora)\W*$", low[max(0, m_.start()-14):m_.start()]))
        vals.append((v, pref))
    if not vals: return []
    top = max(v for v, _ in vals)
    vals = [(v, p) for v, p in vals if v >= 0.2*top] or vals
    pref = [v for v, p in vals if p]
    return [pref[0] if pref else vals[0][0]] + [v for v, _ in vals]

achados = []
for c in CANAIS:
    try: pg = get(f"https://t.me/s/{c}")
    except Exception as e: continue
    for post, txt in re.findall(r'data-post="([^"]+)".*?tgme_widget_message_text[^>]*>(.*?)</div>', pg, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", " ", txt)); low = t.lower()
        if post in visto: continue
        precos = _precos(t)
        for k, mx in ALVOS.items():
            if re.search(r"\b"+re.escape(k)+r"s?\b", low) and not re.search(r"controle de |hidratante|facial|creme|shampoo|perfume", low) and precos and precos[0] <= mx:
                m = precos[0]; vs = _venda(m,'shopee'); vt = _venda(m,'tiktok'); n = _nota(k, low, m, mx, vs)
                br = lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                msg = "\n".join([html.escape(" ".join(t.split())[:90]),
                                 f"Achado: {br(m)}",
                                 f"<b>Shopee: {br(vs)}</b>",
                                 f"<b>TikTok: {br(vt)}</b>",
                                 f"Facilidade de venda: <b>{n}%</b> ({_rotulo(n)})",
                                 f"(taxas incluídas, lucro líquido {int(LUCRO*100)}%)",
                                 f"https://t.me/{post}"])
                achados.append((post, msg)); break
tok = (os.environ.get("TG_TOKEN") or "").replace("﻿","").strip()
chat = (os.environ.get("TG_CHAT") or "-5259574389").replace("﻿","").strip()
print("achados:", len(achados), "| vistos:", len(visto))
for post,a in achados[:12]:
    if not (tok and chat): print(a); continue
    try:
        get(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode({"chat_id":chat,"text":a,"parse_mode":"HTML"}).encode())
        visto.add(post); json.dump(sorted(visto), open(VISTO,"w")); time.sleep(4)
    except Exception as e:
        print("erro envio", e); break
