# Vigia publico: le os mesmos canais de promo (t.me/s/<canal>), pega o link Shopee de cada post, troca pelo link de afiliado do Bruno
# (an_redir, sem API) e posta no canal @jarvis_promocoes com titulo e preco proprios. Roda dentro do mesmo run do vigia (cada 5 min).
import os, re, json, html, time, urllib.request, urllib.parse
CANAIS = ["cjpromos","BenchPromos","Fraguas84Oficial","juaocupons","LaPromotion","souzzatechpromos","promocoesdodia","Promobit"]
AFILIADO = "18309050191"
DESTINO = "@jarvis_promocoes"
MAX_POR_RODADA = 10
BARRA = r"travesseiro|len[cç]ol|toalha|fronha|edredom|cobertor|cama|colch|panela|frigideira|tapete|cortina|sof[aá]|mesa|cadeira|talher|prato|copo|garrafa t|utens|decora|organizador|vassoura|rodo|lavanderia|cozinha|banheiro|jogo de"
SINAL = r"r$|cupom|off\b|%|de r\$|por r\$|menor pre|relâmpago|relampago|desconto|frete gr"
VISTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vigia_publico_visto.json")
visto = set(json.load(open(VISTO))) if os.path.exists(VISTO) else set()
class _Sem(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
_op = urllib.request.build_opener(_Sem)
H = {"User-Agent": "Mozilla/5.0"}
def get(u, data=None): return urllib.request.urlopen(urllib.request.Request(u, data=data, headers=H), timeout=20).read().decode("utf-8", "ignore")
def destino(short):
    """Resolve o s.shopee.com.br/xxx sem seguir: devolve a URL da Shopee (sem parametros) ou None."""
    try: _op.open(urllib.request.Request(short, headers=H), timeout=15)
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") or ""
        u = urllib.parse.urlsplit(loc)
        if "shopee.com.br" in u.netloc and re.search(r"/\d+/\d+$", u.path): return f"https://shopee.com.br{u.path}"
    except Exception: pass
    return None
def meu_link(url):
    return "https://s.shopee.com.br/an_redir?origin_link=" + urllib.parse.quote(url, safe="") + f"&affiliate_id={AFILIADO}&sub_id=canal"
def preco(t):
    ms = re.findall(r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)", t)
    return ms[0] if ms else None
tok = (os.environ.get("TG_TOKEN") or "").replace("﻿", "").strip()
postados = 0
for c in CANAIS:
    if postados >= MAX_POR_RODADA: break
    try: pg = get(f"https://t.me/s/{c}")
    except Exception: continue
    for bloco in re.findall(r'data-post="[^"]+".*?(?=data-post="|$)', pg, re.S)[-15:]:
        post = re.search(r'data-post="([^"]+)"', bloco).group(1)
        if post in visto or postados >= MAX_POR_RODADA: continue
        visto.add(post)
        tm = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', bloco, re.S)
        if not tm: continue
        t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", tm.group(1))).split()); low = t.lower()
        if re.search(BARRA, low) or not re.search(SINAL, low): continue
        links = re.findall(r'href="(https?://s\.shopee\.com\.br/[^"]+)"', bloco)
        if not links: continue
        url = destino(links[0])
        if not url or url in visto: continue
        visto.add(url)
        p = preco(t); cup = re.search(r"cupom\W{0,3}([A-Z0-9]{4,20})\b", re.sub(r"<[^>]+>", " ", tm.group(1)))
        titulo = re.sub(r"[^\w\s\-/.,()%+]", "", re.split(r"R\$|https?://", t)[0]).strip(" -–:|")[:90] or t[:90]
        linhas = [f"🔥 {html.escape(titulo)}"]
        if p: linhas.append(f"💰 R$ {p}")
        if cup: linhas.append(f"🎟 Cupom: <code>{cup.group(1)}</code>")
        linhas += [f"👉 {meu_link(url)}", "Preço e cupom do momento, podem acabar."]
        if not tok: print("\n".join(linhas)); postados += 1; continue
        try:
            get(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode({"chat_id": DESTINO, "text": "\n".join(linhas), "parse_mode": "HTML"}).encode())
            postados += 1; time.sleep(3)
        except Exception as e: print("erro envio", e)
json.dump(sorted(visto)[-3000:], open(VISTO, "w"))
print("publico: postados", postados)
