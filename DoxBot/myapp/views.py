import datetime
from django.core.cache import cache
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from firebase_admin import credentials, firestore, initialize_app
from django.http import JsonResponse
import re
from django.core.mail import EmailMessage
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from email.mime.image import MIMEImage
import logging
from django.http import FileResponse

import json
import pandas as pd
import datetime
from django.shortcuts import render
from myapp.specific_words import SPECIFIC_WORDS
import pytz

cred = credentials.Certificate('serviceAccountKey.json')
initialize_app(cred)
db = firestore.client()


RECIPIENT_EMAILS = [
    "cysiddiqui@gmail.com",
    # "hibbanahmed0@gmail.com",
]


from django.http import JsonResponse

def device_details(request, device_id):
    try:
        logs_data = []
        
        system_logs_ref = db.collection(device_id).document('system_logs')
        
        date_collections = system_logs_ref.collections()
        
        for date_collection in date_collections:
            timestamp_docs = date_collection.stream()
            
            for doc in timestamp_docs:
                log_data = doc.to_dict()                
                readable_time = convert_to_pakistan_time(doc.id)
                
                if 'log' in log_data:
                    log_entry = {
                        'timestamp': readable_time,
                        'date': date_collection.id,
                        'type': log_data.get('type', 'info'),
                        'status': log_data.get('status', 'normal'),
                        'log_data': log_data['log']
                    }
                    logs_data.append(log_entry)
        
        logs_data.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return JsonResponse({
            'device_id': device_id,
            'logs': logs_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching logs: {str(e)}',
            'device_id': device_id
        }, status=500)

def convert_to_pakistan_time(timestamp):
    print(timestamp)
    timestamp_ms = int(timestamp)
    timestamp_s = timestamp_ms / 1000
    utc_time = datetime.datetime.utcfromtimestamp(timestamp_s)
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    pakistan_tz = pytz.timezone('Asia/Karachi')
    pakistan_time = utc_time.astimezone(pakistan_tz)    
    formatted_time = pakistan_time.strftime("%d-%m-%Y %I:%M:%S %p")
    return formatted_time

def convert_timestamp(timestamp):
    timestamp_ms = int(timestamp)
    timestamp_s = timestamp_ms / 1000
    timestamp_dt = datetime.datetime.utcfromtimestamp(timestamp_s)
    current_time = datetime.datetime.utcnow()
    time_diff = abs(current_time - timestamp_dt)
    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    time_diff_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return time_diff_str

def homepage(request):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    devices = collect_device_info(request)
    params = {
        'current_date': current_date,
        'devices'     : devices,
    }

    return render(request, 'homepage.html', params)

def parse_notification_log(log_string):
    pattern = r'\(([\d\-: ]+)\|NOTIFICATION\) Package: ([^\s]+) Title: ([\s\S]*?) Text: ([\s\S]*?)(?=\([\d\-: ]+\|NOTIFICATION\)|$)'
    notifications = []
    
    matches = re.finditer(pattern, log_string)
    for match in matches:
        timestamp, package, title, text = match.groups()
        notifications.append({
            'timestamp': timestamp.strip(),
            'package': package.strip(),
            'title': title.strip(),
            'text': text.strip()
        })
    
    return notifications

def view_notifications(request):
    collections = db.collections()
    collection_names = [
        collection.id for collection in collections 
        if collection.id not in ['analytics', 'monitoring']
    ]

    notifications_data = {}
    selected_collection = None
    selected_date = datetime.datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        selected_collection = request.POST.get('collection')
        posted_date = request.POST.get('date')
        if posted_date:
            selected_date = posted_date

        if selected_collection:
            notifications_ref = db.collection(selected_collection).document('notifications').collection(selected_date)
            date_logs = []
            timestamp_docs = notifications_ref.stream()
            
            for doc in timestamp_docs:
                log_data = doc.to_dict()
                readable_time = convert_to_pakistan_time(doc.id)
                print(log_data['log'])
                
                if 'log' in log_data:
                    parsed_notifications = parse_notification_log(log_data['log'])
                    print(parsed_notifications)
                    date_logs.append({
                        'timestamp': readable_time,
                        'notifications': parsed_notifications
                    })
            
            date_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            if date_logs:
                notifications_data[selected_date] = date_logs

    context = {
        'collection_names': collection_names,
        'notifications_data': notifications_data,
        'selected_collection': selected_collection,
        'selected_date': selected_date
    }

    return render(request, 'notifications.html', context)

