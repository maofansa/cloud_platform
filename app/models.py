"""
    数据库模块包
"""
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_dom_count(self, count=2):
        if self.username == 'admin':
            self.dom_count = -1
        else:
            self.dom_count = count
        self.dom_owned_count = 0

    def check_dom_creatable(self, count):
        creatable = False
        if self.dom_count == -1:
            creatable = True
        elif self.dom_count-self.dom_owned_count >= count:
            creatable =  True
        return creatable
#
# class Host(db.Model):
#     __tablename__ = 'host'
#     id = db.Colume(db.C)
#     ip = db.Column(db.string(15), prim)

class Domain(db.Model):
    __tablename__ = 'domain'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    memory = db.Column(db.Integer, nullable=False)
    vcpu = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.String(256))
    volume_uuid = db.Column(db.String(36), db.ForeignKey('volume.uuid', ondelete='SET NULL'))
    cdrom_id = db.Column(db.Integer, db.ForeignKey('cdrom.id', ondelete='SET NULL'))
    image_uuid = db.Column(db.String(36), db.ForeignKey('image.uuid', ondelete='SET NULL'))
    owner = db.Column(db.Integer, db.ForeignKey('user.id', onedelete='SET NULL'))

    def __repr__(self):
        return '<Domain {}>'.format(self.name)


class Volume(db.Model):
    __tablename__ = 'volume'
    uuid = db.Column(db.String(36), primary_key=True)
    size = db.Column(db.Integer, index=True)
    domain = db.relationship('Domain', backref='volume', lazy='dynamic')
    image = db.relationship('Image', backref='volume', lazy='dynamic')

    def __repr__(self):
        return '<Volume {}>'.format(self.uuid)


class Cdrom(db.Model):
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
