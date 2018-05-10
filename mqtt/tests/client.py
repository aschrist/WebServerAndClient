import logging
import os
import re
import subprocess
import time
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from ambulance.models import Ambulance, \
    AmbulanceCapability
from hospital.models import Hospital, \
    Equipment, HospitalEquipment, EquipmentType
from login.models import GroupAmbulancePermission, GroupHospitalPermission, \
    UserAmbulancePermission, UserHospitalPermission
from mqtt.client import BaseClient

logger = logging.getLogger(__name__)

class MQTTTestCase(StaticLiveServerTestCase):

    @classmethod
    def run_until_success(cls, args, **kwargs):

        # parameters
        MAX_TRIES = kwargs.pop('MAX_TRIES', 10)
        
        # keep trying 
        k = 0
        success = False
        while not success and k < MAX_TRIES:
            if k > 0:
                time.sleep(1)
            k += 1
            retval = subprocess.run(args, **kwargs)
            success = retval.returncode == 0

        if not success:
            raise Exception('Did not succeed!')

    @classmethod
    def run_until_fail(cls, args, **kwargs):

        # parameters
        MAX_TRIES = kwargs.pop('MAX_TRIES', 10)
        
        # keep trying 
        k = 0
        success = True
        while success and k < MAX_TRIES:
            if k > 0:
                time.sleep(1)
            k += 1
            retval = subprocess.run(args, **kwargs)
            success = retval.returncode == 0

        if success:
            raise Exception('Did not fail!')
        
    @classmethod
    def setUpClass(cls):

        try:

            # can get user?
            User.objects.get(username=settings.MQTT['USERNAME'])

        except:

            # Add admin user
            User.objects.create_user(
                username=settings.MQTT['USERNAME'],
                email='admin@user.com',
                password=settings.MQTT['PASSWORD'],
                is_superuser=True)
        
        # call super to create server
        super().setUpClass()

        # determine server and port
        protocol, host, port = cls.live_server_url.split(':')
        host = host[2:]
        
        print('\n>> Starting django server at {}'.format(cls.live_server_url))
        
        print('>> Stoping mosquitto')
        
        # stop mosquito server
        retval = subprocess.run(["service",
                                 "mosquitto",
                                 "stop"])

        # print('>> Stoping mqttclient')
        
        # # stop mqttclient
        # retval = subprocess.run(["supervisorctl",
        #                          "stop",
        #                          "mqttclient"])
        
        # # Wait for shutdown
        # cls.run_until_fail(["service",
        #                     "mosquitto",
        #                     "status"])

        time.sleep(2)
        
        try:

            # saving persistence file
            os.rename("/var/lib/mosquitto/mosquitto.db",
                      "/var/lib/mosquitto/mosquitto.db.bak")

        except:
            print("* * * CAN'T BACKUP MOSQUITTO PERSISTENCE FILE * * *")

        # Does configuration exist?
        config = Path("/etc/mosquitto/conf.d/default.conf")
        if not config.is_file():

            # Can't find configuration, can we recover from backup?
            try:

                # move current configuration file
                os.rename("/etc/mosquitto/conf.d/default.conf.bak",
                          "/etc/mosquitto/conf.d/default.conf")

                print('* * * MOSQUITTO/DEFAULT.CONF RECOVERED * * *')
                
            except:
                raise Exception("Can't find /etc/mosquitto/conf.d/default.conf.")
        
        # create test configuration file
        with open('/etc/mosquitto/conf.d/test.conf', "w") as outfile:
            
            # change default host and port
            cat = subprocess.Popen(["cat",
                                    "/etc/mosquitto/conf.d/default.conf"],
                                   stdout= subprocess.PIPE)
            sed = subprocess.run(["sed",
                                  "s/8000/{}/".format(port)],
                                 stdin=cat.stdout,
                                 stdout=outfile)
            cat.wait()

        # move current configuration file
        os.rename("/etc/mosquitto/conf.d/default.conf",
                  "/etc/mosquitto/conf.d/default.conf.bak")

        print('>> Start mosquitto with test settings')

        # start mosquito server
        retval = subprocess.run(["service",
                                 "mosquitto",
                                 "start"])

        # Wait for start
        cls.run_until_success(["service",
                                "mosquitto",
                                "status"])


        time.sleep(2)
        
        cls.setUpTestData()

    @classmethod
    def tearDownClass(cls):

        # call super to shutdown server
        super().tearDownClass()
        
        print('>> Stopping mosquitto with test settings')
        
        # stop mosquito server
        retval = subprocess.run(["service",
                                 "mosquitto",
                                 "stop"])
        
        # # Wait for shutdown
        # cls.run_until_fail(["service",
        #                      "mosquitto",
        #                      "status"])
        
        time.sleep(2)
        
        # remove test configuration file
        os.rename("/etc/mosquitto/conf.d/test.conf",
                  "/etc/mosquitto/conf.d/test.conf.bak")
        
        # restore current configuration file
        os.rename("/etc/mosquitto/conf.d/default.conf.bak",
                  "/etc/mosquitto/conf.d/default.conf")

        try:
            
            # restore persistence file
            os.rename("/var/lib/mosquitto/mosquitto.db.bak",
                      "/var/lib/mosquitto/mosquitto.db")
        except:
            print("* * * CAN'T RECOVER MOSQUITTO PERSISTENCE FILE * * *")
            
        print('>> Starting mosquitto')
        
        # start mosquito server
        retval = subprocess.run(["service",
                                 "mosquitto",
                                 "start"])
        
        # Wait for start
        cls.run_until_success(["service",
                                "mosquitto",
                                "status"])
        
        # print('>> Starting mqttclient')
        
        # # start mqttclient
        # retval = subprocess.run(["supervisorctl",
        #                          "start",
        #                          "mqttclient"])

        time.sleep(2)
        
        # from django.db import connections

        # for conn in connections.all():
        #     conn.close()
        
    @classmethod
    def setUpTestData(cls):

        # Retrieve admin
        cls.u1 = User.objects.get(username=settings.MQTT['USERNAME'])

        try:
            
            # Add users
            cls.u2 = User.objects.get(username='testuser1')
            cls.u3 = User.objects.get(username='testuser2')

            # Add ambulances
            cls.a1 = Ambulance.objects.get(identifier='BC-179')
            cls.a2 = Ambulance.objects.get(identifier='BC-180')
            cls.a3 = Ambulance.objects.get(identifier='BC-181')

            # Add hospitals
            cls.h1 = Hospital.objects.get(name='Hospital General')
            cls.h2 = Hospital.objects.get(name='Hospital CruzRoja')
            cls.h3 = Hospital.objects.get(name='Hospital Nuevo')

            # Add equipment
            cls.e1 = Equipment.objects.get(name='X-ray')
            cls.e2 = Equipment.objects.get(name='Beds')
            cls.e3 = Equipment.objects.get(name='MRI - Ressonance')
            
            # add hospital equipment
            cls.he1 = HospitalEquipment.objects.get(hospital=cls.h1,
                                                    equipment=cls.e1)
            
            cls.he2 = HospitalEquipment.objects.get(hospital=cls.h1,
                                                    equipment=cls.e2)

            cls.he3 = HospitalEquipment.objects.get(hospital=cls.h2,
                                                    equipment=cls.e1)
            
            cls.he4 = HospitalEquipment.objects.get(hospital=cls.h2,
                                                    equipment=cls.e3)
            
            cls.he5 = HospitalEquipment.objects.get(hospital=cls.h3,
                                                    equipment=cls.e1)

            
        except:

            # Add users
            cls.u2 = User.objects.create_user(
                username='testuser1',
                email='test1@user.com',
                password='top_secret')
        
            cls.u3 = User.objects.create_user(
                username='testuser2',
                email='test2@user.com',
                password='very_secret')

            cls.u4 = User.objects.create_user(
                username='testuser3',
                email='test3@user.com',
                password='highly_secret')

            cls.u5 = User.objects.create_user(
                username='testuser4',
                email='test4@user.com',
                password='extremely_secret')

            # Add ambulances
            cls.a1 = Ambulance.objects.create(
                identifier='BC-179',
                comment='Maintenance due',
                capability=AmbulanceCapability.B.name,
                updated_by=cls.u1)
            
            cls.a2 = Ambulance.objects.create(
                identifier='BC-180',
                comment='Need painting',
                capability=AmbulanceCapability.A.name,
                updated_by=cls.u1)
            
            cls.a3 = Ambulance.objects.create(
                identifier='BC-181',
                comment='Engine overhaul',
                capability=AmbulanceCapability.R.name,
                updated_by=cls.u1)
        
            # Add hospitals
            cls.h1 = Hospital.objects.create(
                name='Hospital General',
                number="1234",
                street="don't know",
                comment="no comments",
                updated_by=cls.u1)
            
            cls.h2 = Hospital.objects.create(
                name='Hospital CruzRoja',
                number="4321",
                street='Forgot',
                updated_by=cls.u1)
            
            cls.h3 = Hospital.objects.create(
                name='Hospital Nuevo',
                number="0000",
                street='Not built yet',
                updated_by=cls.u1)
            
            # add equipment
            cls.e1 = Equipment.objects.create(
                name='X-ray',
                type=EquipmentType.B.name)
            
            cls.e2 = Equipment.objects.create(
                name='Beds',
                type=EquipmentType.I.name)
            
            cls.e3 = Equipment.objects.create(
                name='MRI - Ressonance',     # name with space!
                type=EquipmentType.B.name)
            
            # add hospital equipment
            cls.he1 = HospitalEquipment.objects.create(
                hospital=cls.h1,
                equipment=cls.e1,
                value='True',
                updated_by=cls.u1)
            
            cls.he2 = HospitalEquipment.objects.create(
                hospital=cls.h1,
                equipment=cls.e2,
                value='45',
                updated_by=cls.u1)

            cls.he3 = HospitalEquipment.objects.create(
                hospital=cls.h2,
                equipment=cls.e1,
                value='False',
                updated_by=cls.u1)
            
            cls.he4 = HospitalEquipment.objects.create(
                hospital=cls.h2,
                equipment=cls.e3,
                value='True',
                updated_by=cls.u1)
            
            cls.he5 = HospitalEquipment.objects.create(
                hospital=cls.h3,
                equipment=cls.e1,
                value='True',
                updated_by=cls.u1)

            # add hospitals to users
            UserHospitalPermission.objects.create(user=cls.u2,
                                                  hospital=cls.h1,
                                                  can_write=True)
            UserHospitalPermission.objects.create(user=cls.u2,
                                                  hospital=cls.h3)

            UserHospitalPermission.objects.create(user=cls.u3,
                                                  hospital=cls.h1)
            UserHospitalPermission.objects.create(user=cls.u3,
                                                  hospital=cls.h2,
                                                  can_write=True)

            # u3 has no hospitals

            # add ambulances to users
            UserAmbulancePermission.objects.create(user=cls.u1,
                                                   ambulance=cls.a2,
                                                   can_write=True)

            # u2 has no ambulances

            UserAmbulancePermission.objects.create(user=cls.u3,
                                                   ambulance=cls.a1,
                                                   can_read=False)
            UserAmbulancePermission.objects.create(user=cls.u3,
                                                   ambulance=cls.a3,
                                                   can_write=True)

            # Create groups
            cls.g1 = Group.objects.create(name='EMTs')
            cls.g2 = Group.objects.create(name='Drivers')
            cls.g3 = Group.objects.create(name='Dispatcher')

            # add hospitals to groups
            GroupHospitalPermission.objects.create(group=cls.g1,
                                                   hospital=cls.h1,
                                                   can_write=True)
            GroupHospitalPermission.objects.create(group=cls.g1,
                                                   hospital=cls.h3)

            GroupHospitalPermission.objects.create(group=cls.g2,
                                                   hospital=cls.h1)
            GroupHospitalPermission.objects.create(group=cls.g2,
                                                   hospital=cls.h2,
                                                   can_write=True)

            # g3 has no hospitals

            # add ambulances to groups
            GroupAmbulancePermission.objects.create(group=cls.g1,
                                                    ambulance=cls.a2,
                                                    can_write=True)

            # g2 has no ambulances

            GroupAmbulancePermission.objects.create(group=cls.g3,
                                                    ambulance=cls.a1,
                                                    can_read=False)
            GroupAmbulancePermission.objects.create(group=cls.g3,
                                                    ambulance=cls.a3,
                                                    can_write=True)

            cls.u4.groups.set([cls.g2])
            cls.u5.groups.set([cls.g1, cls.g3])


