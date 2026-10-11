"""Generates fiverr_copy_lint/rules.json (the single source of truth for every rule).

Run:  python tools/gen_rules.py          (rewrites rules.json)
      python tools/gen_rules.py --check  (exit 1 if rules.json is out of date)

Patterns are written for the regex dialect shared by Python `re` and JavaScript
(`RegExp` with the `u` flag) so the optional browser playground runs the same file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "fiverr_copy_lint" / "rules.json"
ALL = ["title", "description", "faq", "message", "request"]
MSG = ["message", "request"]
SAFE = "Let's keep everything in Fiverr's inbox so you're protected"

SEP = r"[\s._\-*]{0,2}"
LEET = {"a": "a4@", "e": "e3", "i": "i1!", "o": "o0", "s": "s5$", "l": "l1"}


def spaced(word: str, leet: bool = False) -> str:
    """Pattern for `word` tolerating separators (g m a i l, w.h.a.t.s.a.p.p) and optional leetspeak."""
    parts = []
    for ch in word:
        if leet and ch in LEET:
            chars = LEET[ch].replace("$", "\\$")
            parts.append("[" + chars + "]")
        else:
            parts.append(re.escape(ch))
    return SEP.join(parts)


LEAD = (
    r"(?:(?:(?:message|msg|text|ping|call|add|reach|contact|find|dm|chat\s+with|talk\s+to)\s+(?:me\s+)?)?"
    r"(?:on|via|through|at|in|using)\s+|my\s+|our\s+)?"
)
TAIL = r"(?:\s+(?:number|no\.?|id|handle|username|group|chat))?"

RULES: list[dict] = []


def R(id, group, severity, applies, pattern=None, *, name, rationale, suggestion, bad, good,
      rewrite=None, rewrite_map=None, flags="i", post=None, heuristic=None, params=None,
      ex_type=None):
    rule = {
        "id": id, "name": name, "group": group, "severity": severity, "applies": applies,
        "kind": "heuristic" if heuristic else "regex",
        "rationale": rationale, "suggestion": suggestion,
        "examples": {"type": ex_type or applies[0], "bad": bad, "good": good},
    }
    if heuristic:
        rule["heuristic"] = heuristic
        rule["params"] = params or {}
    else:
        rule["pattern"] = pattern
        rule["flags"] = flags
    if post:
        rule["post"] = post
    if rewrite is not None:
        rule["rewrite"] = rewrite
    if rewrite_map:
        rule["rewrite_map"] = rewrite_map
    RULES.append(rule)


G_OP, G_PAY, G_REV, G_SEO, G_REQ = "off-platform", "payment", "review-manipulation", "gig-seo", "buyer-request"

# ---------------------------------------------------------------- OFF-PLATFORM
R("OP-001", G_OP, "error", ALL,
  r"(?:\b(?:e-?mail|mail|write|reach|contact)\s+(?:me\s+)?(?:at|on|via|to)?\s*:?\s*)?[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+",
  name="Email address",
  rationale="Sharing an email address is the most common trigger for the 'keep conversations on Fiverr' block.",
  suggestion="Remove the address and invite the buyer to continue in the Fiverr inbox.",
  rewrite=SAFE, bad="Email me at john.doe@gmail.com for the details",
  good="Send your brief through the Fiverr inbox and I will reply within a day", ex_type="message")
R("OP-002", G_OP, "error", ALL,
  r"\b[A-Za-z0-9._\-]{2,}\s*(?:[\(\[\{]\s*(?:at|@)\s*[\)\]\}]|\s+at\s+)\s*[A-Za-z0-9\-]{2,}\s*(?:[\(\[\{]\s*(?:dot|\.)\s*[\)\]\}]|\s+dot\s+)\s*(?:com|net|org|io|co|me)\b",
  name="Obfuscated email (at/dot)",
  rationale="Writing an address as 'name (at) site (dot) com' is still an email address and is the classic evasion attempt.",
  suggestion="Remove it; do not try to disguise contact details.",
  rewrite=SAFE, bad="reach me: john (at) gmail (dot) com", good="We will meet at the studio in the evening", ex_type="message")
R("OP-003", G_OP, "warn", ALL,
  r"\b(?:" + "|".join([spaced("gmail", True), spaced("hotmail", True), spaced("protonmail", True), spaced("yahoo", True)]) + r")\b",
  name="Mail provider name (incl. spaced-out)",
  rationale="Naming a mail provider, even spaced out as 'g m a i l', signals off-platform contact intent.",
  suggestion="Remove it and keep the conversation in the Fiverr inbox.",
  rewrite=SAFE, bad="Add me on g.m.a.i.l and we continue", good="Add the details to your order requirements", ex_type="message")
R("OP-004", G_OP, "error", ALL,
  r"(?:(?:(?:message|msg|text|ping|call|add|reach|contact|dm)\s+(?:me\s+)?(?:on|at|via)\s+)?(?:whatsapp|telegram|phone|mobile|cell|tel|number|signal)\s*(?:me\s+)?(?:on|at|:|number|no\.?)?\s*[:\-]?\s*|(?:call|text)\s+(?:me\s+)?(?:on|at)?\s*[:\-]?\s*)?(?<![\w$€£.])\+?\d[\d 	().\-]{7,}\d(?!\w)",
  post="digits:9-15", name="Phone number",
  rationale="Phone numbers (9 to 15 digits, any common formatting) are blocked as off-platform contact details.",
  suggestion="Remove the number.",
  rewrite=SAFE, bad="Text me +92 300 1234567 anytime", good="I delivered 250 orders in 2026-10 with 5 revisions", ex_type="message")
R("OP-005", G_OP, "error", ALL,
  r"\b(?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\b[\s,.\-]*){7,}",
  name="Phone number spelled out in words",
  rationale="Digits written as words ('zero three zero zero ...') are a known evasion for phone numbers.",
  suggestion="Remove the number.",
  rewrite=SAFE, bad="call zero three zero zero one two three four five", good="I offer two revisions and one round of feedback", ex_type="message")
R("OP-006", G_OP, "error", ALL,
  r"\b" + LEAD + r"(?:" + spaced("whatsapp", True) + r"|wa\.me)\b" + TAIL,
  name="WhatsApp",
  rationale="WhatsApp is the single most-blocked destination for moving a buyer off the platform.",
  suggestion="Remove it; offer to continue in the Fiverr inbox.",
  rewrite=SAFE, bad="Message me on W h a t s A p p", good="I answer every message in the Fiverr inbox", ex_type="message")
R("OP-007", G_OP, "error", ALL,
  r"\b" + LEAD + r"(?:" + spaced("telegram", True) + r"|t\.me)\b" + TAIL,
  name="Telegram",
  rationale="Telegram is treated as an off-platform chat channel.",
  suggestion="Remove it; use the Fiverr inbox.",
  rewrite=SAFE, bad="find me on telegram", good="Questions are welcome in the order chat", ex_type="message")
R("OP-008", G_OP, "error", ALL,
  r"\b" + LEAD + spaced("skype", True) + r"\b" + TAIL,
  name="Skype",
  rationale="Skype is treated as an off-platform chat/call channel.",
  suggestion="Remove it; use the Fiverr inbox.",
  rewrite=SAFE, bad="add me on skype", good="We can discuss it in the order chat", ex_type="message")
R("OP-009", G_OP, "error", ALL,
  r"\b" + LEAD + spaced("discord", True) + r"\b" + TAIL,
  name="Discord",
  rationale="Confirmed live to trigger the filter in a normal discovery message.",
  suggestion="Say 'community group' only if truly needed; otherwise remove.",
  rewrite=SAFE, bad="join my discord", good="Join the order conversation any time", ex_type="message")
R("OP-010", G_OP, "warn", ALL,
  r"\b" + LEAD + r"(?:" + "|".join([spaced("viber", True), spaced("wechat", True), spaced("kakaotalk", True)]) + r"|line\s+id)\b" + TAIL,
  name="Other chat apps (Viber, WeChat, KakaoTalk, LINE)",
  rationale="Other messaging apps are treated like WhatsApp.",
  suggestion="Remove it; use the Fiverr inbox.",
  rewrite=SAFE, bad="my wechat is open", good="My inbox is open every day", ex_type="message")
R("OP-011", G_OP, "warn", ALL,
  r"\b(?:zoom|google\s+meet|gmeet|ms\s+teams|microsoft\s+teams|calendly|hangouts)\b",
  name="External meeting tool",
  rationale="Zoom, Google Meet and similar tools imply moving the conversation off Fiverr. (Can be a false positive in video gigs that mean camera zoom.)",
  suggestion="Use Fiverr's own scheduling/offer features or the inbox.",
  rewrite=SAFE, bad="we can meet on Zoom tomorrow", good="We can plan the project in the order chat", ex_type="message")
R("OP-012", G_OP, "warn", ["faq", "message", "request"],
  r"\b(?:call|phone|ring)\s+me\b|\b(?:phone|voice|video)\s+call\b|\b(?:jump|hop)\s+on\s+a\s+(?:quick\s+)?call\b|\blet'?s\s+(?:have\s+)?a\s+(?:quick\s+)?call\b",
  name="Call me / let's have a call",
  rationale="Suggesting a call is read as moving off-platform.",
  suggestion="Offer to answer in the inbox instead.",
  rewrite="message me here", bad="Let's have a quick call tomorrow", good="Send me your questions and I will answer here", ex_type="message")
R("OP-013", G_OP, "error", ALL,
  r"\b(?:dm|pm)\s+me\b|\bdirect\s+message\s+me\b|\bhit\s+me\s+up\b|\bcontact\s+me\s+(?:outside|off|directly|privately|externally)\b|\b(?:outside|off)\s+(?:of\s+)?(?:fiverr|the\s+platform)\b|\b(?:move|take|continue)\s+(?:this|the|our)\s+(?:chat|conversation|discussion|talk|deal)\s+(?:off|outside|elsewhere|to)\b|\bcontact\s+outside\b|\bcommunicate\s+(?:off|outside)\b",
  name="DM me / contact outside Fiverr",
  rationale="Phrases that explicitly invite off-platform contact are blocked and can lead to account warnings.",
  suggestion="Keep every step inside Fiverr.",
  rewrite=SAFE, bad="DM me and we continue outside of Fiverr", good="Message me here and we will finish the order together", ex_type="message")
R("OP-014", G_OP, "warn", MSG,
  r"\bcontact\s+me\b", name="'Contact me'",
  rationale="Field-observed as risky in seller-to-buyer messages (see rule catalogue note).",
  suggestion="Say 'message me here' instead.",
  rewrite="message me here", bad="Please contact me when you are ready", good="Please message me here when you are ready", ex_type="message")
R("OP-015", G_OP, "error", ALL,
  r"(?:\bhttps?://(?!(?:www\.)?fiverr\.com)[^\s<>\x22')]+|\bwww\.(?!fiverr\.com)[^\s<>\x22')]+|\b(?!fiverr\.com\b)[A-Za-z0-9\-]+\.(?:com|net|org|io|co|me|dev|app|xyz)\b(?:/[^\s<>\x22')]*)?)",
  name="External URL",
  rationale="External links in gigs and messages are blocked or stripped. Fiverr's own links are allowed.",
  suggestion="Put work samples in the gig gallery/portfolio instead of linking out.",
  rewrite="(link shared in the Fiverr inbox)", bad="See my work at https://example-portfolio.com/work", good="See the samples in my gig gallery", ex_type="message")
R("OP-016", G_OP, "warn", ALL,
  r"(?<![\w@.])@[A-Za-z][A-Za-z0-9._]{2,}",
  name="@handle",
  rationale="'@' handles read as social or chat usernames.",
  suggestion="Remove the handle.",
  rewrite=SAFE, bad="I am @johndesigns everywhere", good="I am a designer based in Bali", ex_type="message")
R("OP-017", G_OP, "warn", ALL,
  r"\b(?:(?:find|follow|add|dm|message|text)\s+me\s+(?:on|at|via)\s+(?:instagram|insta|ig|facebook|fb|linkedin|twitter|tiktok|snap)|my\s+(?:instagram|insta|facebook|linkedin|twitter|tiktok|snapchat))\b",
  name="Social profile pointer",
  rationale="Pointing buyers to your social profiles is off-platform contact.",
  suggestion="Remove it.",
  rewrite=SAFE, bad="Follow me on instagram for more", good="Browse the gig gallery for more", ex_type="message")
R("OP-018", G_OP, "warn", MSG,
  r"\bmy\s+(?:own\s+)?(?:website|web\s*site|site|portfolio\s+site|blog|store)\b",
  name="'my website / my site'",
  rationale="Field-observed as a trigger; it points the buyer to an off-platform site.",
  suggestion="Point to your gig portfolio instead.",
  rewrite="my gig portfolio", bad="Please check my website first", good="Please check my gig portfolio first", ex_type="message")

# --------------------------------------------------------------------- PAYMENT
R("PAY-001", G_PAY, "error", ALL,
  r"\b(?:" + spaced("paypal", True) + r"|pay\s*pal|venmo|cash\s*app|cashapp|zelle|payoneer|revolut|transferwise|skrill|neteller|stripe\s+link|payment\s+link)\b",
  name="Outside payment service",
  rationale="Naming an outside payment service is blocked: all payments must go through Fiverr.",
  suggestion="Remove it; the buyer pays through Fiverr checkout.",
  rewrite="order through Fiverr", bad="You can pay via PayPal", good="You can order with Fiverr checkout", ex_type="message")
R("PAY-002", G_PAY, "error", ALL,
  r"\b(?:bank|wire)\s+(?:transfer|payment|deposit)\b|\bwire\s+me\b|\biban\b|\bswift\s+code\b|\baccount\s+(?:number|details)\b|\bsort\s+code\b|\brouting\s+number\b|\bwestern\s+union\b|\bmoneygram\b",
  name="Bank transfer details",
  rationale="Bank and wire details are payment-outside-Fiverr signals.",
  suggestion="Remove; use Fiverr checkout.",
  rewrite="order through Fiverr", bad="Send a bank transfer to my IBAN", good="Place the order and I start right away", ex_type="message")
R("PAY-003", G_PAY, "warn", MSG,
  r"\b(?:bitcoin|btc|usdt|usdc|ethereum|crypto(?:currency)?|binance|tether|wallet\s+address)\b",
  name="Crypto payment words",
  rationale="Crypto terms suggest paying outside the platform. (False positive if your gig is about crypto work.)",
  suggestion="Remove; use Fiverr checkout.",
  rewrite="order through Fiverr", bad="I take USDT too", good="Fiverr checkout keeps both of us covered", ex_type="message")
R("PAY-004", G_PAY, "error", ALL,
  r"\bpay(?:ing|ment)?\s+(?:me\s+)?(?:outside|directly|off[\s-]?platform|off\s+fiverr|externally)\b|\bpay(?:ment)?\s+outside\b|\bdirect(?:ly)?\s+(?:payment|pay|deal)\b|\boff[\s-]?platform\s+(?:payment|deal|order)\b|\b(?:tip|tips)\s+(?:me\s+)?(?:outside|directly|off[\s-]?platform|in\s+cash)\b|\b(?:accept|accepting|take|taking)\s+(?:crypto|bitcoin|paypal|cash|direct)\b|\bpay\s+(?:me\s+)?(?:in\s+)?cash\b",
  name="Pay outside / direct payment",
  rationale="Asking for payment or tips outside Fiverr is a serious violation and a top reason for restrictions.",
  suggestion="Take every payment, tip included, through Fiverr.",
  rewrite="order through Fiverr", bad="You can pay me directly and save fees", good="Order through Fiverr and tip inside the platform", ex_type="message")
R("PAY-005", G_PAY, "warn", MSG,
  r"\bpay\s+me\b", name="'pay me'",
  rationale="Confirmed live: the word 'pay' in a seller message triggered the block.",
  suggestion="Say 'my fee'.",
  rewrite="my fee", bad="Pay me after the draft", good="My fee is on the package page", ex_type="message")
R("PAY-006", G_PAY, "warn", MSG,
  r"\b(?:pay|paying|payment|payments)\b(?!-)|\bpa[._\-*]y\b", name="'pay / payment' (incl. pa.y)",
  rationale="Confirmed live: 'pay' and 'payment' tripped the filter in an otherwise normal message.",
  suggestion="Rephrase with 'fee' or 'order'. Never write 'pa.y' - that looks like evasion.",
  rewrite="fee", rewrite_map={"pay": "cover the fee", "paying": "covering the fee", "payment": "fee", "payments": "fees"},
  bad="Please pay for the extra revision", good="The extra revision has its own fee", ex_type="message")

# ------------------------------------------------------------ REVIEW MANIPULATION
R("REV-001", G_REV, "error", ALL,
  r"\b(?:leave|give|drop|post|write|rate)\s+(?:me\s+|us\s+)?(?:a\s+)?(?:5|five)[\s-]*stars?\b(?:\s+(?:review|rating|feedback))?|\b(?:5|five)[\s-]*stars?\s+(?:review|rating|feedback)\s+(?:please|only|required)\b|\brate\s+(?:me\s+)?(?:5|five)\b",
  name="Asking for a 5-star review",
  rationale="Requesting a specific star rating is review manipulation.",
  suggestion="Ask for honest feedback instead.",
  rewrite="share your honest feedback", bad="Please leave me a 5 star review", good="I would value your honest feedback", ex_type="message")
R("REV-002", G_REV, "error", ALL,
  r"\b(?:positive|good|great|5[\s-]?star|five[\s-]?star)\s+(?:review|rating|feedback)s?\s+(?:in\s+exchange|in\s+return|for\s+(?:a\s+)?(?:discount|refund|free|bonus|extra|gift|tip))\b|\bin\s+(?:exchange|return)\s+for\s+(?:a\s+)?(?:positive|good|great|5|five)\b|\breview\s+(?:swap|exchange|for\s+review)\b|\b(?:discount|refund|bonus|freebie)\s+(?:in\s+exchange\s+)?for\s+(?:a\s+)?(?:positive|good|5[\s-]?star|five[\s-]?star)\s+(?:review|rating)",
  name="Incentivised review",
  rationale="Trading discounts, refunds or bonuses for a positive review is prohibited.",
  suggestion="Remove the incentive; you can only ask for honest feedback.",
  bad="I will add a bonus for a 5 star review", good="Reviews help other buyers decide", ex_type="message")
R("REV-003", G_REV, "warn", ALL,
  r"\bonly\s+(?:positive|5[\s-]?star|good|five[\s-]?star)\s+(?:review|feedback|rating)s?\b|\bdon'?t\s+(?:leave|give|write)\s+(?:me\s+)?(?:a\s+)?(?:bad|negative|low|poor)\b|\bmessage\s+me\s+before\s+(?:leaving|giving|writing)\s+(?:a\s+)?(?:bad|negative|low)",
  name="Pressure against negative reviews",
  rationale="Discouraging negative reviews is review manipulation.",
  suggestion="Offer help fixing issues without conditions on the review.",
  bad="Please don't leave a bad review", good="Tell me what to improve and I will fix it", ex_type="message")
R("REV-004", G_REV, "error", ALL,
  r"\bfake\s+(?:reviews?|ratings?|testimonials?)\b|\b(?:buy|buying|sell|selling|purchase)\s+(?:5[\s-]?star\s+)?(?:reviews|ratings)\b|\bpaid\s+reviews?\b",
  name="Fake or paid reviews",
  rationale="Buying, selling or fabricating reviews is banned.",
  suggestion="Remove it.",
  bad="I sell 5 star reviews cheaply", good="I help you collect real testimonials", ex_type="description")

# ---------------------------------------------------------------- GIG SEO HYGIENE
R("SEO-001", G_SEO, "error", ["title"], name="Title over 80 characters", heuristic="title_length", params={"max": 80},
  rationale="Fiverr gig titles are capped at 80 characters; longer text is cut or rejected.",
  suggestion="Cut filler words; lead with the service and keep the keyword near the start.",
  bad="I will design a modern professional minimalist logo with brand guidelines and unlimited revisions fast",
  good="I will design a modern minimalist logo with brand guidelines")
R("SEO-002", G_SEO, "warn", ALL, name="Keyword stuffing", heuristic="keyword_stuffing",
  params={"title_min": 3, "body_min": 6, "body_density": 0.05},
  rationale="Repeating one keyword 3+ times in a title (or heavily in a description) reads as stuffing to buyers and moderators.",
  suggestion="Use the keyword once, then add related terms.",
  bad="I will design logo design, logo design for business logo design", good="I will design a clean logo for your startup", ex_type="title")
R("SEO-003", G_SEO, "warn", ALL, name="ALL CAPS ratio", heuristic="caps_ratio",
  params={"title": 0.4, "other": 0.3, "min_letters": 12},
  rationale="Shouting in capitals reads as spam and hurts conversion.",
  suggestion="Use sentence case; keep capitals for acronyms.",
  bad="I WILL DESIGN A STUNNING LOGO FOR YOUR BRAND", good="I will design a stunning logo for your brand", ex_type="title")
R("SEO-004", G_SEO, "warn", ALL, name="Emoji spam", heuristic="emoji_spam",
  params={"title": 2, "other": 6},
  rationale="Strings of emoji look like spam and are a common reason for gig edits.",
  suggestion="Use plain text in titles and at most a few emoji elsewhere.",
  bad="I will design your logo \U0001F525\U0001F680✨", good="I will design your logo", ex_type="title")
R("SEO-005", G_SEO, "info", ["title"], name="Missing 'I will' title convention", heuristic="missing_i_will",
  rationale="Fiverr gig titles are conventionally written as 'I will ...' and search matches that phrasing.",
  suggestion="Start with 'I will' followed by the service.",
  bad="Professional logo design", good="I will design a professional logo")
R("SEO-006", G_SEO, "warn", ["description"], name="Thin description (<120 words)", heuristic="short_description",
  params={"min_words": 120},
  rationale="Very short descriptions rank and convert worse and give buyers little to trust.",
  suggestion="Cover what is included, process, who it is for and what you need from the buyer.",
  bad="I will make a logo for you.", good=" ".join(["I design clean logos for small businesses and I include the source files and three revisions in every package."] * 12))
R("SEO-007", G_SEO, "warn", ALL,
  r"\bguarantee[ds]?\s+(?:you\s+)?(?:#\s?1|no\.?\s?1|first[\s-]page|page\s+(?:1|one)|top\s+\d+|top\s+(?:rank\w*|spot)|rank\w*|sales|results|traffic|followers|income|roi|conversions|views|leads|profit)\b|\b100\s*%\s*(?:guarantee[ds]?\s+)?(?:guarantee[ds]?|success|sales|results|ranking|rankings|profit)\b|\bguaranteed\s+(?:#\s?1|no\.?\s?1|first[\s-]page|top\s+\d+|ranking|rankings|sales|results|traffic|followers|income|roi|conversions|views|leads|profit)\b|\b(?:get|reach|hit)\s+(?:you\s+)?(?:#\s?1|no\.?\s?1)\s+(?:on|in)\s+google\b",
  name="Guarantee claims",
  rationale="Guaranteed rankings, sales or results can't be promised and are flagged as misleading.",
  suggestion="Describe the process and past deliverables, not guaranteed outcomes.",
  bad="Guaranteed #1 ranking on Google in 7 days", good="I deliver on time and offer free revisions until you are happy", ex_type="description")
R("SEO-008", G_SEO, "info", ALL,
  r"(?<![\w#])#\s?1\b|\bnumber\s+(?:one|1)\b|\bno\.?\s?1\b|\bworld'?s\s+(?:best|greatest)\b|\bbest\s+in\s+the\s+world\b|\bunbeatable\b|\bcheapest\b|\blowest\s+price\b|\bunmatched\b",
  name="Banned superlatives",
  rationale="Unprovable superlatives weaken trust and can be edited out by moderators.",
  suggestion="Replace with a specific, checkable claim.",
  bad="I am the #1 designer on Fiverr", good="I design clean logos for startups", ex_type="description")
R("SEO-009", G_SEO, "error", ALL,
  r"\bofficial\s+(?:google|facebook|meta|amazon|apple|microsoft|shopify|tiktok|instagram|youtube|openai|fiverr|upwork|paypal|wordpress|linkedin)(?:\s+(?:partner|expert|agency|certified|reseller|employee|consultant))?|\b(?:google|meta|amazon|shopify|microsoft|facebook|tiktok)\s+(?:certified|authori[sz]ed|verified)\s+(?:partner|expert|agency|seller|professional)\b",
  name="Trademark impersonation",
  rationale="Claiming to be an official partner of a brand you are not is impersonation and a policy violation.",
  suggestion="Describe your real experience with the tool instead.",
  bad="Official Google Partner agency", good="I build Shopify stores that load fast", ex_type="description")
R("SEO-010", G_SEO, "warn", ALL,
  r"!{2,}", name="Excess exclamation marks",
  rationale="Stacked exclamation marks read as spam.",
  suggestion="Use one at most.",
  rewrite="!", bad="Order now!!!", good="Order now!", ex_type="description")
R("SEO-011", G_SEO, "warn", ["description"], name="Keyword dump list", heuristic="keyword_dump", params={"min_items": 8},
  rationale="A long comma-separated list of keywords is stuffing and unreadable.",
  suggestion="Turn it into sentences that describe what you deliver.",
  bad="logo, branding, logo design, brand identity, minimalist logo, business logo, modern logo, custom logo, vector logo",
  good="I design logos and brand identities for small businesses.")

# ------------------------------------------------------------- BUYER-REQUEST SPAM
R("REQ-001", G_REQ, "warn", MSG,
  r"\b(?:dear|hello|hi|hey)\s+(?:sir|madam|sir\s*/\s*madam|sir\s+or\s+madam|sir\s+and\s+madam|client|buyer|esteemed\s+\w+|valued\s+\w+|friend)\b[,!]?",
  name="Generic greeting (Dear Sir/Madam)",
  rationale="Template greetings are the first sign of copy-paste offers, and buyers skip them.",
  suggestion="Use the buyer's name or reference something specific from the request.",
  rewrite="Hi,", bad="Dear Sir, I can help you", good="Hi, I can help you", ex_type="request")
R("REQ-002", G_REQ, "warn", MSG,
  r"\bi\s*(?:am|'m)\s+(?:an?\s+)?(?:expert|professional|experienced|skilled)\s+(?:in|at)\s+(?:this|your|that)\s+(?:field|area|domain|niche|type\s+of\s+work)\b",
  name="Generic expertise claim",
  rationale="'I am an expert in this field' says nothing specific and appears in most spam offers.",
  suggestion="Name one relevant project or result you can verify.",
  bad="I am an expert in this field", good="I built three n8n workflows for lead capture last quarter", ex_type="request")
R("REQ-003", G_REQ, "warn", MSG,
  r"\bi\s+(?:have\s+)?(?:read|seen|gone\s+through|checked|reviewed|viewed)\s+(?:all\s+)?(?:your|the)\s+(?:project|request|requirements?|description|post|brief|job)s?\b(?:\s+(?:carefully|thoroughly|completely))?",
  name="'I read your request'",
  rationale="This opener is pasted into every offer and signals no real reading.",
  suggestion="Prove you read it by quoting a detail or asking one specific question.",
  bad="I have read your request carefully", good="You mention a Shopify store with 300 SKUs; are the images already cropped?", ex_type="request")
R("REQ-004", G_REQ, "info", MSG,
  r"\bi\s+can\s+(?:do|complete|handle)\s+(?:this|it)\s+(?:perfectly|easily|quickly|without\s+any\s+problem)\b",
  name="'I can do this perfectly'",
  rationale="Confident but contentless; buyers read it as spam.",
  suggestion="State how you would do it in one line.",
  bad="I can do this perfectly", good="I would start with a wireframe and send it today", ex_type="request")
R("REQ-005", G_REQ, "error", MSG,
  r"\[(?:name|client|buyer|company|your\s+name|first\s+name|business|project)\]|\{\{\s*\w+\s*\}\}|<(?:name|client|buyer)>",
  name="Unfilled template placeholder",
  rationale="Sending '[name]' or '{{client}}' proves the message is a template.",
  suggestion="Fill in or delete every placeholder before sending.",
  bad="Hi [name], I can help", good="Hi Sara, I can help", ex_type="request")
R("REQ-006", G_REQ, "info", ["request"],
  r"\b(?:check|see|visit|view|look\s+at)\s+my\s+(?:portfolio|gigs?|profile|work|samples)\b",
  name="'Check my portfolio'",
  rationale="Pushing the buyer to do the work of evaluating you; lazy pitch.",
  suggestion="Link one relevant sample in your gig gallery and say why it matches.",
  bad="Please check my portfolio", good="My gallery sample #2 is the closest match to your brief", ex_type="request")
R("REQ-007", G_REQ, "info", ["request"], name="Request response under 25 words", heuristic="short_request", params={"min_words": 25},
  rationale="Very short offers rarely show that you understood the brief.",
  suggestion="Restate the goal, give a plan in one line, and ask one question.",
  bad="Hi I can do it", good="You need a landing page for your dental clinic and I would start by sketching the booking flow then ask which services matter most before sending the first draft today.")

meta = {
    "version": "1.0.0",
    "rules_version": "2026.10.1",
    "note": "COMMUNITY-OBSERVED, NOT AN OFFICIAL FIVERR LIST. Fiverr does not publish its filter; these rules come from field observation and common policy themes. Passing this linter does not guarantee Fiverr will accept the text, and failing it does not mean Fiverr will block it.",
    "types": ALL,
    "severity_weights": {"error": 20, "warn": 8, "info": 2},
    "bands": [[0, "low"], [20, "medium"], [50, "high"]],
    "safe_sentence": SAFE,
    "emoji_ranges": [[127744, 129791], [9728, 10175], [11088, 11088], [11093, 11093], [8986, 8987], [9193, 9210], [127462, 127487]],
    "stopwords": "the and for with your you that this from have will are was were our can has not but all any more most very just about into over than then them they their what when where which while also only each both such like make made using use used get got".split(),
}

doc = {"meta": meta, "rules": RULES}
text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"

if __name__ == "__main__":
    if "--check" in sys.argv:
        cur = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        sys.exit(0 if cur == text else 1)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(RULES)} rules)")
