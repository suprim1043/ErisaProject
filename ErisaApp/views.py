from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
import json
from .models import Claim, ClaimDetail, ClaimFlag, ClaimNote



@login_required
def claims_list(request):
    """
    Display all claims with filtering, search, and pagination
    """
    claims_queryset = Claim.objects.select_related().prefetch_related('details', 'flags', 'notes')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        claims_queryset = claims_queryset.filter(
            Q(claim_id__icontains=search_query) |
            Q(patient_name__icontains=search_query) |
            Q(insurer_name__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        # Handle both model choice values and actual database values
        if status_filter == 'under_review':
            # Search for both underscore and space versions
            claims_queryset = claims_queryset.filter(
                Q(status='under_review') | Q(status='Under Review')
            )
        else:
            # For other statuses, try both exact match and capitalized version
            claims_queryset = claims_queryset.filter(
                Q(status=status_filter) | Q(status=status_filter.title())
            )
    
    # Insurer filter
    insurer_filter = request.GET.get('insurer', '')
    if insurer_filter:
        claims_queryset = claims_queryset.filter(insurer_name__icontains=insurer_filter)
    
    # Amount range filters
    min_billed = request.GET.get('min_billed', '')
    if min_billed:
        try:
            claims_queryset = claims_queryset.filter(billed_amount__gte=float(min_billed))
        except ValueError:
            pass
    
    max_billed = request.GET.get('max_billed', '')
    if max_billed:
        try:
            claims_queryset = claims_queryset.filter(billed_amount__lte=float(max_billed))
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(claims_queryset, 25)  # Show 25 claims per page
    page_number = request.GET.get('page')
    claims = paginator.get_page(page_number)
    
    # Get unique status choices for filter dropdown (from actual database values)
    actual_statuses = Claim.objects.values_list('status', flat=True).distinct().order_by('status')
    status_choices = []
    
    # Map actual database values to display values
    status_mapping = {
        'pending': 'Pending',
        'Pending': 'Pending', 
        'paid': 'Paid',
        'Paid': 'Paid',
        'denied': 'Denied', 
        'Denied': 'Denied',
        'Under Review': 'Under Review',
        'under_review': 'Under Review'
    }
    
    # Create choices from actual database values
    seen_displays = set()
    for status in actual_statuses:
        display_name = status_mapping.get(status, status.title())
        if display_name not in seen_displays:
            # Use the database value as the form value for exact matching
            if status == 'Under Review':
                status_choices.append(('under_review', display_name))
            else:
                status_choices.append((status.lower(), display_name))
            seen_displays.add(display_name)
    
    # Get unique insurers for filter dropdown
    unique_insurers = Claim.objects.values_list('insurer_name', flat=True).distinct().order_by('insurer_name')
    
    context = {
        'claims': claims,
        'search_query': search_query,
        'status_filter': status_filter,
        'insurer_filter': insurer_filter,
        'min_billed': min_billed,
        'max_billed': max_billed,
        'status_choices': status_choices,
        'unique_insurers': unique_insurers,
        'request': request,
    }
    
    return render(request, 'claims_list.html', context)


@login_required
def claim_detail(request, claim_id):
    """
    Display detailed view of a single claim including details, flags, and notes
    """
    claim = get_object_or_404(Claim, claim_id=claim_id)
    claim_details = claim.details.all()
    claim_flags = claim.flags.all()
    claim_notes = claim.notes.all()
    
    context = {
        'claim': claim,
        'claim_details': claim_details,
        'claim_flags': claim_flags,
        'claim_notes': claim_notes,
    }
    
    return render(request, 'claim_detail.html', context)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def flag_claim(request, claim_id):
    """
    Flag a claim for review
    """
    try:
        claim = get_object_or_404(Claim, claim_id=claim_id)
        data = json.loads(request.body)
        reason = data.get('reason', 'Flagged for review')
        
        user = request.user
        
        # Check if claim is already flagged by this user with the same reason
        existing_flag = ClaimFlag.objects.filter(
            claim=claim, 
            user=user, 
            reason=reason,
            resolved=False
        ).first()
        
        if existing_flag:
            return JsonResponse({
                'success': False, 
                'message': 'Claim already flagged with this reason'
            })
        
        # Create new flag
        flag = ClaimFlag.objects.create(
            claim=claim,
            user=user,
            reason=reason
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Claim flagged successfully',
            'flag_id': flag.id,
            'flag_count': claim.flags.filter(resolved=False).count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def add_note(request, claim_id):
    """
    Add a note to a claim
    """
    try:
        claim = get_object_or_404(Claim, claim_id=claim_id)
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'message': 'Note content cannot be empty'
            })
        
        user = request.user
        
        # Create new note
        note = ClaimNote.objects.create(
            claim=claim,
            user=user,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Note added successfully',
            'note_id': note.id,
            'note_count': claim.notes.count(),
            'note_data': {
                'content': note.content,
                'user': note.user.username,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@require_http_methods(["GET"])
@login_required
def get_claim_flags_notes(request, claim_id):
    """
    Get flags and notes for a claim
    """
    try:
        claim = get_object_or_404(Claim, claim_id=claim_id)
        
        flags = []
        for flag in claim.flags.filter(resolved=False):
            flags.append({
                'id': flag.id,
                'reason': flag.reason,
                'user': flag.user.username,
                'created_at': flag.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        notes = []
        for note in claim.notes.all()[:10]:  # Limit to 10 most recent notes
            notes.append({
                'id': note.id,
                'content': note.content,
                'user': note.user.username,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'flags': flags,
            'notes': notes,
            'flag_count': len(flags),
            'note_count': claim.notes.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