# MQTTTestClient
class MQTTTestClient(BaseClient):

    def __init__(self, *args, **kwargs):

        self.check_payload = kwargs.pop('check_payload', True)
        
        # call supper
        super().__init__(*args, **kwargs)

        # expect
        self.expecting_topics = {}
        self.expecting_messages = {}
        self.expecting_patterns = {}
        self.expecting = 0
        
        # publishing
        self.publishing = 0
        
    def done(self):

        return self.expecting == 0 and self.publishing == 0
        
    # The callback for when the client receives a CONNACK
    # response from the server.
    def on_connect(self, client, userdata, flags, rc):

        # is connected?
        return super().on_connect(client, userdata, flags, rc)

    def publish(self, topic, payload = None, qos = 0, retain = False):

        # publish
        self.publishing +=1 
        super().publish(topic, payload, qos, retain)

    def on_publish(self, client, userdata, mid):

        # did publish?
        super().on_publish(client, userdata, mid)
        self.publishing -=1 

        if self.debug:
            logging.debug('Just published mid={}[publishing={}]'.format(mid,
                                                                        self.publishing))
        
    # The callback for when a subscribed message is received from the server.
    def on_message(self, client, userdata, msg):

        if msg.topic in self.expecting_topics:

            # regular topic
            topic = msg.topic

        else:
            
            # can it be a pattern?
            match = False
            for k, p in self.expecting_patterns.items():
                if p.match(msg.topic):
                    # initialize topic
                    topic = k
                    match = True
                    break

            if not match:
                # did not match
                raise Exception("Unexpected message topic '{}'".format(msg.topic))

        # handle expected message
        self.expecting_topics[topic] += 1
        self.expecting -= 1

        # is message payload expected? remove
        try:
                
            self.expecting_messages[topic].remove(msg.payload)

        except ValueError:

            if self.check_payload:
                raise Exception('Unexpected message "{}:{}"'.format(msg.topic, msg.payload))

        if self.debug:
            logger.debug('Just received {}[count={},expecting={}]:{}'.format(msg.topic,
                                                                             self.expecting_topics[msg.topic],
                                                                             self.expecting,
                                                                             msg.payload))

    def expect(self, topic, msg=None, qos=2, remove=False):

        # pattern topic?
        if '+' in topic or '#' in topic:
            pattern = topic.replace('+', '[^/]+').replace('#', '[a-zA-Z0-9_/ ]+')
            self.expecting_patterns[topic] = re.compile(pattern)
            #print('pattern = {}'.format(pattern))

        # not subscribed
        if topic not in self.expecting_topics:

            # initialize
            self.expecting_topics[topic] = 0
            self.expecting_messages[topic] = []

            # and subscribe
            logger.debug("Subscribing to topic '{}'".format(topic))
            self.subscribe(topic, qos)

        else:

            logger.debug("Already subscribed to topic '{}'".format(topic))

        self.expecting += 1
        self.expecting_messages[topic].append(msg)


