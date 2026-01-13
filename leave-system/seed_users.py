from app import app,db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create sample users
    hr = User(
        username='HR Manager',
        email="hr@monarchhotelskenya.com",
        password=generate_password_hash('hrpassword'),
        role='manager',
        department='Human Resources',
        leave_balance=21,
        active=True
    )
    it = User(
        username='IT Manager',
        email="it@monarchhotelskenya.com",
        password=generate_password_hash('itpassword'),
        role='manager',
        department='IT',
        leave_balance=21,
        active=True

    )
    staff1 = User(
        username='John Doe',
        email="john@monarchhotelskenya.com",
        password=generate_password_hash('johnpassword'),
        role='staff',
        department='Front Desk',
        leave_balance=21,
        active=True
    )
    staff1 = User(
        username='Brandon Kanute',
        email="brandon@monarchhotelskenya.com",
        password=generate_password_hash('brandonpassword'),
        role='staff',
        department='Front Desk',
        leave_balance=21,
        active=True
    )

    if not User.query.filter_by(email=hr.email).first():
        db.session.add(hr)
    if not User.query.filter_by(email=it.email).first():
        db.session.add(it)
    if not User.query.filter_by(email=staff1.email).first():
        db.session.add(staff1)
    db.session.commit()
    print("Sample users created.")