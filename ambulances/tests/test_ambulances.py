from django.test import TestCase, RequestFactory

from ..models import Ambulances, Capability, Status

from ..serializers import StatusSerializer, AmbulancesSerializer

from django.test import Client

class CreateAmbulance(TestCase):

    def setUp(self):

        # Add status
        self.s1 = Status(name='Out of service')
        self.s1.save()
        self.s2 = Status(name='In service')
        self.s2.save()
        self.s3 = Status(name='Available')
        self.s3.save()
        
        # Add capability
        self.c1 = Capability(name='Basic')
        self.c1.save()
        self.c2 = Capability(name='Advanced')
        self.c2.save()
        self.c3 = Capability(name='Rescue')
        self.c3.save()
        
        # Add ambulances
        self.a1 = Ambulances(
            identifier='BC-179',
            comment='Maintenance due',
            capability=self.c1,
            status=self.s1)
        
        # Add ambulances
        self.a2 = Ambulances(
            identifier='BC-180',
            comment='Need painting',
            capability=self.c2,
            status=self.s3)

    def test_ambulances(self):

        for s in (self.s1, self.s2, self.s3):
            serializer = StatusSerializer(s)
            result = { 'id': s.pk, 'name': s.name }
            self.assertEqual(serializer.data, result)

        
