from flask import Flask, url_for, redirect, render_template, request
from model import Student, Assignment, Grade, db
from datetime import datetime

DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = "'K\xaf\xd2\xc7\xc2#J\x05s%\x99J\x8e\xda\x85\xbe<t\xb2\xea\xab\xa7\xa4\xef'"


def invisible_none(value):
    """A finalizer for Jinja2 to let None values not be rendered."""
    if value is None:
        return ''
    return value

app.jinja_env.finalize = invisible_none


@app.before_request
def before_request():
    # I have to connect to the database from here, and not the main thread,
    # because if I made the connection in model.py for eg. and not the main
    # thread, then when I try to use the model subclasses to access the
    # database in the views in gradebook.py, then the db connection is going
    # to be accessed by *not* the main thread. I think there's probably a
    # more elegant solution. TODO?
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


@app.route('/')
def index():
    return redirect(url_for("gradebook"), code=302)


@app.route('/gradebook/')
def gradebook():
    students = Student.all()
    assignments = Assignment.all()
    assignment_pks = [a.pk for a in assignments]
    for student in students:
        # Set the grades following the order specified by assignment_pks
        grades = student.get_grades()
        by_assignment_pk = dict([(g.assignment_pk, g) for g in grades])
        student.grades = [by_assignment_pk.get(pk) for pk in assignment_pks]
    return render_template(
        "gradebook.html",
        assignments=assignments,
        students=students
    )


@app.route('/public_gradebook/')
def public_gradebook():
    students = Student.all(order='alias')
    assignments = [a for a in Assignment.all() if a.is_public]
    for student in students:
        # Set the grades following the order specified by assignment_pks
        grades = student.get_grades()

        grades_by_assignment_pk = dict([(g.assignment_pk, g) for g in grades])

        student.points_by_assignment_pk = {}
        for assignment in assignments:
            grade = grades_by_assignment_pk.get(assignment.pk)
            if grade:
                grade.assignment = assignment
            points = grade.points if grade else 0
            student.points_by_assignment_pk[assignment.pk] = points
        student.grades = grades
        student.has_comments = any((grade.comment for grade in grades))

    now = datetime.now()
    return render_template(
        "public_gradebook.html",
        assignments=assignments,
        students=students,
        now=now
    )


@app.route('/students/')
def students():
    students = Student.all()
    return render_template('student_list.html', students=students)


@app.route('/students/view/<int:student_pk>/')
def student_view(student_pk):
    student = Student.get(pk=student_pk)
    return render_template("student_view.html", student=student)


@app.route('/students/create/', methods=['GET', 'POST'])
def student_create():
    if request.method == "GET":
        return render_template('student_create.html')
    elif request.method == "POST":
        student = Student(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            alias=request.form['alias'],
            grad_year=request.form['grad_year'],
            email=request.form['email'],
        )
        student.save()
        if "create_and_add" in request.form:
            return render_template('student_create.html')
        elif "create" in request.form:
            return redirect(url_for('student_view', student_pk=student.pk))


@app.route('/students/update/<int:student_pk>/', methods=['GET', 'POST'])
def student_update(student_pk):
    student = Student.get(pk=student_pk)
    if request.method == 'GET':
        return render_template('student_update.html', student=student)
    elif request.method == 'POST':
        student.first_name = request.form['first_name']
        student.last_name = request.form['last_name']
        student.alias = request.form['alias']
        student.grad_year = request.form['grad_year']
        student.email = request.form['email']
        student.save()
        return redirect(url_for('student_view', student_pk=student_pk))


@app.route('/students/delete/<int:student_pk>/', methods=['GET', 'POST'])
def student_delete(student_pk):
    student = Student.get(pk=student_pk)
    if request.method == 'GET':
        return render_template('student_delete.html', student=student)
    if request.method == 'POST':
        student.delete()
        return redirect(url_for('students'))


@app.route('/assignments/')
def assignments():
    assignments = Assignment.all()
    return render_template('assignment_list.html', assignments=assignments)


