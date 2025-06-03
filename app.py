from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///event_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    desc = db.Column(db.String(200))
    image = db.Column(db.String(100))
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    location = db.Column(db.String(100))
    price = db.Column(db.String(20))
    full_desc = db.Column(db.Text)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    ticket_type = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    payment_status = db.Column(db.String(20), default="Pending")
    event = db.relationship('Event', backref='bookings')

# --- Login Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return "User already exists!"
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Protected User Routes ---
@app.route('/')
@login_required
def home():
    events = Event.query.limit(3).all()
    return render_template('index.html', events=events)

@app.route('/events')
@login_required
def events():
    query = request.args.get('q')
    
    if query:
        events = Event.query.filter(
            db.or_(
                Event.title.ilike(f'%{query}%'),
                Event.category.ilike(f'%{query}%'),
                Event.desc.ilike(f'%{query}%'),
                Event.full_desc.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%')
            )
        ).all()
    else:
        events = Event.query.all()
    
    return render_template('events.html', events=events, category=query)


@app.route('/event')
@login_required
def event_detail():
    title = request.args.get('event')
    event = Event.query.filter_by(title=title).first()
    return render_template('event.html', event=event)

@app.route('/book')
@login_required
def booking():
    return render_template('booking.html')

@app.route('/success', methods=['POST'])
@login_required
def success():
    name = request.form.get('name')
    email = request.form.get('email')
    ticket = request.form.get('ticket')
    event_id = request.form.get('event_id')
    booking = Booking(event_id=event_id, name=name, email=email, ticket_type=ticket)
    db.session.add(booking)
    db.session.commit()
    return render_template('success.html', ticket=ticket, name=name, email=email, booking_id=booking.id)

@app.route('/pay/<int:booking_id>')
@login_required
def pay(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.payment_status = "Paid"
    db.session.commit()
    return render_template('payment_success.html', booking=booking)

# --- Admin Routes ---

@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        new_event = Event(
            title=request.form['title'],
            category=request.form['category'],
            desc=request.form['desc'],
            image=request.form['image'],
            date=request.form['date'],
            time=request.form['time'],
            location=request.form['location'],
            price=request.form['price'],
            full_desc=request.form['full_desc']
        )
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    events = Event.query.all()
    return render_template('admin_dashboard.html', events=events)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    password = request.args.get('password')
    if password != 'admin123':
        return "<h3>Unauthorized. Add ?password=admin123 to access.</h3>"

    if request.method == 'POST':
        new_event = Event(
            title=request.form['title'],
            category=request.form['category'],
            desc=request.form['desc'],
            image=request.form['image'],
            date=request.form['date'],
            time=request.form['time'],
            location=request.form['location'],
            price=request.form['price'],
            full_desc=request.form['full_desc']
        )
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('admin', password=password))

    events = Event.query.all()
    return render_template('admin.html', events=events, password=password)

