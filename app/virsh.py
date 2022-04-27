"""
    对libvirt的封装
"""
import re

import libvirt
import xml.etree.ElementTree as ET
from app.models import User, Domain, Cdrom, Volume, Image

# ISO路径（CephFS挂载）
iso_path = '/mnt/cephfs/iso/'

class Host:
    conn = None
    pool = None
    address = ''
    hostname = ''

    def __init__(self, driver, path, extra, name):
        self.address = path
        self.hostname = name
        uri = '{}://{}/{}'.format(driver, path, extra)
        self.conn = libvirt.open(uri)
        self.pool = self.conn.storagePoolLookupByName('libvirt-pool')

    def __repr__(self):
        return '<Host {}>'.format(self.hostname)

    def close(self):
        self.conn.close()
        self.conn = None
        self.hostname = ''

    def get_domains(self):
        domains = []
        vir_domains = self.conn.listAllDomains()
        for d in vir_domains:
            domains.append(MyDomain(d))
        return domains

    def get_domain_by_uuid(self, uuid):
        vir_domain = None
        try:
            vir_domain = self.conn.lookupByUUIDString(uuid)
        except libvirt.libvirtError as e:
            return None
        return MyDomain(vir_domain)

    def get_domain_by_name(self, name):
        vir_domain = None
        try:
            vir_domain = self.conn.lookupByName(name)
        except libvirt.libvirtError as e:
            return None
        return MyDomain(vir_domain)

    def get_hostname(self):
        return self.hostname

    def get_volume(self, uuid):
        return self.pool.storageVolLookupByName(uuid)

    def create_volume(self, uuid, storage):
        vol_xml = """
        <volume type='network'>
          <name>{}</name>
          <capacity unit='GB'>{}</capacity>
          <allocation>0</allocation>
        </volume>
        """.format(uuid, storage)

        try:
          vol = self.pool.createXML(vol_xml)
        except libvirt.libvirtError as e:
            raise e
        return

    def clone_volume(self, uuid, size, dom_vol):
        vol_xml = """
        <volume type='network'>
          <name>{}</name>
          <capacity unit='bytes'>{}</capacity>
          <allocation>0</allocation>
        </volume>
        """.format(uuid, size)

        try:
          vol = self.pool.createXMLFrom(vol_xml, dom_vol)
        except libvirt.libvirtError as e:
            raise e
        return vol

    def delete_volume(self, uuid):
        vol = self.pool.storageVolLookupByName(uuid)
        try:
            vol.delete(0)
        except libvirt.libvirtError as e:
            raise e
        return


class MyDomain:
    domain = None

    def __init__(self, domain):
        self.domain = domain

    def get_id(self):
        dom_id = self.domain.ID()
        if dom_id != -1:
            return dom_id
        return None

    def get_uuid(self):
        # libvirt.virDomain.UUIDString()
        return self.domain.UUIDString()

    def get_os(self):
        uuid = self.get_uuid()
        db_dom = Domain.quert.filter_by(uuid=uuid).first()
        if db_dom is not None:
            return db_dom.cdrom.name
        return -1

    def get_domain_state(self):
        state = 'UNKNOWN'
        virstate, reason = self.domain.state()

        if virstate == libvirt.VIR_DOMAIN_NOSTATE:
            state = 'NOSTATE'
        elif virstate == libvirt.VIR_DOMAIN_RUNNING:
            state = 'RUNNING'
        elif virstate == libvirt.VIR_DOMAIN_BLOCKED:
            state = 'BLOCKED'
        elif virstate == libvirt.VIR_DOMAIN_PAUSED:
            state = 'PAUSED'
        elif virstate == libvirt.VIR_DOMAIN_SHUTDOWN:
            state = 'SHUTDOWN'
        elif virstate == libvirt.VIR_DOMAIN_SHUTOFF:
            state = 'SHUTOFF'
        elif virstate == libvirt.VIR_DOMAIN_CRASHED:
            state = 'CRASHED'
        elif virstate == libvirt.VIR_DOMAIN_PMSUSPENDED:
            state = 'PMSUSPENDED'
        return state

    def get_memory_usage(self):
        if self.get_domain_state() == 'RUNNING':
            memory = self.domain.memoryStats()
            free_memory = memory['actual']
            if 'unused' in memory:
                free_memory -= memory['unused']
            return 1-free_memory/memory['actual']
        return None

    def map_memory_usage(self):
        memory_usage = self.get_memory_usage()
        if memory_usage is None:
            return 0
        elif memory_usage < 0.5:
            return 1
        elif 0.5 <= memory_usage < 0.8:
            return 2
        else:
            return 3


class XMLDomain:
    tree = None
    name = ''
    root = None

    def __init__(self, uri, name, mode):
        self.name = name
        if mode == 1:
            self.tree = ET.parse(uri)
            self.root = self.tree.getroot()
        else:
            text = open(uri).read()
            text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", text)
            self.root = ET.fromstring(text)

    def set_name(self, new_name):
        name = self.root.find('name')
        name.text = new_name

    def set_uuid(self, new_uuid):
        uuid = self.root.find('uuid')
        uuid.text = new_uuid

    def set_memory(self, new_memory):
        memory = self.root.find('memory')
        current_memory = self.root.find('currentMemory')
        memory.text = new_memory
        current_memory.text = new_memory

    def set_vcpu(self, new_vcpu):
        vcpu = self.root.find('vcpu')
        vcpu.text = new_vcpu

    def set_title(self, new_title):
        title = self.root.find('title')
        title.text = new_title

    def set_description(self, new_description):
        description = self.root.find('description')
        description.text = new_description

    def set_cdrom(self, cdrom_uri):
        disk = self.root.find('devices/*[@device="cdrom"]')
        source = disk.find('source')
        source.set('file', cdrom_uri)

    def set_disk(self, disk_uri):
        disk = self.root.find('devices/*[@device="disk"]')
        source = disk.find('source')
        source.set('name', 'libvirt-pool/{}'.format(disk_uri))

    def delete_max(self):
        interface = self.root.find('*/interface')
        mac = interface.find('mac')
        if mac:
            interface.remove(mac)

    def create(self, uuid, name, memory, cpu, cdrom, title='', descript=''):
        self.set_uuid(uuid)
        self.set_name(name)
        self.set_memory(str(memory))
        self.set_vcpu(str(cpu)),
        self.set_cdrom('{}{}'.format(iso_path, cdrom))
        self.set_disk(uuid)
        self.set_title(title)
        self.set_description(descript)
        # uri = '/home/maofan/cloud_platform/app/static/xml/domains/{}.xml'.format(uuid)
        # self.tree.write(uri)
        # return uri
        return ET.tostring(self.root).decode()


def conn_hosts(*args):
    hosts = []
    for driver, path, extra, name in args:
        hosts.append(Host(driver, path, extra, name))
    return hosts


def close_hosts(hosts):
    for host in hosts:
        host.close()
