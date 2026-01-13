from flask import Flask,render_template, redirect, url_for,request,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leave.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

import datetime
from datetime import date, datetime
from datetime import timedelta

def is_overlapping(leave,other_leave):
    return not (leave.end_date < other_leave.start_date or leave.start_date > other_leave.end_date)


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='staff')  # 'staff' or 'manager'
    department = db.Column(db.String(100))
    leave_balance= db.Column(db.Integer, default=21)  # Default leave balance
    active = db.Column(db.Boolean, default=True)

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='Pending')  # 'Pending', 'Approved', 'Rejected'    
    created_at = db.Column(db.Date, default=date.today)
    days= db.Column(db.Integer)
    user = db.relationship('User', backref=db.backref('leave_requests', lazy=True))

#end of models

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def dashboard():
    leaves = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    return render_template('dashboard.html', leaves=leaves)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user=User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            if user.role == 'manager':
                return redirect(url_for('hr_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if request.method == 'POST':
        try:
            # Convert form strings to date objects
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()

            # Validation: end date must be after start date
            if end_date < start_date:
                flash('End date must be after start date.', 'danger')
                return redirect(url_for('apply_leave'))

            # Calculate total leave days
            num_days = (end_date - start_date).days + 1

            # Check leave balance
            if num_days > current_user.leave_balance:
                flash(f"Insufficient leave balance. You have {current_user.leave_balance} days left.", 'danger')
                return redirect(url_for('apply_leave'))

            # Create leave request
            leave = LeaveRequest(
                user_id=current_user.id,
                start_date=start_date,
                end_date=end_date,
                reason=request.form.get('reason'),
                days=num_days
            )

            db.session.add(leave)
            db.session.commit()

            flash(f'Leave request submitted for {num_days} day(s).', 'success')
            return redirect(url_for('dashboard'))

        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('apply_leave'))

    return render_template('apply.html')

@app.route('/hr')
@login_required
def hr_panel():
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    leaves = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id)\
        .add_columns(User.username, LeaveRequest.id, LeaveRequest.start_date, LeaveRequest.end_date, LeaveRequest.status, LeaveRequest.days)\
        .all()
    return render_template('hr.html', leaves=leaves)

@app.route('/approve/<int:id>')
@login_required
def approve(id):
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    leave = LeaveRequest.query.get(id)
    if leave.status != 'Pending':
        flash("This leave request has already been processed.", "warning")
        return redirect(url_for('hr_panel'))
    
    user = User.query.get(leave.user_id)
    user.leave_balance -= leave.days
    leave.status = 'Approved'
    db.session.commit()
    flash('Leave approved')
    return redirect(url_for('hr_panel'))

@app.route('/reject/<int:id>')
@login_required
def reject(id):
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    leave = LeaveRequest.query.get(id)
    if leave.status != 'Pending':
        flash("This leave request has already been processed.", "warning")
        return redirect(url_for('hr_panel'))
    leave.status = 'Rejected'
    db.session.commit()
    flash('Leave rejected')
    return redirect(url_for('hr_panel'))

@app.route('/hr-dashboard')
@login_required
def hr_dashboard():
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    total_requests = LeaveRequest.query.count()
    approved_requests = LeaveRequest.query.filter_by(status='Approved').count()
    rejected_requests = LeaveRequest.query.filter_by(status='Rejected').count()
    pending_requests = LeaveRequest.query.filter_by(status='Pending').count()
    return render_template('hr_dashboard.html', total_requests=total_requests,
                           approved_requests=approved_requests,
                           rejected_requests=rejected_requests,
                           pending_requests=pending_requests)

@app.route('/hr-leave-overview')
@login_required
def hr_leave_overview():
    if current_user.role != 'manager':
        flash("Access denied")
        return redirect(url_for('dashboard'))

    today = date.today()
    selected_department = request.args.get('department')

    base_query = LeaveRequest.query.join(User).filter(
        LeaveRequest.status == 'Approved'
    )

    if selected_department and selected_department != "All":
        base_query = base_query.filter(User.department == selected_department)

    leaves = base_query.order_by(
        User.department,
        LeaveRequest.start_date.asc()
    ).all()

    # Detect overlaps
    overlap_map = {}

    for leave in leaves:
        overlap_map[leave.id] = False
        for other in leaves:
            if leave.id != other.id and leave.user.department == other.user.department:
                if is_overlapping(leave, other):
                    overlap_map[leave.id] = True
                    break

    # Separate current and upcoming
    current_leave = []
    upcoming_leave = []

    for leave in leaves:
        if leave.start_date <= today <= leave.end_date:
            current_leave.append(leave)
        elif leave.start_date > today:
            upcoming_leave.append(leave)

    return render_template(
        'hr_leave_overview.html',
        current_leave=current_leave,
        upcoming_leave=upcoming_leave,
        departments=[d[0] for d in db.session.query(User.department).distinct()],
        selected_department=selected_department or "All",
        overlap_map=overlap_map
    )

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form.get('password'))
        new_user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            password=hashed_password,
            role=request.form.get('role'),
            department=request.form.get('department'),
            leave_balance=int(request.form.get('leave_balance', 21))
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully')
        return redirect(url_for('hr_dashboard'))
    return render_template('add_user.html')


@app.route('/users')
@login_required
def hr_users():
    if current_user.role != 'manager':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.department, User.username).all()
    return render_template('hr_users.html', users=users)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'manager':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.department = request.form.get('department')
        user.leave_balance = int(request.form.get('leave_balance', user.leave_balance))
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('hr_users'))



@app.route('/hr/users/deactivate/<int:user_id>')
@login_required
def deactivate_user(user_id):
    if current_user.role != 'manager':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    user.active = False
    db.session.commit()

    flash('User deactivated', 'warning')
    return redirect(url_for('hr_users'))


@app.route('/hr/users/activate/<int:user_id>')
@login_required
def activate_user(user_id):
    if current_user.role != 'manager':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    user.active = True
    db.session.commit()

    flash('User activated', 'success')
    return redirect(url_for('hr_users'))












if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)