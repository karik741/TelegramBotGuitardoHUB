import os
from telethon.sync import TelegramClient, functions, events
from telethon import types
from telethon.tl.functions.messages import ExportChatInviteRequest, DeleteChatRequest, EditChatTitleRequest, \
    DeleteHistoryRequest


from models import User, MessageCorrespondence, GroupChat
from enums import Role

api_id = int(os.environ.get('API_ID'))
api_hash = os.environ.get('API_HASH')

client = TelegramClient('anon', api_id, api_hash)


@client.on(events.MessageEdited)
async def handler(massage):
    chat = await massage.get_chat()

    if is_group_chat(chat):
        chat_for_reaction_id, message_for_reaction_id = get_message_for_reaction('teacher', chat.id, massage.id)
    else:
        chat_for_reaction_id, message_for_reaction_id = get_message_for_reaction('student', chat.id, massage.id)
    chat_for_reaction = await client.get_entity(chat_for_reaction_id)

    await client(functions.messages.SendReactionRequest(
        peer=chat_for_reaction,
        msg_id=message_for_reaction_id,
        reaction=[massage.reactions.recent_reactions[0].reaction]
    ))


@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    sender = await event.get_sender()
    teacher = get_teacher()
    chat = await event.get_chat()
    await client.get_dialogs()
    if sender.bot:
        print("Сообщение отправлено ботом")
        split_message = event.raw_text.split('|')
        command = split_message[0]
        match command:
            case 'создать_групповой_чат':
                group_name = split_message[1]
                group_chat_id = await create_group_chat(teacher, group_name)
                await event.respond(f'создан_групповой_чат|{group_name}|{teacher.id}|{group_chat_id}')

            case 'отправь_ссылку':
                group_chat_id = split_message[1]
                students_to_send = split_message[2].split(',')
                invite_link = await get_invite_link(int(group_chat_id))
                await client.get_dialogs()
                for student in students_to_send:
                    await client.send_message(int(student), f'Присоединяйся к групповому чату {invite_link}')
                    user = User.select().where(User.id == int(student)).first()
                    await client.send_message(user.group_with_individual_chat_id,
                                              f'<этому студенту отправлена ссылка на групповой чат>')
                await event.respond(f'ссылки_отправлены|{teacher.id}')

            case 'удали_чат':
                group_chat_id = int(split_message[1])
                await delete_group_chat(group_chat_id)
                await event.respond(f'чат_удален|{teacher.id}')

            case 'переименуй_групповой_чат':
                group_chat_id = int(split_message[1])
                new_name = split_message[2]
                await rename_group_chat(group_chat_id, new_name)
                await event.respond(f'чат_переименован|{teacher.id}')

            case 'удали_студента':
                student_id = int(split_message[1])
                await delete_student(student_id)
                await event.respond(f'студент_удален|{teacher.id}')

            case 'переименуй_cтудента':
                student_id = int(split_message[1])
                new_student_first_name = split_message[2]
                new_student_last_name = split_message[3]
                await rename_student(student_id, new_student_first_name, new_student_last_name)
                await event.respond(f'студент_переименован|{teacher.id}')


    else:
        if teacher:
            """Если педагог уже зарегистрирован"""
            if is_teacher_event(sender.id):
                """Если в чат с ботом написал педагог"""
                if is_group_chat(chat):
                    group_chat = GroupChat.select().where(GroupChat.group_clone_id == chat.id).first()
                    if group_chat:
                        """Если это групповой чат со студентами"""
                        sent_message = await client.send_message(group_chat.id, event.message)
                        create_correspondence(chat.id, event.message.id, group_chat.id, sent_message.id)
                    else:
                        """Если это групповой индивидуальный чат со студентом"""
                        student = User.get(User.group_with_individual_chat_id == chat.id)
                        sent_message = await client.send_message(student.id, event.message)
                        create_correspondence(chat.id, event.message.id, student.id, sent_message.id)
                else:
                    """Если педагог пишет в чат с ботом"""
                    await client.send_message(teacher.id, "скоро напишем обработку для тебя")
            else:
                if is_group_chat(chat):
                    """Если это групповой чат в который написал студент"""
                    group_chat = GroupChat.select().where(GroupChat.id == chat.id).first()
                    if sender.id != group_chat.last_message_user_id:
                        group_chat.last_message_user_id = sender.id
                        group_chat.save()
                        student = User.select().where(User.id == sender.id).first()
                        await client.send_message(group_chat.group_clone_id,
                                                  f'👤 **{student.first_name} {student.last_name}:**')
                    sent_message = await client.send_message(group_chat.group_clone_id, event.message)
                    create_correspondence(group_chat.group_clone_id, sent_message.id, sender.id, event.message.id)

                else:
                    """Если в чат с ботом написал студент"""
                    student, created = create_or_get_user(teacher.id, sender.id, sender.username, sender.first_name,
                                                          sender.last_name)
                    if created:
                        """Если студента ранее не было в базе создаем новый групповой чат со студентом"""
                        await create_group_with_individual_chat(student, teacher)
                    sent_message = await client.send_message(student.group_with_individual_chat_id, event.message)
                    create_correspondence(student.group_with_individual_chat_id, sent_message.id, student.id,
                                          event.message.id)
        else:
            if event.raw_text.lower() == 'я педагог':
                teacher, created = create_or_get_user(sender.id, sender.id, sender.username,
                                                      sender.first_name, sender.last_name, Role.teacher)
                if created:
                    await client.send_message(teacher.id, 'Супер, что бы закончить регистрацию в качестве педагога '
                                                          'перейди по ссылке @guitardo_chat_manager_bot и нажми кнопку '
                                                          'старт.')
                    teacher_bot = await get_teacher_bot()
                    teacher_bot.teacher_id = teacher.id
                    teacher_bot.save()
                    teacher.teacher_bot_id = teacher_bot.id
                    await client.send_message('@guitardo_chat_manager_bot', '/start')


