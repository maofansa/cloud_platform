"""
    路由模块包
"""
import json
import math
from uuid import uuid1

import libvirt
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Domain, Cdrom, Volume, Image
from app.public import r
from app.virsh import Host, MyDomain, XMLDomain, conn_hosts, close_hosts
from libvirt import libvirtError


host_list = ['qemu+tcp', '172.18.5.2', 'system', 'Host1']
domain_template = '/home/cloud_platform/app/static/xml/template.xml'
image_domain_url = '/mnt/cephfs/libvirt/imageXML/'


@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('domain'))
    return redirect(url_for('login'))


@app.route('/test')
def test():
    return render_template("test.html")


@app.route('/domain')
@login_required
# def domain():
#     domains = Domain.query.all()
#     uuid = uuid1()
#     form = CreateDomainForm(uuid=uuid)
#     return render_template("index.html", title="Domain Manage", domains=domains, form=form)
def domain():
    return render_template("domain.html")


@app.route('/image')
@login_required
def image():
    return render_template("image.html")


@app.route('/network')
@login_required
def network():
    return render_template("network.html")


@app.route('/domainlist', methods=['GET'])
@login_required
def get_domains():
    rt = {}
    temp = []
    count = 0

    hosts = conn_hosts(host_list)
    for host in hosts:
        hostname = host.get_hostname()
        domains = host.get_domains()
        for d in domains:
            count += 1
            uuid = d.domain.UUIDString()
            db_d = Domain.query.filter_by(uuid=uuid).first()
            title, description, vcpu = '', '', 0
            if db_d is not None:
                title = db_d.title
                description = db_d.description
                vcpu = db_d.vcpu
            temp.append({
                'id': d.get_id(),
                'uuid': d.domain.UUIDString(),
                'name': d.domain.name(),
                'state': d.get_domain_state(),
                'host': hostname,
                'max_memory': d.domain.maxMemory(),
                'memory_usage': d.get_memory_usage(),
                'memory_usage_mapping': d.map_memory_usage(),
                'title': title,
                'description': description,
                'vcpu': vcpu,
                'ip': d.get_ip()
            })
    close_hosts(hosts)

    rt['count'] = count
    rt['items'] = temp

    return r(rt)


