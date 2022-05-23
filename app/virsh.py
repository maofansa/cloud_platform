"""对libvirt的封装"""
import re
import libvirt
import sys
import xml.etree.ElementTree as ET
from app.models import User, Domain, Cdrom, Volume, Image

# ISO路径（CephFS挂载）
iso_path = '/mnt/cephfs/iso/'

class Host:
    """libvirt连接、Domain信息获取和Volume管理

    Attributes:
        conn: libvirt.virConnect
        pool: libvirt.virStoragePool
        address: 主机地址
        hostname: 主机自命名
    """
    conn = None
    pool = None
    address = ''
    hostname = ''

    def __init__(self, driver: str, path: str, extra: str, name: str):
        """与libvirt建立连接

        :param driver: 连接方式
        :param path: 主机地址
        :param except: 连接位置
        :param name: 自命名主机名称
        """
        self.address = path
        self.hostname = name
        uri = '{}://{}/{}'.format(driver, path, extra)
        self.conn = libvirt.open(uri)
        self.pool = self.conn.storagePoolLookupByName('libvirt-pool')

    def __repr__(self):
        return '<Host {}>'.format(self.hostname)

    def close(self):
        """关闭libvirt.virConnect连接"""
        self.conn.close()
        self.conn = None
        self.hostname = ''

    def get_domains(self):
        """获得当前主机内的所有Domain

        :return: libvirt.virDomain的列表
        """
        domains = []
        vir_domains = self.conn.listAllDomains()
        for d in vir_domains:
            domains.append(MyDomain(d))
        return domains

    def get_domain_by_uuid(self, uuid: str):
        """通过UUID在当前主机内查找Domain

        :param uuid: Domain的UUID
        :return: MyDomain
        """
        vir_domain = None
        try:
            vir_domain = self.conn.lookupByUUIDString(uuid)
        except libvirt.libvirtError as e:
            return None
        return MyDomain(vir_domain)

    def get_domain_by_name(self, name: str):
        """通过name在当前主机内查找Domain

        :param name: Domain的name
        :return: MyDomain
        """
        vir_domain = None
        try:
            vir_domain = self.conn.lookupByName(name)
        except libvirt.libvirtError as e:
            return None
        return MyDomain(vir_domain)

    def get_hostname(self) -> str:
        """获得当前主机自命名

        :return: 当前主机自命名
        """
        return self.hostname

    def get_host_address(self) -> str:
        """获得当前主机ip地址

        :return: 当前主机ip地址
        """
        return self.address

    def get_volume(self, uuid: str) -> libvirt.virStorageVol:
        """在当前主机查找Volume

        :param uuid: Volume显示UUID，即实际名称
        :return: libvirt.virStorageVol
        """
        return self.pool.storageVolLookupByName(uuid)

    def create_volume(self, uuid: str, storage: int):
        """创建Volume

        :param uuid: Volume显示UUID，即实际名称
        :param storage: Volume大小，单位GB
        :return: None
        """
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

    def clone_volume(self, uuid: str, size: int, dom_vol: libvirt.virStorageVol) -> libvirt.virStorageVol:
        """克隆Volume

        :param uuid: 新Volume的显示UUID，即实际名称
        :param size: 新Volume大小，单位GB
        :param dom_vol: 被克隆的Volume
        :return: 克隆生成的新的Volume
        """
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

    def delete_volume(self, uuid: str):
        """删除Volume

        :param uuid: 要删除的Volume的显示UUID，即实际名称
        :return: None
        """
        vol = self.pool.storageVolLookupByName(uuid)
        try:
            vol.delete(0)
        except libvirt.libvirtError as e:
            raise e
        return


