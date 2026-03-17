import ast
import json
import operator
import os
import re
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

MAX_HISTORY_ITEMS = 12
MAX_HISTORY_CHARS = 500

SAFE_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
SAFE_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

STORE_INTENT_KEYWORDS = [
    "product",
    "products",
    "shop",
    "store",
    "buy",
    "purchase",
    "price",
    "budget",
    "warranty",
    "order",
    "delivery",
    "shipping",
    "return",
    "refund",
    "cart",
    "coupon",
    "discount",
    "style",
    "outfit",
    "look",
    "fashion",
    "color",
    "colors",
    "shoe",
    "shoes",
    "dress",
    "promo",
    "headline",
    "campaign",
    "copy",
    "منتج",
    "منتجات",
    "متجر",
    "شراء",
    "سعر",
    "ميزانية",
    "ضمان",
    "طلب",
    "طلبات",
    "شحن",
    "توصيل",
    "إرجاع",
    "ارجاع",
    "استرجاع",
    "خصم",
    "ستايل",
    "لوك",
    "موضة",
    "لون",
    "ألوان",
    "حذاء",
    "فستان",
    "حملة",
    "عناوين",
]

COPY_INTENT_KEYWORDS = [
    "copy",
    "headline",
    "headlines",
    "hook",
    "email",
    "campaign",
    "caption",
    "ad",
    "ads",
    "slogan",
    "tagline",
    "description",
    "product description",
    "landing page",
    "cta",
    "وصف",
    "نص",
    "نسخة",
    "اعلان",
    "إعلان",
    "عنوان",
    "عناوين",
    "حملة",
    "بريد",
    "ايميل",
    "cta",
]

SMALL_TALK_KEYWORDS = [
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "good morning",
    "good evening",
    "مرحبا",
    "مرحبًا",
    "اهلا",
    "أهلا",
    "السلام عليكم",
    "شكرا",
    "شكراً",
    "كيف حالك",
]


AGENT_CATALOG = {
    "shop_strategist": {
        "id": "shop_strategist",
        "name": "Shop Strategist",
        "tagline": "Find the right product faster.",
        "description": "Analyzes needs, budget, and use-case then recommends precise options.",
        "emoji": "fa-compass",
        "accent": "#0f766e",
        "system_prompt": (
            "You are Shop Strategist for ElegantShop. "
            "Give practical shopping advice, compare options, and mention tradeoffs. "
            "Use concise, clear language and end with a concrete recommendation. "
            "Keep responses inside ElegantShop service scope."
        ),
        "quick_prompts": [
            "Find me a gift under $120",
            "Recommend everyday products for students",
            "I want premium quality with long warranty",
            "احسب خصم 15% على سعر 240",
        ],
    },
    "style_curator": {
        "id": "style_curator",
        "name": "Style Curator",
        "tagline": "Outfit and style intelligence.",
        "description": "Builds complete looks from your taste, body type, and occasion.",
        "emoji": "fa-shirt",
        "accent": "#c2410c",
        "system_prompt": (
            "You are Style Curator for ElegantShop. "
            "Craft elegant style suggestions with practical combinations and color matching. "
            "Prioritize confidence, comfort, and realism. "
            "Keep responses inside ElegantShop service scope."
        ),
        "quick_prompts": [
            "Build a clean casual look for weekend",
            "I need an elegant wedding guest outfit",
            "Suggest colors that match black shoes",
            "Compare minimal style vs classic style",
        ],
    },
    "care_copilot": {
        "id": "care_copilot",
        "name": "Care Copilot",
        "tagline": "Support answers in seconds.",
        "description": "Handles delivery, returns, and order concerns with action-oriented help.",
        "emoji": "fa-headset",
        "accent": "#1d4ed8",
        "system_prompt": (
            "You are Care Copilot for ElegantShop. "
            "Answer support questions clearly and politely. "
            "When a policy detail is unknown, say so and provide a safe next step. "
            "Keep responses inside ElegantShop service scope."
        ),
        "quick_prompts": [
            "How can I return a product?",
            "My order is delayed, what should I do?",
            "What payment options are usually available?",
            "اعطني خطوات حل مشكلة بشكل منطقي",
        ],
    },
    "copy_spark": {
        "id": "copy_spark",
        "name": "Copy Spark",
        "tagline": "Marketing copy on demand.",
        "description": "Writes product descriptions, ad hooks, and email ideas in your brand tone.",
        "emoji": "fa-bolt",
        "accent": "#7c3aed",
        "system_prompt": (
            "You are Copy Spark for ElegantShop. "
            "Write high-converting product and campaign copy with strong structure. "
            "Keep language vivid but not exaggerated. "
            "Keep responses inside ElegantShop service scope."
        ),
        "quick_prompts": [
            "Write a short product description for homepage",
            "Give me 5 ad headlines for a new collection",
            "Create a 3-line promo email for flash sale",
            "صغ لي خطة محتوى في 4 خطوات",
        ],
    },
}