@app.route('/domain/start/<string:uuid>', methods=['PUT'])
@login_required
def start_domain(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    dom = None
    status = 1
    msg = ''
    for host in hosts:
        dom = host.get_domain_by_uuid(data['uuid'])
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            break
    if dom is None:
        msg = "未找到虚拟机"
    elif dom.get_domain_state() == 'RUNNING':
        msg = "虚拟机已运行"
    elif dom.get_domain_state() == 'PAUSED':
        dom.domain.resume()
        status, msg = 0, "虚拟机恢复"
    elif dom.get_domain_state() == 'SHUTDOWN' or 'SHUTOFF':
        try:
            dom.domain.create()
            status, msg = 0, "虚拟机启动"
        except libvirtError as e:
            status, msg = 1, repr(e)
    else:
        status, msg = 1, "虚拟机无法启动"

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/domain/pause/<string:uuid>', methods=['PUT'])
@login_required
def pause_domain(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    dom = None
    status = 1
    msg = ''
    for host in hosts:
        dom = host.get_domain_by_uuid(data['uuid'])
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            break
    if dom is None:
        msg = "未找到虚拟机"
    elif dom.get_domain_state() != 'RUNNING':
        msg = "虚拟机未运行"
    else:
        try:
            dom.domain.suspend()
            status, msg = 0, "虚拟机已挂起"
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/domain/shutdown/<string:uuid>', methods=['PUT'])
@login_required
def shutdown_domain(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    dom = None
    status = 1
    msg = ''
    for host in hosts:
        dom = host.get_domain_by_uuid(data['uuid'])
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            break
    if dom is None:
        msg = "未找到虚拟机"
    elif dom.get_domain_state() != 'RUNNING':
        msg = "虚拟机未运行"
    else:
        try:
            dom.domain.shutdownFlags(0)
            status, msg = 0, "虚拟机关闭中"
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/domain/destroy/<string:uuid>', methods=['PUT'])
@login_required
def destroy_domain(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    dom = None
    status = 1
    msg = ''
    for host in hosts:
        dom = host.get_domain_by_uuid(data['uuid'])
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            break
    if dom is None:
        msg = "未找到虚拟机"
    elif dom.get_domain_state() == 'SHUTOFF':
        msg = "虚拟机未运行"
    else:
        try:
            dom.domain.destroyFlags(0)
            status, msg = 0, "虚拟机已强制关闭"
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/domain/undefine/<string:uuid>', methods=['PUT'])
@login_required
def undefine_domain(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    dom = None
    status = 1
    msg = ''
    uuid = data['uuid']
    for host in hosts:
        dom = host.get_domain_by_uuid(uuid)
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            break
    if dom is None:
        msg = "未找到虚拟机"
    # elif dom.get_domain_state() != 'RUNNING':
    #     msg = "虚拟机未运行"
    else:
        try:
            msg = "虚拟机已删除"
            if dom.get_domain_state() == 'RUNNING':
                dom.domain.destroyFlags(0)
            dom.domain.undefineFlags(0)
            host.delete_volume(uuid)
            status = 0

            db_dom = Domain.query.filter_by(uuid=uuid).first()
            db_vol = Volume.query.filter_by(uuid=uuid).first()
            db.session.delete(db_dom)
            db.session.delete(db_vol)
            db.session.commit()
            # db.session.close()
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/domain/create', methods=['POST'])
@login_required
def create_domain():
    data = request.json
    if data['modeSelect'] == '1':
        # Make sure uuid and name are unique
        status, msg = 1, "未创建虚拟机"
        name = data['name']
        # if Domain.query.filter_by(uuid=uuid).first() is not None:
        #     status, msg = 1, "虚拟机UUID不唯一"
        #     return r({}, status, msg)
        if Domain.query.filter_by(name=name).first() is not None:
            status, msg = 1, "虚拟机名称不唯一"
            return r({}, status, msg)

        # from cdrom
        if not data['imageSwitch']:
            uuid = data['uuid']
            memory = int(data['memory'][0:-2])
            disk_size = int(data['storage'][0:-2])
            db_cdrom = Cdrom.query.filter_by(id=int(data['cdrom'])).first()

            # xml = XMLDomain(url_for('static', filename='xml/template.xml'), data['name'])
            xml = XMLDomain(domain_template, name, 1)
            xml_str = xml.create(uuid, name, memory*1024, data['vcpu'], db_cdrom.url,
                                 data['title'], data['description'])
            # return r({}, 1, xml_str)
            # f = open(xml_uri)
            # xmlconfig = f.read()
            # f.close()

            hosts = conn_hosts(host_list)
            # TO DO..
            host = hosts[0]
            try:
                # Volume Create
                host.create_volume(uuid, disk_size)
                # insert db.Volume
                db_vol = Volume(uuid=uuid, size=disk_size)
                db.session.add(db_vol)
                db.session.commit()
                # db.session.close()

                # Domain Create
                # host.conn.defineXMLFlags(xmlconfig, 0)
                host.conn.defineXMLFlags(xml_str, 0)
                status, msg = 0, "创建虚拟机 {} 成功".format(data['name'])

                # insert db
                db_dom = Domain(uuid=uuid, name=name, memory=memory, vcpu=int(data['vcpu']),
                                title=data['title'], description=data['description'],
                                volume=db_vol, cdrom=db_cdrom)
                db.session.add(db_dom)
                db.session.commit()
                # db.session.close()
            except libvirtError as e:
                status, msg = 1, repr(e)

        # from image
        else:
            image_uuid = data['image']
            new_uuid = str(uuid1())
            db_image = Image.query.filter_by(uuid=image_uuid).first()
            db_cdrom = db_image.cdrom
            image_domain_xml = '{}{}.xml'.format(image_domain_url, db_image.uuid)
            disk_size = db_image.volume.size
            memory = int(data['memory'][0:-2])

            xml = XMLDomain(domain_template, name, 1)
            xml_str = xml.create(new_uuid, name, memory * 1024, data['vcpu'], db_cdrom.url,
                                 data['title'], data['description'])

            hosts = conn_hosts(host_list)
            # TO DO..
            host = hosts[0]
            try:
                # Volume Create
                img_vol = host.get_volume(image_uuid)
                host.clone_volume(new_uuid, disk_size, img_vol)
                # insert db.Volume
                db_vol = Volume(uuid=new_uuid, size=disk_size)
                db.session.add(db_vol)
                db.session.commit()
                # db.session.close()

                # Domain Create
                # host.conn.defineXMLFlags(xmlconfig, 0)
                host.conn.defineXMLFlags(xml_str, 0)
                status, msg = 0, "创建虚拟机 {} 成功".format(data['name'])

                # insert db
                db_dom = Domain(uuid=new_uuid, name=name, memory=memory, vcpu=int(data['vcpu']),
                                title=data['title'], description=data['description'],
                                volume=db_vol, cdrom=db_cdrom)
                db.session.add(db_dom)
                db.session.commit()
                # db.session.close()
            except libvirtError as e:
                status, msg = 1, repr(e)

        close_hosts(hosts)
        return r({}, status, msg)
    elif data['modeSelect'] == 2:
        name_sample = data['name']
        count = int(data['number'])
        names = []
        uuids = []
        memory = int(data['memory'][0:-2]) * 1024
        vcpu = int(data['vcpu'])
        storage = int(data['storage'][0:-2])
        cdrom = data['cdrom']
        title = data['title']
        descript = data['description']

        for i in range(count):
            name = '{}_{}'.format(name_sample, i)
            names.append(name)
            if Domain.query.filter_by(name=name).first() is not None:
                status, msg = 1, "虚拟机名称不唯一"
                return r({}, status, msg)

        hosts = conn_hosts(host_list)
        # TO DO..
        host = hosts[0]
        status = 0
        success_stat = 0
        failed_dict = {}
        db_cdrom = Cdrom.query.filter_by(id=int(cdrom)).first()
        for i in range(count):
            uuid = str(uuid1())
            name = names[i]
            uuids.append(uuid)
            xml = XMLDomain(domain_template, name, 1)
            xml_str = xml.create(uuid, name, memory, vcpu, db_cdrom.url, title, descript)

            # f = open(xml_uri)
            # xmlconfig = f.read()
            # f.close()

            try:
                # Volume Create
                host.create_volume(uuid, storage)
                # insert db.Volume
                db_vol = Volume(uuid=uuid, size=storage)
                db.session.add(db_vol)
                db.session.commit()
                # db.session.close()

                # Domain Create
                host.conn.defineXMLFlags(xml_str, 0)
                success_stat += 1
                # insert db
                db_dom = Domain(uuid=uuid, name=name, memory=memory, vcpu=int(data['vcpu']),
                                title=data['title'], description=data['description'],
                                volume=db_vol, cdrom=db_cdrom)
                db.session.add(db_dom)
                db.session.commit()
                # db.session.close()
            except libvirtError as e:
                failed_dict[name] = repr(e)

        status = 0
        msg = "{}个创建成功， {}个创建失败".format(success_stat, count - success_stat)
        if success_stat == 0:
            status = 1
        for key in failed_dict:
            msg = '{}\n{}: {}'.format(msg, key, failed_dict[key])
        return r({}, status, msg)

    return r({}, 1, 'modeSelect out of range')


@app.route('/initUUID', methods=['GET'])
@login_required
def generate_uuid():
    return r({'uuid': str(uuid1())})


@app.route('/domain/save', methods=['POST'])
@login_required
def save_domain():
    data = request.json

    if Image.query.filter_by(name=data['name']).first() is not None:
        status, msg = 1, "模板名称不唯一"
        return r({}, status, msg)

    img_uuid = str(uuid1())
    # img_url = '{}{}.xml'.format(image_domain_url, img_uuid)
    hosts = conn_hosts(host_list)
    this_host = None
    dom = None
    vol = None
    status = 1
    msg = ''

    for host in hosts:
        dom = host.get_domain_by_uuid(data['dom_uuid'])
        vol = host.get_volume(data['dom_uuid'])
        # dom = host.get_domain_by_name(data['name'])
        if dom is not None:
            this_host = host
            break
    if dom is None:
        msg = "未找到虚拟机"
    # elif dom.get_domain_state() == 'SHUTOFF':
    #     msg = "虚拟机未运行"
    else:
        try:
            # vol_size = round(int(vol.info()[1])/math.pow(1024, 3), 0)
            vol_size = vol.info()[1]
            vol_size_gb = round(int(vol.info()[1]) / math.pow(1024, 3), 0)
            # dom.domain.saveFlags(img_url)
            img_vol = this_host.clone_volume(img_uuid, vol_size, vol)
            # img_vol.info()

            db_dom = Domain.query.filter_by(uuid=dom.get_uuid()).first()
            db_vol = Volume(uuid=img_uuid, size=vol_size_gb)
            db.session.add(db_vol)
            db.session.commit()

            db_img = Image(uuid=img_uuid, name=data['img-name'], title=data['img-title'],
                           cdrom=db_dom.cdrom, volume=db_vol)
            db.session.add(db_img)
            db.session.commit()
            status, msg = 0, "成功创建模板 {}".format(data['img-name'])
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)

    return r({}, status, msg)


@app.route('/domain/config', methods=['POST'])
@login_required
def config_domain():
    data = request.json
    hosts = conn_hosts(host_list)
    this_host = None
    dom = None
    status = 1
    msg = ''

    for host in hosts:
        dom = host.get_domain_by_uuid(data['dom_uuid'])
        if dom is not None:
            this_host = host
            break
    if dom is None:
        msg = "未找到虚拟机"
    else:
        try:
            dom.domain.setVcpus(int(data['vcpu']))
            dom.domain.setMemory(int(data['memory'][0:-2]))
            # dom.domain.setMaxMemory(int(data['memory'][0:-2]))

            db_dom = Domain.query.filter_by(uuid=dom.get_uuid()).first()
            db_dom.vcpu = int(data['vcpu'])
            db_dom.memory = int(data['memory'][0:-2])
            db.session.commit()

            status, msg = 0, "修改成功"
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)

    return r({}, status, msg)


@app.route('/domains/pause', methods=['PUT'])
@login_required
def pause_domains():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 1
    for item in items:
        dom = None
        for host in hosts:
            dom = host.get_domain_by_uuid(item['uuid'])
            if dom is not None:
                break
        if dom is None:
            msg_dict[item['name']] = "未找到虚拟机"
        elif dom.get_domain_state() != 'RUNNING':
            msg_dict[item['name']] = "虚拟机未运行"
        else:
            try:
                dom.domain.suspend()
                status = 0
                msg_dict[item['name']] = "虚拟机已挂起"
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, 0, msg)


@app.route('/domains/start', methods=['PUT'])
@login_required
def start_domains():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 1
    for item in items:
        dom = None
        for host in hosts:
            dom = host.get_domain_by_uuid(item['uuid'])
            if dom is not None:
                break
        if dom is None:
            msg_dict[item['name']] = "未找到虚拟机"
        elif dom.get_domain_state() == 'RUNNING':
            msg_dict[item['name']] = "虚拟机已运行"
        elif dom.get_domain_state() == 'PAUSED':
            try:
                dom.domain.resume()
                status = 0
                msg_dict[item['name']] = "虚拟机恢复"
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)
        elif dom.get_domain_state() == 'SHUTDOWN' or 'SHUTOFF':
            try:
                dom.domain.create()
                msg_dict[item['name']] = "虚拟机启动"
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)
        else:
            msg_dict[item['name']] = "虚拟机无法启动"

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, 0, msg)


