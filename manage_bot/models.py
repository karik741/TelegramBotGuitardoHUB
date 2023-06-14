import peewee as pw
import os
from playhouse.db_url import connect

from enums import Role


db_url = os.environ.get('DATABASE_URL')
db = connect(db_url)


class BaseModel(pw.Model):
    class Meta:
        database = db


class User(BaseModel):
    id = pw.BigIntegerField(primary_key=True)
    username = pw.CharField(null=True)
    first_name = pw.CharField()
    last_name = pw.CharField(null=True)
    role = pw.IntegerField(default=Role.student)
    group_with_individual_chat_id = pw.BigIntegerField(default=0)
    group_chat_id = pw.BigIntegerField(default=0)
    teacher_bot_id = pw.BigIntegerField(default=0)
    teacher_id = pw.BigIntegerField(default=0)


class GroupChat(BaseModel):
    id = pw.BigIntegerField(primary_key=True)
    group_clone_id = pw.BigIntegerField()
    name = pw.CharField()
    teacher = pw.ForeignKeyField(User, backref='chats', column_name='teacher_id')
    last_message_user_id = pw.BigIntegerField()


class MessageCorrespondence(BaseModel):
    teacher_chat_id = pw.BigIntegerField()
    teacher_message_id = pw.BigIntegerField()
    student_chat_id = pw.BigIntegerField()
    student_message_id = pw.BigIntegerField()