def get_agent_catalog() -> dict[str, dict[str, Any]]:
    return AGENT_CATALOG


def get_agent(agent_id: str) -> dict[str, Any]:
    return AGENT_CATALOG.get(agent_id) or AGENT_CATALOG["shop_strategist"]


def _openai_api_key() -> str:
    key = getattr(settings, "OPENAI_API_KEY", "")
    if key:
        return key
    return os.getenv("OPENAI_API_KEY", "")


def _openai_model() -> str:
    model = getattr(settings, "OPENAI_MODEL", "")
    return model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def _sanitize_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not isinstance(history, list):
        return []

    sanitized: list[dict[str, str]] = []
    for item in history[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role", "")).strip().lower()
        if role not in {"user", "assistant"}:
            continue

        content = str(item.get("content", "")).strip()
        if not content:
            continue

        sanitized.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return sanitized


def _build_system_prompt(agent_prompt: str) -> str:
    return (
        f"{agent_prompt}\n\n"
        "Conversation policy:\n"
        "- Be context-aware and use recent conversation details.\n"
        "- Mirror the user's language (Arabic, English, or other).\n"
        "- Think step-by-step internally and present only concise reasoning, not hidden chain-of-thought.\n"
        "- Persuade ethically: use reasons, tradeoffs, and user benefit. Never pressure, shame, or deceive.\n"
        "- If the user asks a direct question, answer it directly first.\n"
        "- For complex asks, use a short numbered plan (3-6 steps).\n"
        "- Stay inside ElegantShop services: products, orders, payments, shipping, returns, and product marketing copy.\n"
        "- If a key detail is missing, ask one focused question.\n"
        "- Keep answers practical, clear, and non-generic.\n"
        "- If the user asks about topics completely unrelated to ElegantShop, its products, or its services, politely refuse to answer and state that you are an AI assistant for ElegantShop.\n"
        "- Do not apologize or use phrases like 'As an AI' or 'As a language model'."
    )


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()

    chunks: list[str] = []
    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text_part = content_item.get("text")
            if isinstance(text_part, str) and text_part.strip():
                chunks.append(text_part.strip())

    return "\n".join(chunks).strip()


def _call_openai(system_prompt: str, user_prompt: str, history: list[dict[str, Any]] | None = None) -> str:
    api_key = _openai_api_key()
    if not api_key:
        return ""

    chat_history = _sanitize_history(history)
    chat_input = [{"role": "system", "content": system_prompt}, *chat_history, {"role": "user", "content": user_prompt}]

    payload = {
        "model": _openai_model(),
        "temperature": 0.55,
        "max_output_tokens": 640,
        "input": chat_input,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            return _extract_output_text(parsed)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""


def _is_arabic_text(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_budget(message: str) -> float | None:
    text = message.lower()
    direct_patterns = [
        r"(?:under|below|less than|up to|budget)\s*\$?\s*(\d+(?:\.\d{1,2})?)",
        r"(?:تحت|اقل من|أقل من|حدود|ميزانية)\s*(\d+(?:\.\d{1,2})?)",
        r"\$\s*(\d+(?:\.\d{1,2})?)",
    ]
    for pattern in direct_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return float(match.group(1))
        except ValueError:
            continue
    return None


def _price_to_float(price_label: str) -> float | None:
    cleaned = re.sub(r"[^0-9.]", "", str(price_label))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _rank_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        recommendations,
        key=lambda item: _price_to_float(item.get("price_label", "")) if _price_to_float(item.get("price_label", "")) is not None else 1e9,
    )


def _is_store_intent(message: str) -> bool:
    text = message.lower()
    return _contains_any(text, STORE_INTENT_KEYWORDS)


def _is_copy_intent(message: str) -> bool:
    text = message.lower()
    return _contains_any(text, COPY_INTENT_KEYWORDS)


def _is_explicit_reasoning_intent(message: str) -> bool:
    text = message.lower().strip()
    keywords = [
        "calculate",
        "math",
        "equation",
        "formula",
        "compare",
        "vs",
        "difference",
        "plan",
        "roadmap",
        "steps",
        "strategy",
        "explain",
        "define",
        "meaning",
        "why",
        "how",
        "decision",
        "should i",
        "worth it",
        "احسب",
        "معادلة",
        "قارن",
        "مقارنة",
        "الفرق",
        "خطة",
        "خطوات",
        "استراتيجية",
        "اشرح",
        "فسر",
        "عرف",
        "عرّف",
        "لماذا",
        "كيف",
        "قرار",
    ]
    if _contains_any(text, keywords):
        return True

    is_question = ("?" in text) or ("؟" in text)
    if not is_question:
        return False

    question_words = [
        "what",
        "who",
        "where",
        "when",
        "why",
        "how",
        "ما",
        "من",
        "أين",
        "متى",
        "لماذا",
        "كيف",
    ]
    return _contains_any(text, question_words)


def _recent_user_context(history: list[dict[str, Any]] | None, limit: int = 3) -> list[str]:
    sanitized = _sanitize_history(history)
    recent_user_turns = [item["content"] for item in sanitized if item.get("role") == "user"]
    return recent_user_turns[-limit:]


def _scope_followup_hints() -> list[str]:
    return [
        "this",
        "that",
        "it",
        "same",
        "option",
        "first",
        "second",
        "details",
        "more info",
        "المزيد",
        "تفاصيل",
        "هذا",
        "هاذا",
        "ذلك",
        "نفس",
        "الخيار",
        "الأول",
        "الثاني",
        "اشرح أكثر",
    ]


def _service_scope_keywords() -> list[str]:
    return STORE_INTENT_KEYWORDS + COPY_INTENT_KEYWORDS + [
        "payment",
        "pay",
        "stripe",
        "paypal",
        "visa",
        "mastercard",
        "cancel",
        "exchange",
        "size",
        "stock",
        "inventory",
        "checkout",
        "order status",
        "دفع",
        "بطاقة",
        "الغاء",
        "إلغاء",
        "استبدال",
        "مقاس",
        "مخزون",
        "الدفع",
        "الطلب",
    ]


def _has_recent_service_context(history: list[dict[str, Any]] | None) -> bool:
    for turn in _recent_user_context(history, limit=4):
        if _contains_any(turn.lower(), _service_scope_keywords()):
            return True
    return False


def _is_service_scope_message(message: str, history: list[dict[str, Any]] | None = None) -> bool:
    text = message.lower().strip()
    if not text:
        return False

    if _contains_any(text, SMALL_TALK_KEYWORDS):
        return True

    if _contains_any(text, _service_scope_keywords()):
        return True

    # Allow short follow-up questions when the recent context is already in scope.
    if _has_recent_service_context(history):
        is_short_followup = len(text) <= 100
        looks_like_followup = ("?" in text) or ("؟" in text) or _contains_any(text, _scope_followup_hints())
        if is_short_followup and looks_like_followup:
            return True

    return False


def _scope_boundary_reply(message: str) -> str:
    if _is_arabic_text(message):
        return (
            "أقدر أتحدث معك بحرية داخل خدمات ElegantShop فقط: "
            "المنتجات، الأسعار، الطلبات، الدفع، الشحن، الإرجاع، والنسخ التسويقي للمنتجات. "
            "اكتب سؤالك ضمن هذا النطاق وسأساعدك مباشرة."
        )
    return (
        "I can chat freely within ElegantShop services only: "
        "products, pricing, orders, payments, shipping, returns, and product marketing copy. "
        "Ask me within this scope and I will help right away."
    )


def _extract_math_expression(message: str) -> str | None:
    normalized = (
        message.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("^", "**")
        .replace(",", "")
    )
    for match in re.finditer(r"[0-9\.\+\-\*\/%\(\)\s]{5,}", normalized):
        candidate = re.sub(r"\s+", " ", match.group(0)).strip()
        if not candidate:
            continue
        if not re.search(r"\d", candidate):
            continue
        if not re.search(r"[\+\-\*\/%]", candidate):
            continue
        if re.fullmatch(r"\d{1,4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}", candidate):
            continue
        return candidate
    return None


def _safe_eval_math_expression(expression: str) -> float | None:
    if not expression:
        return None

    if not re.fullmatch(r"[0-9\.\+\-\*\/%\(\)\s]{1,80}", expression):
        return None

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_BINARY_OPERATORS:
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, (ast.Div, ast.Mod)) and abs(right) < 1e-12:
                raise ZeroDivisionError
            if isinstance(node.op, ast.Pow):
                if abs(right) > 8 or abs(left) > 1e6:
                    raise ValueError("unsafe_power")
            result = SAFE_BINARY_OPERATORS[type(node.op)](left, right)
            if abs(result) > 1e12:
                raise ValueError("unsafe_magnitude")
            return float(result)

        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_UNARY_OPERATORS:
            value = _eval(node.operand)
            return float(SAFE_UNARY_OPERATORS[type(node.op)](value))

        raise ValueError("unsupported_expression")

    try:
        return _eval(parsed)
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def _extract_percent_of_expression(text: str) -> tuple[float, float] | None:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of|من)\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:percent)\s*(?:of)\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            continue
    return None


