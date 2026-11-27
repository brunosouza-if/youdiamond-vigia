# Vigia de promocoes: le canais publicos t.me/s/<canal>, filtra por palavra e preco e posta no grupo via bot.
# Roda no GitHub Actions (TG_TOKEN e TG_CHAT em secrets). Mensagem em HTML: precos de venda em negrito + nota de facilidade de venda.
import os, re, json, html, time, datetime, urllib.request, urllib.parse
CANAIS = ["cjpromos","BenchPromos","Fraguas84Oficial","juaocupons","LaPromotion","souzzatechpromos","placasdevideoparaosbetinha","chinacuponsbr","ImportaHardwareCanal","peperaiohardware","aliexpressofertasnew"]
# palavra-chave -> preco maximo (alvo). Ajustar com a lista_cacada_promos.html
ALVOS = {"smarttag":150,"smart tag":150,"airtag":150,"superframe":400,"super frame":400,"havit":250,"infinity":600,"alok":600,"ugreen":45,"f75":330,"aula":330,"easysmx":110,"hyperx":220,"echo dot":330,"gamesir":180,"8bitdo":260,"fifine":230,"controle":330,"gamepad":250,"joystick":250,"cabo":25,"carregador":60,"fone":180,"tws":180,"earbuds":180,"earphone":180,"teclado":280,"mouse":120,"headset":220,"microfone":200,"ssd":300,"placa de v":99999,"rtx":99999,"action figure":60,"fonte":400,"placa m":99999,"processador":99999,"ryzen":99999,"memória":400,"memoria":400,"ddr4":400,"ddr5":600,"water cooler":400,"gabinete":300,"rádio":150,"radio":150,"walkie":200,"smartwatch":200,"caixa de som":340,"webcam":150,"roteador":150,"tv box":200,"gtx":99999,"radeon":99999,"nvme":300,"hd externo":300,"powerbank":100,"power bank":100,"tv ":4000,"smart tv":4000,"televis":4000,"notebook":5000,"celular":3000,"smartphone":3000,"iphone":6000,"galaxy":3000,"xiaomi":2500,"redmi":2500,"poco":2500,"tablet":2500,"ipad":5000,"console":4000,"playstation":4000,"ps5":4000,"xbox":4000,"alexa":330,"waaw":340,"machenike":150,"coibeu":40,"filtro de linha":40,"kindle":600,"soundbar":1000,"projetor":2000,"cadeira gamer":1500,"impressora":1500,"carregador port":150,"hub usb":150,"suporte":150}
GATE_BOM = {"fone","headset","tws","earbuds","earphone"}
BOA_MARCA = r"havit|superframe|super frame|jbl|edifier|soundcore|anker|qcy|baseus|sony|jabra|philips|haylou|1more|moondrop|sennheiser|bose|airpods|apple|samsung|galaxy buds|redmi buds|xiaomi|lenovo|ugreen|hyperx|logitech|razer|steelseries|corsair|redragon|fifine|motorola|harman|marshall|skullcandy|oneplus|realme|nothing|tozo|soundpeats|lg tone|jlab"
# Demanda base por categoria na Shopee (0-100): giro rapido e ticket baixo pontuam mais.
DEMANDA = {"smarttag":65,"smart tag":65,"airtag":65,"cabo":85,"carregador":85,"fone":85,"mouse":80,"teclado":75,"headset":75,"controle":75,"gamepad":75,"joystick":75,"ugreen":85,"f75":70,"aula":70,"easysmx":75,"hyperx":75,"echo dot":70,"gamesir":70,"8bitdo":70,"fifine":65,
           "caixa de som":70,"smartwatch":65,"powerbank":70,"power bank":70,"webcam":65,"microfone":65,"ssd":65,"nvme":65,"memória":60,"memoria":60,"ddr4":60,"ddr5":60,"hd externo":60,
           "action figure":55,"tv box":55,"roteador":55,"rádio":50,"radio":50,"walkie":50,"placa de v":45,"rtx":45,"gtx":45,"radeon":45,"processador":45,"ryzen":45,"fonte":50,"gabinete":45,"water cooler":45,"placa m":45,"tv ":60,"smart tv":60,"televis":60,"notebook":55,"celular":65,"smartphone":65,"iphone":65,"galaxy":65,"xiaomi":70,"redmi":70,"poco":65,"tablet":55,"ipad":55,"console":55,"playstation":55,"ps5":55,"xbox":50,"alexa":70,"kindle":55,"soundbar":50,"projetor":50,"cadeira gamer":45,"impressora":45,"carregador port":75,"hub usb":70,"suporte":60}
