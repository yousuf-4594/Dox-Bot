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

import json
import pandas as pd
import datetime
from django.shortcuts import render

# logger = logging.getLogger(__name__)



cred = credentials.Certificate('serviceAccountKey.json')
initialize_app(cred)
db = firestore.client()

SPECIFIC_WORDS = ['incognito', 'nude', 'fuck', 'sex', 'porn', 'hentai', 'pussy', 'boobs', 'Incognito', 'naked', 'busty', 'blowjob'] 

a = 100


RECIPIENT_EMAILS = [
    "cysiddiqui@gmail.com",
    "hibbanahmed0@gmail.com",
]

def homepage(request):
    return render(request, 'homepage.html')

def app_usage_monitoring(request):
    if request.method == 'POST':
        selected_date = request.POST.get('date')
        formatted_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')

        doc_ref = db.collection('monitoring').document(formatted_date)
        doc = doc_ref.get()

        if doc.exists:
            content = doc.to_dict()
            app_list = []
            launch_time_list = []
            close_time_list = []
            duration_list = []

            for timestamp, json_string in content.items():
                if isinstance(json_string, str):
                    json_objects = json_string.strip().split('\n')
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
            duration_per_app = duration_per_app.sort_values(by='Duration_minutes')

            # Convert the DataFrame to a list of dictionaries
            duration_per_app_list = duration_per_app.to_dict(orient='records')

            # Render the data in the template
            return render(request, 'app_usage_monitoring.html', {'duration_per_app': duration_per_app_list, 'selected_date': selected_date})

        else:
            print('No document found for the selected date.')

    return render(request, 'app_usage_monitoring.html')



def check_firebase_and_send_email(request):
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')

    # Fetch the document for today
    doc_ref = db.collection('analytics').document(today_date)
    doc = doc_ref.get()

    detected_words = []

    if doc.exists:
        content = doc.to_dict()
        new_maps = {}
        print('Document Found')

        # Process each field in the document
        for map_name, map_value in content.items():
            # Check if the map has a 'processed' flag and if it's set to True
            if isinstance(map_value, dict) and map_value.get('processed', False):
                # Skip processing if the map has already been processed
                print(f'{map_name} already processed')
                continue
            
            # Process the map
            new_maps[map_name] = map_value
            
            # Ensure map_value is a string
            if isinstance(map_value, dict) or isinstance(map_value, list):
                map_value_str = str(map_value)
            else:
                map_value_str = map_value

            # Tokenize the map_value_str using regular expressions
            map_value_words = re.findall(r'\b\w+\b', map_value_str)

            # Find specific words present in the map_value_words
            detected_words += [word for word in SPECIFIC_WORDS if word in map_value_words]

            if detected_words:
                print(f'Specific Word(s) Found in {map_name}: {", ".join(detected_words)}')
                
                # Construct the email body with detected words
                detected_words_str = ', '.join(detected_words)
                sender_email = settings.DEFAULT_FROM_EMAIL
                recipient_emails = RECIPIENT_EMAILS
                subject = "Alarming Activity Detected on Your Mobile Device (itel-S661LP)"
                body = f"""
                <html>
                <body>
                    <h2>Concerning Activity Detected on Your Mobile Device (itel-S661LP)</h2>
                    <p>We have identified concerning activity on your mobile device (itel-S661LP) within the past hour. Specifically, the device has been detected accessing inappropriate content.</p>
                    <h3>Detected Words:</h3>
                    <p>{detected_words_str}</p>
                    <h3>As a reminder of our values:</h3>
                    <blockquote style="background-color: #f9f9f9; border-left: 10px solid #ccc; padding: 10px;">
                        <p><em>“The adultery of the eye is the lustful look.”</em> (Sahih Muslim, 2658a)</p>
                        <p><em>"And come not near adultery, for it is a shameful deed and an evil, opening the road to other evils."</em> (Qur'an, 17:32)</p>
                        <p><em>"A man came to the Prophet (peace be upon him) and said: 'O Messenger of Allah, I have a friend who says that he believes in some parts of the Quran and disbelieves in others.' The Prophet replied: 'Tell him he is a disbeliever.'"</em> (Musnad Ahmad)</p>
                        <p><em>"When the disbeliever sees his place in Hell, he will wish that he had never been created."</em> (Sahih al-Bukhari)</p>
                    </blockquote>
                    <img src="cid:image1" alt="Reminder Image" style="max-width: 100%; height: auto;">
                    <p>This is an autogenerated message from DoxBot.</p>
                </body>
                </html>
                """

                # Create the email message
                email = EmailMessage(
                    subject,
                    body,
                    sender_email,
                    recipient_emails  # List of recipient emails
                )
                email.content_subtype = 'html'
                with open('Asset/warning.png', 'rb') as img:
                    img_data = img.read()
                    image = MIMEImage(img_data, name='warning.png')
                    image.add_header('Content-ID', '<image1>')  # Referenced in the HTML content
                    email.attach(image)

                email.send(fail_silently=False)
                print('Email Sent successfully')

            # After processing, update the map with the 'processed' flag
            new_maps[map_name] = {'value': map_value, 'processed': True}

        # Update the document in Firestore with the processed flags
        if new_maps:
            doc_ref.update(new_maps)

    # Render the response with the template
    context = {
        'detected_words': ', '.join(detected_words) if detected_words else 'No specific words detected.'
    }
    return render(request, 'check_complete.html', context)

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
