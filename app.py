import os
import json
import base64
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="AI Trading Strategy Backend")

# Local development uchun. Deploy qilishda faqat o'z domeningizni ruxsat eting.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OPENAI_API_KEY muhit o'zgaruvchisi oldindan sozlangan bo'lishi kerak.
client = OpenAI()

STRATEGY_PROMPT = """
Sen trading grafik skrinshotlarini tahlil qiluvchi yordamchisan.
Faqat rasmda ko'rinadigan dalillarga tayangan holda javob ber.
Narxlarni, indikatorlarni yoki sham ma'lumotlarini o'ylab topma.

Tahlilni quyidagi tartibda bajargin:

1. MARKET STRUCTURE:
- Swing High va Swing Low nuqtalarini ko'rib chiq.
- HH, HL, LH, LL ketma-ketligini bahola.
- Trendni bullish, bearish, ranging yoki unclear deb belgilagin.
- Dalillarni yoz.

2. LIQUIDITY ZONES:
- Equal Highs (EQH), Equal Lows (EQL), oldingi swing high/low ni qidir.
- Buy-side va sell-side liquidity ehtimoliy hududlarini ko'rsat.
- Narx o'qi o'qilmasa, aniq narx kiritma.

3. LIQUIDITY SWEEP:
- Narx muhim high/low darajasidan o'tib, qaytganiga vizual dalil bormi?
- Status confirmed, possible, none yoki unclear bo'lsin.
- Rasmning o'zi likvidlik yig'ilganini mutlaq isbotlamasligini yodda tut.

4. STRUCTURE SHIFT:
- BOS yoki CHoCH ni qidir.
- Qaysi swing darajasi buzilganini tushuntir.
- Sham yopilishi yoki daraja buzilishi aniq ko'rinmasa, tasdiqlangan demagin.

5. ENTRY ZONE:
- Oldingi bosqichlar dalillarini birga bahola.
- Faqat setup yetarli bo'lsa LONG yoki SHORT ssenariysi ber; aks holda NO TRADE.
- Entry, Stop Loss va Take Profit narxlari rasmda aniq ko'rinmasa null bo'lsin.
- Stop Loss setup bekor bo'ladigan joyda, TP esa keyingi ko'rinadigan liquidity darajasi atrofida bo'lishi mumkin.
- Risk/foyda nisbatini o'ylab topma.

Faqat valid JSON qaytar:
{
  "market_structure": {
    "trend": "bullish | bearish | ranging | unclear",
    "evidence": [],
    "swing_points": []
  },
  "liquidity_zones": {
    "buy_side": [],
    "sell_side": [],
    "evidence": []
  },
  "liquidity_sweep": {
    "status": "confirmed | possible | none | unclear",
    "direction": "above_highs | below_lows | none | unclear",
    "evidence": []
  },
  "structure_shift": {
    "status": "confirmed | possible | none | unclear",
    "type": "BOS | CHoCH | none | unclear",
    "direction": "bullish | bearish | unclear",
    "evidence": []
  },
  "entry_plan": {
    "signal": "LONG | SHORT | NO TRADE",
    "entry_zone": null,
    "stop_loss": null,
    "take_profit": [],
    "reason": [],
    "invalidation": null
  },
  "confidence": "low | medium | high",
  "limitations": []
}
Narxlar noaniq bo'lsa taxminiy raqamlarni yaratma.
Bu ehtimoliy texnik ssenariy, kafolatlangan prognoz emas.
"""

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "AI Trading Strategy Backend",
        "analyze_endpoint": "/analyze"
    }

@app.post("/analyze")
async def analyze_chart(
    image: UploadFile = File(...),
    timeframe: str = Form("5m"),
    asset: str = Form("BTCUSDT"),
):
    allowed_types = {"image/png", "image/jpeg", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="PNG, JPG yoki WEBP rasm yuboring."
        )

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Rasm bo'sh.")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Rasm hajmi 10 MB dan oshmasin.")

    try:
        picture = Image.open(BytesIO(raw))
        picture.verify()
        picture = Image.open(BytesIO(raw))
        formats = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "WEBP": "image/webp",
        }
        mime = formats.get(picture.format)
        if not mime:
            raise ValueError("Unsupported image format")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Rasm faylini o'qib bo'lmadi.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY sozlanmagan. Terminalda API kalitini kiriting."
        )

    data_url = "data:" + mime + ";base64," + base64.b64encode(raw).decode("utf-8")
    instructions = (
        f"Aktiv: {asset}\nTimeframe: {timeframe}\n\n" + STRATEGY_PROMPT
    )

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": instructions},
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        return {
            "success": True,
            "asset": asset,
            "timeframe": timeframe,
            "analysis": result,
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI javobi JSON formatida emas.")
    except Exception as exc:
        # Batafsil xatolar server terminalida ko'rinadi; mijozga maxfiy ma'lumot chiqarmaymiz.
        print("AI request failed:", repr(exc))
        raise HTTPException(
            status_code=502,
            detail="AI tahlili bajarilmadi. API kaliti, internet va modelga kirishni tekshiring."
        )
