# Copyright 2013-2020 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)
"""
Upload data to MQTT server

This service requires the python bindings for mqtt:

   pip install paho-mqtt

Minimal configuration:

[StdRestful]
    [[MQTT]]
        server_url = mqtt://username:password@localhost:1883/
        topic = weather
        unit_system = METRIC
        persist_connection = False # persist the connection across publishing data

Other MQTT options can be specified:

[StdRestful]
    [[MQTT]]
        ...
        qos = 1        # options are 0, 1, 2
        retain = true  # options are true or false

The observations can be sent individually, or in an aggregated packet:

[StdRestful]
    [[MQTT]]
        ...
        aggregation = individual, aggregate # individual, aggregate, or both

Bind to loop packets or archive records:

[StdRestful]
    [[MQTT]]
        ...
        binding = loop # options are loop or archive

Use the inputs map to customize name, format, or units for any observation:

[StdRestful]
    [[MQTT]]
        ...
        unit_system = METRIC # default to metric
        [[[inputs]]]
            [[[[outTemp]]]]
                name = inside_temperature  # use a label other than outTemp
                format = %.2f              # two decimal places of precision
                units = degree_F           # convert outTemp to F, others in C
            [[[[windSpeed]]]]
                units = knot  # convert the wind speed to knots

Use TLS to encrypt connection to broker.  The TLS options will be passed to
Paho client tls_set method.  Refer to Paho client documentation for details:

  https://eclipse.org/paho/clients/python/docs/

[StdRestful]
    [[MQTT]]
        ...
        [[[tls]]]
            # CA certificates file (mandatory)
            ca_certs = /etc/ssl/certs/ca-certificates.crt
            # PEM encoded client certificate file (optional)
            certfile = /home/user/.ssh/id.crt
            # private key file (optional)
            keyfile = /home/user/.ssh/id.key
            # Certificate requirements imposed on the broker (optional).
            #   Options are 'none', 'optional' or 'required'.
            #   Default is 'required'.
            cert_reqs = required
            # SSL/TLS protocol (optional).
            #   Options include sslv2, sslv23, sslv3, tls, tlsv1, tlsv11,
            #   tlsv12.
            #   Default is 'tlsv12'
            #   Not all options are supported by all systems.
            #   OpenSSL version till 1.0.0.h supports sslv2, sslv3 and tlsv1
            #   OpenSSL >= 1.0.1 supports tlsv11 and tlsv12
            #   OpenSSL >= 1.1.1 support TLSv1.3 (use tls_version = tls)
            #   Check your OpenSSL protocol support with:
            #   openssl s_client -help 2>&1  > /dev/null | egrep "\-(ssl|tls)[^a-z]"
            tls_version = tlsv12
            # Allowable encryption ciphers (optional).
            #   To specify multiple cyphers, delimit with commas and enclose
            #   in quotes.
            #ciphers =

Publish to multiple topics and override options specified above:

[StdRestful]
    [[MQTT]]
        [[[topics]]]
            [[[[topic-1]]]]
                unit_system = METRIC
                aggregation = individual, aggregate # individual, aggregate, or both
                binding = loop # options are loop or archive
                augment_record = True
                qos = 1        # options are 0, 1, 2
                retain = true  # options are true or false
                [[[[[inputs]]]]]
                    [[[[[[outTemp]]]]]]
                        name = inside_temperature  # use a label other than outTemp
                        format = %.2f              # two decimal places of precision
                        units = degree_F           # convert outTemp to F, others in C
          [[[[topic-2]]]]

"""

try:
    import queue as Queue
except ImportError:
    import Queue

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import paho.mqtt.client as mqtt
import random
import sys
import time

try:
    import cjson as json
    setattr(json, 'dumps', json.encode)
    setattr(json, 'loads', json.decode)
except (ImportError, AttributeError):
    try:
        import simplejson as json
    except ImportError:
        import json

import weewx
import weewx.restx
import weewx.units
from weeutil.weeutil import to_int, to_bool
try:
    from weeutil.config import search_up
except ImportError:
    # pre 3.9.0
    from weeutil.weeutil import search_up

VERSION = "0.23"

if weewx.__version__ < "3":
    raise weewx.UnsupportedFeature("weewx 3 is required, found %s" %
                                   weewx.__version__)

try:
    # weewx4 logging
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)
    def logdbg(msg):
        log.debug(msg)
    def loginf(msg):
        log.info(msg)
    def logerr(msg):
        log.error(msg)
except ImportError:
    # old-style weewx logging
    import syslog
    def logmsg(level, msg):
        syslog.syslog(level, 'restx: MQTT: %s' % msg)
    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)
    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)
    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


