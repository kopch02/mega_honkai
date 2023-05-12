from flask import Flask, url_for, render_template, redirect, send_from_directory, abort, session, request, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from sqlalchemy import func
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


app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['MAX_COOKIE_SIZE'] = 1024 * 5
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

def main():
    db_session.global_init()
    app.run()

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        param = {}
        tables = []
        for i, jump_name in enumerate(JUMPS):

            table = Myclass()
            table.name = name_jumps_ru[i]
            table.count = user.count_all_jumps[i]
            table.garant_5 = user.count_garant_5[i]
            table.garant_4 = user.count_garant_4[i]
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
    temp = [i for i in user.count_all_jumps]
    num_jump = db_sess.query(func.max(jump_tables[banner_num - 1].num_jump)).filter(jump_tables[banner_num - 1].user_id == current_user.id).scalar() or 0
    async with starrail.Jump(link = link,banner = banner_num,lang = "ru") as hist:
        async for key in hist.get_history():
            for item in key:
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
            count_all_jump += len(key)
    temp[banner_num - 1] = user.count_all_jumps[banner_num - 1] + count_all_jump
    user.count_all_jumps = temp
    db_sess.commit()
    


def count_garant():
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(current_user.id)
    
    last_rank_4_jump = None
    last_rank_5_jump = None
    
    all_jumps = db_sess.query(Jump_event).filter(Jump_event.user_id==current_user.id).order_by(Jump_event.item_time.asc()).all()
    for aj in all_jumps:
        aj_item = db_sess.query(Item).get(aj.item_id)
        if aj_item.rank == 4:
            last_rank_4_jump = aj.id
        elif aj_item.rank == 5:
            last_rank_5_jump = aj.id
    
    if last_rank_5_jump:
        rank_5_delta = len(all_jumps) - (db_sess.query(Jump_event).filter(Jump_event.id <= last_rank_5_jump).count())
        user.last_rank_5_jump = last_rank_5_jump
    else:
        rank_5_delta = None
        
    db_sess.commit()
    
    response = {'rank_5_delta': rank_5_delta}
    return jsonify(response)
    


@app.route('/import_jump', methods=['GET', 'POST'])
@login_required
def import_jump():
    form = Jump_History_Form()
    if form.validate_on_submit():
        link = form.url_history.data
        for i in range(3):
            asyncio.run(get_jump_history(link,jump_tables[i], i+1))
        return redirect('/')
    return render_template('import.html', form = form)


@app.route('/history', methods=['GET', 'POST'])
@login_required
def history():
    db_sess = db_session.create_session()
    user = db_sess.query(User).all()
    return render_template('history.html', users = user)


@app.route('/register', methods = ['GET','POST'])
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
        new_user.count_all_jumps = [0,0,0]
        new_user.count_garant_5 = [0,0,0]
        new_user.count_garant_4 = [0,0,0]
        if passworld != None:
            new_user.set_password(passworld)
        db_sess.add(new_user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', form = form)


@app.route('/login', methods=["GET","POST"])
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