@app.route('/assignments/view/<int:assignment_pk>/')
def assignment_view(assignment_pk):
    assignment = Assignment.get(pk=assignment_pk)
    students = Student.all()
    grades = assignment.get_grades()
    g_by_student_pk = dict([(g.student_pk, g) for g in grades])
    for s in students:
        s.grade = g_by_student_pk.get(s.pk)
    return render_template(
        'assignment_view.html', assignment=assignment, students=students
    )


@app.route('/assignments/create/', methods=['GET', 'POST'])
def assignment_create():
    if request.method == 'GET':
        return render_template('assignment_create.html')
    elif request.method == 'POST':
        assignment = Assignment(
            name=request.form['name'],
            description=request.form['description'],
            #comment=request.form['comment'],#ThiscausesanHTTP400whenavaluewasn'tsubmittedintheform(becauseofaKeyErrorontheMultiDict).Howstupid!
            due_date=request.form['due_date'],
            points=request.form['points'],
            is_public=request.form.get('is_public', False, bool)
        )
        assignment.save()
        if "create_and_add" in request.form:
            return render_template('assignment_create.html')
        elif "create" in request.form:
            return redirect(
                url_for('assignment_view', assignment_pk=assignment.pk)
            )


@app.route('/assignments/update/<int:assignment_pk>/', methods=['GET', 'POST'])
def assignment_update(assignment_pk):
    assignment = Assignment.get(pk=assignment_pk)
    if request.method == 'GET':
        return render_template('assignment_update.html', assignment=assignment)
    elif request.method == 'POST':
        assignment.name = request.form['name']
        assignment.description = request.form['description']
        assignment.comment = request.form['comment']
        assignment.due_date = request.form['due_date']
        assignment.points = request.form['points']
        assignment.is_public = request.form.get('is_public', False, bool)
        assignment.save()
        return redirect(url_for('assignment_view', assignment_pk=assignment.pk))


@app.route('/assignments/delete/<int:assignment_pk>/', methods=['GET', 'POST'])
def assignment_delete(assignment_pk):
    assignment = Assignment.get(pk=assignment_pk)
    if request.method == 'GET':
        return render_template('assignment_delete.html', assignment=assignment)
    if request.method == 'POST':
        assignment.delete()
        return redirect(url_for('assignments'))


@app.route('/assignment/update_grades/<int:assignment_pk>/', methods=['GET', 'POST'])
def assignment_grades_update(assignment_pk):
    assignment = Assignment.get(pk=assignment_pk)
    students = Student.all()
    grades = assignment.get_grades()
    # We decorate the student's with their grades.
    # Ideally, this would be done with a select_related type thing in the
    # model. At the SQL level. TODO
    g_by_student_pk = dict([(grade.student_pk, grade) for grade in grades])
    for s in students:
        s.grade = g_by_student_pk.get(s.pk)

    if request.method == 'GET':
        return render_template(
            "assignment_grades_update.html",
            assignment=assignment,
            students=students
        )

    # TODO: This POSt method seems cumbersome. Can it be fixed?
    if request.method == 'POST':
        for student in students:
            # These keys are first generated in the template as input tag
            # name attributes.
            points_key = "student_{0}_points".format(student.pk)
            comment_key = "student_{0}_comment".format(student.pk)
            try:
                points = request.form[points_key].strip()
                comment = request.form[comment_key].strip()
            except KeyError:
                # This will prevent a 400 status code from being returned if we
                # try to get data from the form about a student that didn't
                # exist when the form was created.
                continue
            try:
                points = int(points.strip())
            except ValueError:
                points = None
            comment = comment.strip()

            if student.grade is None:
                student.grade = Grade(
                    student_pk=student.pk,
                    assignment_pk=assignment.pk,
                    points=points,
                    comment=comment
                )
            else:
                student.grade.points = points
                student.grade.comment = comment
            student.grade.save()
        return redirect(url_for('assignment_view', assignment_pk=assignment_pk))


if __name__ == '__main__':
    app.run(debug=True)
