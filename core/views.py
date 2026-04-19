"""
FarmerChat Admin — Views
=========================
All request handlers for the admin dashboard.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta

from .models import (
    FarmerProfile, Expert, ChatSession, ChatMessage,
    MarketRate, GovernmentScheme, IoTDevice, SensorReading,
    WeatherAlert, ContentItem
)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import IoTDevice, SensorReading

@csrf_exempt
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            
            # Check karein ke device register hai ya nahi
            device, created = IoTDevice.objects.get_or_create(
                device_id=device_id, 
                defaults={'farm_name': 'Default Farm', 'location': 'Main Field'}
            )

            # Database mein save karein
            SensorReading.objects.create(
                device=device,
                temperature=data.get('temp'),
                humidity=data.get('hum'),
                moisture=data.get('moisture')
            )
            return JsonResponse({"status": "success"}, status=201)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

is_staff = lambda u: u.is_staff



# ─── AUTH ────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user and user.is_staff:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials or insufficient permissions.')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def dashboard_view(request):
    latest_reading = SensorReading.objects.all().order_by('-timestamp').first()
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    # Stats
    total_users    = User.objects.filter(is_staff=False).count()
    active_chats   = ChatSession.objects.filter(status='active').count()
    total_farmers  = FarmerProfile.objects.count()
    experts_avail  = Expert.objects.filter(status='available').count()
    total_experts  = Expert.objects.filter(status__in=['available','busy']).count()
    expert_pct     = round((experts_avail / total_experts * 100) if total_experts else 0)

    # Chat activity last 7 days (by day)
    chat_activity = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = ChatMessage.objects.filter(
            timestamp__date=day.date()
        ).count()
        chat_activity.append({'label': day.strftime('%a'), 'count': count})

    # Recent join trends (last 7 days of farmer registrations)
    join_trends = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = FarmerProfile.objects.filter(joined_at__date=day.date()).count()
        join_trends.append({'label': day.strftime('%a'), 'count': count})

    # Recent chat sessions
    recent_sessions = ChatSession.objects.select_related('farmer').order_by('-started_at')[:8]

    # Recent farmers
    recent_farmers  = FarmerProfile.objects.select_related('user').order_by('-joined_at')[:5]

    # Active alerts
    alerts = WeatherAlert.objects.filter(is_active=True).order_by('-issued_at')[:3]

    context = {
        'total_users':   total_users,
        'active_chats':  active_chats,
        'total_farmers': total_farmers,
        'expert_pct':    expert_pct,
        'chat_activity': json.dumps(chat_activity),
        'join_trends':   json.dumps(join_trends),
        'recent_sessions': recent_sessions,
        'recent_farmers':  recent_farmers,
        'alerts': alerts,
        'latest_reading': latest_reading,
    }
    return render(request, 'core/dashboard.html', context)


# ─── FARMER DATABASE ─────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def farmer_list(request):
    q = request.GET.get('q', '')
    region = request.GET.get('region', '')
    farmers = FarmerProfile.objects.select_related('user').order_by('-joined_at')
    if q:
        farmers = farmers.filter(user__username__icontains=q) | \
                  farmers.filter(region__icontains=q) | \
                  farmers.filter(primary_crop__icontains=q)
    if region:
        farmers = farmers.filter(region__icontains=region)
    return render(request, 'core/farmers.html', {
        'farmers': farmers, 'q': q, 'region': region,
        'total': farmers.count(),
    })


# ─── CHAT MONITORING ─────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def chat_monitoring(request):
    sessions = ChatSession.objects.select_related('farmer', 'expert').prefetch_related('messages').order_by('-started_at')[:50]
    return render(request, 'core/chat_monitoring.html', {'sessions': sessions})


# ─── EXPERT MANAGEMENT ───────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def expert_list(request):
    experts = Expert.objects.select_related('user').annotate(
        chat_count=Count('chatsession')
    ).order_by('-rating')
    return render(request, 'core/experts.html', {'experts': experts})


# ─── MARKET RATES ────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def market_rates(request):
    rates = MarketRate.objects.select_related('created_by').order_by('-date_recorded', '-updated_at')
    published = rates.filter(status='published').count()
    pending   = rates.filter(status='pending').count()
    draft     = rates.filter(status='draft').count()
    return render(request, 'core/market_rates.html', {
        'rates': rates,
        'published': published, 'pending': pending, 'draft': draft,
        'total': rates.count(),
    })


@login_required
@user_passes_test(is_staff)
@require_POST
def market_rate_create(request):
    try:
        data = json.loads(request.body)
        rate = MarketRate.objects.create(
            crop_name    = data['crop_name'],
            crop_name_ur = data.get('crop_name_ur', ''),
            mandi_name   = data['mandi_name'],
            region       = data['region'],
            price        = float(data['price']),
            unit         = data.get('unit', '40kg'),
            price_change = float(data.get('price_change', 0)),
            status       = data.get('status', 'draft'),
            created_by   = request.user,
        )
        return JsonResponse({'success': True, 'id': rate.pk, 'message': f'{rate.crop_name} rate saved.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def market_rate_delete(request, pk):
    rate = get_object_or_404(MarketRate, pk=pk)
    crop = rate.crop_name
    rate.delete()
    return JsonResponse({'success': True, 'message': f'{crop} rate deleted.'})


@login_required
@user_passes_test(is_staff)
@require_POST
def market_rate_update(request, pk):
    rate = get_object_or_404(MarketRate, pk=pk)
    try:
        data = json.loads(request.body)
        for field in ['crop_name', 'mandi_name', 'region', 'status']:
            if field in data:
                setattr(rate, field, data[field])
        if 'price' in data:        rate.price = float(data['price'])
        if 'price_change' in data: rate.price_change = float(data['price_change'])
        rate.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─── GOVERNMENT SCHEMES ──────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def govt_schemes(request):
    status_filter = request.GET.get('status', '')
    schemes = GovernmentScheme.objects.select_related('created_by').order_by('-created_at')
    if status_filter:
        schemes = schemes.filter(status=status_filter)
    counts = {
        'all':    GovernmentScheme.objects.count(),
        'active': GovernmentScheme.objects.filter(status='active').count(),
        'review': GovernmentScheme.objects.filter(status='review').count(),
        'draft':  GovernmentScheme.objects.filter(status='draft').count(),
    }
    return render(request, 'core/govt_schemes.html', {
        'schemes': schemes, 'counts': counts,
        'active_filter': status_filter,
    })


@login_required
@user_passes_test(is_staff)
@require_POST
def scheme_create(request):
    try:
        data = json.loads(request.body)
        scheme = GovernmentScheme.objects.create(
            title         = data['title'],
            title_ur      = data.get('title_ur', ''),
            description   = data['description'],
            category      = data.get('category', 'subsidy'),
            target_region = data.get('target_region', 'All Regions'),
            beneficiaries = int(data.get('beneficiaries', 0)),
            status        = data.get('status', 'draft'),
            created_by    = request.user,
        )
        if data.get('deadline'):
            from datetime import date
            scheme.deadline = date.fromisoformat(data['deadline'])
            scheme.save()
        return JsonResponse({'success': True, 'id': scheme.pk, 'message': f'Scheme "{scheme.title}" created.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff)
@require_POST
def scheme_delete(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)
    title = scheme.title
    scheme.delete()
    return JsonResponse({'success': True, 'message': f'"{title}" deleted.'})


@login_required
@user_passes_test(is_staff)
@require_POST
def scheme_update_status(request, pk):
    scheme = get_object_or_404(GovernmentScheme, pk=pk)
    data = json.loads(request.body)
    scheme.status = data.get('status', scheme.status)
    scheme.save()
    return JsonResponse({'success': True})


# ─── IoT SENSORS ─────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def iot_dashboard(request):
    devices  = IoTDevice.objects.select_related('farmer').order_by('-registered')
    online   = sum(1 for d in devices if d.is_online)
    offline  = devices.count() - online
    # Latest reading for the primary device
    primary = devices.filter(is_active=True).first()
    latest_reading = None
    if primary:
        latest_reading = primary.readings.first()
    return render(request, 'core/iot_dashboard.html', {
        'devices': devices, 'online': online, 'offline': offline,
        'primary': primary, 'latest_reading': latest_reading,
    })


@csrf_exempt
@require_POST
def iot_ingest(request):
    """Endpoint that ESP8266 posts sensor data to."""
    from django.conf import settings
    secret = request.headers.get('X-IoT-Secret', '')
    if secret != settings.IOT_API_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        data    = json.loads(request.body)
        device, _ = IoTDevice.objects.get_or_create(
            device_id=data['device_id'],
            defaults={'farm_name': data.get('farm_name', data['device_id']),
                      'location': data.get('location', 'Unknown')}
        )
        SensorReading.objects.create(
            device=device,
            moisture=data.get('moisture'),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
        )
        device.last_ping = timezone.now()
        device.save(update_fields=['last_ping'])
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def iot_live_api(request):
    node_id = request.GET.get('node', '')
    try:
        qs = SensorReading.objects.filter(device__device_id=node_id) if node_id \
             else SensorReading.objects.all()
        reading = qs.latest('timestamp')
        return JsonResponse({
            'moisture': reading.moisture,
            'temperature': reading.temperature,
            'humidity': reading.humidity,
            'timestamp': reading.timestamp.isoformat(),
        })
    except SensorReading.DoesNotExist:
        return JsonResponse({'error': 'No data yet'}, status=404)


@login_required
def iot_history_api(request):
    node_id = request.GET.get('node', '')
    qs = SensorReading.objects.filter(device__device_id=node_id) if node_id \
         else SensorReading.objects.all()
    readings = list(reversed(list(qs.order_by('-timestamp')[:24])))
    return JsonResponse({'readings': [
        {'moisture': r.moisture, 'temperature': r.temperature,
         'humidity': r.humidity, 'time': r.timestamp.strftime('%H:%M')}
        for r in readings
    ]})


# ─── ANALYTICS ───────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def analytics(request):
    top_crops = MarketRate.objects.values('crop_name').annotate(
        count=Count('id'), avg_price=Avg('price')
    ).order_by('-count')[:10]
    chats_by_lang = ChatMessage.objects.values('language').annotate(count=Count('id')).order_by('-count')
    return render(request, 'core/analytics.html', {
        'top_crops': list(top_crops),
        'chats_by_lang': list(chats_by_lang),
    })


# ─── CONTENT MANAGEMENT ──────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def content_management(request):
    items = ContentItem.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'core/content.html', {'items': items})


# ─── SETTINGS ────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_staff)
def settings_view(request):
    return render(request, 'core/settings.html')


# ─── API: Market rates JSON (for dashboard widget) ───────────────────────────
@login_required
def market_rates_api(request):
    rates = MarketRate.objects.filter(status='published').order_by('-date_recorded')[:20]
    return JsonResponse({'rates': [
        {'crop': r.crop_name, 'mandi': r.mandi_name,
         'price': str(r.price), 'change': str(r.price_change),
         'direction': r.change_direction}
        for r in rates
    ]})


# ─── API: Schemes JSON (for dashboard widget) ────────────────────────────────
@login_required
def schemes_api(request):
    schemes = GovernmentScheme.objects.filter(status='active').order_by('-created_at')[:10]
    return JsonResponse({'schemes': [
        {'id': s.pk, 'title': s.title, 'region': s.target_region,
         'status': s.status, 'beneficiaries': s.beneficiaries,
         'deadline': s.deadline.isoformat() if s.deadline else None}
        for s in schemes
    ]})
