from enum import IntEnum


class Role(IntEnum):
    teacher = 1
    teacher_bot = 2
    student = 3


class State(IntEnum):
    none = 0
    awaiting_group_name = 1
    awaiting_new_group_name = 2
    awaiting_new_student_name = 3