def _compat(d, old_label, new_label):
    if old_label in d and new_label not in d:
        d.setdefault(new_label, d[old_label])
        d.pop(old_label)

def _obfuscate_password(url):
    parts = urlparse(url)
    if parts.password is not None:
        # split out the host portion manually. We could use
        # parts.hostname and parts.port, but then you'd have to check
        # if either part is None. The hostname would also be lowercased.
        host_info = parts.netloc.rpartition('@')[-1]
        parts = parts._replace(netloc='{}:xxx@{}'.format(
            parts.username, host_info))
        url = parts.geturl()
    return url

# some unit labels are rather lengthy.  this reduces them to something shorter.
UNIT_REDUCTIONS = {
    'degree_F': 'F',
    'degree_C': 'C',
    'inch': 'in',
    'mile_per_hour': 'mph',
    'mile_per_hour2': 'mph',
    'km_per_hour': 'kph',
    'km_per_hour2': 'kph',
    'knot': 'knot',
    'knot2': 'knot2',
    'meter_per_second': 'mps',
    'meter_per_second2': 'mps',
    'degree_compass': None,
    'watt_per_meter_squared': 'Wpm2',
    'uv_index': None,
    'percent': None,
    'unix_epoch': None,
    }

# return the units label for an observation
def _get_units_label(obs, unit_system, unit_type=None):
    if unit_type is None:
        (unit_type, _) = weewx.units.getStandardUnitType(unit_system, obs)
    return UNIT_REDUCTIONS.get(unit_type, unit_type)

# get the template for an observation based on the observation key
def _get_template(obs_key, overrides, append_units_label, unit_system):
    tmpl_dict = dict()
    if append_units_label:
        unit_type = overrides.get('units')
        label = _get_units_label(obs_key, unit_system, unit_type)
        if label is not None:
            tmpl_dict['name'] = "%s_%s" % (obs_key, label)
    for x in ['name', 'format', 'units']:
        if x in overrides:
            tmpl_dict[x] = overrides[x]
    return tmpl_dict


