"""数据库"""
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    """user表"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    dom_count = db.Column(db.Integer, nullable=False)
    dom_owned_count = db.Column(db.Integer, nullable=False)
    domain = db.relationship('Domain', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password: str):
        """设置用户密码，以Hash码保存

        :param password: 用户密码
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """判断密码是否正确

        :param password: 输入密码
        :return: 密码是否正确
        """
        return check_password_hash(self.password_hash, password)

    def set_dom_count(self, count=2):
        """设置用户最大虚拟机创建数量

        :param count: 该用户最大虚拟机创建数量，默认为2
        """
        if self.username == 'admin':
            self.dom_count = -1
        else:
            self.dom_count = count
        self.dom_owned_count = 0

    def check_dom_creatable(self, count: int) -> bool:
        """判断用户是否可以新建虚拟机

        :param count: 要创建的虚拟机数量
        :return: 是否可以新建虚拟机
        """
        creatable = False
        if self.dom_count == -1:
            creatable = True
        elif self.dom_count-self.dom_owned_count >= count:
            creatable =  True
        return creatable

    def increase_owned_dom_count(self, num=1):
        """增加用户已拥有虚拟机数量

        :param num: 减少数量
        """
        self.dom_owned_count += num

    def reduce_owned_dom_count(self, num=-1):
        """减少用户已拥有虚拟机数量

        :param num: 减少数量
        """
        self.dom_owned_count += num


class Domain(db.Model):
    __tablename__ = 'domain'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    memory = db.Column(db.Integer, nullable=False)
    vcpu = db.Column(db.Integer, nullable=False)
    host = db.Column(db.String(32), index=True)
    graphic = db.Column(db.String(128))
    port = db.Column(db.Integer)
    title = db.Column(db.String(200))
    description = db.Column(db.String(256))
    volume_uuid = db.Column(db.String(36), db.ForeignKey('volume.uuid', ondelete='SET NULL'))
    cdrom_id = db.Column(db.Integer, db.ForeignKey('cdrom.id', ondelete='SET NULL'))
    image_uuid = db.Column(db.String(36), db.ForeignKey('image.uuid', ondelete='SET NULL'))
    owner = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    # gen_image = db.Column(db.String(36), db.ForeignKey('image.uuid', ondelete='SET NULL'))

    def __repr__(self):
        return '<Domain {}>'.format(self.name)

    def set_gen_image(self, image_uuid):
        self.image_uuid = image_uuid


class Volume(db.Model):
    """volume表"""
    __tablename__ = 'volume'
    uuid = db.Column(db.String(36), primary_key=True)
    size = db.Column(db.Integer, index=True)
    domain = db.relationship('Domain', backref='volume', lazy='dynamic')
    image = db.relationship('Image', backref='volume', lazy='dynamic')

    def __repr__(self):
        return '<Volume {}>'.format(self.uuid)


class Cdrom(db.Model):
    """cdrom表"""
    __tablename__ = 'cdrom'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    url = db.Column(db.String(120), index=True, unique=True)
    title = db.Column(db.String(200))
    domains = db.relationship('Domain', backref='cdrom', lazy='dynamic')
    images = db.relationship('Image', backref='cdrom', lazy='dynamic')

    def __repr__(self):
        return '<CDROM {}>'.format(self.name)


class Image(db.Model):
    """image表"""
    __tablename__ = 'image'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    title = db.Column(db.String(200))
    volume_uuid = db.Column(db.String(36), db.ForeignKey('volume.uuid', ondelete='SET NULL'))
    cdrom_id = db.Column(db.Integer, db.ForeignKey('cdrom.id', ondelete='SET NULL'))
    domains = db.relationship('Domain', backref='image', lazy='dynamic')

    def __repr__(self):
        return '<Image {}>'.format(self.name)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
