from django.contrib import admin
from .models import Conversation

class ConversationAdmin(admin.ModelAdmin):
    list_display = ('thread_id', 'prompt', 'response', 'timestamp')
    search_fields = ('thread_id', 'prompt', 'response')
    list_filter = ('timestamp',)

admin.site.register(Conversation, ConversationAdmin)