class MyDomain:
    """Domain查看、管理

    Arrtibutes:
        domain: libvirt.virDomain
    """
    domain: libvirt.virDomain

    def __init__(self, domain: libvirt.virDomain):
        self.domain = domain

    def get_id(self):
        """获得Domain的ID

        :return: Domain的ID
        """
        dom_id = self.domain.ID()
        if dom_id != -1:
            return dom_id
        return None

    def get_uuid(self) -> str:
        """获得Domain的UUID

        :return: Domain的UUID
        """
        # libvirt.virDomain.UUIDString()
        return self.domain.UUIDString()

    def get_os(self):
        """获得Domain的操作系统名称

        :return: Domain的操作系统名称
        """
        uuid = self.get_uuid()
        db_dom = Domain.quert.filter_by(uuid=uuid).first()
        if db_dom is not None:
            return db_dom.cdrom.name
        return -1

    def get_domain_state(self) -> str:
        """获得Domain的状态

        :return: Domain的状态
        """
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
        """获得Domain的内存使用比例

        :return: Domain的内存使用比例
        """
        if self.get_domain_state() == 'RUNNING':
            memory = self.domain.memoryStats()
            free_memory = memory['actual']
            if 'unused' in memory:
                free_memory -= memory['unused']
            return 1-free_memory/memory['actual']
        return None

    def map_memory_usage(self) -> int:
        """获得Domain的内存使用比例映射

        :return: Domain的内存使用比例映射
        """
        memory_usage = self.get_memory_usage()
        if memory_usage is None:
            return 0
        elif memory_usage < 0.5:
            return 1
        elif 0.5 <= memory_usage < 0.8:
            return 2
        else:
            return 3

    def get_ip(self) -> str:
        """获得Domain的IP地址

        :return: Domain的IP地址
        """
        if self.get_domain_state() != 'RUNNING':
            return ''
        try:
            # 获得domain interfaces字典
            ifaces = self.domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)

            # 查询IPV4地址
            # return repr(ifaces)
            for (name, val) in ifaces.items():
                if val['addrs']:
                    for ipaddr in val['addrs']:
                        if ipaddr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                            ip_addr = ipaddr['addr']
                            if ip_addr.startswith('192.168.122.'):
                                return ip_addr
        except libvirt.libvirtError as e:
            return repr(e)


