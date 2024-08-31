from django.db import models

"""
MonitoredWord: Stores words to look for in the data.
ProcessedData: Keeps track of which data has been processed to avoid duplicates.
"""


# class MonitoredWord(models.Model):
#     word = models.CharField(max_length=100, unique=True)
    
#     def __str__(self):
#         return self.word

# class ProcessedData(models.Model):
#     data_id = models.CharField(max_length=100, unique=True)
#     processed_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Data {self.data_id} processed at {self.processed_at}"