class MQTT(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):
        """This service recognizes standard restful options plus the following:

        Required parameters:

        server_url: URL of the broker, e.g., something of the form
          mqtt://username:password@localhost:1883/
        Default is None

        Optional parameters:

        unit_system: one of US, METRIC, or METRICWX
        Default is None; units will be those of data in the database

        topic: the MQTT topic under which to post
        Default is 'weather'

        append_units_label: should units label be appended to name
        Default is True

        obs_to_upload: Which observations to upload.  Possible values are
        none or all.  When none is specified, only items in the inputs list
        will be uploaded.  When all is specified, all observations will be
        uploaded, subject to overrides in the inputs list.
        Default is all

        inputs: dictionary of weewx observation names with optional upload
        name, format, and units
        Default is None

        tls: dictionary of TLS parameters used by the Paho client to establish
        a secure connection with the broker.
        Default is None
        """
        super(MQTT, self).__init__(engine, config_dict)
        loginf("service version is %s" % VERSION)
        try:
            site_dict = config_dict['StdRESTful']['MQTT']
            site_dict['server_url']
        except KeyError as e:
            logerr("Data will not be uploaded: Missing option %s" % e)
            return

        if not to_bool(site_dict.get('enable', True)):
            return

        # for backward compatibility: 'units' is now 'unit_system'
        _compat(site_dict, 'units', 'unit_system')

        if 'tls' in config_dict['StdRESTful']['MQTT']:
            site_dict['tls'] = dict(config_dict['StdRESTful']['MQTT']['tls'])

        topic_configs = site_dict.get('topics', {})
        if not topic_configs:
            aggregation = site_dict.get('aggregation', 'individual,aggregate')
            topics = {}
            if aggregation.find('aggregate') >= 0:
                topic = site_dict.get('topic', 'weather') + '/loop'
                site_dict['topics'] = {}
                site_dict['topics'][topic] = {}
                topics[topic] = {}
                self.init_topic_dict(topic, site_dict, topics[topic], aggregation='aggregate')

            if aggregation.find('individual') >= 0:
                topic = site_dict.get('topic', 'weather')
                site_dict['topics'] = {}
                site_dict['topics'][topic] = {}
                topics[topic] = {}
                self.init_topic_dict(topic, site_dict, topics[topic], aggregation='individual')
        else:
            if site_dict.get('topic', None) is not None:
                loginf("'topics' configuration option found, ignoring 'topic' option")
            topics = {}
            for topic in topic_configs:
                topics[topic] = {}
                self.init_topic_dict(topic, site_dict, topics[topic])

        mqtt_dict = {}
        mqtt_dict['server_url'] = site_dict['server_url']
        mqtt_dict['client_id'] = site_dict.get('client_id', '')
        mqtt_dict['persist_connection'] = to_bool(site_dict.get('persist_connection', False))
        mqtt_dict['tls'] = site_dict.get('tls', None)
        mqtt_dict['log_success'] = to_bool(search_up(site_dict, 'log_success', True))
        mqtt_dict['log_failure'] = to_bool(search_up(site_dict, 'log_failure', True))
        mqtt_dict['post_interval'] = to_int(search_up(site_dict, 'post_interval', None))
        mqtt_dict['timeout'] = to_int(search_up(site_dict, 'timeout', 60))
        mqtt_dict['max_tries'] = to_int(search_up(site_dict, 'max_tries', 3))
        mqtt_dict['retry_wait'] = to_int(search_up(site_dict, 'retry_wait', 5))

        single_thread = to_bool(site_dict.get('single_thread', False))
        augment_record = False
        archive_binding = False
        loop_binding = False
        for topic in topics:
            if topics[topic]['augment_record']:
                augment_record = True
            if 'archive' in topics[topic]['binding']:
                archive_binding = True
            if 'loop' in topics[topic]['binding']:
                loop_binding = True
        mqtt_dict['topics'] = topics

        # if we are supposed to augment the record with data from weather
        # tables, then get the manager dict to do it.  there may be no weather
        # tables, so be prepared to fail.
        try:
            if augment_record:
                _manager_dict = weewx.manager.get_manager_dict_from_config(
                    config_dict, 'wx_binding')
                mqtt_dict['manager_dict'] = _manager_dict
                self.dbmanager = weewx.manager.open_manager(_manager_dict)
        except weewx.UnknownBinding:
            pass

        if single_thread:
            self.archive_queue = None
            if archive_binding:
                self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record_single_thread)
            if loop_binding:
                self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet_single_thread)
        else:
            self.archive_queue = Queue.Queue()
            if archive_binding:
                self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
            if loop_binding:
                self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

        self.archive_thread = MQTTThread(self.archive_queue, **mqtt_dict)
        if not single_thread:
            self.archive_thread.start()

        if 'topic' in site_dict:
            loginf("topic is %s" % site_dict['topic'])
        loginf("data will be uploaded to %s" %
               _obfuscate_password(site_dict['server_url']))
        if 'tls' in site_dict:
            loginf("network encryption/authentication will be attempted")

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)

    def new_loop_packet(self, event):
        self.archive_queue.put(event.packet)

    def new_archive_record_single_thread(self, event):
        self.archive_thread.process_record(event.record, self.dbmanager)

    def new_loop_packet_single_thread(self, event):
        self.archive_thread.process_record(event.packet, self.dbmanager)

    def init_topic_dict(self, topic, site_dict, topic_dict, aggregation=None):
        topic_dict['skip_upload'] = False
        topic_dict['binding'] = site_dict['topics'][topic].get('binding', site_dict.get('binding', 'archive'))
        if aggregation is None:
            topic_dict['aggregation'] = site_dict['topics'][topic].get('aggregation', site_dict.get('aggregation', 'individual,aggregate'))
        else:
            topic_dict['aggregation'] = aggregation
        topic_dict['append_units_label'] = to_bool(site_dict['topics'][topic].get('append_units_label', site_dict.get('append_units_label', True)))
        topic_dict['augment_record'] = to_bool(site_dict['topics'][topic].get('augment_record', site_dict.get('augment_record', True)))
        usn = site_dict['topics'][topic].get('unit_system', site_dict.get('unit_system', None))
        if  usn is not None:
            topic_dict['unit_system'] = weewx.units.unit_constants[usn]
            loginf("for %s: desired unit system is %s" % (topic, usn))

        topic_dict['upload_all'] = True if site_dict['topics'][topic].get('obs_to_upload', site_dict.get('obs_to_upload', 'all')).lower() == 'all' else False
        topic_dict['retain'] = to_bool(site_dict['topics'][topic].get('retain', site_dict.get('retain', False)))
        topic_dict['qos'] = to_int(site_dict['topics'][topic].get('qos', site_dict.get('qos', 0)))
        topic_dict['inputs'] = dict(site_dict['topics'][topic].get('inputs', site_dict).get('inputs', {}))
        topic_dict['templates'] = dict()

        loginf("for %s binding to %s" % (topic, topic_dict['binding']))

