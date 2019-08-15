# coding=utf-8
import functools
import json
import time
import os
import base64
import config

# 解决工程字符集，中文显示异常问题
import sys

reload(sys)
sys.setdefaultencoding('utf8')

from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# 加密的密匙
app.config["SECRET_KEY"] = "saflhsalghalshglahsg"

# 上传文件的文件夹访问权限和路径配置
UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
basedir = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = {'txt', 'png', 'jpg', 'xls', 'JPG', 'PNG', 'xlsx', 'gif', 'GIF'}

# 导入数据库配置类
app.config.from_object(config)
# 获得连接对象
db = SQLAlchemy(app)


# 加载对应的数据库模型类
# 数据库模型类
class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    pwd = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(50), nullable=False)

    def __init__(self, **kwargs):
        name = kwargs.get('username')
        pwd = kwargs.get('password')
        email = kwargs.get('email')

        self.name = name
        # 将传入的密码加密
        self.pwd = generate_password_hash(pwd)
        self.email = email

    # 校验请求的密码
    def check_password(self, input_passowd):
        result = check_password_hash(self.pwd, input_passowd)
        return result

    # 重写类的魔方方法，使得输出直观
    def __repr__(self):
        return 'User id=%s name=%s pwd=%s email=%s' % (self.id, self.name, self.pwd, self.email)


# 存储文件Url的模型类
class FileUpload(db.Model):
    __tablename__ = 'upload_file'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=False, unique=False)
    filename = db.Column(db.String(50), nullable=False, unique=True)
    filename_md5 = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return 'FileUpload---id=%s---name=%s---filename=%s---filename_md5=%s' % (
            self.id, self.name, self.filename, self.filename_md5)


# 用户验证用户登录状态的装饰器
def login_required(func):
    @functools.wraps(func)  # 修饰内层函数，防止当前装饰器去修改被装饰函数的属性
    def inner(*args, **kwargs):
        # 从session获取用户信息，如果有，则用户已登录，否则没有登录
        user_id = session.get('user_id')
        print("session user_id-->:", user_id)
        if not user_id:
            # WITHOUT_LOGIN是一个常量
            # return jsonify(errcode=404,err=u"you have not login yet")
            return redirect(url_for('login'))
        else:
            # 已经登录的话 g变量保存用户信息，相当于flask程序的全局变量
            # g.user_id = user_id
            return func(*args, **kwargs)

    return inner


# 路由方法,上传界面需要授权
@app.route('/index', methods=['GET', 'POST'])
@app.route('/')
@login_required
def index():
    # 登录成功后从session中获取user_id,用户查询对应的用户数据
    user_id = session.get('user_id')
    print("index session user_id-->:", user_id)

    # 登录成功获取user_id
    if user_id:
        user = User.query.filter_by(id=user_id).first()
        print ("index2 session user_id-->:", user_id)
        return render_template('upload.html', user=user)


# 登录验证，如果成功授权一个session
@app.route('/login', methods=['GET', 'POST'])
def login():
    # 这个语句是临时用于创立表的
    # db.drop_all()
    # db.create_all()

    if request.method == 'GET':
        print "get request"
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(name=username).first()

        if user and user.check_password(password):
            # 返回一个session
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return render_template('login.html', errot_info="账号或密码错误！")


# 实现注销当前账号的功能
@app.route('/logout')
def logout():
    # 将session中的user_id字段移除
    session.pop('user_id', None)
    return redirect(url_for('login'))


# 注册模块路由，后面需要拆分成蓝图注册模式
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':

        success_color = "#4DB3B3"
        fail_color = "#b21f2d"

        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        print "register-->" + username

        if not all([username, password, email]):
            return render_template('register.html', info=u"参数不能为空", color=fail_color)
        else:
            # 构造方法中进行加密，所以在 new 对象的时候传入对应的参数
            user = User(username=username, password=password, email=email)
            try:
                # 数据库操作要捕获 异常并回滚数据
                # print "register--->"+user.pwd
                db.session.add(user)
                db.session.commit()

            except Exception as e:
                # 这里应该置换成日志框架
                print e
                # 事务提交异常则回滚操作
                db.session.rollback()
                return render_template('register.html', info=u"注册失败，请稍后重试", color=fail_color)
            # 如果成功则提示信息，不提供重定向
            return render_template('register.html', info=u"注册成功，点击下方登录传送门", color=success_color)


# 处理验证注册用户名的ajax请求
@app.route('/register/verification', methods=['GET', 'POST'])
def username_verification():
    if request.method == 'POST':
        username = request.form['username']

        print "/register/verification---->" + username

        username_local = ""

        if username != "":
            try:
                username_local = User.query.filter_by(name=username).first()

                # print "query result--->" + username_local
            except Exception as e:
                print e
                return "<span style='visibility:visible;color: #A7181E'>服务器异常</span>"

            # 避免空对象异常
            if username_local:
                if username_local.name != "" and username_local.name == username:
                    # 根据查询结果 设置内容和颜色
                    return "<span style='visibility:visible;color: #A7181E'>用户名已存在</span>"
                else:
                    return "<span style='visibility:visible;color: #28a745'>用户名可用</span>"
            else:
                return "<span style='visibility:visible;color: #28a745'>用户名可用</span>"


