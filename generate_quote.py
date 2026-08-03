#!/usr/bin/env python3
"""
Generate a Sketch décor quote page (standalone HTML) from event details,
a venue description, and the editable presets in presets/pricing.json
and presets/themes.json.

Usage:
    python generate_quote.py --config example_input.json --out quote.html

Or import and call generate(...) directly from the intake app.
"""
import json
import argparse
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_presets():
    with open(os.path.join(HERE, "presets", "pricing.json")) as f:
        pricing = json.load(f)
    with open(os.path.join(HERE, "presets", "themes.json")) as f:
        themes = json.load(f)
    return pricing, themes


def render_card(theme, venue_tie_in):
    swatches = "".join(
        f'<span class="sw" style="background:{c}"></span>' for c in theme["swatches"]
    )
    details = "".join(f"<div>· {d}</div>" for d in theme["scaled_details"])
    desc = theme["description_template"].format(venue_tie_in=venue_tie_in)
    return f"""
      <div class="card" data-id="{theme['id']}" data-base="{theme['base_price']}" style="--swatch:{theme['accent']}">
        <div class="swatches">{swatches}</div>
        <div class="eyebrow">Concept</div>
        <h3>{theme['name']}</h3>
        <div class="style-tag">{theme['style_tag']}</div>
        <p class="desc">{desc}</p>
        <div class="scaled">{details}</div>
        <div class="pick">Select {theme['name']}</div>
      </div>"""


def render_lighting_options(tiers):
    opts = []
    for t in tiers:
        label = t["label"] if t["price"] == 0 else f"{t['label']} — +${t['price']:,}"
        opts.append(f'<option value="{t["price"]}">{label}</option>')
    return "\n".join(opts)


def render_addons(addons):
    rows = []
    for a in addons:
        rows.append(f'''
              <div class="addon"><label><input type="checkbox" data-price="{a['price']}"> {a['label']}</label><span class="price">+${a['price']:,}</span></div>''')
    return "".join(rows)


def generate(event, venue, out_path):
    """
    event: dict with keys event_type, guests (int), budget, date
    venue: dict with keys headline (str), description (str), tie_in (str)
           tie_in is a short phrase reused inside each concept's description,
           e.g. "The arch sits at the water's edge, blooms reflected in the pond."
    out_path: where to write the HTML file
    """
    pricing, themes = load_presets()

    cards_html = "".join(render_card(t, venue.get("tie_in", "")) for t in themes)
    lighting_html = render_lighting_options(pricing["lighting_tiers"])
    addons_html = render_addons(pricing["addons"])
    base_guests = pricing["base_guests"]
    scale_factor = pricing["guest_scaling_factor"]

    html = HTML_SHELL.format(
        event_type=event["event_type"],
        guests=event["guests"],
        budget=event["budget"],
        date=event.get("date", "TBD"),
        venue_headline=venue["headline"],
        venue_description=venue["description"],
        cards_html=cards_html,
        lighting_html=lighting_html,
        addons_html=addons_html,
        base_guests=base_guests,
        scale_factor=scale_factor,
        guest_min=max(1, base_guests - 50),
        guest_max=base_guests + 150,
    )

    with open(out_path, "w") as f:
        f.write(html)
    return out_path


