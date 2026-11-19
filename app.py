from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['SECRET_KEY'] = 'college_od_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///college_od.db')
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgresql://', 'postgresql+psycopg2://')

db = SQLAlchemy(app)

# Upload configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Student Database Table
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)   


# OD Application Database Table
class ODApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    event_name = db.Column(db.String(150), nullable=False)
    event_location = db.Column(db.String(150), nullable=False)
    from_date = db.Column(db.String(20), nullable=False)
    to_date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    proof_file = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    staff_remarks = db.Column(db.Text, nullable=True)

    student = db.relationship('Student', backref='applications')

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Staff Login
@app.route('/staff_login', methods=['GET', 'POST'])
def staff_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        staff = Staff.query.filter_by(username=username).first()

        if staff and check_password_hash(staff.password, password):
            session['staff_id'] = staff.id
            return redirect('/staff_dashboard')

        return "Invalid staff username or password!"

    return render_template('staff_login.html')


# Student Registration
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        student = Student(
            full_name=request.form['full_name'],
            roll_number=request.form['roll_number'],
            department=request.form['department'],
            email=request.form['email'],
            username=request.form['username'],
            password=generate_password_hash(request.form['password'])
        )

        try:
            db.session.add(student)
            db.session.commit()
            return redirect('/student_login')

        except Exception:
            db.session.rollback()
            return "Registration failed. Username, email or roll number may already exist."

    return render_template('register.html')


# Student Login
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        student = Student.query.filter_by(username=username).first()

        if student and check_password_hash(student.password, password):

            session['student_id'] = student.id

            return redirect('/student_dashboard')

        return "Invalid username or password!"

    return render_template('login.html')


# Student Dashboard
@app.route('/student_dashboard')
def student_dashboard():

    if 'student_id' not in session:
        return redirect('/student_login')

    student = db.session.get(Student, session['student_id'])

    if student is None:
        session.clear()
        return redirect('/student_login')

    return render_template('student_dashboard.html', student=student)


# OD Application
@app.route('/apply_od', methods=['GET', 'POST'])
def apply_od():

    if 'student_id' not in session:
        return redirect('/student_login')

    if request.method == 'POST':
        from_date = request.form['from_date']
        to_date = request.form['to_date']

        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()

        if start_date < date.today():
            return render_template('apply_od.html', error="Past dates are not allowed!")

        if end_date < start_date:
            return render_template('apply_od.html', error="To Date cannot be earlier than From Date!")

        file = request.files.get('proof')

        if not file or not file.filename:
            return "Please select a proof document!"

        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

        if file_size == 0:
            return "The uploaded file is empty!"

        if file_size > 5 * 1024 * 1024:
            return "File size must not exceed 5 MB!"

        if '.' not in file.filename:
            return "Invalid file!"

        extension = file.filename.rsplit('.', 1)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            return "Only PDF, JPG and PNG files are allowed!"

        filename = secure_filename(file.filename)

        if not filename:
            return "Invalid filename!"

        filename = str(session['student_id']) + '_' + filename

        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        application = ODApplication(
            student_id=session['student_id'],
            event_name=request.form['event_name'],
            event_location=request.form['event_location'],
            from_date=from_date,
            to_date=to_date,
            reason=request.form['reason'],
            proof_file=filename
        )

        db.session.add(application)
        db.session.commit()

        return "OD Application Submitted Successfully!"

    return render_template('apply_od.html')
@app.route('/uploads/<filename>')
def uploaded_file(filename):

    if 'staff_id' not in session:
        return redirect('/staff_login')

    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename)
    )

# My Applications
@app.route('/my_applications')
def my_applications():

    if 'student_id' not in session:
        return redirect('/student_login')

    applications = ODApplication.query.filter_by(
        student_id=session['student_id']
    ).all()

    return render_template(
        'my_applications.html',
        applications=applications
    )

@app.route('/download_od/<int:application_id>')
def download_od(application_id):

    if 'student_id' not in session:
        return redirect('/student_login')

    application = ODApplication.query.filter_by(
        id=application_id,
        student_id=session['student_id']
    ).first()

    if application is None:
        return "Application not found!"

    if application.status != 'Approved':
        return "Only approved applications can be downloaded!"

    student = db.session.get(Student, session['student_id'])

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(150, 800, "COLLEGE ON-DUTY APPROVAL")

    pdf.setFont("Helvetica", 12)

    details = [
        f"Student Name: {student.full_name}",
        f"Roll Number: {student.roll_number}",
        f"Department: {student.department}",
        f"Event Name: {application.event_name}",
        f"Event Location: {application.event_location}",
        f"From Date: {application.from_date}",
        f"To Date: {application.to_date}",
        f"Reason: {application.reason}",
        f"Status: {application.status}"
    ]

    y = 750

    for detail in details:
        pdf.drawString(70, y, detail[:100])
        y -= 35

    pdf.drawString(70, y - 20, "This application has been approved.")

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='OD_Approval.pdf',
        mimetype='application/pdf'
    )


# Student Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# Create Database Tables
with app.app_context():
    db.create_all()

# Staff Dashboard
@app.route('/staff_dashboard')
def staff_dashboard():

    if 'staff_id' not in session:
        return redirect('/staff_login')

    staff = db.session.get(Staff, session['staff_id'])

    if staff is None:
        session.clear()
        return redirect('/staff_login')

    search = request.args.get('search', '').strip()

    if search:
        applications = ODApplication.query.join(Student).filter(
            or_(
                Student.full_name.ilike(f'%{search}%'),
                Student.roll_number.ilike(f'%{search}%'),
                ODApplication.event_name.ilike(f'%{search}%')
            )
        ).all()
    else:
        applications = ODApplication.query.all()

    total_applications = ODApplication.query.count()

    pending_count = ODApplication.query.filter_by(status='Pending').count()

    approved_count = ODApplication.query.filter_by(status='Approved').count()

    rejected_count = ODApplication.query.filter_by(status='Rejected').count()

    return render_template(
        'staff_dashboard.html',
        applications=applications,
        staff=staff,
        total_applications=total_applications,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count
    )

@app.route('/update_status/<int:application_id>', methods=['POST'])
def update_status(application_id):
    if 'staff_id' not in session:
        return redirect('/staff_login')

    application = db.session.get(ODApplication, application_id)

    if application is None:
        return "Application not found!"

    new_status = request.form.get('status')
    remarks = request.form.get('staff_remarks', '').strip()

    if new_status not in ['Approved', 'Rejected']:
        return "Invalid status!"

    application.status = new_status
    application.staff_remarks = remarks

    db.session.commit()

    return redirect('/staff_dashboard')
    

    

# Run Flask Application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)