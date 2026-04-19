"""
Management command: python manage.py seed_data
Creates demo data so the dashboard isn't empty on first run.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (FarmerProfile, Expert, ChatSession, ChatMessage,
                         MarketRate, GovernmentScheme, IoTDevice, WeatherAlert)
from django.utils import timezone
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seeds the database with demo data for FarmerChat Admin'

    def handle(self, *args, **kwargs):
        self.stdout.write('🌱 Seeding demo data...')

        # Create superuser admin
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@farmerchat.com', 'admin123')
            admin.first_name = 'Admin'; admin.last_name = 'User'; admin.save()
            self.stdout.write('  ✓ Created admin user (username: admin, password: admin123)')
        else:
            admin = User.objects.get(username='admin')

        # Create farmers
        farmer_data = [
            ('ali_hassan',    'Ali',     'Hassan',    'Faisalabad', 'Chak 203',  'Wheat',     12.5, 'ur'),
            ('tariq_mahmood', 'Tariq',   'Mahmood',   'Multan',     'Shujabad',  'Cotton',    8.0,  'pa'),
            ('sara_bibi',     'Sara',    'Bibi',      'Lahore',     'Chunian',   'Rice',      5.0,  'ur'),
            ('ghulam_rasool', 'Ghulam',  'Rasool',    'Gujranwala', 'Wazirabad', 'Tomato',    3.5,  'en'),
            ('nadia_akhtar',  'Nadia',   'Akhtar',    'Rawalpindi', 'Gujar Khan','Wheat',     7.0,  'ur'),
            ('imran_ch',      'Imran',   'Chaudhry',  'Sargodha',   'Bhera',     'Sugarcane', 20.0, 'pa'),
        ]

        for uname, fn, ln, region, village, crop, acres, lang in farmer_data:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, f'{uname}@farmer.com', 'farmer123',
                                             first_name=fn, last_name=ln)
                FarmerProfile.objects.create(
                    user=u, region=region, village=village, primary_crop=crop,
                    land_acres=Decimal(str(acres)), language=lang, is_verified=random.choice([True, False]),
                    phone=f'03{random.randint(100000000,999999999)}'
                )
        self.stdout.write('  ✓ Created 6 demo farmers')

        # Create market rates
        rates = [
            ('Wheat',     'گندم',   'Faisalabad Mandi',  'Punjab',       4800,  2.1,  'published'),
            ('Rice',      'چاول',   'Lahore Mandi',      'Punjab',       9200,  0.8,  'published'),
            ('Cotton',    'کپاس',   'Bahawalpur Mandi',  'Punjab',       6400,  3.4,  'published'),
            ('Sugarcane', 'گنا',    'Multan Region',     'Punjab',       450,  -1.2,  'published'),
            ('Maize',     'مکئی',   'Gujranwala',        'Punjab',       2100,  1.5,  'pending'),
            ('Tomato',    'ٹماٹر',  'Rawalpindi',        'Punjab',       3200,  5.0,  'published'),
            ('Potato',    'آلو',    'Sahiwal Mandi',     'Punjab',       1800, -0.5,  'published'),
            ('Onion',     'پیاز',   'Karachi',           'Sindh',        2600,  2.3,  'published'),
            ('Mango',     'آم',     'Multan Export Hub', 'South Punjab', 8500,  7.8,  'published'),
            ('Chili',     'مرچ',    'Khairpur',          'Sindh',        5400,  1.1,  'draft'),
        ]

        if not MarketRate.objects.exists():
            for crop, crop_ur, mandi, region, price, change, status in rates:
                MarketRate.objects.create(
                    crop_name=crop, crop_name_ur=crop_ur, mandi_name=mandi,
                    region=region, price=Decimal(str(price)),
                    price_change=Decimal(str(change)), status=status,
                    created_by=admin
                )
            self.stdout.write('  ✓ Created 10 market rate entries')

        # Create government schemes
        schemes = [
            ('Kissan Card Subsidy 2026', 'کسان کارڈ سبسڈی ۲۰۲۶',
             'Financial aid for purchasing certified seeds, fertilizers, and pesticides at subsidized rates.',
             'subsidy', 'All Punjab', 12400, 'active', '2026-12-31'),
            ('Solar Tube-well Provision', 'شمسی ٹیوب ویل فراہمی',
             '60% subsidy on solar panel installation for agricultural tube-wells in water-stressed areas.',
             'solar', 'South Punjab & Sindh', 3200, 'review', '2026-08-15'),
            ('Drip Irrigation Subsidy', 'ڈرپ آبپاشی سبسڈی',
             '40% subsidy on drip irrigation equipment to promote water-efficient farming across arid zones.',
             'water', 'Sindh & Balochistan', 8700, 'active', None),
            ('Organic Farming Grant', 'نامیاتی کاشتکاری گرانٹ',
             'Direct grants for farmers transitioning to certified organic practices, including soil testing kits.',
             'organic', 'KPK', 540, 'draft', '2027-03-31'),
            ('Crop Insurance Programme', 'فصل بیمہ پروگرام',
             'Government-backed crop insurance covering losses due to floods, drought, and pest attacks.',
             'insurance', 'All Pakistan', 25000, 'active', None),
        ]

        if not GovernmentScheme.objects.exists():
            from datetime import date
            for title, title_ur, desc, cat, region, benef, status, deadline in schemes:
                GovernmentScheme.objects.create(
                    title=title, title_ur=title_ur, description=desc,
                    category=cat, target_region=region, beneficiaries=benef,
                    status=status, created_by=admin,
                    deadline=date.fromisoformat(deadline) if deadline else None
                )
            self.stdout.write('  ✓ Created 5 government schemes')

        # Create IoT devices
        if not IoTDevice.objects.exists():
            for did, farm, loc, dtype in [
                ('NODE-001', 'Farm A', 'Faisalabad', 'full'),
                ('NODE-002', 'Farm B', 'Lahore',     'full'),
                ('NODE-003', 'Farm C', 'Multan',     'soil'),
                ('NODE-004', 'Farm D', 'Gujranwala', 'full'),
            ]:
                IoTDevice.objects.create(
                    device_id=did, farm_name=farm, location=loc, device_type=dtype,
                    last_ping=timezone.now() if did in ('NODE-001','NODE-002') else None
                )
            self.stdout.write('  ✓ Created 4 IoT devices')

        # Chat sessions
        farmers = FarmerProfile.objects.all()
        if not ChatSession.objects.exists() and farmers.exists():
            topics = [
                'Wheat watering schedule query',
                'Cotton disease — yellowing leaves',
                'Rice market price enquiry',
                'Tomato fertilizer timing',
                'Sugarcane pest control',
                'Wheat sowing season advice',
            ]
            for i, f in enumerate(farmers[:6]):
                s = ChatSession.objects.create(
                    farmer=f.user, topic=topics[i % len(topics)],
                    status=random.choice(['active','active','closed']),
                    session_type='ai'
                )
                ChatMessage.objects.create(session=s, role='user',
                    content=f'Query about {topics[i % len(topics)]}', language=f.language)
                ChatMessage.objects.create(session=s, role='assistant',
                    content='AI response with detailed farming advice.', language='en')
            self.stdout.write('  ✓ Created 6 chat sessions')

        # Weather alert
        if not WeatherAlert.objects.exists():
            WeatherAlert.objects.create(
                title='Heavy Rain Warning — Punjab',
                message='Heavy rainfall expected in Central Punjab over the next 48 hours. Farmers advised to delay harvesting operations.',
                region='Central Punjab', severity='high', is_active=True
            )
            self.stdout.write('  ✓ Created 1 weather alert')

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))
        self.stdout.write('   → Login at /login/ with username: admin  password: admin123')