# Full page shell — CSS/JS carried over from the working prototype built
# earlier in this thread, with dynamic sections as {placeholders}.
HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sketch — Instant Décor Quote</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,600;1,9..144,400&family=Work+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--ink:#1B2A4A;--blueline:#6FA8DC;--parchment:#F7F3EA;--brass:#B08D57;--charcoal:#2B2B2B;--rose:#C98A93;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--parchment);color:var(--charcoal);font-family:'Work Sans',sans-serif;line-height:1.5;}}
  .wrap{{max-width:1080px;margin:0 auto;padding:0 32px;}}
  header{{padding:28px 0 20px;border-bottom:1px solid rgba(27,42,74,0.15);}}
  .brandrow{{display:flex;justify-content:space-between;align-items:baseline;}}
  .brand{{font-family:'Fraunces',serif;font-weight:600;font-size:28px;color:var(--ink);}}
  .brand span{{color:var(--brass);font-style:italic;font-weight:300;}}
  .tag{{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink);opacity:0.55;}}
  .hero{{padding:48px 0 8px;}}
  .hero h1{{font-family:'Fraunces',serif;font-weight:500;font-size:38px;color:var(--ink);max-width:640px;line-height:1.15;}}
  .hero h1 em{{color:var(--brass);font-style:italic;}}
  .plate{{margin-top:32px;border:1px solid var(--ink);background:linear-gradient(rgba(27,42,74,0.9),rgba(27,42,74,0.9)),repeating-linear-gradient(0deg,transparent,transparent 23px,rgba(111,168,220,0.18) 24px),repeating-linear-gradient(90deg,transparent,transparent 23px,rgba(111,168,220,0.18) 24px);color:#EAF1FA;min-height:280px;position:relative;display:flex;align-items:center;justify-content:center;text-align:center;padding:32px;}}
  .plate-inner{{max-width:460px;}}
  .plate .callout{{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--blueline);margin-bottom:10px;}}
  .plate h3{{font-family:'Fraunces',serif;font-weight:500;font-size:20px;margin-bottom:8px;}}
  .plate p{{font-size:13px;opacity:0.8;}}
  .plate .corner{{position:absolute;width:18px;height:18px;border:1.5px solid var(--blueline);}}
  .c-tl{{top:14px;left:14px;border-right:none;border-bottom:none;}}
  .c-tr{{top:14px;right:14px;border-left:none;border-bottom:none;}}
  .c-bl{{bottom:14px;left:14px;border-right:none;border-top:none;}}
  .c-br{{bottom:14px;right:14px;border-left:none;border-top:none;}}
  .brief-row{{margin-top:18px;display:flex;gap:22px;flex-wrap:wrap;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--ink);}}
  .brief-row div{{display:flex;gap:6px;align-items:baseline;}}
  .brief-row .lbl{{opacity:0.5;text-transform:uppercase;letter-spacing:0.5px;font-size:10px;}}
  .section-label{{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--brass);margin-bottom:6px;}}
  .section-title{{font-family:'Fraunces',serif;font-weight:500;font-size:26px;color:var(--ink);margin-bottom:28px;}}
  .concepts{{margin-top:64px;}}
  .cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}}
  @media(max-width:860px){{.cards{{grid-template-columns:1fr;}}}}
  .card{{background:#fff;border:1px solid rgba(27,42,74,0.15);border-top:3px solid var(--swatch,var(--brass));padding:22px 20px 24px;display:flex;flex-direction:column;cursor:pointer;transition:transform .15s ease,box-shadow .15s ease;}}
  .card:hover{{transform:translateY(-3px);box-shadow:0 10px 24px rgba(27,42,74,0.10);}}
  .card.selected{{outline:2px solid var(--ink);outline-offset:-2px;}}
  .swatches{{display:flex;gap:6px;margin-bottom:14px;}}
  .sw{{width:20px;height:20px;border-radius:50%;border:1px solid rgba(0,0,0,0.1);}}
  .card .eyebrow{{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:1px;text-transform:uppercase;opacity:0.55;margin-bottom:4px;}}
  .card h3{{font-family:'Fraunces',serif;font-style:italic;font-weight:500;font-size:23px;color:var(--ink);margin-bottom:2px;}}
  .card .style-tag{{font-size:12px;opacity:0.6;margin-bottom:12px;}}
  .card p.desc{{font-size:13.5px;line-height:1.55;opacity:0.85;margin-bottom:16px;flex-grow:1;}}
  .scaled{{font-family:'IBM Plex Mono',monospace;font-size:10.5px;border-top:1px dashed rgba(27,42,74,0.25);padding-top:12px;color:var(--ink);opacity:0.75;}}
  .scaled div{{margin-bottom:4px;}}
  .pick{{margin-top:16px;font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:1px;text-align:center;padding:9px 0;border:1px solid var(--ink);color:var(--ink);background:transparent;}}
  .card.selected .pick{{background:var(--ink);color:#fff;}}
  .builder{{margin-top:72px;padding-bottom:80px;}}
  .builder-box{{border:1px solid rgba(27,42,74,0.2);background:#fff;padding:36px;}}
  .row{{display:grid;grid-template-columns:1fr 1fr;gap:32px;}}
  @media(max-width:700px){{.row{{grid-template-columns:1fr;}}}}
  .field{{margin-bottom:22px;}}
  .field label{{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:0.6;margin-bottom:8px;}}
  .field .val{{font-family:'Fraunces',serif;font-size:20px;color:var(--ink);margin-bottom:6px;}}
  input[type="range"]{{width:100%;accent-color:var(--brass);}}
  select{{width:100%;padding:10px 12px;font-family:'Work Sans',sans-serif;font-size:14px;border:1px solid rgba(27,42,74,0.3);background:#fff;color:var(--charcoal);}}
  .addons{{display:flex;flex-direction:column;gap:10px;}}
  .addon{{display:flex;align-items:center;justify-content:space-between;font-size:13.5px;border-bottom:1px solid rgba(27,42,74,0.08);padding-bottom:8px;}}
  .addon label{{display:flex;align-items:center;gap:10px;cursor:pointer;font-family:'Work Sans',sans-serif;font-size:13.5px;}}
  .addon .price{{font-family:'IBM Plex Mono',monospace;opacity:0.6;font-size:12px;}}
  .total-box{{margin-top:8px;border-top:2px solid var(--ink);padding-top:22px;}}
  .total-lbl{{font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:0.6;}}
  .total-num{{font-family:'Fraunces',serif;font-size:40px;color:var(--ink);font-weight:500;}}
  .total-num sup{{font-size:15px;opacity:0.5;font-weight:400;}}
  .estimate-flag{{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.5px;color:var(--brass);text-transform:uppercase;margin-top:6px;}}
  footer{{text-align:center;padding:26px 0 40px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;opacity:0.45;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brandrow">
      <div class="brand">Sketch<span>·</span></div>
      <div class="tag">Instant Décor Quotes</div>
    </div>
  </header>

  <section class="hero">
    <h1>Your venue, <em>redrawn</em> — three ways.</h1>
    <div class="plate">
      <span class="corner c-tl"></span><span class="corner c-tr"></span>
      <span class="corner c-bl"></span><span class="corner c-br"></span>
      <div class="plate-inner">
        <div class="callout">Venue Plate — Traced</div>
        <h3>{venue_headline}</h3>
        <p>{venue_description}</p>
      </div>
    </div>
    <div class="brief-row">
      <div><span class="lbl">Event</span><b>{event_type}</b></div>
      <div><span class="lbl">Guests</span><b>{guests}</b></div>
      <div><span class="lbl">Budget</span><b>{budget}</b></div>
      <div><span class="lbl">Date</span><b>{date}</b></div>
    </div>
  </section>

  <section class="concepts">
    <div class="section-label">Three Concepts</div>
    <div class="section-title">Pick a direction to build your quote</div>
    <div class="cards" id="cards">{cards_html}
    </div>
  </section>

  <section class="builder">
    <div class="section-label">Quote Builder</div>
    <div class="section-title">Fine-tune your estimate</div>
    <div class="builder-box">
      <div class="row">
        <div>
          <div class="field">
            <label>Guest count</label>
            <div class="val" id="guestVal">{guests}</div>
            <input type="range" id="guestSlider" min="{guest_min}" max="{guest_max}" value="{guests}" step="10">
          </div>
          <div class="field">
            <label>Lighting design</label>
            <select id="lightingSelect">{lighting_html}</select>
          </div>
        </div>
        <div>
          <div class="field">
            <label>Add-ons</label>
            <div class="addons">{addons_html}
            </div>
          </div>
        </div>
      </div>
      <div class="total-box">
        <div class="total-lbl">Selected concept: <span id="conceptName">—</span></div>
        <div class="total-num">$<span id="totalNum">0</span><sup>estimate</sup></div>
        <div class="estimate-flag">Estimate only · final quote confirmed after venue review</div>
      </div>
    </div>
  </section>

  <footer>Sketch — décor concepts &amp; pricing are estimates until confirmed on-site.</footer>
</div>

<script>
  const cards = document.querySelectorAll('.card');
  const guestSlider = document.getElementById('guestSlider');
  const guestVal = document.getElementById('guestVal');
  const lightingSelect = document.getElementById('lightingSelect');
  const addons = document.querySelectorAll('.addon input[type="checkbox"]');
  const conceptName = document.getElementById('conceptName');
  const totalNum = document.getElementById('totalNum');
  const BASE_GUESTS = {base_guests};
  const SCALE_FACTOR = {scale_factor};
  let selectedCard = null;

  function guestFactor(g) {{ return 1 + ((g - BASE_GUESTS) / BASE_GUESTS) * SCALE_FACTOR; }}

  function recalc(){{
    let base = selectedCard ? parseInt(selectedCard.dataset.base) : 0;
    const guests = parseInt(guestSlider.value);
    base = Math.round(base * guestFactor(guests));
    let total = base + parseInt(lightingSelect.value);
    addons.forEach(a => {{ if(a.checked) total += parseInt(a.dataset.price); }});
    totalNum.textContent = total.toLocaleString();
    conceptName.textContent = selectedCard ? selectedCard.querySelector('h3').textContent : '—';
  }}

  cards.forEach(card => {{
    card.addEventListener('click', () => {{
      cards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedCard = card;
      recalc();
    }});
  }});
  guestSlider.addEventListener('input', () => {{ guestVal.textContent = guestSlider.value; recalc(); }});
  lightingSelect.addEventListener('change', recalc);
  addons.forEach(a => a.addEventListener('change', recalc));
  cards[0].click();
</script>
</body>
</html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON file with event + venue keys")
    parser.add_argument("--out", required=True, help="Output HTML path")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    generate(cfg["event"], cfg["venue"], args.out)
    print(f"Wrote {args.out}")
