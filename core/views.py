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
        session = ChatSession.objects.create(
            farmer=request.user if request.user.is_authenticated else None,
            session_type="ai",
            topic=message[:180],
            status="active",
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
    Flutter chatbot endpoint.

    Expected body:
    {
        "message": "What is wheat rate in Faisalabad?",
        "language": "en"
    }
    """

    data = get_json_body(request)
    message = data.get("message", "").strip()
    language = data.get("language", "en")

    if not message:
        return json_error("Message is required.", status=400)

    result = generate_chatbot_reply(message)

    session = save_chat_log(
        request=request,
        message=message,
        reply=result["reply"],
        intent=result["intent"],
        language=language,
    )

    return JsonResponse({
        "success": True,
        "intent": result["intent"],
        "reply": result["reply"],
        "data": result.get("data"),
        "session_id": session.pk if session else None,
    })


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
    try:
        data = get_json_body(request)
        device_id = data.get("device_id")

        if not device_id:
            return json_error("device_id is required.", status=400)

        device, created = IoTDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                "farm_name": data.get("farm_name", "Default Farm"),
                "location": data.get("location", "Main Field"),
            }
        )

        if not created:
            update_fields = []
            if data.get("farm_name") and device.farm_name != data.get("farm_name"):
                device.farm_name = data.get("farm_name")
                update_fields.append("farm_name")
            if data.get("location") and device.location != data.get("location"):
                device.location = data.get("location")
                update_fields.append("location")
            if update_fields:
                device.save(update_fields=update_fields)

        reading = SensorReading.objects.create(
            device=device,
            temperature=data.get("temp") or data.get("temperature"),
            humidity=data.get("hum") or data.get("humidity"),
            moisture=data.get("moisture"),
        )

        device.last_ping = timezone.now()
        device.save(update_fields=["last_ping"])

        return json_success({
            "reading": serialize_sensor_reading(reading)
        }, message="Sensor data saved.", status=201)

    except Exception as e:
        return json_error(str(e), status=400)


@csrf_exempt
@require_POST
def iot_ingest(request):
    secret = request.headers.get("X-IoT-Secret", "")
    expected_secret = getattr(settings, "IOT_API_SECRET", "")

    if expected_secret and secret != expected_secret:
        return json_error("Unauthorized", status=401)

    try:
        data = get_json_body(request)
        device_id = data.get("device_id")

        if not device_id:
            return json_error("device_id is required.", status=400)

        device, created = IoTDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                "farm_name": data.get("farm_name", device_id),
                "location": data.get("location", "Unknown"),
            }
        )

        reading = SensorReading.objects.create(
            device=device,
            moisture=data.get("moisture"),
            temperature=data.get("temperature") or data.get("temp"),
            humidity=data.get("humidity") or data.get("hum"),
        )

        device.last_ping = timezone.now()
        device.save(update_fields=["last_ping"])

        return json_success({
            "reading": serialize_sensor_reading(reading)
        }, message="IoT data received.", status=201)

    except Exception as e:
        return json_error(str(e), status=400)


@login_required
def iot_live_api(request):
    node_id = request.GET.get("node", "").strip()

    try:
        queryset = SensorReading.objects.select_related("device")

        if node_id:
            queryset = queryset.filter(device__device_id=node_id)

        reading = queryset.latest("timestamp")

        return JsonResponse({
            "success": True,
            **serialize_sensor_reading(reading),
        })

    except SensorReading.DoesNotExist:
        return json_error("No sensor data available yet.", status=404)


@login_required
def iot_history_api(request):
    node_id = request.GET.get("node", "").strip()

    queryset = SensorReading.objects.select_related("device")

    if node_id:
        queryset = queryset.filter(device__device_id=node_id)

    readings = list(reversed(list(queryset.order_by("-timestamp")[:24])))

    return JsonResponse({
        "success": True,
        "count": len(readings),
        "readings": [serialize_sensor_reading(reading) for reading in readings],
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