class TLSDefaults(object):
    def __init__(self):
        import ssl

        # Paho acceptable TLS options
        self.TLS_OPTIONS = [
            'ca_certs', 'certfile', 'keyfile',
            'cert_reqs', 'tls_version', 'ciphers'
            ]
        # map for Paho acceptable TLS cert request options
        self.CERT_REQ_OPTIONS = {
            'none': ssl.CERT_NONE,
            'optional': ssl.CERT_OPTIONAL,
            'required': ssl.CERT_REQUIRED
            }
        # Map for Paho acceptable TLS version options. Some options are
        # dependent on the OpenSSL install so catch exceptions
        self.TLS_VER_OPTIONS = dict()
        try:
            self.TLS_VER_OPTIONS['tls'] = ssl.PROTOCOL_TLS
        except AttributeError:
            pass
        try:
            # deprecated - use tls instead, or tlsv12 if python < 2.7.13
            self.TLS_VER_OPTIONS['tlsv1'] = ssl.PROTOCOL_TLSv1
        except AttributeError:
            pass
        try:
            # deprecated - use tls instead, or tlsv12 if python < 2.7.13
            self.TLS_VER_OPTIONS['tlsv11'] = ssl.PROTOCOL_TLSv1_1
        except AttributeError:
            pass
        try:
            # deprecated - use tls instead if python >= 2.7.13
            self.TLS_VER_OPTIONS['tlsv12'] = ssl.PROTOCOL_TLSv1_2
        except AttributeError:
            pass
        try:
            # SSLv2 is insecure - this protocol is deprecated
            self.TLS_VER_OPTIONS['sslv2'] = ssl.PROTOCOL_SSLv2
        except AttributeError:
            pass
        try:
            # deprecated - use tls instead, or tlsv12 if python < 2.7.13
            # (alias for PROTOCOL_TLS)
            self.TLS_VER_OPTIONS['sslv23'] = ssl.PROTOCOL_SSLv23
        except AttributeError:
            pass
        try:
            # SSLv3 is insecure - this protocol is deprecated
            self.TLS_VER_OPTIONS['sslv3'] = ssl.PROTOCOL_SSLv3
        except AttributeError:
            pass


