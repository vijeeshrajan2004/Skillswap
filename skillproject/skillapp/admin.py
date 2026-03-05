from django.contrib import admin
from .models import Skill, UserSkill, SwapRequest, Profile, Payment, Message


admin.site.register(Skill)
admin.site.register(UserSkill)
admin.site.register(SwapRequest)
admin.site.register(Profile)
admin.site.register(Payment)
admin.site.register(Message)