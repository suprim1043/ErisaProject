from django.contrib import admin
from .models import Claim, ClaimDetail, ClaimFlag, ClaimNote
# Register your models here.    

admin.site.register(Claim)
admin.site.register(ClaimDetail)
admin.site.register(ClaimFlag)
admin.site.register(ClaimNote)
