import logging
import math
from enum import Enum

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.utils import timezone
from django.urls import reverse
from django.template.defaulttags import register

from emstrack.models import AddressModel, UpdatedByModel, defaults
import login.permissions as permissions


logger = logging.getLogger(__name__)


# filters

@register.filter
def get_ambulance_status(key):
    return AmbulanceStatus[key].value


@register.filter
def get_ambulance_capability(key):
    return AmbulanceCapability[key].value


@register.filter
def get_location_type(key):
    return LocationType[key].value


@register.filter
def get_call_priority(key):
    return CallPriority[key].value


def calculate_orientation(location1, location2):
    # Calculate orientation based on two locations
    # https://www.movable-type.co.uk/scripts/latlong.html

    # convert latitude and longitude to radians first
    lat1 = math.pi * location1.y / 180
    lon1 = math.pi * location1.x / 180
    lat2 = math.pi * location2.y / 180
    lon2 = math.pi * location2.x / 180

    # calculate orientation and convert to degrees
    orientation = (180 / math.pi) * math.atan2(math.cos(lat1) * math.sin(lat2) -
                                               math.sin(lat1) * math.cos(lat2) *
                                               math.cos(lon2 - lon1),
                                               math.sin(lon2 - lon1) * math.cos(lat2))

    if orientation < 0:
        orientation += 360

    return orientation


# User and ambulance location models


# Ambulance model

class AmbulanceStatus(Enum):
    UK = 'Unknown'
    AV = 'Available'
    OS = 'Out of service'
    PB = 'Patient bound'
    AP = 'At patient'
    HB = 'Hospital bound'
    AH = 'At hospital'


class AmbulanceCapability(Enum):
    B = 'Basic'
    A = 'Advanced'
    R = 'Rescue'


class Ambulance(UpdatedByModel):
    # ambulance properties
    identifier = models.CharField(max_length=50, unique=True)

    AMBULANCE_CAPABILITY_CHOICES = \
        [(m.name, m.value) for m in AmbulanceCapability]
    capability = models.CharField(max_length=1,
                                  choices=AMBULANCE_CAPABILITY_CHOICES)

    # status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    # default value for _loaded_values
    _loaded_values = None

    @classmethod
    def from_db(cls, db, field_names, values):

        # call super
        instance = super(Ambulance, cls).from_db(db, field_names, values)

        # store the original field values on the instance
        instance._loaded_values = dict(zip(field_names, values))

        # return instance
        return instance

    def save(self, *args, **kwargs):

        # creation?
        created = self.pk is None

        # calculate orientation only if orientation has not changed and location has changed
        if (self._loaded_values and
                self._loaded_values['orientation'] == self.orientation and
                self._loaded_values['location'] != self.location):
            # TODO: should we allow for a small radius before updating direction?
            self.orientation = calculate_orientation(self._loaded_values['location'], self.location)
            logger.debug('calculating orientation: < {} - {} = {}'.format(self._loaded_values['location'],
                                                                          self.location,
                                                                          self.orientation))

        # save to Ambulance
        super().save(*args, **kwargs)

        # publish to mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().publish_ambulance(self)

        # if comment, status or location changed
        if (self._loaded_values is None) or \
                self._loaded_values['location'] != self.location or \
                self._loaded_values['status'] != self.status or \
                self._loaded_values['comment'] != self.comment:
            # save to AmbulanceUpdate
            data = {k: getattr(self, k)
                    for k in ('status', 'orientation',
                              'location', 'timestamp',
                              'comment', 'updated_by', 'updated_on')}
            data['ambulance'] = self
            obj = AmbulanceUpdate(**data)
            obj.save()

        # just created?
        if created:
            # invalidate permissions cache
            permissions.cache_clear()

    def delete(self, *args, **kwargs):

        # remove from mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().remove_ambulance(self)

        # invalidate permissions cache
        permissions.cache_clear()

        # delete from Ambulance
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('ambulance:detail', kwargs={'pk': self.id})

    def __str__(self):
        return ('Ambulance {}(id={}) ({}) [{}]:\n' +
                '    Status: {}\n' +
                '  Location: {} @ {}\n' +
                '   Updated: {} by {}').format(self.identifier,
                                               self.id,
                                               AmbulanceCapability[self.capability].value,
                                               self.comment,
                                               AmbulanceStatus[self.status].value,
                                               self.location,
                                               self.timestamp,
                                               self.updated_by,
                                               self.updated_on)


class AmbulanceUpdate(models.Model):
    # ambulance id
    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    # ambulance status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp, indexed
    timestamp = models.DateTimeField(db_index=True, default=timezone.now)

    # comment
    comment = models.CharField(max_length=254, null=True, blank=True)

    # updated by
    updated_by = models.ForeignKey(User,
                                   on_delete=models.CASCADE)
    updated_on = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=['ambulance', 'timestamp'],
                name='ambulance_timestamp_idx',
            ),
        ]


# Call related models

class CallPriority(Enum):
    A = 'Resucitation'
    B = 'Emergent'
    C = 'Urgent'
    D = 'Less urgent'
    E = 'Not urgent'


class Call(AddressModel, UpdatedByModel):

    # active status
    active = models.BooleanField(default=False)

    # details
    details = models.CharField(max_length=500, default="")

    # call priority
    CALL_PRIORITY_CHOICES = \
        [(m.name, m.value) for m in CallPriority]
    priority = models.CharField(max_length=1,
                                choices=CALL_PRIORITY_CHOICES,
                                default=CallPriority.E.name)

    # created at
    created_at = models.DateTimeField(auto_now_add=True)

    # ended at
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{} ({})".format(self.location, self.priority)


class AmbulanceCallTime(models.Model):

    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    dispatch_time = models.DateTimeField(null=True, blank=True)
    departure_time = models.DateTimeField(null=True, blank=True)
    patient_time = models.DateTimeField(null=True, blank=True)
    hospital_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('call', 'ambulance')


# Patient might be expanded in the future

class Patient(models.Model):
    """
    A model that provides patient fields.
    """

    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    name = models.CharField(max_length=254, default="")
    age = models.IntegerField(null=True)


# Location related models

# noinspection PyPep8
class LocationType(Enum):
    B = 'Base'
    A = 'AED'
    O = 'Other'


class Location(AddressModel, UpdatedByModel):
    # location name
    name = models.CharField(max_length=254, unique=True)

    # location type
    LOCATION_TYPE_CHOICES = \
        [(m.name, m.value) for m in LocationType]
    type = models.CharField(max_length=1,
                            choices=LOCATION_TYPE_CHOICES,
                            default=LocationType.O.name)

    # location
    location = models.PointField(srid=4326, null=True)

    def get_absolute_url(self):
        return reverse('ambulance:location_detail', kwargs={'pk': self.id})

    def __str__(self):
        return "{} @{} ({})".format(self.name, self.location, self.comment)


# THOSE NEED REVIEWING

class Region(models.Model):
    name = models.CharField(max_length=254, unique=True)
    center = models.PointField(srid=4326, null=True)

    def __str__(self):
        return self.name
