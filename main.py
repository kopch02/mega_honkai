from flask import Flask, url_for, render_template, redirect, send_from_directory, abort, session, request, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from data.user import User
from forms.jump_history import Jump_History_Form
import asyncio
from honkaistarrail import starrail

class Myclass():
    pass

JUMPS = ['jumps_event','jumps_weapon','jumps_standart']
name_jumps_ru = ["Ивентовый баннер","Оружейный баннер","Стандартный баннер"]


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
    db_session.global_init("db/test.db")
    app.run()

@app.route('/')
@app.route('/index')
def index():
    param = {}
    tables = []
    for i, jump_name in enumerate(JUMPS):
        jumps = session.get(jump_name, [])
        table = Myclass()
        table.name = name_jumps_ru[i]
        table.count = len(jumps)
        table.garant_5 = 100
        table.garant_4 = 100
        tables.append(table)
    param['tables'] = tables
    return render_template('index.html', **param)


async def get_jump_history(link, jumps, banner_num):
    async with starrail.Jump(link = link,banner = banner_num,lang = "ru") as hist:
        async for key in hist.get_history():
            for item in key:
                pass
                jump = {'id':item.id,
                        'item_name':item.name,
                        'rarity':item.rank,
                        'type_loot':item.type,
                        'time':item.time.strftime("%d.%m.%Y %H:%M:%S")}
                jumps.append(jump)

@app.route('/import_jump', methods=['GET', 'POST'])
def import_jump():
    db_sess = db_session.create_session()
    form = Jump_History_Form()
    if form.validate_on_submit():
        link = form.url_history.data
        for i, jumps_name in enumerate(JUMPS):
            jumps = session.get(jumps_name, [])
            asyncio.run(get_jump_history(link,jumps, 2))
            session[jumps_name] = jumps
        return redirect('/')
    return render_template('import.html', form = form)


@app.route('/history', methods=['GET', 'POST'])
def history():
    db_sess = db_session.create_session()
    user = db_sess.query(User).all()
    return render_template('history.html', users = user)


@app.route('/add_jump', methods=['POST'])
def add_jump():
    link = request.get_json()
    for i, jumps in enumerate(JUMPS):
        jumps = session.get(jumps, [])
        asyncio.run(get_jump_history(link,jumps, i))
        session[jumps] = jumps
    return jsonify(success=True)

@app.route('/get_jumps', methods=['GET'])
def get_jumps():
    return jsonify(jumps=session.get('jumps', []))

@app.route('/clear_jumps', methods=['DELETE'])
def clear_jumps():
    for jumps in JUMPS:
        session.pop(jumps, None)
    #session.pop("jumps", None)
    return jsonify(success=True)

if __name__ == '__main__':
    main()