@app.route('/domains/shutdown', methods=['PUT'])
@login_required
def shutdown_domains():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 1
    for item in items:
        dom = None
        for host in hosts:
            dom = host.get_domain_by_uuid(item['uuid'])
            if dom is not None:
                break
        if dom is None:
            msg_dict[item['name']] = "未找到虚拟机"
        elif dom.get_domain_state() != 'RUNNING':
            msg_dict[item['name']] = "虚拟机未运行"
        else:
            try:
                dom.domain.shutdownFlags(0)
                status = 0
                msg_dict[item['name']] = "虚拟机关闭中"
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, 0, msg)


@app.route('/domains/destroy', methods=['PUT'])
@login_required
def destroy_domains():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 1
    for item in items:
        dom = None
        for host in hosts:
            dom = host.get_domain_by_uuid(item['uuid'])
            if dom is not None:
                break
        if dom is None:
            msg_dict[item['name']] = "未找到虚拟机"
        elif dom.get_domain_state() == 'SHUTOFF':
            msg_dict[item['name']] = "虚拟机未运行"
        else:
            try:
                dom.domain.destroyFlags(0)
                status = 0
                msg_dict[item['name']] = "虚拟机已强制关闭"
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, 0, msg)


@app.route('/domains/undefine', methods=['PUT'])
@login_required
def undefine_domains():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 1
    for item in items:
        dom = None
        uuid = item['uuid']
        for host in hosts:
            dom = host.get_domain_by_uuid(item['uuid'])
            if dom is not None:
                break
        if dom is None:
            msg_dict[item['name']] = "未找到虚拟机"
            break
        #     msg_dict[item['name']] = "虚拟机未运行"
        else:
            try:
                msg_dict[item['name']] = "虚拟机已删除"
                if dom.get_domain_state() == 'RUNNING':
                    dom.domain.shutdownFlags(0)
                dom.domain.undefineFlags(0)
                host.delete_volume(uuid)
                status = 0
                db_dom = Domain.query.filter_by(uuid=uuid).first()
                db_vol = Volume.query.filter_by(uuid=uuid).first()
                db.session.delete(db_dom)
                db.session.delete(db_vol)
                db.session.commit()
                # db.session.close()

            except libvirtError as e:
                msg_dict[item['name']] = repr(e)

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, 0, msg)