@app.route('/delete/<int:event_id>')
def delete_event(event_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/init')
def init_data():
    if Event.query.count() == 0:
        sample_events = [
            Event(title='Sydney Music Festival', category='Music', desc='Live performances by Aussie bands',
                  image='event1.jpg', date='July 10, 2025', time='6:00 PM',
                  location='Sydney Opera House', price='$30',
                  full_desc='Experience the best of Australian indie and rock music.'),

            Event(title='Melbourne Art Showcase', category='Art', desc='Contemporary Australian art',
                  image='event2.jpg', date='August 2, 2025', time='11:00 AM – 6:00 PM',
                  location='National Gallery of Victoria', price='Free',
                  full_desc='Explore works by top Australian modern artists.'),

            Event(title='Brisbane Startup Summit', category='Business', desc='Tech and entrepreneurship in Australia',
                  image='event3.jpg', date='August 15, 2025', time='9:00 AM – 4:00 PM',
                  location='Brisbane Convention Centre', price='$45',
                  full_desc='Network with founders, VCs, and tech leaders from across Australia.'),

            Event(title='Gold Coast Food Fiesta', category='Lifestyle', desc='Australia’s top street food festival',
                  image='event4.jpg', date='September 5, 2025', time='12:00 PM – 10:00 PM',
                  location='Surfers Paradise', price='$20',
                  full_desc='Sample local favorites, seafood, and multicultural Aussie dishes.'),

            Event(title='Adelaide Literature Festival', category='Education', desc='Readings by Aussie authors',
                  image='event5.jpg', date='October 12, 2025', time='10:00 AM – 5:00 PM',
                  location='Adelaide Writers’ Centre', price='Free',
                  full_desc='Join talks, readings, and workshops with Australia’s finest writers.'),

            Event(title='Canberra Wellness Retreat', category='Health', desc='Yoga, meditation, and healing sessions',
                  image='event6.jpg', date='October 28, 2025', time='7:00 AM – 5:00 PM',
                  location='Tidbinbilla Nature Reserve', price='$25',
                  full_desc='Recharge your mind and body in the heart of Australia’s capital.'),

            Event(title='Perth Coding Bootcamp', category='Education', desc='Learn Python, HTML, and Flask',
                  image='event7.jpg', date='November 15, 2025', time='9:00 AM – 3:00 PM',
                  location='University of Western Australia', price='$35',
                  full_desc='Hands-on web development crash course for beginners.'),

            Event(title='Darwin Wildlife Photography Walk', category='Workshops', desc='Capture NT’s rich wildlife',
                  image='event8.jpg', date='December 3, 2025', time='6:00 AM – 10:00 AM',
                  location='Charles Darwin National Park', price='$15',
                  full_desc='Photography enthusiasts explore unique Northern Territory wildlife.'),

            Event(title='Tasmania Eco Adventure', category='Entertainment', desc='Outdoor trek and nature games',
                  image='event9.jpg', date='January 18, 2026', time='8:00 AM – 6:00 PM',
                  location='Freycinet National Park', price='$40',
                  full_desc='Enjoy guided bushwalks, kayaking, and eco-learning in Tasmania.'),

            Event(title='Sydney Esports Arena', category='Gaming', desc='Nationwide esports tournament finals',
                  image='event10.jpg', date='February 5, 2026', time='1:00 PM – 9:00 PM',
                  location='Qudos Bank Arena, Sydney', price='$50',
                  full_desc='Top Australian gamers face off in Valorant, FIFA, and CS:GO finals.')
        ]
        db.session.add_all(sample_events)
        db.session.commit()
        return "✅ 10 sample events added."
    return "⚠️ Events already exist."

@app.route('/init_bookings')
def init_bookings():
    from datetime import datetime
    import random

    if Booking.query.count() >= 50:
        return "⚠️ At least 50 bookings already exist."

    users = User.query.all()
    events = Event.query.all()

    if not users or not events:
        return "❌ Add users and events before creating bookings."

    ticket_types = ['General', 'VIP']
    current_count = Booking.query.count()
    remaining = 50 - current_count

    for i in range(remaining):
        user = random.choice(users)
        event = random.choice(events)
        ticket_type = random.choice(ticket_types)

        booking = Booking(
            name=user.name,
            email=user.email,
            event_id=event.id,
            ticket_type=ticket_type,
            timestamp=datetime.now(),
            payment_status="Confirmed"
        )
        db.session.add(booking)

    db.session.commit()
    return f"✅ {remaining} bookings added. Total now: {Booking.query.count()}"

#app-route
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return "Invalid credentials"
    return render_template('admin_login.html')

@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if Admin.query.filter_by(username=username).first():
            return "Admin already exists"
        admin = Admin(username=username, password=password)
        db.session.add(admin)
        db.session.commit()
        return redirect(url_for('admin_login'))
    return render_template('admin_register.html')

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/events')
def admin_events():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    events = Event.query.all()
    return render_template('admin_events.html', events=events)

@app.route('/admin/events/delete/<int:event_id>')
def admin_delete_event(event_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('admin_events'))

@app.route('/admin/bookings')
def admin_bookings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    event_id = request.args.get('event_id')
    events = Event.query.all()
    bookings = Booking.query.filter_by(event_id=event_id).all() if event_id else Booking.query.all()
    return render_template('admin_bookings.html', bookings=bookings, events=events, selected_event=event_id)


@app.route('/admin/reports')
def admin_reports():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    events = Event.query.all()
    report_data = []

    total_bookings_all = 0
    total_revenue_all = 0

    for event in events:
        bookings = event.bookings
        total_bookings = len(bookings)
        revenue = 0
        ticket_counts = {'General': 0, 'VIP': 0, 'Free': 0}
        for b in bookings:
            if b.ticket_type == 'General':
                revenue += 20
                ticket_counts['General'] += 1
            elif b.ticket_type == 'VIP':
                revenue += 50
                ticket_counts['VIP'] += 1
            elif b.ticket_type == 'Free':
                ticket_counts['Free'] += 1

        total_bookings_all += total_bookings
        total_revenue_all += revenue

        report_data.append({
            'title': event.title,
            'bookings': total_bookings,
            'revenue': revenue,
            'ticket_counts': ticket_counts
        })

    return render_template(
        'admin_reports.html',
        report_data=report_data,
        total_bookings_all=total_bookings_all,
        total_revenue_all=total_revenue_all
    )


# --- Run ---
if __name__ == '__main__':
    app.run(debug=True)
