from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Claim, ClaimFlag, ClaimNote
from django.contrib.auth.models import User
import json

@login_required
def admin_dashboard(request):
    """
    Admin dashboard with comprehensive statistics and analytics
    """
    # Basic Statistics
    total_claims = Claim.objects.count()
    total_flags = ClaimFlag.objects.filter(resolved=False).count()
    total_notes = ClaimNote.objects.count()
    total_users = User.objects.count()
    
    # Financial Statistics
    financial_stats = Claim.objects.aggregate(
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount'),
        avg_billed=Avg('billed_amount'),
        avg_paid=Avg('paid_amount')
    )
    
    # Calculate underpayment statistics
    total_billed = financial_stats['total_billed'] or 0
    total_paid = financial_stats['total_paid'] or 0
    total_underpayment = total_billed - total_paid
    avg_underpayment = (financial_stats['avg_billed'] or 0) - (financial_stats['avg_paid'] or 0)
    
    # Underpayment percentage
    underpayment_percentage = (total_underpayment / total_billed * 100) if total_billed > 0 else 0
    
    # Claims by Status (group similar statuses together)
    status_stats = Claim.objects.values('status').annotate(
        count=Count('status'),
        total_amount=Sum('billed_amount')
    ).order_by('status')
    
    # Consolidate duplicate statuses
    consolidated_status = {}
    for stat in status_stats:
        status = stat['status'].lower().strip()
        if status in consolidated_status:
            consolidated_status[status]['count'] += stat['count']
            consolidated_status[status]['total_amount'] += stat['total_amount'] or 0
        else:
            consolidated_status[status] = {
                'status': status.title(),
                'count': stat['count'],
                'total_amount': stat['total_amount'] or 0
            }
    
    status_stats = list(consolidated_status.values())
    
    # Top Insurers by Claims Count
    top_insurers = Claim.objects.values('insurer_name').annotate(
        claim_count=Count('claim_id'),
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount')
    ).order_by('-claim_count')[:10]
    
    # Calculate underpayment for each insurer
    for insurer in top_insurers:
        insurer['underpayment'] = (insurer['total_billed'] or 0) - (insurer['total_paid'] or 0)
        insurer['underpayment_rate'] = (
            insurer['underpayment'] / insurer['total_billed'] * 100 
            if insurer['total_billed'] > 0 else 0
        )
    
    # Claims by Month (last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_claims = Claim.objects.filter(
        discharge_date__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('discharge_date')
    ).values('month').annotate(
        count=Count('claim_id'),
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount')
    ).order_by('month')
    
    # Recent Activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_flags = ClaimFlag.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    recent_notes = ClaimNote.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    
    # Flag Statistics
    flag_stats = ClaimFlag.objects.aggregate(
        total_flags=Count('id'),
        resolved_flags=Count('id', filter=Q(resolved=True)),
        pending_flags=Count('id', filter=Q(resolved=False))
    )
    
    # Most Active Users (by notes and flags)
    active_users = User.objects.annotate(
        note_count=Count('claimnote'),
        flag_count=Count('claimflag'),
        total_activity=F('note_count') + F('flag_count')
    ).filter(total_activity__gt=0).order_by('-total_activity')[:5]
    
    # High-value underpaid claims
    high_value_underpaid = Claim.objects.annotate(
        underpayment=F('billed_amount') - F('paid_amount')
    ).filter(underpayment__gt=10000).order_by('-underpayment')[:10]
    
    # Claims requiring attention (flagged and not resolved)
    flagged_claims = Claim.objects.filter(
        flags__resolved=False
    ).distinct().annotate(
        flag_count=Count('flags', filter=Q(flags__resolved=False))
    ).order_by('-flag_count')[:10]
    
    # Weekly trend (last 8 weeks)
    eight_weeks_ago = timezone.now() - timedelta(weeks=8)
    weekly_stats = Claim.objects.filter(
        discharge_date__gte=eight_weeks_ago
    ).annotate(
        week=TruncWeek('discharge_date')
    ).values('week').annotate(
        count=Count('claim_id'),
        flags_created=Count('flags', filter=Q(flags__created_at__gte=F('week')))
    ).order_by('week')
    
    # Prepare chart data
    chart_data = {
        'status_labels': [item['status'].title() for item in status_stats],
        'status_counts': [item['count'] for item in status_stats],
        'monthly_labels': [item['month'].strftime('%b %Y') for item in monthly_claims],
        'monthly_counts': [item['count'] for item in monthly_claims],
        'monthly_billed': [float(item['total_billed'] or 0) for item in monthly_claims],
        'insurer_labels': [item['insurer_name'][:20] for item in top_insurers[:5]],
        'insurer_underpayments': [float(item['underpayment']) for item in top_insurers[:5]]
    }
    
    context = {
        # Basic Stats
        'total_claims': total_claims,
        'total_flags': total_flags,
        'total_notes': total_notes,
        'total_users': total_users,
        'recent_flags': recent_flags,
        'recent_notes': recent_notes,
        
        # Financial Stats
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_underpayment': total_underpayment,
        'avg_underpayment': avg_underpayment,
        'underpayment_percentage': underpayment_percentage,
        
        # Detailed Stats
        'status_stats': status_stats,
        'top_insurers': top_insurers,
        'monthly_claims': monthly_claims,
        'flag_stats': flag_stats,
        'active_users': active_users,
        'high_value_underpaid': high_value_underpaid,
        'flagged_claims': flagged_claims,
        'weekly_stats': weekly_stats,
        
        # Chart Data
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context) 