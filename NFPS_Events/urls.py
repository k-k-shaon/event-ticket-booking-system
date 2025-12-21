"""
URL configuration for NFPS_Events project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# urls.py
from django.contrib import admin
from django.urls import path, include
from events import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Social auth (Google)
    path('auth/', include('social_django.urls', namespace='social')),

    # User routes
    path('', views.event_list, name='event_list'),
    path('login-success/', views.login_success, name='login_success'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/<int:pk>/register/', views.register_event, name='register_event'),
    path('event/<int:pk>/payment/', views.payment_page, name='payment_page'),
    path('ticket/<str:tracking_code>/', views.ticket_view, name='ticket_view'),

    # Admin access (specific first, general last)
    path('admin_access/login/', views.admin_access_login, name='admin_access_login'),
    path('admin_access/logout/', views.admin_access_logout, name='admin_access_logout'),
    path('admin_access/events/new/', views.admin_create_event, name='admin_create_event'),
    path('admin_access/registrations/<int:reg_id>/approve/', views.admin_approve_registration, name='admin_approve_registration'),
    path('admin_access/registrations/<int:reg_id>/reject/', views.admin_reject_registration, name='admin_reject_registration'),
    path('admin_access/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/event/<int:pk>/edit/', views.admin_edit_event, name='admin_edit_event'),
    path('dashboard/event/<int:pk>/delete/', views.admin_delete_event, name='admin_delete_event'),
    path('admin_access/payment-methods/',views.manage_payment_methods,name='manage_payment_methods'),
    path('admin_access/payment-methods/<int:pk>/edit/', views.edit_payment_method, name='edit_payment_method'),

]