MARCAS = ["ugreen","hyperx","baseus","logitech","redragon","kingston","samsung","xiaomi","jbl","echo","amazon","aula","8bitdo","gamesir","fifine","razer","sandisk","wd ","crucial","anker","tp-link","intelbras"]
VISTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vigia_visto.json")
# O que foi de fato mandado ao grupo (os 200 ultimos): o painel do Jarvis mostra daqui, o visto so guarda ids.
ENVIADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vigia_enviados.json")
ENVIADOS_MAX = 200
visto = set(json.load(open(VISTO))) if os.path.exists(VISTO) else set()
def get(u, data=None): return urllib.request.urlopen(urllib.request.Request(u, data=data, headers={"User-Agent":"Mozilla/5.0"}), timeout=20).read().decode("utf-8","ignore")

LUCRO=0.12
def _venda(custo, canal):
    if canal=="shopee":
        extra = (0.05 if datetime.date.today() <= datetime.date(2026,12,1) else 0) + 0.03   # Campanha de Destaque ate 01/12
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
        if re.search(r"(?<!suporte de )(?<!suporte para )monitor(es)?|nintendo|switch|placa de v|\brtx\b|\bgtx\b|radeon|celular|smartphone|iphone|galaxy|redmi|\bpoco\b|moto g|(?<!para )(?<!de )(?<!em )(?<!pra )\bjogos?\b|steam|\bpsn\b|gift card|game pass|eshop|epic games|xbox live|cd key|mídia física|midia fisica|espelho|notebook|tablet|\bipad|televis|smart tv|\broku\b|toshiba|\btv (?!box)", low) and "tcl" not in low: continue  # Bruno 24/11: sem placa de video nem celular
        if re.search(r"playstation|\bps ?[45]\b|\bps plus\b", low) and not re.search(r"controle|dualsense|headset|fone|console|suporte|carregador|base|cabo", low): continue  # Bruno 26/11: sem jogo de PS4/PS5
        precos = _precos(t)
        for k, mx in ALVOS.items():
            if k in GATE_BOM and not re.search(BOA_MARCA, low): continue  # Bruno 24/11: fone so de marca boa
            if re.search(r"\b"+re.escape(k)+r"s?\b", low) and not re.search(r"controle de |hidratante|facial|creme|shampoo|perfume|roupa|feminin|masculin|camis|blusa|vestido|calça|calca|bermuda|jaqueta|moletom|cueca|legging|saia|suti|sapato|tênis|tenis|sandália|sandalia|chinelo", low) and precos and precos[0] <= mx:
                m = precos[0]; vs = _venda(m,'shopee'); vt = _venda(m,'tiktok'); n = _nota(k, low, m, mx, vs)
                br = lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                top = m <= 0.7*mx and n >= 70   # preco muito bom e vende facil: etiqueta #COMPRAR (Bruno 24/11)
                msg = "\n".join(([("🏷 <b>#COMPRAR</b>")] if top else []) + [html.escape(" ".join(t.split())[:90]),
                                 f"Achado: {br(m)}",
                                 f"<b>Shopee: {br(vs)}</b>",
                                 f"<b>TikTok: {br(vt)}</b>",
                                 f"Facilidade de venda: <b>{n}%</b> ({_rotulo(n)})",
                                 f"(taxas incluídas, lucro líquido {int(LUCRO*100)}%)",
                                 f"https://t.me/{post}"])
                info = {"post": post, "titulo": " ".join(t.split())[:90], "achado": round(m, 2),
                        "shopee": round(vs, 2), "tiktok": round(vt, 2), "nota": n, "alvo": k}
                achados.append((post, msg, info)); break
# --- AliExpress proprio (Bruno 25/11): busca por palavra-chave sem login, mesmos filtros e conta de margem ---
ALI_TERMOS = {"ugreen cabo":"ugreen","ugreen carregador":"ugreen","baseus":"cabo","rastreador":"smarttag","airtag":"airtag","8bitdo":"8bitdo","gamesir":"gamesir","easysmx":"easysmx","fifine":"fifine","hyperx":"hyperx","aula f75":"f75","redragon":"mouse","anker":"carregador","xiaomi fone":"fone"}
ALI_MAX = {"ugreen":19}   # custo maximo (preco de venda ~R$ 41 menos taxa Shopee e 12% liquido)
_H_ALI = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36","Accept-Language":"pt-BR"}
def _chave_ali():
    k, sec = os.environ.get("ALI_KEY"), os.environ.get("ALI_SECRET")
    if k and sec: return k.strip(), sec.strip()
    try:
        d = dict(l.strip().split("=",1) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "memoria", "aliexpress_api.txt")) if "=" in l)
        return d["AppKey"], d["AppSecret"]
    except Exception: return None, None