# 处理验证该文件是否已经存在
@app.route('/upload/verification', methods=['GET', 'POST'])
def upload_file_verification():
    if request.method == 'GET':
        return redirect('index')
    else:
        name = request.form['name']
        filename = request.form['filename']
        filename_md5 = request.form['filename_md5']

        print "校验1：本地的文件的MD5--->" + filename_md5

        print "upload-->" + name + "----" + filename + "----" + filename_md5

        if not all([name, filename, filename_md5]):
            return "<span style='visibility:visible;color: #A7181E'>检验MD5过程出错了...</span>"
        else:
            local_file = FileUpload.query.filter_by(filename_md5=filename_md5).first()
            if local_file:
                if local_file.filename_md5 == filename_md5:
                    return "<span style='visibility:visible;color: #A7181E'>文件已存在</span>"
            else:
                return "<span style='visibility:visible;color: #28a745'>文件可上传</span>"


# 点击上传列表选项时重定向到index,目前index就是上传的页面
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return redirect('index')
    else:
        name = request.form['name']
        filename = request.form['filename']
        filename_md5 = request.form['filename_md5']

        print "校验2：-->" + name + "----" + filename + "----" + filename_md5

        if not all([name, filename, filename_md5]):
            result = {"status code": 100, "save_flag": False, "message": "提交数据不完整,无法上传"}
            return jsonify(result)
        else:
            local_file = FileUpload.query.filter_by(filename_md5=filename_md5).first()
            if local_file:
                if local_file.filename_md5 == filename_md5:
                    result = {"status code": 101, "save_flag": False, "message": "文件已存在,无法上传"}
                    return jsonify(result)
            else:
                file_add = FileUpload()
                file_add.name = name
                file_add.filename = filename
                file_add.filename_md5 = filename_md5

                try:
                    db.session.add(file_add)
                    db.session.commit()
                except Exception as e:
                    print e
                    # 事务提交异常则回滚操作
                    db.session.rollback()
                    result = {"status code": 102, "save_flag": True, "message": "存储信息出错,无法上传，已回滚数据"}
                    return jsonify(result)

                result = {"status code": 200, "save_flag": True, "message": "文件提交中..."}
                return jsonify(result)


# 用于判断文件后缀，是否是允许的范围
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# 上传文件到服务器
@app.route('/upload/file', methods=['POST'], strict_slashes=False)
def api_upload():
    # 获取存储的文件夹
    file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    # 从表单的file字段获取文件，file_upload为该表单的name值
    f = request.files['file_upload']

    fname = f.filename

    print 'fname=' + fname
    print 'file_dir=' + file_dir

    # 获取当前时间戳
    unix_time = int(time.time())

    # 获取当前的用户
    user_id = session['user_id']
    user = User.query.filter_by(id=user_id).first()

    # 修改了上传的文件名
    new_filename = user.name + '---' + str(unix_time) + '---' + str(fname)

    # 保存文件到upload目录
    try:
        f.save(os.path.join(file_dir, new_filename))
    except Exception as e:
        print e
        return jsonify({"status_code": 1001, "message": "上传失败:存储文件失败", "token": ""})

    # 生成文件的令牌
    # token = base64.b64encode(new_filename)
    # print token

    result = {"status_code": 2000, "message": "文件上传成功", "token": ""}

    return jsonify(result)


# 下载相应的文件到浏览器本地
@app.route('/api_download/<filename>', methods=['GET'])
def download(filename):
    if request.method == "GET":
        if os.path.isfile(os.path.join('upload_dir', filename)):
            # print "下载文件路径---->" + os.path.join('upload_dir', filename)
            return send_from_directory('upload_dir', filename, as_attachment=True)
        abort(404)


# 筛选集合
ALLOWED_EXTENSIONS = {'png', 'jpg', 'PNG', 'gif', 'GIF'}


# 用于判断文件后缀
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# 获取所有图片的文件名
@app.route('/api_query/img', methods=['GET'])
def api_query_all():
    result = []
    # dir = 'F:/flask_pros/env_test/upload_dir'
    dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
    print dir
    image_list = get_all_filename(dir)
    for image_file in image_list:
        if allowed_file(image_file):
            result.append(image_file)
    return jsonify({"image_list": result})


# 遍历文件夹下的所有文件名字
def get_all_filename(file_dir):
    global utf8_file
    filename_list = []
    for s_file in os.listdir(file_dir):
        u_file = s_file.decode('gbk')
        utf8_file = u_file.encode('utf-8')
        filename_list.append(utf8_file)
    # print "输出文件名；---->"
    # print filename_list[6]
    return filename_list


if __name__ == '__main__':
    app.run()
