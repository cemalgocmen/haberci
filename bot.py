#!/usr/bin/env python3
"""Telegram kanallarını tarar, kelimelerinizle eşleşen yeni paylaşımları size ve @cgindirim kanalına iletir."""
import html, json, os, re, sys, unicodedata
import urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "state.json")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


# ---------- dosyalar ----------
def read_lines(name):
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def load_state():
    try:
        s = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        s = {}
    s.setdefault("last", {})
    s.setdefault("warned", [])
    return s


def save_state(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1, sort_keys=True)


# ---------- eşleştirme ----------
def norm(s):
    t = unicodedata.normalize("NFD", s.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.replace("ı", "i")


TOKEN_RE = re.compile(r'"([^"]+)"|(\S+)')


def parse_rules(lines):
    rules = []
    for line in lines:
        line = line.replace("“", '"').replace("”", '"')
        must, mustnot = [], []
        for m in TOKEN_RE.finditer(line):
            quoted, word = m.group(1), m.group(2)
            if quoted:
                must.append(norm(quoted))
            elif word.startswith("-") and len(word) > 1:
                mustnot.append(norm(word[1:]))
            else:
                must.append(norm(word))
        if must:
            rules.append({"raw": line, "must": must, "not": mustnot})
    return rules


def first_match(rules, text):
    t = norm(text)
    for r in rules:
        if all(w in t for w in r["must"]) and not any(w in t for w in r["not"]):
            return r
    return None


# ---------- Telegram kanal sayfası ----------
def channel_name(line):
    s = line.strip()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^(www\.)?t\.me/", "", s)
    s = re.sub(r"^s/", "", s).lstrip("@")
    s = re.split(r"[/?#]", s)[0]
    if not re.fullmatch(r"[A-Za-z0-9_]{4,}", s or ""):
        print(f"UYARI: '{line}' geçerli bir herkese açık kanal adı değil, atlandı.")
        return None
    return s


def fetch(ch):
    req = urllib.request.Request(
        f"https://t.me/s/{ch}",
        headers={"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def _link(m):
    url = html.unescape(m.group(1))
    label = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
    if not url.startswith("http"):
        return label
    if label == url or label.endswith("…") or not label:
        return url
    return f"{label} {url}"


def clean(h):
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', _link, h, flags=re.S)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h).strip()


def parse_posts(page):
    posts = []
    for part in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="[^"/]+/(\d+)"', part)
        if not m:
            continue
        pid = int(m.group(1))
        chunks = []
        t = re.search(
            r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>',
            part, re.S)
        if t:
            chunks.append(clean(t.group(1)))
        for cls in ("link_preview_title", "link_preview_description"):
            p = re.search(r'class="%s[^"]*"[^>]*>(.*?)</div>' % cls, part, re.S)
            if p:
                chunks.append(clean(p.group(1)))
        posts.append((pid, "\n".join(c for c in chunks if c)))
    return posts


# ---------- bildirim ----------
def send(token, chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=25) as r:
        return bool(json.load(r).get("ok"))


# ---------- Telegram'dan yönetim komutları ----------
def read_raw(name):
    path = os.path.join(BASE, name)
    return open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []


def write_raw(name, lines):
    with open(os.path.join(BASE, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def is_entry(line):
    s = line.strip()
    return bool(s) and not s.startswith("#")


def entries(name):
    return [l.strip() for l in read_raw(name) if is_entry(l)]


def listing():
    kw, ch = entries("kelimeler.txt"), [channel_name(c) or c for c in entries("kanallar.txt")]
    out = ["📋 İstekler:"]
    out += [f"{i}. {k}" for i, k in enumerate(kw, 1)] or ["(boş)"]
    out += ["", "📣 Kanallar:"]
    out += [f"{i}. {c}" for i, c in enumerate(ch, 1)] or ["(boş)"]
    return "\n".join(out)


def remove_entry(name, arg, label):
    lines = read_raw(name)
    idx = [i for i, l in enumerate(lines) if is_entry(l)]
    target = None
    arg = arg.strip()
    if arg.isdigit():
        n = int(arg)
        if 1 <= n <= len(idx):
            target = idx[n - 1]
    else:
        key = norm(" ".join(arg.split()))
        key_ch = norm(channel_name(arg) or "") if name == "kanallar.txt" else None
        for i in idx:
            cur = norm(" ".join(lines[i].split()))
            cur_ch = norm(channel_name(lines[i]) or "") if name == "kanallar.txt" else None
            if cur == key or (key_ch and cur_ch == key_ch):
                target = i
                break
    if target is None:
        return None
    removed = lines.pop(target).strip()
    write_raw(name, lines)
    return removed


HELP = (
    "🤖 Komutlar\n"
    "/liste → istek ve kanalları numaralı gösterir\n"
    "/ekle fissler düdüklü → istek ekler\n"
    "/sil 2 → 2 numaralı isteği siler\n"
    "/degistir 2 philips airfryer → 2 numaralı isteği değiştirir\n"
    "/kanal t.me/kanaladi → kanal ekler\n"
    "/kanalsil 1 → 1 numaralı kanalı siler\n\n"
    "Yakalanan indirimler doğrudan @cgindirim kanalında paylaşılır!"
)


def handle(cmd, arg, state):
    arg = " ".join(arg.split())
    if cmd in ("start", "yardim", "help"):
        return HELP
    if cmd in ("liste", "list"):
        return listing()
    if cmd == "ekle":
        if not arg:
            return "Kullanım: /ekle fissler düdüklü"
        if not parse_rules([arg]):
            return "Bu istekte aranacak kelime yok. Örnek: /ekle fissler düdüklü"
        if norm(arg) in [norm(" ".join(e.split())) for e in entries("kelimeler.txt")]:
            return "Bu istek zaten var.\n\n" + listing()
        write_raw("kelimeler.txt", read_raw("kelimeler.txt") + [arg])
        return f"✅ Eklendi: {arg}\n\n" + listing()
    if cmd == "sil":
        if not arg:
            return "Kullanım: /sil 2   veya   /sil fissler düdüklü"
        r = remove_entry("kelimeler.txt", arg, "istek")
        return (f"🗑 Silindi: {r}\n\n" if r else "Bulunamadı. /liste ile numaraya bakın.\n\n") + listing()
    if cmd == "degistir":
        m = re.match(r"^(\d+)\s+(.+)$", arg)
        if not m or not parse_rules([m.group(2)]):
            return "Kullanım: /degistir 2 philips airfryer"
        lines = read_raw("kelimeler.txt")
        idx = [i for i, l in enumerate(lines) if is_entry(l)]
        n = int(m.group(1))
        if not 1 <= n <= len(idx):
            return "Bu numarada istek yok.\n\n" + listing()
        old = lines[idx[n - 1]].strip()
        lines[idx[n - 1]] = m.group(2)
        write_raw("kelimeler.txt", lines)
        return f"✏️ {old} → {m.group(2)}\n\n" + listing()
    if cmd == "kanal":
        name = channel_name(arg) if arg else None
        if not name:
            return "Kullanım: /kanal t.me/kanaladi (herkese açık kanal olmalı)"
        if name.lower() in [(channel_name(c) or "").lower() for c in entries("kanallar.txt")]:
            return "Bu kanal zaten ekli.\n\n" + listing()
        try:
            posts = parse_posts(fetch(name))
        except Exception:
            posts = []
        write_raw("kanallar.txt", read_raw("kanallar.txt") + [f"t.me/{name}"])
        if posts:
            state["last"][name] = max(p[0] for p in posts)
            note = f"✅ Eklendi: {name} (kanal okunabiliyor, bundan sonraki paylaşımlar izlenecek)"
        else:
            note = (f"⚠️ Eklendi ama '{name}' okunamadı. Herkese açık bir kanal olmayabilir "
                    f"veya Telegram grupları webden okunamıyor olabilir.")
        return note + "\n\n" + listing()
    if cmd == "kanalsil":
        if not arg:
            return "Kullanım: /kanalsil 1   veya   /kanalsil kanaladi"
        r = remove_entry("kanallar.txt", arg, "kanal")
        return (f"🗑 Silindi: {r}\n\n" if r else "Bulunamadı. /liste ile numaraya bakın.\n\n") + listing()
    return "Bilinmeyen komut.\n\n" + HELP


def api(token, method, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


MENU = [("liste", "İstek ve kanalları göster"), ("ekle", "İstek ekle"), ("sil", "İstek sil"),
        ("degistir", "İsteği değiştir"), ("kanal", "Kanal ekle"), ("kanalsil", "Kanal sil"),
        ("yardim", "Yardım")]


def process_commands(token, chat, state):
    if not state.get("menu_set"):
        try:
            api(token, "setMyCommands", {"commands": json.dumps(
                [{"command": c, "description": d} for c, d in MENU])})
            state["menu_set"] = True
        except Exception as e:
            print("menü ayarlanamadı:", e)
    try:
        res = api(token, "getUpdates", {"offset": state.get("offset", 0), "timeout": 0,
                                        "allowed_updates": json.dumps(["message"])})
    except Exception as e:
        print("komutlar okunamadı:", e)
        return
    for upd in res.get("result", []):
        state["offset"] = upd["update_id"] + 1
        msg = upd.get("message") or {}
        if str(msg.get("chat", {}).get("id")) != str(chat):
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        m = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)$", text, re.S)
        reply = handle(m.group(1).lower(), m.group(2), state) if m else \
            "Komutları görmek için /yardim yazın."
        try:
            send(token, chat, reply)
        except Exception as e:
            print("yanıt gönderilemedi:", e)


def main():
    token, chat = os.environ.get("BOT_TOKEN", ""), os.environ.get("CHAT_ID", "")
    target_channel = os.environ.get("TARGET_CHANNEL", "@cgindirim")

    if not token or not chat:
        sys.exit("HATA: BOT_TOKEN ve CHAT_ID 'secret' olarak tanımlanmalı.")

    state = load_state()
    process_commands(token, chat, state)
    rules = parse_rules(read_lines("kelimeler.txt"))
    chans = list(dict.fromkeys(c for c in map(channel_name, read_lines("kanallar.txt")) if c))
    print(f"{len(chans)} kanal, {len(rules)} istek. Hedef kanal: {target_channel}")

    # Test modunda hem sana hem @cgindirim kanalına onay mesajı atar
    if os.environ.get("TEST", "").lower() == "true":
        send(token, chat, f"✅ İndirim botu çalışıyor.\nKanallar: {', '.join(chans)}\n"
                          f"İstekler: {' | '.join(r['raw'] for r in rules)}")
        if target_channel:
            try:
                send(token, target_channel, f"🚀 @cgindirim kanalı başarıyla bağlandı!\n\n"
                                            f"Takip edilen kanallar: {', '.join(chans)}\n"
                                            f"Aranan fırsatlar: {' | '.join(r['raw'] for r in rules)}\n\n"
                                            f"Bot 7/24 nöbette, fırsatlar yakalandıkça buraya düşecek!")
            except Exception as e:
                print(f"Kanala test mesajı atılamadı: {e}")

    for ch in chans:
        try:
            posts = parse_posts(fetch(ch))
        except Exception as e:
            print(f"[{ch}] okunamadı: {e}")
            continue
        if not posts:
            print(f"[{ch}] paylaşım bulunamadı")
            if ch not in state["last"] and ch not in state["warned"]:
                try:
                    send(token, chat, f"⚠️ '{ch}' kanalı okunamadı. Herkese açık değil ya da web "
                                      f"önizlemesi kapalı olabilir.")
                    state["warned"].append(ch)
                except Exception as e:
                    print("uyarı gönderilemedi:", e)
            continue

        newest = max(p[0] for p in posts)
        last = state["last"].get(ch)
        if last is None:
            state["last"][ch] = newest
            print(f"[{ch}] ilk tarama, {newest} numarasına kadar işaretlendi")
            continue

        ok = True
        for pid, text in sorted(posts):
            if pid <= last:
                continue
            hit = first_match(rules, text)
            if not hit:
                continue
                          msg = f"🔥 {hit['raw']}\n\n{text[:1500]}\n\n📣 https://t.me/{ch}/{pid}"
               try:
                   send(token, target_channel, msg)
                   print(f"[{ch}] eşleşme #{pid}: {hit['raw']}")
               except Exception as e:
                   ok = False
                   print(f"[{ch}] kanala gönderilemedi #{pid}: {e}")

                print(f"[{ch}] eşleşme #{pid}: {hit['raw']}")
            except Exception as e:
                ok = False
                print(f"[{ch}] gönderilemedi #{pid}: {e}")
        if ok:
            state["last"][ch] = max(last, newest)

    save_state(state)


if __name__ == "__main__":
    main()