_IMG = {}
def _busca_ali(q):
    import hashlib, hmac
    k, sec = _chave_ali()
    if not k: raise RuntimeError("sem chave AliExpress")
    p = {"app_key":k,"timestamp":str(int(time.time()*1000)),"sign_method":"sha256","method":"aliexpress.affiliate.product.query","keywords":q,"target_currency":"BRL","target_language":"PT","ship_to_country":"BR","page_size":"30","sort":"LAST_VOLUME_DESC","tracking_id":"default","fields":"product_id,product_title,target_sale_price,product_main_image_url"}
    p["sign"] = hmac.new(sec.encode(), "".join(a+p[a] for a in sorted(p)).encode(), hashlib.sha256).hexdigest().upper()
    r = json.loads(urllib.request.urlopen("https://api-sg.aliexpress.com/sync?"+urllib.parse.urlencode(p), timeout=30).read().decode())
    prods = r["aliexpress_affiliate_product_query_response"]["resp_result"]["result"]["products"]["product"]
    for x in prods: _IMG[str(x["product_id"])] = x.get("product_main_image_url","")
    return [(str(x["product_id"]), x["product_title"], float(x["target_sale_price"])) for x in prods]
for q, k in ALI_TERMOS.items():
    mx = ALI_MAX.get(k) or (ALVOS.get(k) or 0)*0.65   # AliExpress: so o que da lucro de verdade (Bruno 25/11)
    if not mx: continue
    try: itens = _busca_ali(q)
    except Exception as e:
        print("aliexpress erro", q, e); continue
    n_q = 0
    for pid, t, m in itens[:30]:
        post = "aliexpress:" + pid; low = t.lower()
        if post in visto or m > mx or m < 0.15*mx: continue
        if k in GATE_BOM and not re.search(BOA_MARCA, low): continue
        if not re.search(r"\b"+re.escape(q.split()[0])+r"\b", low): continue   # titulo tem que citar a marca/termo buscado
        vs = _venda(m,'shopee'); vt = _venda(m,'tiktok'); n = _nota(k, low, m, mx, vs)
        br = lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
        top = m <= 0.7*mx and n >= 70
        msg = "\n".join(([("🏷 <b>#COMPRAR</b>")] if top else []) + ["🛒 AliExpress (API própria)", html.escape(" ".join(t.split())[:90]),
                         f"Achado: {br(m)}", f"<b>Shopee: {br(vs)}</b>", f"<b>TikTok: {br(vt)}</b>",
                         f"Facilidade de venda: <b>{n}%</b> ({_rotulo(n)})", f"(taxas incluídas, lucro líquido {int(LUCRO*100)}%)",
                         f"https://pt.aliexpress.com/item/{pid}.html"])
        achados.append((post, msg, {"post": post, "titulo": " ".join(t.split())[:90], "achado": round(m,2), "shopee": round(vs,2), "tiktok": round(vt,2), "nota": n, "alvo": k}))
        n_q += 1
        if n_q >= 2: break
    time.sleep(3)
tok = (os.environ.get("TG_TOKEN") or "").replace("﻿","").strip()
chat = (os.environ.get("TG_CHAT") or "-5259574389").replace("﻿","").strip()
print("achados:", len(achados), "| vistos:", len(visto))
def _registrar_envio(info):
    try: env = json.load(open(ENVIADOS, encoding="utf-8")) if os.path.exists(ENVIADOS) else []
    except ValueError: env = []
    info = dict(info, quando=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    env = (env + [info])[-ENVIADOS_MAX:]
    json.dump(env, open(ENVIADOS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for _x in achados:  # Bruno 27/11 (Black): TCL 65 nunca filtrado por nota
    if "tcl" in _x[1].lower() and "65" in _x[1]: _x[2]["nota"] = 99
achados = sorted([x for x in achados if x[2].get('nota',0) >= 65], key=lambda x: -x[2].get('nota',0))  # Bruno 26/11: menos enxurrada, so nota 65+
for post,a,info in achados[:4]:
    if not (tok and chat): print(a); continue
    try:
        _img = _IMG.get(post.split(":",1)[-1]) if post.startswith("aliexpress:") else None
        try:
            if _img and len(a) <= 1000: get(f"https://api.telegram.org/bot{tok}/sendPhoto", urllib.parse.urlencode({"chat_id":chat,"photo":_img,"caption":a,"parse_mode":"HTML"}).encode())
            else: raise ValueError("sem foto")
        except Exception:
            get(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode({"chat_id":chat,"text":a,"parse_mode":"HTML"}).encode())
        visto.add(post); json.dump(sorted(visto), open(VISTO,"w")); _registrar_envio(info); time.sleep(4)
        if "tcl" in a.lower() and re.search(r"65", a):  # Bruno 24/11: TCL 65 pol avisa no privado
            try: get(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode({"chat_id":868917098,"text":"TCL 65 em promo: "+a,"parse_mode":"HTML"}).encode())
            except Exception as e: print("erro privado", e)
    except Exception as e:
        print("erro envio", e); break