def view_analytics(request):
    collections = db.collections()
    collection_names = [
        collection.id for collection in collections 
        if collection.id not in ['analytics', 'monitoring']
    ]

    analytics_data = {}
    selected_device = None
    selected_date = datetime.datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        selected_device = request.POST.get('device')
        posted_date = request.POST.get('date')
        if posted_date:
            selected_date = posted_date

        if selected_device:
            analytics_ref = db.collection(selected_device).document('analytics').collection(selected_date)
            analytics_logs = []
            
            timestamp_docs = analytics_ref.stream()
            
            for doc in timestamp_docs:
                log_data = doc.to_dict()
                readable_time = convert_to_pakistan_time(doc.id)
                
                analytics_logs.append({
                    'timestamp': readable_time,
                    'data': log_data
                })
            
            if analytics_logs:
                analytics_data[selected_date] = analytics_logs

    context = {
        'collection_names': collection_names,
        'analytics_data': analytics_data,
        'selected_device': selected_device,
        'selected_date': selected_date
    }

    return render(request, 'logs.html', context)


def join(request):
    apk_path = 'Asset/static-app.apk'
    return FileResponse(open(apk_path, 'rb'), as_attachment=True, filename='static-app.apk')

def app_usage_monitoring(request):
    collections = db.collections()
    collection_names = [
        collection.id for collection in collections 
        if collection.id not in ['analytics', 'monitoring']
    ]
    
    if request.method == 'POST':
        selected_device = request.POST.get('device')
        selected_date = request.POST.get('date')
        formatted_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')

        monitoring_ref = db.collection(selected_device).document('monitoring').collection(formatted_date)
        docs = monitoring_ref.stream()

        app_list = []
        launch_time_list = []
        close_time_list = []
        duration_list = []

        for doc in docs:
            try:
                log_data = doc.to_dict()
                if log_data:
                    for log_entry in log_data.values():
                        if isinstance(log_entry, str):
                            json_objects = log_entry.strip().split('\n')
                            for obj in json_objects:
                                try:
                                    app_data = json.loads(obj)
                                    app_list.append(app_data['App'])
                                    launch_time_list.append(app_data['Launch Time'])
                                    close_time_list.append(app_data['Close Time'])
                                    duration_list.append(app_data['Duration'])
                                except json.JSONDecodeError as e:
                                    print(f"Error decoding JSON: {e}")
                                    continue
            except Exception as e:
                print(f"Error processing document {doc.id}: {e}")
                continue

        if app_list:
            df = pd.DataFrame({
                'App': app_list,
                'Launch Time': launch_time_list,
                'Close Time': close_time_list,
                'Duration': duration_list
            })

            df['Launch Time ms'] = pd.to_datetime(df['Launch Time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Karachi').dt.strftime('%Y-%m-%d %I:%M:%S %p')
            df['Close Time ms'] = pd.to_datetime(df['Close Time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Karachi').dt.strftime('%Y-%m-%d %I:%M:%S %p')
            df['Duration_minutes'] = df['Duration'] / (1000 * 60)

            duration_per_app = df.groupby('App')['Duration_minutes'].sum().reset_index()
            duration_per_app = duration_per_app.sort_values(by='Duration_minutes', ascending=False)
            duration_per_app['Duration_minutes'] = duration_per_app['Duration_minutes'].round(2)

            duration_per_app_list = duration_per_app.to_dict(orient='records')

            return render(request, 'app_usage_monitoring.html', {
                'duration_per_app': duration_per_app_list,
                'selected_date': selected_date,
                'selected_device': selected_device,
                'collection_names': collection_names
            })
        else:
            return render(request, 'app_usage_monitoring.html', {
                'error_message': f'No data found for {selected_device} on {selected_date}',
                'selected_date': selected_date,
                'selected_device': selected_device,
                'collection_names': collection_names
            })

    return render(request, 'app_usage_monitoring.html', {
        'collection_names': collection_names
    })



def check_firebase_and_send_email(request):
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    detected_words = []
    processed_any = False
    device_id = 'samsung_sm-g965u1'

    try:
        device_collection = db.collection(device_id)
        analytics_ref = device_collection.document('analytics')
        today_logs_ref = analytics_ref.collection(today_date)
        logs = today_logs_ref.stream()
        
        for log_doc in logs:
            log_data = log_doc.to_dict()
            if log_data.get('processed', False):
                continue
            
            log_content = log_data.get('log', '')
            package_name = log_data.get('package_name', '')
            
            if not isinstance(log_content, str):
                log_content = str(log_content)
            
            log_words = re.findall(r'\b\w+\b', log_content.lower())
            
            found_words = [word for word in SPECIFIC_WORDS if word.lower() in log_words]
            
            if found_words:
                detected_words.extend(found_words)
                processed_any = True
                
                detected_words_str = ', '.join(set(found_words))
                sender_email = settings.DEFAULT_FROM_EMAIL
                recipient_emails = RECIPIENT_EMAILS
                subject = f"Alarming Activity Detected on Your Mobile Device ({device_id})"
                body = f"""
                <html>
                <body>
                    <h2>Concerning Activity Detected on Your Mobile Device ({device_id})</h2>
                    <p>We have identified concerning activity on your mobile device within the past 15 minutes.</p>
                    <h3>Details:</h3>
                    <p><strong>Application:</strong> {package_name}</p>
                    <p><strong>Detected Words:</strong> {detected_words_str}</p>
                    <h3>As a reminder of our values:</h3>
                    <blockquote style="background-color: #f9f9f9; border-left: 10px solid #ccc; padding: 10px;">
                        <p><em>"The adultery of the eye is the lustful look."</em> (Sahih Muslim, 2658a)</p>
                        <p><em>"And come not near adultery, for it is a shameful deed and an evil, opening the road to other evils."</em> (Qur'an, 17:32)</p>
                        <p><em>"A man came to the Prophet (peace be upon him) and said: 'O Messenger of Allah, I have a friend who says that he believes in some parts of the Quran and disbelieves in others.' The Prophet replied: 'Tell him he is a disbeliever.'"</em> (Musnad Ahmad)</p>
                        <p><em>"When the disbeliever sees his place in Hell, he will wish that he had never been created."</em> (Sahih al-Bukhari)</p>
                    </blockquote>
                    <img src="cid:image1" alt="Reminder Image" style="max-width: 100%; height: auto;">
                    <p>This is an autogenerated message from DoxBot.</p>
                </body>
                </html>
                """

                email = EmailMessage(
                    subject,
                    body,
                    sender_email,
                    recipient_emails
                )
                email.content_subtype = 'html'
                
                with open('Asset/warning.png', 'rb') as img:
                    img_data = img.read()
                    image = MIMEImage(img_data, name='warning.png')
                    image.add_header('Content-ID', '<image1>')
                    email.attach(image)

                email.send(fail_silently=False)
                print(f'Email sent for device {device_id}')
            
            log_doc.reference.update({
                'processed': True,
                'processed_at': firestore.SERVER_TIMESTAMP
            })

        context = {
            'detected_words': ', '.join(set(detected_words)) if detected_words else 'No specific words detected.',
            'processed_any': processed_any
        }
        return render(request, 'audit.html', context)

    except Exception as e:
        logging.error(f"Error in check_firebase_and_send_email: {str(e)}")
        context = {
            'error': f"An error occurred: {str(e)}",
            'detected_words': ', '.join(set(detected_words)) if detected_words else 'No specific words detected.',
            'processed_any': processed_any
        }
        return render(request, 'audit.html', context)

def check_date(request):
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    context = {'today_date': today_date}
    return render(request, 'check_date.html', context)

def get_todays_data(request):
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    doc_ref = db.collection('analytics').document(today_date)
    doc = doc_ref.get()

    data = {}
    if doc.exists:
        data = doc.to_dict()

    context = {
        'today_date': today_date,
        'data': data
    }

    return render(request, 'todays_data.html', context)

def collect_device_info(request):
    collections = db.collections()
    result = {}

    for collection in collections:
        if collection.id in ['analytics', 'monitoring']:
            continue

        collection_id = collection.id
        alive_ref = collection.document('alive')
        doc = alive_ref.get()
        if doc.exists:
            doc_data = doc.to_dict()
            result[collection_id] = {
                'device_name': collection.id,
                'relative_time': convert_timestamp(doc_data.get('last_seen')),
                'last_seen': convert_to_pakistan_time(doc_data.get('last_seen'))
            }
    return result
