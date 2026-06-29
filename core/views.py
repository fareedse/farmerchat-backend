"""
FarmerChat Admin — Views
=========================
Enterprise-ready request handlers for:
- Admin dashboard
- Market rates
- Government schemes
- IoT sensors
- Mobile-friendly APIs
- Chatbot API
"""
from .services import (
    process_sensor_reading,
    run_login_checks,
    send_ai_followup_notification,
    send_ai_report_notification,
)
import json
import re
from datetime import timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from openai import OpenAI
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
)

from .models import (
    FarmerProfile,
    Expert,
    ChatSession,
    ChatMessage,
    MarketRate,
    GovernmentScheme,
    IoTDevice,
    SensorReading,
    WeatherAlert,
    ContentItem,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_latest_sensor_context():
    reading = (
        SensorReading.objects
        .select_related("device")
        .order_by("-timestamp")
        .first()
    )

    if not reading:
        return "No sensor data available."

    return f"""
Device: {reading.device.device_id}
Farm: {reading.device.farm_name}
Location: {reading.device.location}

Moisture: {reading.moisture}
Temperature: {reading.temperature}
Humidity: {reading.humidity}

Timestamp:
{reading.timestamp}
"""

def get_market_context():
    rates = (
        MarketRate.objects
        .filter(status="published")
        .order_by("-date_recorded")[:10]
    )

    if not rates:
        return "No market rates available."

    data = []

    for r in rates:
        data.append(
            f"""
Crop: {r.crop_name}
Region: {r.region}
Mandi: {r.mandi_name}
Price: {r.price}
Unit: {r.unit}
"""
        )

    return "\n".join(data)


def get_scheme_context():
    schemes = (
        GovernmentScheme.objects
        .filter(status="active")
        .order_by("-created_at")[:10]
    )

    if not schemes:
        return "No schemes available."

    data = []

    for s in schemes:
        data.append(
            f"""
Title: {s.title}
Region: {s.target_region}
Category: {s.category}

Description:
{s.description}
"""
        )

    return "\n".join(data)
from langdetect import detect

def ask_openai(message, history=None, productivity_prediction=None):

    try:
        lang = detect(message)
    except:
        lang = "en"

    market_context = get_market_context()
    scheme_context = get_scheme_context()
    sensor_context = get_latest_sensor_context()

    # Only search web for recent/current information
    web_keywords = [
        "today",
        "latest",
        "current",
        "price",
        "market",
        "online",
        "news",
        "weather",
        "scheme",
        "2026"
    ]

    web_context = ""

    if any(word in message.lower() for word in web_keywords):
        web_context = web_search(message)

    prediction_context = ""

    if productivity_prediction:
        prediction_context = productivity_prediction

    system_prompt = f"""
You are FarmerGPT.

You are an advanced AI assistant for farmers in Pakistan.

=========================
LANGUAGE
=========================

Reply ONLY in the same language as the user's message.

Detected language:
{lang}

Examples:

English -> English

Urdu -> Urdu

Hindi -> Hindi

Arabic -> Arabic

Never translate unless asked.

=========================
GENERAL KNOWLEDGE
=========================

You can answer BOTH:

• Agriculture questions
• General knowledge
• Science
• Technology
• Education
• Business
• Internet
• Programming

Do NOT refuse general questions.

=========================
PRIORITY
=========================

1 Database
2 IoT
3 Productivity Prediction
4 Web Search
5 Your own knowledge

=========================
IMPORTANT
=========================

Use database ONLY when relevant.

If user asks unrelated questions like

"What is AI?"

"Price of Apple online"

"Who is Elon Musk?"

"Python programming"

then answer normally using your own knowledge plus web search if available.

Do NOT force agriculture context.

=========================
DATABASE
=========================

Market Rates

{market_context}

Government Schemes

{scheme_context}

IoT

{sensor_context}

Prediction

{prediction_context}

Web

{web_context}

=========================
STYLE
=========================

Be accurate.

Use Markdown.

Give practical answers.

Use bullet points.

Never invent market prices.

Never invent schemes.

Never invent IoT values.

If no database information exists, clearly say so.

If web search contains newer information, use it.

Never say "I don't know" if you can answer from general knowledge.

RESPONSE POLICY

Always try to answer the user's question.

Use this priority:

1. Database
2. Web Search
3. Your own knowledge

If the database does not contain the answer, continue using web search.

If web search does not contain the exact answer, answer using your general knowledge.

Never stop after checking only one source.

Never reply "I don't know" unless the answer truly cannot be determined.

If an exact value (such as today's price) is unavailable, provide:

• the closest available information
• a realistic price range if appropriate
• explain that it is an estimate

Clearly label estimates as estimates.

Never fabricate database records, government schemes, IoT readings, or precise numerical values.

Always provide the most helpful answer possible.

PRICE QUESTIONS

If the user asks for a product price:

1. Search the database.
2. Use web search if needed.
3. If no current price is available, provide an approximate market price range based on general knowledge.
4. Clearly state that the figure is an estimate.
5. Mention factors that may affect the price.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=1200,
    )

    return response.choices[0].message.content.strip()

def get_chat_history(user, limit=12):
    if not user.is_authenticated:
        return []

    session = (
        ChatSession.objects
        .filter(farmer=user)
        .order_by("-started_at")
        .first()
    )

    if not session:
        return []

    history = []

    chats = (
        ChatMessage.objects
        .filter(session=session)
        .order_by("timestamp")
    )[-limit:]

    

    for chat in chats:
        history.append({
            "role": chat.role,
            "content": chat.content,
        })

    return history




from duckduckgo_search import DDGS


from duckduckgo_search import DDGS

def web_search(query):
    try:
        with DDGS() as ddgs:

            results = ddgs.text(
                query,
                region="pk-en",
                max_results=8
            )

            output = []

            for r in results:
                output.append(
                    f"""
Title: {r.get('title','')}
Body: {r.get('body','')}
URL: {r.get('href','')}
"""
                )

            return "\n".join(output)

    except Exception as e:
        print(e)
        return ""


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


def json_success(data=None, message="Success", status=200):
    payload = {
        "success": True,
        "message": message,
    }
    if data is not None:
        payload.update(data)
    return JsonResponse(payload, status=status)


def json_error(message="Something went wrong", status=400, errors=None):
    payload = {
        "success": False,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def get_json_body(request):
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def parse_float(value, default=0):
    try:
        if value in [None, ""]:
            return default
        return float(value)
    except Exception:
        return default


def parse_int(value, default=0):
    try:
        if value in [None, ""]:
            return default
        return int(value)
    except Exception:
        return default


def parse_iso_date(value):
    try:
        if value:
            return date.fromisoformat(value)
    except Exception:
        return None
    return None


def normalize_text(text):
    return (text or "").lower().strip()


def contains_any(text, keywords):
    text = normalize_text(text)
    return any(keyword.lower() in text for keyword in keywords)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
from django.contrib.auth.decorators import login_required

@login_required
@require_GET
def profile_api(request):
    profile = FarmerProfile.objects.get(user=request.user)

    return JsonResponse({
        "success": True,
        "user": {
            "id": request.user.id,
            "full_name": request.user.get_full_name(),
            "email": request.user.email,
            "phone": profile.phone,
            "location": profile.region,
            "farm_type": profile.primary_crop,
        }
    })


@login_required
@csrf_exempt
@require_POST
def update_profile_api(request):
    data = get_json_body(request)

    user = request.user
    profile = FarmerProfile.objects.get(user=user)

    full_name = data.get("full_name", "")
    names = full_name.split(" ", 1)

    user.first_name = names[0]
    user.last_name = names[1] if len(names) > 1 else ""
    user.email = data.get("email", user.email)
    user.username = user.email
    user.save()

    profile.phone = data.get("phone", profile.phone)
    profile.region = data.get("location", profile.region)
    profile.primary_crop = data.get("farm_type", profile.primary_crop)
    profile.save()

    return JsonResponse({
        "success": True,
        "message": "Profile updated successfully."
    })

    
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user and user.is_staff:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid credentials or insufficient permissions.")

    return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@require_POST
def register_api(request):
    data = get_json_body(request)

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    location = data.get("location", "").strip()
    farm_type = data.get("farm_type", "").strip()
    password = data.get("password", "").strip()

    if not all([full_name, email, phone, location, farm_type, password]):
        return json_error("All fields are required.", status=400)

    if User.objects.filter(username=email).exists():
        return json_error("Account already exists.", status=400)

    try:
        names = full_name.split(" ", 1)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=names[0],
            last_name=names[1] if len(names) > 1 else "",
        )

        FarmerProfile.objects.create(
            user=user,
            phone=phone,
            region=location,
            primary_crop=farm_type,
        )

        return json_success(
            {
                "user_id": user.id,
            },
            message="Account created successfully",
            status=201,
        )

    except Exception as e:
        return json_error(str(e), status=400)

@login_required
@user_passes_test(is_staff_user)
def dashboard_view(request):
    latest_reading = SensorReading.objects.all().order_by("-timestamp").first()
    now = timezone.now()

    total_users = User.objects.filter(is_staff=False).count()
    active_chats = ChatSession.objects.filter(status="active").count()
    total_farmers = FarmerProfile.objects.count()
    experts_available = Expert.objects.filter(status="available").count()
    total_experts = Expert.objects.filter(status__in=["available", "busy"]).count()

    expert_pct = round((experts_available / total_experts * 100) if total_experts else 0)

    chat_activity = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = ChatMessage.objects.filter(timestamp__date=day.date()).count()
        chat_activity.append({"label": day.strftime("%a"), "count": count})

    join_trends = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = FarmerProfile.objects.filter(joined_at__date=day.date()).count()
        join_trends.append({"label": day.strftime("%a"), "count": count})

    recent_sessions = (
        ChatSession.objects
        .select_related("farmer")
        .prefetch_related("messages")
        .order_by("-started_at")[:8]
    )

    recent_farmers = (
        FarmerProfile.objects
        .select_related("user")
        .order_by("-joined_at")[:5]
    )

    alerts = WeatherAlert.objects.filter(is_active=True).order_by("-issued_at")[:3]

    return render(request, "core/dashboard.html", {
        "total_users": total_users,
        "active_chats": active_chats,
        "total_farmers": total_farmers,
        "expert_pct": expert_pct,
        "chat_activity": json.dumps(chat_activity),
        "join_trends": json.dumps(join_trends),
        "recent_sessions": recent_sessions,
        "recent_farmers": recent_farmers,
        "alerts": alerts,
        "latest_reading": latest_reading,
    })


# ─────────────────────────────────────────────────────────────────────────────
# FARMER DATABASE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def farmer_list(request):
    q = request.GET.get("q", "").strip()
    region = request.GET.get("region", "").strip()

    farmers = FarmerProfile.objects.select_related("user").order_by("-joined_at")

    if q:
        farmers = farmers.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(region__icontains=q) |
            Q(primary_crop__icontains=q)
        )

    if region:
        farmers = farmers.filter(region__icontains=region)

    return render(request, "core/farmers.html", {
        "farmers": farmers,
        "q": q,
        "region": region,
        "total": farmers.count(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# CHAT MONITORING
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def chat_monitoring(request):
    sessions = (
        ChatSession.objects
        .select_related("farmer", "expert")
        .prefetch_related("messages")
        .order_by("-started_at")[:50]
    )

    return render(request, "core/chat_monitoring.html", {
        "sessions": sessions,
    })


# ─────────────────────────────────────────────────────────────────────────────
# EXPERT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def expert_list(request):
    experts = (
        Expert.objects
        .select_related("user")
        .annotate(chat_count=Count("chatsession"))
        .order_by("-rating")
    )

    return render(request, "core/experts.html", {
        "experts": experts,
    })


# ─────────────────────────────────────────────────────────────────────────────
# MARKET RATES ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def market_rates(request):
    status_filter = request.GET.get("status", "").strip()
    crop_filter = request.GET.get("crop", "").strip()
    region_filter = request.GET.get("region", "").strip()

    rates = MarketRate.objects.select_related("created_by").order_by("-date_recorded", "-updated_at")

    if status_filter:
        rates = rates.filter(status=status_filter)

    if crop_filter:
        rates = rates.filter(crop_name__icontains=crop_filter)

    if region_filter:
        rates = rates.filter(region__icontains=region_filter)

    counts = {
        "all": MarketRate.objects.count(),
        "published": MarketRate.objects.filter(status="published").count(),
        "pending": MarketRate.objects.filter(status="pending").count(),
        "draft": MarketRate.objects.filter(status="draft").count(),
    }

    return render(request, "core/market_rates.html", {
        "rates": rates,
        "counts": counts,
        "active_status": status_filter,
        "crop_filter": crop_filter,
        "region_filter": region_filter,
    })


@login_required
@user_passes_test(is_staff_user)
@require_POST
def market_rate_create(request):
    data = get_json_body(request)

    required_fields = ["crop_name", "mandi_name", "region", "price"]
    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return json_error("Required fields are missing.", errors=missing, status=400)

    try:
        rate = MarketRate.objects.create(
            crop_name=data.get("crop_name"),
            crop_name_ur=data.get("crop_name_ur", ""),
            mandi_name=data.get("mandi_name"),
            region=data.get("region"),
            price=parse_float(data.get("price")),
            unit=data.get("unit", "40kg"),
            price_change=parse_float(data.get("price_change")),
            status=data.get("status", "draft"),
            date_recorded=parse_iso_date(data.get("date_recorded")) or timezone.now().date(),
            created_by=request.user,
        )

        return json_success({
            "id": rate.pk,
            "rate": serialize_market_rate(rate),
        }, message=f"{rate.crop_name} rate saved.", status=201)

    except Exception as e:
        return json_error(str(e), status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def market_rate_update(request, pk):
    rate = get_object_or_404(MarketRate, pk=pk)
    data = get_json_body(request)

    try:
        editable_fields = [
            "crop_name",
            "crop_name_ur",
            "mandi_name",
            "region",
            "unit",
            "status",
        ]

        for field in editable_fields:
            if field in data:
                setattr(rate, field, data[field])

        if "price" in data:
            rate.price = parse_float(data.get("price"), rate.price)

        if "price_change" in data:
            rate.price_change = parse_float(data.get("price_change"), rate.price_change)

        if "date_recorded" in data:
            parsed_date = parse_iso_date(data.get("date_recorded"))
            if parsed_date:
                rate.date_recorded = parsed_date

        rate.save()

        return json_success({
            "id": rate.pk,
            "rate": serialize_market_rate(rate),
        }, message="Market rate updated successfully.")

    except Exception as e:
        return json_error(str(e), status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def market_rate_delete(request, pk):
    rate = get_object_or_404(MarketRate, pk=pk)
    crop_name = rate.crop_name
    rate.delete()

    return json_success(message=f"{crop_name} rate deleted successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNMENT SCHEMES ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def govt_schemes(request):
    status_filter = request.GET.get("status", "").strip()
    region_filter = request.GET.get("region", "").strip()
    category_filter = request.GET.get("category", "").strip()

    schemes = GovernmentScheme.objects.select_related("created_by").order_by("-created_at")

    if status_filter:
        schemes = schemes.filter(status=status_filter)

    if region_filter:
        schemes = schemes.filter(target_region__icontains=region_filter)

    if category_filter:
        schemes = schemes.filter(category=category_filter)

    counts = {
        "all": GovernmentScheme.objects.count(),
        "active": GovernmentScheme.objects.filter(status="active").count(),
        "review": GovernmentScheme.objects.filter(status="review").count(),
        "draft": GovernmentScheme.objects.filter(status="draft").count(),
        "expired": GovernmentScheme.objects.filter(status="expired").count(),
    }

    return render(request, "core/govt_schemes.html", {
        "schemes": schemes,
        "counts": counts,
        "active_filter": status_filter,
        "region_filter": region_filter,
        "category_filter": category_filter,
    })


@login_required
@user_passes_test(is_staff_user)
@require_POST
def scheme_create(request):
    data = get_json_body(request)

    required_fields = ["title", "description"]
    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return json_error("Required fields are missing.", errors=missing, status=400)

    try:
        scheme = GovernmentScheme.objects.create(
            title=data.get("title"),
            title_ur=data.get("title_ur", ""),
            description=data.get("description"),
            eligibility=data.get("eligibility", ""),
            benefits=data.get("benefits", ""),
            application_process=data.get("application_process", ""),
            required_documents=data.get("required_documents", ""),
            official_link=data.get("official_link", ""),
            category=data.get("category", "subsidy"),
            target_region=data.get("target_region", "All Regions"),
            beneficiaries=parse_int(data.get("beneficiaries")),
            budget_pkr=parse_int(data.get("budget_pkr"), None) if data.get("budget_pkr") else None,
            deadline=parse_iso_date(data.get("deadline")),
            status=data.get("status", "draft"),
            created_by=request.user,
        )

        return json_success({
            "id": scheme.pk,
            "scheme": serialize_scheme(scheme),
        }, message=f'Scheme "{scheme.title}" created.', status=201)

    except Exception as e:
        return json_error(str(e), status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def scheme_update(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)
    data = get_json_body(request)

    try:
        editable_fields = [
            "title",
            "title_ur",
            "description",
            "eligibility",
            "benefits",
            "application_process",
            "required_documents",
            "official_link",
            "category",
            "target_region",
            "status",
        ]

        for field in editable_fields:
            if field in data:
                setattr(scheme, field, data[field])

        if "beneficiaries" in data:
            scheme.beneficiaries = parse_int(data.get("beneficiaries"), scheme.beneficiaries)

        if "budget_pkr" in data:
            scheme.budget_pkr = parse_int(data.get("budget_pkr"), None) if data.get("budget_pkr") else None

        if "deadline" in data:
            scheme.deadline = parse_iso_date(data.get("deadline"))

        scheme.save()

        return json_success({
            "id": scheme.pk,
            "scheme": serialize_scheme(scheme),
        }, message="Scheme updated successfully.")

    except Exception as e:
        return json_error(str(e), status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def scheme_update_status(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)
    data = get_json_body(request)

    new_status = data.get("status", scheme.status)
    valid_statuses = [item[0] for item in GovernmentScheme.STATUS]

    if new_status not in valid_statuses:
        return json_error("Invalid status selected.", status=400)

    scheme.status = new_status
    scheme.save(update_fields=["status", "updated_at"])

    return json_success({
        "id": scheme.pk,
        "status": scheme.status,
    }, message="Scheme status updated successfully.")


@login_required
@user_passes_test(is_staff_user)
@require_POST
def scheme_delete(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)
    title = scheme.title
    scheme.delete()

    return json_success(message=f'"{title}" deleted successfully.')


# ─────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

def serialize_market_rate(rate):
    return {
        "id": rate.pk,
        "crop_name": rate.crop_name,
        "crop_name_ur": getattr(rate, "crop_name_ur", ""),
        "mandi_name": rate.mandi_name,
        "region": rate.region,
        "price": str(rate.price),
        "unit": getattr(rate, "unit", "40kg"),
        "price_change": str(getattr(rate, "price_change", 0)),
        "change_percent": str(getattr(rate, "price_change", 0)),
        "direction": getattr(rate, "change_direction", "neutral"),
        "status": rate.status,
        "date_recorded": rate.date_recorded.isoformat() if getattr(rate, "date_recorded", None) else None,
        "created_by": rate.created_by.username if getattr(rate, "created_by", None) else None,
        "updated_at": rate.updated_at.isoformat() if getattr(rate, "updated_at", None) else None,
    }


def serialize_scheme(scheme):
    return {
        "id": scheme.pk,
        "title": scheme.title,
        "title_ur": getattr(scheme, "title_ur", ""),
        "description": scheme.description,
        "eligibility": getattr(scheme, "eligibility", ""),
        "benefits": getattr(scheme, "benefits", ""),
        "application_process": getattr(scheme, "application_process", ""),
        "required_documents": getattr(scheme, "required_documents", ""),
        "official_link": getattr(scheme, "official_link", ""),
        "category": scheme.category,
        "category_display": scheme.get_category_display() if hasattr(scheme, "get_category_display") else scheme.category,
        "region": scheme.target_region,
        "target_region": scheme.target_region,
        "beneficiaries": scheme.beneficiaries,
        "budget_pkr": getattr(scheme, "budget_pkr", None),
        "status": scheme.status,
        "deadline": scheme.deadline.isoformat() if scheme.deadline else None,
        "created_by": scheme.created_by.username if getattr(scheme, "created_by", None) else None,
        "created_at": scheme.created_at.isoformat() if getattr(scheme, "created_at", None) else None,
        "updated_at": scheme.updated_at.isoformat() if getattr(scheme, "updated_at", None) else None,
    }

@csrf_exempt
@require_POST
def login_api(request):
    """
    Mobile Login API

    Features
    --------
    • User authentication
    • Django session login
    • Automatic notification checks
        - Profile completion
        - Weather alerts
    """

    data = get_json_body(request)

    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return json_error(
            "Email and password are required.",
            status=400
        )

    user = authenticate(
        request,
        username=email,
        password=password,
    )

    if not user:
        return json_error(
            "Invalid email or password.",
            status=401,
        )

    login(request, user)

    # --------------------------------------------------
    # Run notification checks after successful login
    # --------------------------------------------------

    profile = getattr(user, "farmer_profile", None)

    latitude = None
    longitude = None

    if profile:
        latitude = getattr(profile, "latitude", None)
        longitude = getattr(profile, "longitude", None)

    try:
        run_login_checks(
            user=user,
            latitude=latitude,
            longitude=longitude,
        )
    except Exception as e:
        print("Notification Error:", e)

    # --------------------------------------------------

    role = "Admin" if user.is_staff else "User"

    response = {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.get_full_name(),
            "role": role,
            "is_staff": user.is_staff,
        }
    }

    if profile:
        response["profile"] = {
            "phone": profile.phone,
            "region": profile.region,
            "village": profile.village,
            "primary_crop": profile.primary_crop,
            "land_acres": profile.land_acres,
        }

    return JsonResponse(response)

def serialize_sensor_reading(reading):
    return {
        "id": reading.pk,
        "device_id": reading.device.device_id,
        "farm_name": reading.device.farm_name,
        "location": reading.device.location,
        "moisture": reading.moisture,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "time": reading.timestamp.strftime("%H:%M"),
        "timestamp": reading.timestamp.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MOBILE / PUBLIC APIs
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def market_rates_api(request):
    crop = request.GET.get("crop", "").strip()
    region = request.GET.get("region", "").strip()
    mandi = request.GET.get("mandi", "").strip()
    status = request.GET.get("status", "published").strip()
    limit = min(parse_int(request.GET.get("limit"), 100), 200)

    rates = MarketRate.objects.all().order_by("-date_recorded", "-updated_at")

    if status:
        rates = rates.filter(status=status)

    if crop:
        rates = rates.filter(Q(crop_name__icontains=crop) | Q(crop_name_ur__icontains=crop))

    if region:
        rates = rates.filter(region__icontains=region)

    if mandi:
        rates = rates.filter(mandi_name__icontains=mandi)

    data = [serialize_market_rate(rate) for rate in rates[:limit]]

    return JsonResponse({
        "success": True,
        "count": len(data),
        "rates": data,
    })


@require_GET
def api_market_rates(request):
    return market_rates_api(request)


@require_GET
def schemes_api(request):
    region = request.GET.get("region", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "active").strip()
    q = request.GET.get("q", "").strip()
    limit = min(parse_int(request.GET.get("limit"), 100), 200)

    schemes = GovernmentScheme.objects.all().order_by("-created_at")

    if status:
        schemes = schemes.filter(status=status)

    if region:
        schemes = schemes.filter(target_region__icontains=region)

    if category:
        schemes = schemes.filter(category=category)

    if q:
        schemes = schemes.filter(
            Q(title__icontains=q) |
            Q(title_ur__icontains=q) |
            Q(description__icontains=q) |
            Q(target_region__icontains=q) |
            Q(category__icontains=q)
        )

    data = [serialize_scheme(scheme) for scheme in schemes[:limit]]

    return JsonResponse({
        "success": True,
        "count": len(data),
        "schemes": data,
    })


@require_GET
def scheme_detail_api(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)

    return JsonResponse({
        "success": True,
        "scheme": serialize_scheme(scheme),
    })


# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CHATBOT ENGINE
# ─────────────────────────────────────────────────────────────────────────────

CROP_ALIASES = {
    "wheat": ["wheat", "gandum", "گندم"],
    "rice": ["rice", "chawal", "basmati", "چاول"],
    "cotton": ["cotton", "kapas", "کپاس"],
    "sugarcane": ["sugarcane", "ganna", "گنا"],
    "tomato": ["tomato", "ٹماٹر"],
    "potato": ["potato", "aloo", "آلو"],
    "onion": ["onion", "pyaz", "پیاز"],
    "mango": ["mango", "aam", "آم"],
    "chili": ["chili", "chilli", "mirch", "مرچ"],
    "maize": ["maize", "corn", "makai", "مکئی"],
}

REGION_ALIASES = [
    "punjab", "sindh", "balochistan", "kpk", "kp",
    "lahore", "faisalabad", "multan", "karachi",
    "rawalpindi", "sahiwal", "bahawalpur", "khairpur",
    "gujranwala", "hyderabad", "quetta", "peshawar",
]

MARKET_KEYWORDS = [
    "rate", "rates", "price", "prices", "mandi", "market",
    "crop price", "today rate", "latest rate",
    "قیمت", "ریٹ", "منڈی", "بازار"
]

SCHEME_KEYWORDS = [
    "scheme", "schemes", "subsidy", "loan", "grant", "insurance",
    "government", "kissan card", "program", "programme", "aid",
    "سکیم", "سبسڈی", "قرض", "حکومت", "کسان کارڈ"
]

IOT_KEYWORDS = [
    "iot", "sensor", "moisture", "temperature", "humidity",
    "soil moisture", "device", "node", "field status",
    "نمی", "درجہ حرارت", "سینسر"
]

FERTILIZER_KEYWORDS = [
    "fertilizer", "urea", "dap", "npk", "potash", "zinc",
    "کھاد", "یوریا"
]

PEST_DISEASE_KEYWORDS = [
    "pest", "disease", "yellow leaves", "leaf", "spots", "fungus",
    "insect", "attack", "rust", "blight",
    "بیماری", "کیڑا", "پتے", "زرد"
]


def detect_chatbot_intent(message):
    msg = normalize_text(message)

    if contains_any(msg, MARKET_KEYWORDS):
        return "market_rate"

    if contains_any(msg, SCHEME_KEYWORDS):
        return "government_scheme"

    if contains_any(msg, IOT_KEYWORDS):
        return "iot_status"

    if contains_any(msg, FERTILIZER_KEYWORDS):
        return "fertilizer_advice"

    if contains_any(msg, PEST_DISEASE_KEYWORDS):
        return "pest_disease_advice"

    return "general"


def extract_crop_from_message(message):
    msg = normalize_text(message)

    for crop, aliases in CROP_ALIASES.items():
        for alias in aliases:
            if alias.lower() in msg:
                return crop

    return ""


def extract_region_from_message(message):
    msg = normalize_text(message)

    for region in REGION_ALIASES:
        if region in msg:
            return region

    return ""


def extract_node_from_message(message):
    match = re.search(r"(node[-_\s]?\d+|NODE[-_\s]?\d+)", message, re.IGNORECASE)
    if match:
        return match.group(0).replace(" ", "-").replace("_", "-").upper()
    return ""


def build_market_rate_response(message):
    crop = extract_crop_from_message(message)
    region = extract_region_from_message(message)

    rates = MarketRate.objects.filter(status="published").order_by("-date_recorded", "-updated_at")

    if crop:
        rates = rates.filter(crop_name__icontains=crop)

    if region:
        rates = rates.filter(Q(region__icontains=region) | Q(mandi_name__icontains=region))

    rates = list(rates[:5])

    if not rates:
        return {
            "text": "No matching market rate is available right now. Please try another crop or mandi name.",
            "data": [],
        }

    lines = ["Latest market rates:"]

    for rate in rates:
        change = rate.price_change
        direction_word = "up" if change > 0 else "down" if change < 0 else "stable"
        sign = "+" if change > 0 else ""
        lines.append(
            f"{rate.crop_name} in {rate.mandi_name}, {rate.region}: "
            f"PKR {rate.price} / {rate.unit}. "
            f"Change: {sign}{change}% ({direction_word})."
        )

    return {
        "text": "\n".join(lines),
        "data": [serialize_market_rate(rate) for rate in rates],
    }


def build_scheme_response(message):
    region = extract_region_from_message(message)
    msg = normalize_text(message)

    schemes = GovernmentScheme.objects.filter(status="active").order_by("-created_at")

    if region:
        schemes = schemes.filter(target_region__icontains=region)

    crop_or_topic_terms = ["kissan", "card", "insurance", "solar", "water", "drip", "subsidy", "loan", "training"]
    for term in crop_or_topic_terms:
        if term in msg:
            schemes = schemes.filter(
                Q(title__icontains=term) |
                Q(description__icontains=term) |
                Q(category__icontains=term)
            ) | GovernmentScheme.objects.filter(status="active", title__icontains=term)

    schemes = list(schemes.distinct()[:5])

    if not schemes:
        return {
            "text": "No active government scheme is available right now for this query.",
            "data": [],
        }

    lines = ["Available government schemes:"]

    for scheme in schemes:
        deadline = scheme.deadline.isoformat() if scheme.deadline else "Ongoing"
        benefit_text = getattr(scheme, "benefits", "") or scheme.description[:120]
        lines.append(
            f"{scheme.title} - Region: {scheme.target_region}. "
            f"Deadline: {deadline}. "
            f"Benefit: {benefit_text}"
        )

    return {
        "text": "\n".join(lines),
        "data": [serialize_scheme(scheme) for scheme in schemes],
    }


def build_iot_response(message):
    node_id = extract_node_from_message(message)

    readings = SensorReading.objects.select_related("device").order_by("-timestamp")

    if node_id:
        readings = readings.filter(device__device_id__iexact=node_id)

    reading = readings.first()

    if not reading:
        return {
            "text": "No IoT sensor data is available yet. Please check whether the sensor device is sending data.",
            "data": None,
        }

    moisture = reading.moisture
    temp = reading.temperature
    humidity = reading.humidity

    advice = []

    if moisture is not None:
        if moisture < 30:
            advice.append("Soil moisture is low. Irrigation may be required.")
        elif moisture > 85:
            advice.append("Soil moisture is very high. Avoid over-irrigation.")
        else:
            advice.append("Soil moisture is in a good range.")

    if temp is not None:
        if temp > 40:
            advice.append("Temperature is very high. Crop may face heat stress.")
        elif temp > 33:
            advice.append("Temperature is slightly high. Monitor crop condition.")
        else:
            advice.append("Temperature is normal.")

    if humidity is not None:
        if humidity > 88:
            advice.append("Humidity is high. Fungal disease risk may increase.")
        elif humidity < 40:
            advice.append("Humidity is low. Crop stress risk may increase.")
        else:
            advice.append("Humidity is suitable.")

    text = (
        f"Latest IoT reading from {reading.device.device_id} ({reading.device.farm_name}):\n"
        f"Soil moisture: {moisture}%\n"
        f"Temperature: {temp}°C\n"
        f"Humidity: {humidity}%\n"
        f"Time: {reading.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        + "\n".join(advice)
    )

    return {
        "text": text,
        "data": serialize_sensor_reading(reading),
    }


def build_fertilizer_response(message):
    crop = extract_crop_from_message(message)

    if crop:
        text = (
            f"For {crop}, fertilizer need depends on soil test, crop stage, and irrigation. "
            "As a safe general guide, use balanced nutrition and avoid overuse of urea. "
            "For accurate recommendation, check soil test results, crop age, and local agriculture department guidance."
        )
    else:
        text = (
            "Fertilizer recommendation depends on crop type, soil test, crop stage, and water availability. "
            "Please mention crop name and growth stage, for example: 'fertilizer for wheat at tillering stage'."
        )

    return {"text": text, "data": None}


def build_pest_disease_response(message):
    crop = extract_crop_from_message(message)

    if crop:
        text = (
            f"For {crop}, pest or disease diagnosis needs symptoms such as leaf color, spots, insects, crop stage, and weather. "
            "Remove heavily infected leaves if possible, avoid unnecessary pesticide use, and consult a local agriculture expert for chemical treatment. "
            "You can send a clearer symptom description like: yellow leaves, brown spots, white powder, insects, or wilting."
        )
    else:
        text = (
            "Please mention crop name and visible symptoms. Example: 'wheat leaves are yellow' or 'cotton has insects under leaves'. "
            "Then I can provide more specific guidance."
        )

    return {"text": text, "data": None}


def build_general_response(message):
    return {
        "text": (
            "I can help with crop guidance, market rates, government schemes, IoT sensor status, fertilizers, pests, and diseases.\n"
            "Try asking:\n"
            "1. What is wheat rate in Faisalabad?\n"
            "2. Any subsidy scheme for farmers in Punjab?\n"
            "3. What is my soil moisture?\n"
            "4. Fertilizer advice for wheat.\n"
            "5. Cotton pest problem."
        ),
        "data": None,
    }


def generate_chatbot_reply(message):
    intent = detect_chatbot_intent(message)

    if intent == "market_rate":
        result = build_market_rate_response(message)
    elif intent == "government_scheme":
        result = build_scheme_response(message)
    elif intent == "iot_status":
        result = build_iot_response(message)
    elif intent == "fertilizer_advice":
        result = build_fertilizer_response(message)
    elif intent == "pest_disease_advice":
        result = build_pest_disease_response(message)
    else:
        result = build_general_response(message)

    return {
        "intent": intent,
        "reply": result["text"],
        "data": result.get("data"),
    }


def save_chat_log(request, message, reply, intent, language="en"):
    try:
        session, created = ChatSession.objects.get_or_create(
       farmer=request.user if request.user.is_authenticated else None,
       status="active",
       defaults={
        "session_type": "ai",
        "topic": message[:180],
    }
   )

        ChatMessage.objects.create(
            session=session,
            role="user",
            content=message,
            language=language,
        )

        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply,
            language=language,
        )

        return session

    except Exception as e:
        print("Chat logging error:", e)
        return None


@csrf_exempt
@require_POST
def chatbot_api(request):
    """
    Main AI Chatbot API.

    Features
    --------
    ✓ OpenAI Chat
    ✓ Chat History
    ✓ Database Logging
    ✓ AI Report Notification
    ✓ AI Follow-up Notification
    """

    data = get_json_body(request)

    message = data.get("message", "").strip()

    if not message:
        return JsonResponse(
            {
                "success": False,
                "message": "Message required",
            },
            status=400,
        )

    try:

        # ------------------------------------
        # Previous conversation
        # ------------------------------------

        history = get_chat_history(request.user)

        # ------------------------------------
        # Ask OpenAI
        # ------------------------------------

        reply = ask_openai(
            message=message,
            history=history,
        )

        # ------------------------------------
        # Save chat
        # ------------------------------------

        save_chat_log(
            request=request,
            message=message,
            reply=reply,
            intent="openai",
        )

        # ------------------------------------
        # Notifications
        # ------------------------------------

        try:

            if request.user.is_authenticated:

                crop = extract_crop_from_message(message)

                send_ai_followup_notification(
                    user=request.user,
                    crop_name=crop,
                )

                send_ai_report_notification(
                    user=request.user,
                )

        except Exception as notification_error:

            print(
                "Notification Error:",
                notification_error,
            )

        # ------------------------------------
        # Response
        # ------------------------------------

        return JsonResponse(
            {
                "success": True,
                "reply": reply,
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )

# ─────────────────────────────────────────────────────────────────────────────
# IoT SENSORS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def iot_dashboard(request):
    devices = IoTDevice.objects.select_related("farmer").order_by("-registered")

    online = sum(1 for device in devices if device.is_online)
    offline = devices.count() - online

    primary = devices.filter(is_active=True).first()
    latest_reading = primary.readings.first() if primary else SensorReading.objects.order_by("-timestamp").first()

    return render(request, "core/iot_dashboard.html", {
        "devices": devices,
        "online": online,
        "offline": offline,
        "primary": primary,
        "latest_reading": latest_reading,
    })


@csrf_exempt
@require_POST
def receive_sensor_data(request):
    """
    Receive IoT sensor readings from ESP32/NodeMCU.

    Also triggers automatic soil moisture notifications
    for the farmer connected to the device.
    """

    try:
        data = get_json_body(request)

        device_id = data.get("device_id")

        if not device_id:
            return json_error(
                "device_id is required.",
                status=400,
            )

        device, created = IoTDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                "farm_name": data.get("farm_name", "Default Farm"),
                "location": data.get("location", "Main Field"),
            },
        )

        if not created:

            update_fields = []

            if (
                data.get("farm_name")
                and device.farm_name != data.get("farm_name")
            ):
                device.farm_name = data.get("farm_name")
                update_fields.append("farm_name")

            if (
                data.get("location")
                and device.location != data.get("location")
            ):
                device.location = data.get("location")
                update_fields.append("location")

            if update_fields:
                device.save(update_fields=update_fields)

        moisture = data.get("moisture")
        temperature = (
            data.get("temp")
            or data.get("temperature")
        )
        humidity = (
            data.get("hum")
            or data.get("humidity")
        )

        reading = SensorReading.objects.create(
            device=device,
            moisture=moisture,
            temperature=temperature,
            humidity=humidity,
        )

        device.last_ping = timezone.now()
        device.save(update_fields=["last_ping"])

        # =====================================================
        # Trigger IoT Notifications
        # =====================================================

        try:

            if device.farmer:

               process_sensor_reading(
               user=device.farmer.user,
               moisture=moisture,
                )

        except Exception as e:
            print("IoT Notification Error:", e)

        # =====================================================

        return json_success(
            {
                "reading": serialize_sensor_reading(reading)
            },
            message="Sensor data saved.",
            status=201,
        )

    except Exception as e:
        return json_error(
            str(e),
            status=400,
        )


@csrf_exempt
@require_POST
def iot_ingest(request):
    """
    Enterprise IoT Ingestion Endpoint

    Features
    --------
    ✓ Secret Authentication
    ✓ Device Auto Registration
    ✓ Safe Numeric Validation
    ✓ Reading Storage
    ✓ Last Ping Update
    ✓ Farmer Notifications
    ✓ Production Error Handling
    """

    secret = request.headers.get("X-IoT-Secret", "")
    expected_secret = getattr(settings, "IOT_API_SECRET", "")

    if expected_secret and secret != expected_secret:
        return json_error(
            "Unauthorized",
            status=401,
        )

    try:

        data = get_json_body(request)

        device_id = str(data.get("device_id", "")).strip()

        if not device_id:
            return json_error(
                "device_id is required.",
                status=400,
            )

        farm_name = str(
            data.get("farm_name", device_id)
        ).strip()

        location = str(
            data.get("location", "Unknown")
        ).strip()

        device, created = IoTDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                "farm_name": farm_name,
                "location": location,
            },
        )

        changed = False

        if device.farm_name != farm_name:
            device.farm_name = farm_name
            changed = True

        if device.location != location:
            device.location = location
            changed = True

        moisture = parse_float(
            data.get("moisture"),
            default=None,
        )

        temperature = parse_float(
            data.get(
                "temperature",
                data.get("temp"),
            ),
            default=None,
        )

        humidity = parse_float(
            data.get(
                "humidity",
                data.get("hum"),
            ),
            default=None,
        )

        reading = SensorReading.objects.create(
            device=device,
            moisture=moisture,
            temperature=temperature,
            humidity=humidity,
        )

        device.last_ping = timezone.now()

        if changed:
            device.save()

        else:
            device.save(update_fields=["last_ping"])

        try:

            if device.farmer:

                process_sensor_reading(
                    user=device.farmer.user,
                    moisture=moisture,
                )

        except Exception as notification_error:
            print(
                "IoT Notification Error:",
                notification_error,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "IoT data received successfully.",
                "reading": {
                    "id": reading.id,
                    "device": device.device_id,
                    "farm": device.farm_name,
                    "location": device.location,
                    "moisture": reading.moisture,
                    "temperature": reading.temperature,
                    "humidity": reading.humidity,
                    "timestamp": reading.timestamp.isoformat(),
                },
            },
            status=201,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=400,
        )

@csrf_exempt
@require_GET
def iot_live_api(request):
    node_id = request.GET.get("node", "").strip()

    try:
        queryset = SensorReading.objects.select_related("device")

        if node_id:
            queryset = queryset.filter(
                device__device_id__iexact=node_id
            )

        reading = queryset.latest("timestamp")

        return JsonResponse({
            "success": True,
            "reading": serialize_sensor_reading(reading)
        })

    except SensorReading.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "No sensor data available."
        }, status=404)

@csrf_exempt
@require_GET
def iot_history_api(request):
    node_id = request.GET.get("node", "").strip()

    queryset = SensorReading.objects.select_related("device")

    if node_id:
        queryset = queryset.filter(
            device__device_id__iexact=node_id
        )

    readings = queryset.order_by("-timestamp")[:24]

    return JsonResponse({
        "success": True,
        "count": len(readings),
        "readings": [
            serialize_sensor_reading(r)
            for r in readings
        ]
    })

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS / CONTENT / SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_user)
def analytics(request):
    top_crops = (
        MarketRate.objects
        .values("crop_name")
        .annotate(count=Count("id"), avg_price=Avg("price"))
        .order_by("-count")[:10]
    )

    chats_by_lang = (
        ChatMessage.objects
        .values("language")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return render(request, "core/analytics.html", {
        "top_crops": list(top_crops),
        "chats_by_lang": list(chats_by_lang),
    })


@login_required
@user_passes_test(is_staff_user)
def content_management(request):
    items = ContentItem.objects.select_related("created_by").order_by("-created_at")

    return render(request, "core/content.html", {
        "items": items,
    })


@login_required
@user_passes_test(is_staff_user)
def settings_view(request):
    return render(request, "core/settings.html")


@login_required
def notifications_api(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    data = []

    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "priority": n.priority,
            "action": n.action,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%d %b %Y %I:%M %p"),
        })

    return JsonResponse({
        "success": True,
        "notifications": data,
    })


@login_required
def unread_notification_count(request):
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "success": True,
        "count": count
    })



@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )

        notification.is_read = True
        notification.save()

        return JsonResponse({
            "success": True
        })

    except Notification.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Notification not found"
        }, status=404)