@app.route('/cdromlist', methods=['GET'])
@login_required
def get_cdrom():
    rt = {}
    temp = []
    tc = Cdrom.query.all()

    for t in tc:
        temp.append({
            'label': t.name,
            'value': t.id
        })

    rt['options'] = temp

    return r(rt)


@app.route('/imagelistname', methods=['GET'])
@login_required
def get_image_name():
    rt = {}
    temp = []
    tc = Image.query.all()

    for t in tc:
        temp.append({
            'label': t.name,
            'value': t.uuid
        })

    rt['options'] = temp

    return r(rt)


@app.route('/imagelist', methods=['GET'])
@login_required
def get_image():
    rt = {}
    temp = []
    count = 0
    tc = Image.query.all()

    for t in tc:
        count += 1
        temp.append({
            'uuid': t.uuid,
            'name': t.name,
            'title': t.title
        })

    rt['count'] = count
    rt['items'] = temp

    return r(rt)


@app.route('/image/undefine/<string:uuid>', methods=['PUT'])
@login_required
def delete_image(uuid):
    data = request.json
    hosts = conn_hosts(host_list)
    status = 1
    msg = ''
    uuid = data['uuid']
    # return r({}, 1, 'uuid: <{}> {}'.format(type(uuid), uuid))
    for host in hosts:
        vol = host.get_volume(uuid)
        # dom = host.get_domain_by_name(data['name'])
        if vol is not None:
            break
    if vol is None:
        msg = "未找到模板"
    # elif dom.get_domain_state() != 'RUNNING':
    #     msg = "虚拟机未运行"
    else:
        # libvirt.virStorageVol.name()
        # return r({}, 1, vol.name())
        try:
            msg = "模板已删除"
            vol.delete(0)
            status = 0

            db_img = Image.query.filter_by(uuid=uuid).first()
            db_vol = Volume.query.filter_by(uuid=uuid).first()
            db.session.delete(db_img)
            db.session.delete(db_vol)
            db.session.commit()
            # db.session.close()
        except libvirtError as e:
            status, msg = 1, repr(e)

    close_hosts(hosts)
    return r({}, status, msg)


