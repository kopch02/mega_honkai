from flask import Flask, url_for, render_template, redirect, send_from_directory, abort, session, request, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from sqlalchemy import func, select
from data.users import User
from data.items import Item
from data.jumps_weapon import Jump_weapon
from data.jumps_event import Jump_event
from data.jumps_standart import Jump_standart
from forms.jump_history import Jump_History_Form
from forms.user import RegisterForm, LoginForm
from password_test import passworld_check, PasswordError
import asyncio
from honkaistarrail import starrail

class Myclass():
    pass

JUMPS = ['jumps_event','jumps_weapon','jumps_standart']
name_jumps_ru = ["Ивентовый баннер","Оружейный баннер","Стандартный баннер"]
jump_tables = [Jump_event,Jump_weapon,Jump_standart]


application = Flask(__name__)
application.config['SECRET_KEY'] = 'my_secret_key'
application.config['MAX_COOKIE_SIZE'] = 1024 * 5
login_manager = LoginManager()
login_manager.init_app(application)
db_session.global_init()

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

def main():
    application.run(host='0.0.0.0')

@application.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@application.route('/')
@application.route('/index')
def index():
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        param = {}
        tables = []
        all_jumps = user.count_all_jumps.split(';')
        garant_5 = user.count_garant_5.split(';')
        garant_4 = user.count_garant_4.split(';')
        for i, jump_name in enumerate(JUMPS):

            table = Myclass()
            table.name = name_jumps_ru[i]
            table.count = all_jumps[i]
            table.garant_5 = garant_5[i]
            table.garant_4 = garant_4[i]
            tables.append(table)
        param['tables'] = tables
        #count_garant()
        return render_template('index.html', **param)
    else:
        return render_template('authorization.html')


async def get_jump_history(link, db_table, banner_num):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == current_user.id).first()
    count_all_jump = 0
    garant5 = list(map(int,[i for i in user.count_garant_5.split(';')]))
    garant4 = list(map(int,[i for i in user.count_garant_4.split(';')]))
    temp = list(map(int,[i for i in user.count_all_jumps.split(';')]))
    count_all_jumps = list(map(int,[i for i in user.count_all_jumps.split(';')]))
    num_jump = db_sess.query(func.max(jump_tables[banner_num - 1].num_jump)).\
        filter(jump_tables[banner_num - 1].user_id == current_user.id).scalar() or 0
    last_jump = db_sess.query(jump_tables[banner_num - 1]).first()
    mark = False
    async with starrail.Jump(link = link,banner = banner_num,lang = "ru") as hist:
        async for key in hist.get_history():
            for item in key:
                if item.time == last_jump.item_time:
                    mark = True
                    break
                if not(db_sess.query(Item).filter(Item.id == item.id).first()):
                    new_item = Item()
                    new_item.id = item.id
                    new_item.name = item.name
                    new_item.rank = item.rank
                    new_item.type = item.type
                    db_sess.add(new_item)
                num_jump += 1
                jump = db_table(user_id = current_user.id, 
                                item_id = item.id, 
                                item_time = item.time,
                                num_jump = num_jump)
                db_sess.add(jump)
            if mark:
                break
            count_all_jump += len(key)
    temp[banner_num - 1] = count_all_jumps[banner_num - 1] + count_all_jump
    user.count_all_jumps = conver_array_to_str(temp)
    db_sess.commit()
    garant5[banner_num - 1],garant4[banner_num - 1] = count_garant(jump_tables[banner_num - 1], db_sess)
    user.count_garant_5 = conver_array_to_str(garant5)
    user.count_garant_4 = conver_array_to_str(garant4)
    db_sess.commit()


def conver_array_to_str(arr):
    return';'.join(list(map(str,arr)))


def count_garant(banner,db_sess):
    num_jump = db_sess.query(func.max(banner.num_jump)).filter(banner.user_id == current_user.id).scalar() or 0
    last_5 = db_sess.query(banner.num_jump).\
        join(Item, banner.item_id == Item.id).\
        filter(Item.rank == 5).\
        filter(banner.user_id == current_user.id).\
        order_by(banner.id.asc()).first()[0]
    last_4 = db_sess.query(banner.num_jump).\
        join(Item, banner.item_id == Item.id).\
        filter(Item.rank == 4).\
        filter(banner.user_id == current_user.id).\
        order_by(banner.id.asc()).first()[0]
    return last_5 - 1, last_4 - 1

'''
select num_jump from jumps_event, items
where items.rank = 5 and jumps_event.item_id = items.id
'''

@application.route('/import_jump', methods=['GET', 'POST'])
@login_required
def import_jump():
    form = Jump_History_Form()
    if form.validate_on_submit():
        link = form.url_history.data
        for i in range(3):
            asyncio.run(get_jump_history(link,jump_tables[i], i+1))
        return redirect('/')
    return render_template('import.html', form = form)


@application.route('/history', methods=['GET', 'POST'])
@login_required
def history():
    db_sess = db_session.create_session()
    user = db_sess.query(User).all()
    return render_template('history.html', users = user)


@application.route('/register', methods = ['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_re.data:
            return render_template('register.html',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html',
                                   form=form,
                                   message="Такой пользователь уже есть")
        passworld = form.password.data
        try:
            passworld_check(passworld)
        except PasswordError as e:
            return render_template('register.html',
                                   form=form,
                                   message=str(e))
        new_user = User()
        new_user.name = form.name.data 
        new_user.email = form.email.data
        new_user.count_all_jumps = '0;0;0'
        new_user.count_garant_5 = '0;0;0'
        new_user.count_garant_4 = '0;0;0'
        if passworld != None:
            new_user.set_password(passworld)
        db_sess.add(new_user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', form = form)


@application.route('/login', methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(
            User.email == form.email.data).first()
        if not (user):
            return render_template('login.html',
                                    form=form,
                                    message="Пользователь с такой почтой не найден")
        if not (user.check_password(form.password.data)):
            return render_template('login.html',
                                   form=form,
                                   message="Не правильный пароль")
        login_user(user, remember=form.remember_me.data)
        return redirect('/')
    return render_template("login.html", form = form)
if __name__ == '__main__':
    main()
