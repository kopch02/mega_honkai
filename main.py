from flask import Flask, url_for, render_template, redirect, send_from_directory, abort, session, request, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from data.user import User
from forms.jump_history import Jump_History_Form
import asyncio
from honkaistarrail import starrail


async def get_jump_history_link(link):
    async with starrail.Jump(link = link,banner = 1,lang = "ru") as hist:
        async for key in hist.get_history():
            for info in key:
                print(f'[{info.type}] Name: {info.name} ({info.rank}*) - {info.time.strftime("%d.%m.%Y %H:%M:%S")}')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
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
    return render_template('index.html')


async def get_jump_history(link, jumps):
    async with starrail.Jump(link = link,banner = 1,lang = "ru") as hist:
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
        db_sess = db_session.create_session()
        asyncio.run(get_jump_history(link,db_sess))
        
        db_sess.commit()
        return redirect('/history')
    return render_template('import.html', form = form)


@app.route('/history', methods=['GET', 'POST'])
def history():
    db_sess = db_session.create_session()
    user = db_sess.query(User).all()
    return render_template('history.html', users = user)


@app.route('/add_jump', methods=['POST'])
def add_jump():
    link = request.get_json()
    jumps = session.get('jumps', [])
    asyncio.run(get_jump_history(link,jumps))
    session['jumps'] = jumps
    return jsonify(success=True)

@app.route('/get_jumps', methods=['GET'])
def get_jumps():
    return jsonify(jumps=session.get('jumps', []))

@app.route('/clear_jumps', methods=['DELETE'])
def clear_jumps():
    session.pop('jumps', None)
    return jsonify(success=True)

if __name__ == '__main__':
    main()