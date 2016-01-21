from django.contrib import admin
from server_profile.models import Server, Profile, Result

# Register your models here.
admin.site.register(Server)
admin.site.register(Profile)
admin.site.register(Result)