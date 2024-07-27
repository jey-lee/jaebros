from django.db import models

class Conversation(models.Model):
    thread_id = models.CharField(max_length=255)
    prompt = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread {self.thread_id} at {self.timestamp}"