def _format_number(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _extract_comparison_pair(message: str) -> tuple[str, str] | None:
    compact = re.sub(r"\s+", " ", message).strip(" \t\r\n؟?!.,،:;")
    patterns = [
        r"(?i)(?:compare|comparison)\s+(.+?)\s+(?:and|vs|versus)\s+(.+)$",
        r"(?i)(.+?)\s+vs\.?\s+(.+)$",
        r"(?i)(?:difference between)\s+(.+?)\s+(?:and)\s+(.+)$",
        r"(?:قارن بين|مقارنة بين)\s+(.+?)\s+(?:و|أو|او|أم)\s*(.+)$",
        r"(?:الفرق بين)\s+(.+?)\s+(?:و|أو|او|أم)\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if not match:
            continue
        left = re.sub(r"\s+", " ", match.group(1)).strip(" ؟?!.,،:;")
        right = re.sub(r"\s+", " ", match.group(2)).strip(" ؟?!.,،:;")
        if not left or not right:
            continue
        if len(left) > 60 or len(right) > 60:
            continue
        return left, right
    return None


def _extract_explain_topic(message: str) -> str:
    text = message.strip()
    patterns = [
        r"(?i)(?:what is|what are|define|explain)\s+(.+)",
        r"(?:ما هو|ما هي|اشرح|فسر|عرف|عرّف)\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        topic = match.group(1).strip(" ؟?!.,،:;")
        if topic:
            return topic[:80]
    return ""


def _extract_copy_topic(message: str) -> str:
    compact = re.sub(r"\s+", " ", message).strip(" \t\r\n؟?!.,،:;")
    if not compact:
        return "your offer"
    if len(compact) <= 80:
        return compact
    return f"{compact[:80].rstrip()}..."


def _general_reasoning_fallback(
    message: str,
    recommendations: list[dict[str, Any]],
    context_line: str,
    is_ar: bool,
    history: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> str | None:
    text = message.lower().strip()
    reasoning_intent = _is_explicit_reasoning_intent(message)

    percent_data = _extract_percent_of_expression(text)
    if percent_data is not None:
        percent, base = percent_data
        result = (percent / 100.0) * base
        result_text = _format_number(result)
        if is_ar:
            return (
                f"{context_line}"
                f"النتيجة المباشرة: {result_text}\n"
                f"تفكير مختصر: {percent}% من {base} = ({percent}/100) × {base} = {result_text}."
            )
        return (
            f"{context_line}"
            f"Direct answer: {result_text}\n"
            f"Quick reasoning: {percent}% of {base} = ({percent}/100) x {base} = {result_text}."
        )

    expression = _extract_math_expression(message)
    if expression:
        result = _safe_eval_math_expression(expression)
        if result is not None:
            result_text = _format_number(result)
            if is_ar:
                return (
                    f"{context_line}"
                    f"النتيجة: {result_text}\n"
                    f"المعادلة التي تم حلها: {expression}"
                )
            return (
                f"{context_line}"
                f"Result: {result_text}\n"
                f"Solved expression: {expression}"
            )

    if not force and _is_store_intent(message):
        return None

    if not force and not reasoning_intent:
        return None

    compare_requested = _contains_any(text, ["compare", "vs", "versus", "difference", "قارن", "مقارنة", "الفرق"])
    if compare_requested:
        pair = _extract_comparison_pair(message)
        if pair:
            left, right = pair
            if is_ar:
                return (
                    f"{context_line}"
                    f"مقارنة عقلانية بين {left} و {right}:\n"
                    "1) قارن الهدف الأساسي: النتيجة الأهم التي تريدها.\n"
                    "2) قارن الكلفة مقابل القيمة: ليس السعر وحده.\n"
                    "3) قارن المخاطر والمرونة: سهولة التعديل لاحقًا.\n"
                    f"الخلاصة: اختر {left} إذا كانت الأولوية للسرعة، واختر {right} إذا كانت الأولوية للقيمة طويلة المدى."
                )
            return (
                f"{context_line}"
                f"Reasoned comparison for {left} vs {right}:\n"
                "1) Compare your primary objective first.\n"
                "2) Compare total value, not only upfront cost.\n"
                "3) Compare risk and flexibility over time.\n"
                f"Bottom line: choose {left} for speed, choose {right} for longer-term value."
            )

    wants_plan = _contains_any(
        text,
        ["plan", "roadmap", "steps", "strategy", "learn", "خطة", "خارطة", "خطوات", "استراتيجية", "اتعلم", "تعلم"],
    )
    if wants_plan:
        topic = _extract_explain_topic(message) or message.strip(" ؟?!.,،:;")[:80]
        if is_ar:
            return (
                f"{context_line}"
                f"خطة عملية لـ \"{topic}\":\n"
                "1) حدّد النتيجة المطلوبة ومعيار نجاح واضح.\n"
                "2) قسّم الهدف إلى مهام صغيرة أسبوعية.\n"
                "3) نفّذ دورة: تنفيذ -> قياس -> تحسين.\n"
                "4) راجع التقدم كل 7 أيام وعدّل الخطة."
            )
        return (
            f"{context_line}"
            f"Practical plan for \"{topic}\":\n"
            "1) Define one clear outcome and success metric.\n"
            "2) Split the goal into small weekly tasks.\n"
            "3) Run an execute -> measure -> improve loop.\n"
            "4) Review progress every 7 days and adjust."
        )

    wants_decision = _contains_any(
        text,
        ["should i", "which should", "worth it", "decision", "اختار", "أفضل", "هل أ", "هل ", "قرار"],
    )
    if wants_decision:
        if recommendations:
            ranked = _rank_recommendations(recommendations)
            top = ranked[0]
            if is_ar:
                return (
                    f"{context_line}"
                    f"قرار سريع مبني على المعطيات الحالية: ابدأ بـ {top['name']} ({top['price_label']}).\n"
                    "السبب: يوازن بين الوضوح والسعر الآن. إذا أعطيتني أولوية واحدة (سعر/جودة/سرعة) أحسمه بدقة أعلى."
                )
            return (
                f"{context_line}"
                f"Quick decision from current data: start with {top['name']} ({top['price_label']}).\n"
                "Reason: it gives a strong value baseline now. Share one priority (price/quality/speed) and I will finalize precisely."
            )

        if is_ar:
            return (
                f"{context_line}"
                "قاعدة قرار سريعة:\n"
                "1) اكتب أفضل نتيجة تريدها.\n"
                "2) رتّب الأولويات (سعر، جودة، وقت).\n"
                "3) اختر الخيار الذي يحقق أعلى أولوية بأقل مخاطرة."
            )
        return (
            f"{context_line}"
            "Quick decision framework:\n"
            "1) Define your desired outcome.\n"
            "2) Rank priorities (cost, quality, time).\n"
            "3) Pick the option that satisfies top priority with the lowest risk."
        )

    explain_requested = _contains_any(text, ["what is", "what are", "explain", "define", "meaning", "ما هو", "ما هي", "اشرح", "فسر", "عرّف"])
    if explain_requested:
        topic = _extract_explain_topic(message)
        if topic:
            if is_ar:
                return (
                    f"{context_line}"
                    f"شرح مبسط لـ \"{topic}\":\n"
                    "1) التعريف: المفهوم الأساسي باختصار.\n"
                    "2) الأهمية: لماذا يفيدك عمليًا.\n"
                    "3) التطبيق: خطوة أولى تبدأ بها اليوم."
                )
            return (
                f"{context_line}"
                f"Simple explanation of \"{topic}\":\n"
                "1) Definition: the core idea in plain terms.\n"
                "2) Why it matters: practical value.\n"
                "3) How to apply: one concrete first step today."
            )

    recent_context = _recent_user_context(history, limit=2)
    if recent_context:
        if is_ar:
            return (
                f"{context_line}"
                "أحتاج معطى إضافي واحد حتى أجيب بدقة أعلى.\n"
                "اكتب: النتيجة المطلوبة + أهم قيد عندك."
            )
        return (
            f"{context_line}"
            "I need one extra detail to answer with higher precision.\n"
            "Send: desired outcome + your most important constraint."
        )

    if is_ar:
        return f"{context_line}أرسل سؤالك مع الهدف والقيود، وسأجيبك بمنطق واضح ومباشر."
    return f"{context_line}Share your goal and constraints, and I will answer with clear reasoning."


def _shop_fallback(message: str, recommendations: list[dict[str, Any]], context_line: str, is_ar: bool) -> str:
    text = message.lower()
    budget = _extract_budget(message)
    ranked = _rank_recommendations(recommendations)

    compare_requested = _contains_any(text, ["compare", "vs", "difference", "قارن", "مقارنة", "الفرق"])
    cheapest_requested = _contains_any(text, ["cheap", "cheapest", "budget", "economy", "ارخص", "الأرخص", "اقتصادي"])
    premium_requested = _contains_any(text, ["premium", "best quality", "luxury", "فاخر", "جودة عالية", "الأفضل"])

    if not recommendations:
        if is_ar:
            return (
                f"{context_line}"
                "أحتاج تفاصيل أكثر حتى أعطيك جواب واضح.\n"
                "أرسل: الفئة المطلوبة + الميزانية + أهم أولوية (سعر/جودة/ضمان)."
            )
        return (
            f"{context_line}"
            "I need one more detail to give a clear answer.\n"
            "Send: category + budget + top priority (price/quality/warranty)."
        )

    within_budget = []
    if budget is not None:
        within_budget = [
            item for item in ranked
            if (_price_to_float(item.get("price_label", "")) is not None and _price_to_float(item.get("price_label", "")) <= budget)
        ]

    if cheapest_requested:
        primary = ranked[0]
    elif premium_requested:
        known = [item for item in ranked if _price_to_float(item.get("price_label", "")) is not None]
        primary = known[-1] if known else ranked[0]
    elif within_budget:
        primary = within_budget[-1]
    else:
        primary = ranked[0]

    if compare_requested and len(ranked) >= 2:
        first = ranked[0]
        second = ranked[1]
        if is_ar:
            return (
                f"{context_line}"
                f"المقارنة السريعة:\n"
                f"- {first['name']} ({first['price_label']}) مناسب إذا تريد أقل سعر.\n"
                f"- {second['name']} ({second['price_label']}) مناسب إذا تريد قيمة أعلى.\n"
                f"ترشيحي لك الآن: {primary['name']}."
            )
        return (
            f"{context_line}"
            f"Quick comparison:\n"
            f"- {first['name']} ({first['price_label']}) is better for lower cost.\n"
            f"- {second['name']} ({second['price_label']}) is better for stronger value.\n"
            f"My recommendation right now: {primary['name']}."
        )

    if is_ar:
        tail = "إذا تريد، أختار لك خيارًا واحدًا نهائيًا."
        if budget is not None and not within_budget:
            tail = f"لا يوجد خيار ضمن ميزانية {budget:.0f} حاليًا، وأقرب خيار هو {primary['name']}."
        return (
            f"{context_line}"
            f"بناءً على سؤالك، أفضل جواب الآن: {primary['name']} بسعر {primary['price_label']} "
            f"({primary['category']}).\n"
            f"{tail}"
        )

    tail = "If you want, I can pick one final winner for you."
    if budget is not None and not within_budget:
        tail = f"I could not find one under {budget:.0f}; closest option is {primary['name']}."
    return (
        f"{context_line}"
        f"Based on your question, the best answer now is: {primary['name']} at {primary['price_label']} "
        f"({primary['category']}).\n"
        f"{tail}"
    )


def _style_fallback(message: str, context_line: str, is_ar: bool) -> str:
    text = message.lower()
    occasion = "casual"
    if _contains_any(text, ["wedding", "party", "زفاف", "عرس", "حفلة"]):
        occasion = "wedding"
    elif _contains_any(text, ["work", "office", "business", "عمل", "مكتب"]):
        occasion = "work"
    elif _contains_any(text, ["interview", "مقابلة"]):
        occasion = "interview"

    if is_ar:
        if occasion == "wedding":
            return (
                f"{context_line}"
                "للزفاف: اختَر قطعة أساسية أنيقة بلون محايد، مع إكسسوار واحد بارز وحذاء مريح.\n"
                "لو ترسل ميزانيتك أجهّز لك طقم كامل بخيارات دقيقة."
            )
        if occasion == "work":
            return (
                f"{context_line}"
                "للعمل: قاعدة ألوان هادئة + قطعة رئيسية مرتبة + إكسسوار بسيط.\n"
                "هذا يعطي مظهرًا احترافيًا بدون مبالغة."
            )
        return (
            f"{context_line}"
            "الجواب الأنسب: ابدأ بقطعة رئيسية، أضف ألوان محايدة، ثم لمسة لون واحدة.\n"
            "أرسل المناسبة وسأبني لك لوك كامل."
        )

    if occasion == "wedding":
        return (
            f"{context_line}"
            "For a wedding: choose one elegant statement piece, a neutral base, and one refined accessory.\n"
            "Share your budget and I will build a full look."
        )
    if occasion == "work":
        return (
            f"{context_line}"
            "For work: use calm base colors, one polished main piece, and minimal accessories.\n"
            "It gives a professional look without overdoing it."
        )
    return (
        f"{context_line}"
        "Best approach: one key piece, neutral base, one accent color.\n"
        "Tell me the occasion and I will tailor the full outfit."
    )


def _care_fallback(message: str, context_line: str, is_ar: bool) -> str:
    text = message.lower()
    is_return = _contains_any(text, ["return", "refund", "استرجاع", "ارجاع", "إرجاع"])
    is_delay = _contains_any(text, ["delay", "late", "shipping", "delivery", "تأخير", "الشحنة", "توصيل"])
    is_payment = _contains_any(text, ["payment", "card", "visa", "mastercard", "paypal", "دفع", "بطاقة"])
    is_cancel = _contains_any(text, ["cancel", "cancellation", "إلغاء", "الغاء"])

    if is_ar:
        if is_return:
            return (
                f"{context_line}"
                "للاسترجاع: أرسل رقم الطلب + تاريخ الاستلام + حالة المنتج.\n"
                "بعدها أعطيك الخطوة التالية مباشرة."
            )
        if is_delay:
            return (
                f"{context_line}"
                "لتأخير الشحنة: أرسل رقم الطلب وسأعطيك المسار الأسرع للتتبع والتصعيد."
            )
        if is_payment:
            return (
                f"{context_line}"
                "بالنسبة للدفع: الخيار الأكثر أمانًا عادةً هو البطاقة مع تحقق ثنائي.\n"
                "إذا أردت أقارن لك بين الطرق المتاحة."
            )
        if is_cancel:
            return (
                f"{context_line}"
                "للإلغاء: أرسل رقم الطلب وحالته الحالية (قيد المعالجة/تم الشحن).\n"
                "بناءً عليها أحدد لك إن كان الإلغاء أو الاسترجاع هو الأسرع."
            )
        return (
            f"{context_line}"
            "أرسل نوع المشكلة (إرجاع/تأخير/دفع/إلغاء) مع رقم الطلب، وسأعطيك جوابًا مباشرًا."
        )

    if is_return:
        return (
            f"{context_line}"
            "For return: share order number, delivery date, and item condition.\n"
            "Then I will give the exact next step."
        )
    if is_delay:
        return (
            f"{context_line}"
            "For delayed shipping: share your order number and I will give the fastest tracking/escalation path."
        )
    if is_payment:
        return (
            f"{context_line}"
            "For payments: card with 2-step verification is usually the safest option.\n"
            "I can compare methods for your case."
        )
    if is_cancel:
        return (
            f"{context_line}"
            "For cancellation: share order number and current status.\n"
            "I will tell you whether cancellation or return is faster."
        )
    return (
        f"{context_line}"
        "Share the issue type (return/delay/payment/cancel) and order number for a direct answer."
    )


def _copy_fallback(message: str, context_line: str, is_ar: bool) -> str:
    text = message.lower()
    count_match = re.search(r"\b([2-9]|10)\b", text)
    count = int(count_match.group(1)) if count_match else 3

    wants_headlines = _contains_any(text, ["headline", "headlines", "hook", "عنوان", "عناوين"])
    wants_email = _contains_any(text, ["email", "campaign", "ايميل", "بريد", "حملة"])
    wants_copy = _is_copy_intent(message)

    if wants_headlines:
        if is_ar:
            lines = [f"{i + 1}) جودة تثق بها. سعر يرضيك." for i in range(count)]
            return f"{context_line}عناوين مقترحة:\n" + "\n".join(lines)
        lines = [f"{i + 1}) Built to Perform. Priced to Win." for i in range(count)]
        return f"{context_line}Suggested headlines:\n" + "\n".join(lines)

    if wants_email:
        if is_ar:
            return (
                f"{context_line}"
                "صيغة بريد سريعة:\n"
                "عنوان: عرض محدود لفترة قصيرة\n"
                "نص: اكتشف منتجاتنا الأكثر طلبًا اليوم مع قيمة أعلى وسعر أفضل.\n"
                "CTA: اطلب الآن قبل انتهاء العرض."
            )
        return (
            f"{context_line}"
            "Quick email draft:\n"
            "Subject: Limited-Time Offer You Shouldn't Miss\n"
            "Body: Discover our most-loved products with stronger value today.\n"
            "CTA: Shop now before the offer ends."
        )

    topic = _extract_copy_topic(message)
    if wants_copy:
        if is_ar:
            return (
                f"{context_line}"
                f"نسخة تسويقية سريعة لـ \"{topic}\":\n"
                "عنوان: قيمة أعلى، قرار أسهل.\n"
                "نص: منتج عملي مصمم ليعطيك نتيجة واضحة بدون تعقيد.\n"
                "CTA: اكتشف التفاصيل الآن."
            )
        return (
            f"{context_line}"
            f"Quick marketing copy for \"{topic}\":\n"
            "Headline: Better value, easier decision.\n"
            "Body: A practical choice designed to deliver clear results without complexity.\n"
            "CTA: Explore details now."
        )

    if is_ar:
        return (
            f"{context_line}"
            "هذا السؤال لا يبدو طلب كتابة تسويقية مباشرة.\n"
            "اكتب المطلوب بصيغة: نوع النص + المنتج/الخدمة + الهدف + النبرة."
        )
    return (
        f"{context_line}"
        "This does not look like a direct copywriting task.\n"
        "Use: content type + product/service + goal + tone."
    )


def _fallback_reply(agent_id: str, message: str, recommendations: list[dict[str, Any]], history: list[dict[str, Any]] | None = None) -> str:
    if not _is_service_scope_message(message, history=history):
        return _scope_boundary_reply(message)

    is_ar = _is_arabic_text(message)
    context_line = ""

    general_reply = _general_reasoning_fallback(
        message=message,
        recommendations=recommendations,
        context_line=context_line,
        is_ar=is_ar,
        history=history,
        force=False,
    )
    if general_reply:
        return general_reply

    if agent_id == "shop_strategist":
        return _shop_fallback(message, recommendations, context_line, is_ar)

    if agent_id == "style_curator":
        return _style_fallback(message, context_line, is_ar)

    if agent_id == "care_copilot":
        return _care_fallback(message, context_line, is_ar)

    if agent_id == "copy_spark":
        if not _is_copy_intent(message):
            general_for_copy = _general_reasoning_fallback(
                message=message,
                recommendations=recommendations,
                context_line=context_line,
                is_ar=is_ar,
                history=history,
                force=True,
            )
            if general_for_copy:
                return general_for_copy
        return _copy_fallback(message, context_line, is_ar)

    if is_ar:
        return f"{context_line}سأعطيك جوابًا أدق إذا أرسلت هدفك بشكل مباشر في سطر واحد."
    return f"{context_line}I can give a sharper answer if you share your goal in one clear sentence."


def generate_agent_reply(
    agent_id: str,
    message: str,
    recommendations: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
) -> str:
    agent = get_agent(agent_id)
    if not _is_service_scope_message(message, history=history):
        return _scope_boundary_reply(message)

    recommendations_context = "\n".join(
        [f"- {item['name']} | {item['price_label']} | {item['category']}" for item in recommendations[:6]]
    )
    history_context = "\n".join([f"- {item}" for item in _recent_user_context(history, limit=3)])
    user_prompt = (
        f"Latest user request:\n{message}\n\n"
        f"Recent user context:\n{history_context if history_context else '- No prior context.'}\n\n"
        f"Candidate products:\n{recommendations_context if recommendations_context else '- No direct matches yet.'}\n\n"
        "Answer based on the exact question, not a generic template.\n"
        "If the question is direct, start with a direct answer.\n"
        "For complex prompts, include concise reasoning and numbered steps.\n"
        "Stay within ElegantShop service scope while answering.\n"
        "Then include recommendation + reason + (optional) one tradeoff when relevant."
    )

    llm_reply = _call_openai(_build_system_prompt(agent["system_prompt"]), user_prompt, history=history)
    if llm_reply:
        return llm_reply

    return _fallback_reply(agent_id, message, recommendations, history=history)
