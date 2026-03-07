from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class UserLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    name = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_location' 
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='idx_user_location_lat_lng'),
        ]

    def __str__(self):
        return self.name or f"({self.latitude}, {self.longitude})"

class LocationGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'location_group'

class LocationGroupItem(models.Model):
    group = models.ForeignKey(LocationGroup, on_delete=models.CASCADE, db_column='group_id')
    location = models.ForeignKey(UserLocation, on_delete=models.CASCADE, db_column='location_id')
    display_order = models.IntegerField()

    class Meta:
        db_table = 'location_group_item'
        unique_together = ('group', 'location') 

class Route(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    name = models.CharField(max_length=255)
    start_location = models.ForeignKey(UserLocation, on_delete=models.CASCADE, 
                                       db_column='start_location_id', related_name='routes_start')
    end_location = models.ForeignKey(UserLocation, on_delete=models.CASCADE, 
                                     db_column='end_location_id', related_name='routes_end')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'route'