def create_or_get_user(teacher_id, user_id, username, first_name, last_name=None, role=Role.student):
    user, created = User.get_or_create(
        id=user_id,
        defaults={
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'teacher_id': teacher_id,
        }
    )

    return user, created


def get_teacher():
    return User.select().where(User.role == Role.teacher).first()


async def delete_group_chat(group_chat_id):
    await client(DeleteChatRequest(chat_id=group_chat_id))
    chat = GroupChat.select().where(GroupChat.id == group_chat_id).first()
    clone_chat_id = chat.group_clone_id
    await client(DeleteChatRequest(chat_id=clone_chat_id))


async def delete_student(student_id):
    await client(DeleteHistoryRequest(peer=student_id, max_id=0))
    chat = User.select().where(User.id == student_id).first()
    group_with_individual_chat_id = chat.group_with_individual_chat_id
    await client(DeleteChatRequest(chat_id=group_with_individual_chat_id))


async def rename_group_chat(group_chat_id, new_name):
    await client(EditChatTitleRequest(chat_id=group_chat_id, title=new_name))
    chat = GroupChat.select().where(GroupChat.id == group_chat_id).first()
    chat.name = new_name
    chat.save()
    clone_chat_id = chat.group_clone_id
    await client(EditChatTitleRequest(chat_id=clone_chat_id, title=new_name))


async def rename_student(student_id, new_student_first_name, new_student_last_name):
    student = User.select().where(User.id == student_id).first()
    student.first_name = new_student_first_name
    student.last_name = new_student_last_name
    student.save()
    chat_to_rename = student.group_with_individual_chat_id
    await client(EditChatTitleRequest(chat_id=chat_to_rename,
                                      title=f'{new_student_first_name} {new_student_last_name}'))


def is_teacher_event(user_id):
    user = User.select().where(User.id == user_id).first()
    if user:
        return user.role == Role.teacher
    return False


async def create_group_with_individual_chat(user, teacher):
    group_title = f"{user.first_name} {user.last_name}"
    user_id_list = [teacher.id]
    created_group = await client(functions.messages.CreateChatRequest(
        users=user_id_list,
        title=group_title
    ))
    group_with_individual_chat = created_group.chats[0]
    group_with_individual_chat_id = group_with_individual_chat.id
    user.group_with_individual_chat_id = group_with_individual_chat_id
    user.save()


async def create_group_chat(teacher, group_name):
    await client.get_dialogs()
    group_title = group_name
    user_id_list = []
    created_group = await client(functions.messages.CreateChatRequest(
        users=user_id_list,
        title=group_title
    ))
    user_id_list.append(teacher.id)
    created_group_for_teacher = await client(functions.messages.CreateChatRequest(
        users=user_id_list,
        title=f'{group_title} - групповой чат'
    ))
    group = created_group.chats[0]
    group_chat_id = group.id
    clone_group = created_group_for_teacher.chats[0]
    clone_group_chat_id = clone_group.id
    GroupChat.create(
        id=group_chat_id,
        group_clone_id=clone_group_chat_id,
        name=group_name,
        teacher=teacher.id,
    )
    return group_chat_id


def is_group_chat(chat):
    return isinstance(chat, types.Chat)


def get_message_for_reaction(user, chat_id, message_id):
    if user == 'teacher':
        message_info = MessageCorrespondence.select().where((MessageCorrespondence.teacher_message_id == message_id) &
                                                            (MessageCorrespondence.teacher_chat_id == chat_id)).first()
        return message_info.student_chat_id, message_info.student_message_id
    else:
        message_info = MessageCorrespondence.select().where((MessageCorrespondence.student_message_id == message_id) &
                                                            (MessageCorrespondence.student_chat_id == chat_id)).first()
        return message_info.teacher_chat_id, message_info.teacher_message_id


def create_correspondence(teacher_chat_id, teacher_message_id, student_chat_id, student_message_id):
    MessageCorrespondence.create(
        teacher_chat_id=teacher_chat_id,
        teacher_message_id=teacher_message_id,
        student_chat_id=student_chat_id,
        student_message_id=student_message_id
    )


async def get_teacher_bot():
    me = await client.get_me()
    teacher = get_teacher()
    teacher_bot, _ = create_or_get_user(teacher.id, me.id, me.username, me.first_name, me.last_name, Role.teacher_bot)
    return teacher_bot


async def main():
    await client.start()
    print('Клиент запущен')
    await client.run_until_disconnected()


async def get_invite_link(chat_id):
    invite_link = await client(ExportChatInviteRequest(chat_id))
    return invite_link.link


if __name__ == '__main__':
    client.loop.run_until_complete(main())