@app.route('/images/undefine', methods=['PUT'])
@login_required
def delete_images():
    data = request.json
    items = data['items']
    hosts = conn_hosts(host_list)
    msg_dict = {}
    msg = ''
    status = 0
    for item in items:
        this_status = 1
        uuid = item['uuid']
        for host in hosts:
            vol = host.get_volume(uuid)
            if vol is not None:
                break
        if vol is None:
            msg_dict[item['name']] = "未找到模板"
        else:
            try:
                vol.delete(0)
                this_status = 0
                msg_dict[item['name']] = "模板已删除"

                db_img = Image.query.filter_by(uuid=uuid).first()
                db_vol = Volume.query.filter_by(uuid=uuid).first()
                db.session.delete(db_img)
                db.session.delete(db_vol)
                db.session.commit()
            except libvirtError as e:
                msg_dict[item['name']] = repr(e)

        if this_status != 0:
            status = 1

    close_hosts(hosts)
    for key in msg_dict:
        msg = '{}\n{}: {}'.format(msg, key, msg_dict[key])

    return r({}, status, msg)



@app.route('/networklist', methods=['GET'])
@login_required
def get_networks():
    rt = {}
    temp = []
    count = 0

    hosts = conn_hosts(host_list)
    for host in hosts:
        networks = host.conn.listAllNetworks()
        hostname = host.get_hostname()
        for n in networks:
            count += 1
            status = "运行" if n.isActive() == 1 else "关闭"
            temp.append({
                'name': n.name(),
                'uuid': n.UUIDString(),
                'bridge': n.bridgeName(),
                'state': status,
                'host': hostname
            })
    close_hosts(hosts)

    rt['count'] = count
    rt['items'] = temp

    return r(rt)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('domain'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('domain')
        return redirect(next_page)
    return render_template('login.html', title="Sign In", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # db.session.close()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title="Register", form=form)