class XMLDomain:
    """虚拟机xml配置

    Arributes:
        tree:
        name:
        root: xml.etree.ElementTree解析xml后的根节点
    """
    tree = None
    name = ''
    root = None

    def __init__(self, uri: str, name: str, mode: int):
        self.name = name
        if mode == 1:
            self.tree = ET.parse(uri)
            self.root = self.tree.getroot()
        else:
            text = open(uri).read()
            text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", text)
            self.root = ET.fromstring(text)

    def set_name(self, new_name: str):
        """配置xml中虚拟机名称

        :param new_name: 虚拟机名称
        """
        name = self.root.find('name')
        name.text = new_name

    def set_uuid(self, new_uuid: str):
        """配置xml中虚拟机UUID

        :param new_uuid: 虚拟机UUID
        """
        uuid = self.root.find('uuid')
        uuid.text = new_uuid

    def set_memory(self, new_memory: str):
        """配置xml中虚拟机内存大小

        :param new_memory: 虚拟机内存大小
        """
        memory = self.root.find('memory')
        current_memory = self.root.find('currentMemory')
        memory.text = new_memory
        current_memory.text = new_memory

    def set_vcpu(self, new_vcpu: str):
        """配置xml中虚拟机CPU数量

        :param new_vcpu:
        """
        vcpu = self.root.find('vcpu')
        vcpu.text = new_vcpu

    def set_title(self, new_title: str):
        """配置xml中虚拟机简单描述

        :param new_title: 虚拟机简单描述
        """
        title = self.root.find('title')
        title.text = new_title

    def set_description(self, new_description: str):
        """配置xml中虚拟机详细描述

        :param new_description: xml中虚拟机详细描述
        """
        description = self.root.find('description')
        description.text = new_description

    def set_cdrom(self, cdrom_uri: str):
        """配置xml中虚拟机系统

        :param cdrom_uri: 安装镜像路径
        """
        disk = self.root.find('devices/*[@device="cdrom"]')
        source = disk.find('source')
        source.set('file', cdrom_uri)

    def set_disk(self, disk_uri: str):
        """配置xml中虚拟机硬盘

        :param disk_uri: 硬盘路径
        """
        disk = self.root.find('devices/*[@device="disk"]')
        source = disk.find('source')
        source.set('name', 'libvirt-pool/{}'.format(disk_uri))

    def delete_max(self):
        """删除xml中MAC地址"""
        interface = self.root.find('*/interface')
        mac = interface.find('mac')
        if mac:
            interface.remove(mac)

    def set_vnc(self, port: str, cdrom: str):
        """配置虚拟机VNC连接

        :param port: 虚拟机VNC连接端口
        :param cdrom: 虚拟机安装镜像名称
        """
        devices = self.root.find('devices')
        '''
        <graphics type='vnc' port='xxxx' autoport='no' listen='0.0.0.0'>
            <listen type='address' address='0.0.0.0'/>
        </graphics>
        '''
        graphics = ET.Element('graphics', {'type':'vnc', 'port':str(port), 'autoport':'no', 'listen':'0.0.0.0'})
        listen = ET.Element('listen', {'type':'address', 'address':'0.0.0.0'})
        graphics.append(listen)
        devices.append(graphics)
        #  Windows虚拟机减少鼠标漂移
        if 'win' in cdrom.lower():
            '''
            <input type='tablet' bus='usb'/>
            '''
            inputs = ET.Element('input', {'type':'tablet', 'bus':'usb'})
            devices.append(inputs)


    def set_spice(self, port: str, cdrom: str):
        """配置虚拟机SPICE连接

        :param port: 虚拟机SPICE连接端口
        :param cdrom: 虚拟机安装镜像名称
        """
        devices = self.root.find('devices')
        '''
        <channel type='spicevmc'>
          <target type='virtio' name='com.redhat.spice.0'/>
        </channel>
        <graphics type='spice' port='6433' autoport='no' listen='0.0.0.0'>
        </graphics>
        <video>
          <model type='qxl' heads='1'/>
          <alias name='video0'/>
        </video>
        <sound model='ich6'>
          <alias name='sound0'/>
        </sound>
        '''
        channel = ET.Element('channel', {'type':'spicevmc'})
        target = ET.Element('target', {'type':'virtio', 'name':'com.redhat.spice.0'})
        channel.append(target)
        graphics = ET.Element('graphics', {'type': 'spice', 'port': str(port), 'autoport': 'no', 'listen': '0.0.0.0'})
        video = ET.Element('video')
        model = ET.Element('model', {'type':'qxl', 'heads':'1'})
        video_alias = ET.Element('alias', {'name':'video0'})
        video.append(model)
        video.append(video_alias)
        #  Windows虚拟机声音使用ac97
        if 'win' in cdrom.lower():
            sound = ET.Element('sound', {'model':'ac97'})
        #  Linux虚拟机声音使用ich6
        else:
            sound = ET.Element('sound', {'model':'ich6'})
        sound_alias = ET.Element('alias', {'name':'sound0'})
        sound.append(sound_alias)
        devices.append(channel)
        devices.append(graphics)
        devices.append(video)
        devices.append(sound)

    def create(self,
               uuid: str,
               name: str,
               memory: int,
               cpu: int,
               cdrom: str,
               protocol: str,
               port: int,
               title='',
               descript='') -> str:
        """生成新的Domain xml内容

        :param uuid: Doamin UUID
        :param name: Domain名称
        :param memory: Domain内存大小
        :param cpu: Domain CPU数量
        :param cdrom: Domain系统名称
        :param protocol: Domain远程连接方式（VNC/SPICE）
        :param port: Domain远程连接端口
        :param title: Domain简单描述
        :param descript: Doamin详细描述
        :return: 新生成的Domain xml字符串
        """
        self.set_uuid(uuid)
        self.set_name(name)
        self.set_memory(str(memory))
        self.set_vcpu(str(cpu)),
        self.set_cdrom('{}{}'.format(iso_path, cdrom))
        self.set_disk(uuid)
        self.set_title(title)
        self.set_description(descript)

        #  VNC连接
        if protocol == 'vnc':
            self.set_vnc(str(port), cdrom)
        #  SPICE连接
        else:
            self.set_spice(str(port), cdrom)
        # uri = '/home/maofan/cloud_platform/app/static/xml/domains/{}.xml'.format(uuid)
        # self.tree.write(uri)
        # return uri
        return ET.tostring(self.root).decode()


def conn_hosts(*args) -> []:
    """连接libvirt主机们

    :param args: 形如[driver, path, extra, name ...]的一维列表，每个主机包含4个属性：
        driver: 连接协议
        path: 主机IP地址
        extra: libvirt连接具体位置
        name: 主机名称
    :return: 类型为Host的列表
    """
    hosts = []
    for driver, path, extra, name in args:
        hosts.append(Host(driver, path, extra, name))
    return hosts


def close_hosts(hosts: []):
    """关闭libvirt主机们的连接

    :param hosts: Host列表
    """
    for host in hosts:
        host.close()