class MQTTThread(weewx.restx.RESTThread):

    def __init__(self, queue, server_url, topics, persist_connection,
                 client_id='',
                 manager_dict=None, tls=None,
                 post_interval=None, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5,
                 max_backlog=sys.maxsize):
        super(MQTTThread, self).__init__(queue,
                                         protocol_name='MQTT',
                                         manager_dict=manager_dict,
                                         post_interval=post_interval,
                                         max_backlog=max_backlog,
                                         stale=stale,
                                         log_success=log_success,
                                         log_failure=log_failure,
                                         max_tries=max_tries,
                                         timeout=timeout,
                                         retry_wait=retry_wait)
        self.server_url = server_url
        self.client_id = client_id
        self.persist_connection = persist_connection
        self.tls_dict = {}
        if tls is not None:
            # we have TLS options so construct a dict to configure Paho TLS
            dflts = TLSDefaults()
            for opt in tls:
                if opt == 'cert_reqs':
                    if tls[opt] in dflts.CERT_REQ_OPTIONS:
                        self.tls_dict[opt] = dflts.CERT_REQ_OPTIONS.get(tls[opt])
                elif opt == 'tls_version':
                    if tls[opt] in dflts.TLS_VER_OPTIONS:
                        self.tls_dict[opt] = dflts.TLS_VER_OPTIONS.get(tls[opt])
                elif opt in dflts.TLS_OPTIONS:
                    self.tls_dict[opt] = tls[opt]
            logdbg("TLS parameters: %s" % self.tls_dict)
        self.topics = topics
        self.mc = None
        if persist_connection:
            for _count in range(self.max_tries):
                try:
                    self.mc = self.connect()
                    self.mc.loop_start()
                    break
                except (ConnectionRefusedError) as e:
                    logdbg("Failed connection %d: %s" % (_count+1, e))
                time.sleep(self.retry_wait)
            else:
                raise ConnectionError

    def filter_data(self, upload_all, templates, inputs, append_units_label, record):
        # if uploading everything, we must check the upload variables list
        # every time since variables may come and go in a record.  use the
        # inputs to override any generic template generation.
        if upload_all:
            for f in record:
                if f not in templates:
                    templates[f] = _get_template(f,
                                                 inputs.get(f, {}),
                                                 append_units_label,
                                                 record['usUnits'])

        # otherwise, create the list of upload variables once, based on the
        # user-specified list of inputs.
        elif not templates:
            for f in inputs:
                templates[f] = _get_template(f, inputs[f],
                                             append_units_label,
                                             record['usUnits'])

        # loop through the templates, populating them with data from the record
        data = dict()
        for k in templates:
            try:
                v = float(record.get(k))
                name = templates[k].get('name', k)
                fmt = templates[k].get('format', '%s')
                to_units = templates[k].get('units')
                if to_units is not None:
                    (from_unit, from_group) = weewx.units.getStandardUnitType(
                        record['usUnits'], k)
                    from_t = (v, from_unit, from_group)
                    v = weewx.units.convert(from_t, to_units)[0]
                s = fmt % v
                data[name] = s
            except (TypeError, ValueError):
                pass
        # FIXME: generalize this
        if 'latitude' in data and 'longitude' in data:
            parts = [str(data['latitude']), str(data['longitude'])]
            if 'altitude_meter' in data:
                parts.append(str(data['altitude_meter']))
            elif 'altitude_foot' in data:
                parts.append(str(data['altitude_foot']))
            data['position'] = ','.join(parts)
        return data

    def process_record(self, record, dbmanager):
        if self.persist_connection:
            mc = self.mc
        else:
            mc = self.connect()
            mc.loop_start()
        for topic in self.topics:
            data = self.update_record(topic, record, dbmanager)
            if weewx.debug >= 2:
                logdbg("data: %s" % data)
            if self.topics[topic]['skip_upload']:
                loginf("skipping upload")
                break       
            if 'interval' in record:
                if 'archive' in self.topics[topic]['binding']:
                    self.prep_data(mc, data, topic)
            else:
                if 'loop' in self.topics[topic]['binding']:
                    self.prep_data(mc, data, topic)
        
        if not self.persist_connection:
            self.disconnect(mc)

    def update_record(self, topic, record, dbmanager):
        updated_record = dict(record)
        if self.topics[topic]['augment_record'] and dbmanager is not None:
            updated_record = self.get_record(updated_record, dbmanager)
        if self.topics[topic]['unit_system'] is not None:
            updated_record = weewx.units.to_std_system(updated_record, self.topics[topic]['unit_system'])
        data = self.filter_data(self.topics[topic]['upload_all'],
                                self.topics[topic]['templates'],
                                self.topics[topic]['inputs'],
                                self.topics[topic]['append_units_label'],
                                record)
        return data
        
    def prep_data(self, mc, data, topic):
        if self.topics[topic]['aggregation'].find('aggregate') >= 0:
            self.publish_data(mc,
                                        data,
                                        topic,
                                        self.topics[topic]['qos'],
                                        self.topics[topic]['retain'])
        if self.topics[topic]['aggregation'].find('individual') >= 0:
            for key in data:
                tpc = topic + '/' + key
                self.publish_data(mc, tpc, data[key], retain=self.topics[topic]['retain'], qos=self.topics[topic]['qos'])

    def publish_data(self, mc, data, topic, qos, retain):
        import socket
        for _count in range(self.max_tries):
            try:
                (res, mid) = mc.publish(topic, json.dumps(data),
                                        retain=retain, qos=qos)
                if res == mqtt.MQTT_ERR_SUCCESS:
                    return
                elif res == mqtt.MQTT_ERR_NO_CONN:
                    logerr("Publish failed for %s: %s. Attempting to reconnect." % (topic, res))
                    mc = self.connect()
                    mc.loop_start()
                    if self.persist_connection:
                        self.mc = mc
                else:
                    logerr("Publish failed for %s: %s. Skipping." % (topic, res))
                    return
            except (socket.error, socket.timeout, socket.herror) as e:
                logdbg("Failed publish attempt %d: %s" % (_count+1, e))
                time.sleep(self.retry_wait)
        else:
            raise weewx.restx.FailedPost("Failed upload after %d tries" %
                                         (self.max_tries,))

    def connect(self):
        url = urlparse(self.server_url)
        client_id = self.client_id
        if not client_id:
            pad = "%032x" % random.getrandbits(128)
            client_id = 'weewx_%s' % pad[:8]
        mc = mqtt.Client(client_id=client_id)
        if url.username is not None and url.password is not None:
            mc.username_pw_set(url.username, url.password)
        # if we have TLS opts configure TLS on our broker connection
        if len(self.tls_dict) > 0:
            mc.tls_set(**self.tls_dict)
        mc.connect(url.hostname, url.port)
        return mc

    def disconnect(self, mc):
        mc.loop_stop()
        mc.disconnect()
