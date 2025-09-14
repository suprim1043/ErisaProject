from django.urls import path
from . import views, auth_views, dashboard_views

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.login_view, name='login'),
    path('signup/', auth_views.signup_view, name='signup'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    # Dashboard URLs
    path('dashboard/', dashboard_views.admin_dashboard, name='admin_dashboard'),
    
    # Claims URLs
    path('', views.claims_list, name='claims_list'),
    path('claims/<int:claim_id>/', views.claim_detail, name='claim_detail'),
    path('claims/<int:claim_id>/flag/', views.flag_claim, name='flag_claim'),
    path('claims/<int:claim_id>/note/', views.add_note, name='add_note'),
    path('claims/<int:claim_id>/flags-notes/', views.get_claim_flags_notes, name='get_claim_flags_notes'),
]