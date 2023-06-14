from enum import IntEnum


class Role(IntEnum):
    teacher = 1
    teacher_bot = 2
    student = 3


class State(IntEnum):
    none = 0
    awaiting_group_name = 1
