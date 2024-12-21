from django.contrib import admin
from django.urls import path
from myapp.views import *

urlpatterns = [
    path('', homepage, name='homepage'), 
    path('admin/', admin.site.urls),
    path('check-firebase/', check_firebase_and_send_email, name='check_firebase_and_send_email'),
    path('check-date/', check_date, name='check_date'),
    path('logs/', view_analytics, name='logs'),
    path('activity/', app_usage_monitoring, name='activity'),
    path('join/', join, name='join'),
    path('notifications/', view_notifications, name='notifications'),
    path('<str:device_id>/', device_details, name='device_details'),

]