class TestMQTT:

    def is_connected(self, client, MAX_TRIES=10):

        # connected?
        k = 0
        while not client.connected and k < MAX_TRIES:
            k += 1
            client.loop()

        self.assertEqual(client.connected, True)

    def is_subscribed(self, client, MAX_TRIES=10):

        client.loop_start()

        # connected?
        k = 0
        while len(client.subscribed) and k < MAX_TRIES:
            k += 1
            time.sleep(1)

        client.loop_stop()

        self.assertEqual(len(client.subscribed), 0)

    def loop(self, *clients, MAX_TRIES=10):

        # logger.debug('clients = {}'.format(clients))
        # logger.debug('MAX_TRIES = {}'.format(MAX_TRIES))

        # starts clients
        for client in clients:
            client.loop_start()

        # connected?
        k = 0
        done = False
        while not done and k < MAX_TRIES:
            done = True
            for client in clients:
                done = done and client.done()
            k += 1
            time.sleep(1)

        # stop clients
        for client in clients:
            client.loop_stop()

        if not done:
            # logging.debug('NOT DONE:')
            for client in clients:
                if hasattr(client, 'expecting') and hasattr(client, 'publishing'):
                    logging.debug(('expecting = {}, ' +
                                   'publishing = {}').format(client.expecting,
                                                             client.publishing))

        self.assertEqual(done, True)
