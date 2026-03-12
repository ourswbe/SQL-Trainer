from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Task

SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS groups (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      course_number INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
      id INTEGER PRIMARY KEY,
      full_name TEXT NOT NULL,
      age INTEGER NOT NULL,
      group_id INTEGER,
      FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS teachers (
      id INTEGER PRIMARY KEY,
      full_name TEXT NOT NULL,
      subject TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS courses (
      id INTEGER PRIMARY KEY,
      title TEXT NOT NULL,
      teacher_id INTEGER,
      FOREIGN KEY(teacher_id) REFERENCES teachers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grades (
      id INTEGER PRIMARY KEY,
      student_id INTEGER,
      course_id INTEGER,
      grade INTEGER,
      FOREIGN KEY(student_id) REFERENCES students(id),
      FOREIGN KEY(course_id) REFERENCES courses(id)
    )
    """,
]

SEED_SQL = [
    "DELETE FROM grades",
    "DELETE FROM courses",
    "DELETE FROM teachers",
    "DELETE FROM students",
    "DELETE FROM groups",
    "INSERT INTO groups (id,name,course_number) VALUES (1,'SE-101',1),(2,'SE-201',2),(3,'DA-301',3)",
    "INSERT INTO students (id,full_name,age,group_id) VALUES (1,'Иван Петров',19,1),(2,'Мария Сидорова',21,2),(3,'Алексей Иванов',22,2),(4,'Анна Кузнецова',20,1),(5,'Ольга Смирнова',23,3)",
    "INSERT INTO teachers (id,full_name,subject) VALUES (1,'Дмитрий Лебедев','Databases'),(2,'Наталья Романова','Algorithms')",
    "INSERT INTO courses (id,title,teacher_id) VALUES (1,'SQL Basics',1),(2,'Advanced SQL',1),(3,'Data Structures',2)",
    "INSERT INTO grades (id,student_id,course_id,grade) VALUES (1,1,1,78),(2,2,1,91),(3,2,2,88),(4,3,1,95),(5,4,1,84),(6,5,2,97)"
]

TASKS = [
    {
        "title": "Студенты старше 20",
        "description": "Выведите всех студентов старше 20 лет.",
        "difficulty": "easy",
        "topic": "WHERE",
        "expected_query": "SELECT id, full_name, age, group_id FROM students WHERE age > 20 ORDER BY id",
    },
    {
        "title": "Группы",
        "description": "Покажите названия всех групп.",
        "difficulty": "easy",
        "topic": "SELECT",
        "expected_query": "SELECT name FROM groups ORDER BY name",
    },
    {
        "title": "Средний балл по студентам",
        "description": "Покажите средний балл каждого студента.",
        "difficulty": "medium",
        "topic": "GROUP BY",
        "expected_query": "SELECT s.full_name, ROUND(AVG(g.grade), 2) AS avg_grade FROM students s JOIN grades g ON s.id = g.student_id GROUP BY s.id, s.full_name ORDER BY s.id",
    },
    {
        "title": "Преподаватели и курсы",
        "description": "Выведите имена преподавателей и названия их курсов.",
        "difficulty": "medium",
        "topic": "JOIN",
        "expected_query": "SELECT t.full_name, c.title FROM teachers t JOIN courses c ON t.id = c.teacher_id ORDER BY t.full_name, c.title",
    },
]


def bootstrap_training_db(session: Session) -> None:
    for statement in SCHEMA_SQL:
        session.execute(text(statement))
    for statement in SEED_SQL:
        session.execute(text(statement))

    if session.query(Task).count() == 0:
        for task in TASKS:
            session.add(Task(**task))

    session.commit()
