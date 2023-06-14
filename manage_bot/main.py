import asyncio
import os
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from enums import Role, State
from models import User, GroupChat


api_id = int(os.environ.get('API_ID'))
api_hash = os.environ.get('API_HASH')
bot_token = os.environ.get('BOT_TOKEN')

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

user_stages = {}
student_states = {}
message_to_delete = 0
unchecked_box = "☐"
checked_box = "☑"
main_keyboard = [
    [Button.text("Управление групповыми чатами", resize=True),
     Button.text("Управление студентами", resize=True)]
]


@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    sender_id = event.sender_id
    if get_user_role(sender_id) == Role.teacher_bot:
        await event.respond('Привет брат')
    else:
        """Если пишет кто угодно кроме клона педагога"""
        await event.respond('Отлично, регистрация в качестве педагога завершена!', buttons=main_keyboard)
        await event.respond('Как только твой список студентов пополнится, с помощью меня ты сможешь управлять '
                            'групповыми чатами со студентами. Студент добавляется в твой список в тот момент когда он '
                            'напишет тебе первое сообщение. Удачи!')


@client.on(events.NewMessage)
async def text_handler(event):
    sender_id = event.sender_id
    match get_user_role(sender_id):
        case Role.teacher:
            state_data = user_stages.get(sender_id, {'state': State.none})
            state = state_data['state']
            teacher_bot = get_teacher_bot()
            match state:
                case State.awaiting_group_name:
                    await event.respond('Жди...')
                    group_name = event.text
                    await client.send_message(teacher_bot.id, f'создать_групповой_чат|{group_name}')
                    user_stages[sender_id] = {
                        'state': State.none,
                    }

                case State.awaiting_new_group_name:
                    await event.respond('Жди...')
                    group_chat_id = state_data['group_chat_id']
                    group_name = event.text
                    await client.send_message(teacher_bot.id, f'переименуй_групповой_чат|{group_chat_id}|{group_name}')
                    user_stages[sender_id] = {
                        'state': State.none,
                    }

                case State.awaiting_new_student_name:
                    await event.respond('Жди...')
                    student_id = state_data['student_id']
                    student_name = event.text.split()
                    student_first_name = student_name[0]
                    student_last_name = student_name[1]
                    await client.send_message(teacher_bot.id, f'переименуй_cтудента|'
                                                              f'{student_id}|{student_first_name}|{student_last_name}')
                    user_stages[sender_id] = {
                        'state': State.none,
                    }

        case Role.teacher_bot:
            split_message = event.raw_text.split('|')
            command = split_message[0]
            match command:
                case 'создан_групповой_чат':
                    group_name = split_message[1]
                    teacher_id = int(split_message[2])
                    group_chat_id = int(split_message[3])
                    keyboard = [
                        [Button.inline('Пригласить студентов в чат', f'chooseChat_{group_chat_id}'.encode())]
                    ]
                    await client.send_message(teacher_id, f'Групповой чат "{group_name}" успешно создан',
                                              buttons=keyboard)
                case 'ссылки_отправлены':
                    teacher_id = int(split_message[1])
                    await client.send_message(teacher_id, f'Ссылки успешно отправлены', buttons=main_keyboard)

                case 'чат_удален':
                    teacher_id = int(split_message[1])
                    await client.send_message(teacher_id, f'Чат успешно удалён', buttons=main_keyboard)

                case 'чат_переименован':
                    teacher_id = int(split_message[1])
                    await client.send_message(teacher_id, f'Чат успешно переименован', buttons=main_keyboard)

                case 'студент_удален':
                    teacher_id = int(split_message[1])
                    await client.send_message(teacher_id, f'Студент успешно удален', buttons=main_keyboard)

                case 'студент_переименован':
                    teacher_id = int(split_message[1])
                    await client.send_message(teacher_id, f'Студент успешно переименован', buttons=main_keyboard)


@client.on(events.NewMessage(pattern='Управление студентами'))
async def button_edit_students_chats_handler(event):
    teacher_id = event.sender_id
    students = User.select().where((User.role == Role.student) & (User.teacher_id == teacher_id))
    if students:
        students_buttons = [[Button.inline(f'{student.first_name} {student.last_name}',
                                           f'editStudent_{student.id}'.encode())] for student in students]
        students_keyboard = students_buttons
        await event.respond('Твои студенты:', buttons=students_keyboard)
    else:
        await event.respond('У вас пока нет студентов')


@client.on(events.NewMessage(pattern='Управление групповыми чатами'))
async def button_edit_group_chats_handler(event):
    teacher_id = event.sender_id
    group_chats = GroupChat.select().where(GroupChat.teacher == teacher_id)
    manage_keyboard = [[Button.text("Создать новый групповой чат", resize=True)]]
    await event.respond('Для управления чатом нажми на название чата;\n'
                        'Для создания группового чата нажми "Создать новый групповой чат"',
                        buttons=manage_keyboard)
    if group_chats:
        chats_buttons = [[Button.inline(chat.name, f'editChat_{chat.id}'.encode())] for chat in group_chats]
        chats_keyboard = chats_buttons
        await event.respond('Твои чаты:', buttons=chats_keyboard)
    else:
        await event.respond('У вас пока нет групповых чатов')


# Обработка событий нажатия кнопки
@client.on(events.CallbackQuery)
async def callback_handler(event):
    teacher_bot = get_teacher_bot()
    button_data = event.data.decode().split('_')
    action = button_data[0]
    teacher_id = event.sender_id
    students = User.select().where((User.teacher_id == teacher_id) & (User.role == Role.student))
    match action:
        case 'chooseChat':
            group_chat_id = button_data[1]
            students_buttons = []
            for student in students:
                students_buttons.append([Button.inline(f'{unchecked_box} {student.first_name} {student.last_name}',
                                        f'checkStudentToSendLink_{student.id}_unchecked_{group_chat_id}'.encode())])
                student_states[student.id] = 'unchecked'
            students_keyboard = students_buttons
            await event.edit('Выбери студентов которых хочешь пригласить в этот чат:', buttons=students_keyboard)

        case 'checkStudentToSendLink':
            checked_student = button_data[1]
            group_chat_id = button_data[3]
            student = User.select().where(User.id == checked_student).first()
            state = button_data[2]
            new_state = "checked" if state == "unchecked" else "unchecked"
            student_states[student.id] = new_state
            new_buttons = [
                [Button.inline(f'{checked_box if student_states[student.id] == "checked" else unchecked_box}'
                               f' {student.first_name} {student.last_name}',
                               f'checkStudentToSendLink_{student.id}_'
                               f'{student_states[student.id]}_{group_chat_id}'.encode())] for student in students]

            new_buttons.append([Button.inline('⬆️ОТПРАВИТЬ ПРИГЛАШЕНИЕ⬆️',
                                              f'sendLinkToChat_{group_chat_id}'.encode())])
            new_keyboard = new_buttons
            await event.edit('Выбери студентов которых хочешь пригласить в этот чат:', buttons=new_keyboard)

        case 'sendLinkToChat':
            group_chat_id = button_data[1]
            students_to_send = [str(student) for student, state in student_states.items() if state == 'checked']
            students_to_send_string = ','.join(students_to_send)
            await client.send_message(teacher_bot.id, f'отправь_ссылку|{group_chat_id}|{students_to_send_string}')
            await event.delete()

        case 'editChat':
            group_chat_id = int(button_data[1])
            group_chat = GroupChat.select().where(GroupChat.id == group_chat_id).first()
            keyboard = [
                [Button.inline(f'Пригласить студентов в чат', f'chooseChat_{group_chat_id}'.encode())],
                [Button.inline(f'Удалить чат', f'deleteChat_{group_chat_id}_{group_chat.name}'.encode())],
                [Button.inline(f'Переименовать чат', f'renameChat_{group_chat_id}'.encode())],
            ]
            await event.edit(f'Управление чатом: **{group_chat.name}**:', buttons=keyboard)

        case 'deleteChat':
            group_chat_id = int(button_data[1])
            group_chat_name = button_data[2]
            keyboard = [
                [Button.inline(f'Да', f'confirmDeleteChat_{group_chat_id}'.encode())],
                [Button.inline(f'Нет', f'editChat_{group_chat_id}'.encode())]
            ]
            await event.edit(f'Вы уверены что хотите удалить чат **{group_chat_name}**?', buttons=keyboard)

        case 'confirmDeleteChat':
            group_chat_id = int(button_data[1])
            GroupChat.delete().where(GroupChat.id == group_chat_id)
            await client.send_message(teacher_bot.id, f'удали_чат|{group_chat_id}')
            await event.delete()

        case 'renameChat':
            group_chat_id = int(button_data[1])
            user_stages[event.sender_id] = {
                'state': State.awaiting_new_group_name,
                'group_chat_id': group_chat_id
            }
            await event.respond('В ответном сообщении напиши название группового чата')
            await event.delete()

        case 'editStudent':
            student_id = int(button_data[1])
            student = User.select().where(User.id == student_id).first()
            keyboard = [
                [Button.inline(f'Удалить',
                               f'deleteStudent_{student_id}_{student.first_name} {student.last_name}'.encode())],
                [Button.inline(f'Переименовать', f'renameStudent_{student_id}'.encode())],
            ]
            await event.edit(f'Управление студентом: **{student.first_name} {student.last_name}**:', buttons=keyboard)

        case 'deleteStudent':
            student_id = int(button_data[1])
            student_name = button_data[2]
            keyboard = [
                [Button.inline(f'Да', f'confirmDeleteStudent_{student_id}'.encode())],
                [Button.inline(f'Нет', f'editStudent_{student_id}'.encode())]
            ]
            await event.edit(f'Вы уверены что хотите удалить студента: **{student_name}**?', buttons=keyboard)

        case 'confirmDeleteStudent':
            student_id = int(button_data[1])
            User.delete().where(User.id == student_id)
            await client.send_message(teacher_bot.id, f'удали_студента|{student_id}')
            await event.delete()

        case 'renameStudent':
            student_id = int(button_data[1])
            user_stages[event.sender_id] = {
                'state': State.awaiting_new_student_name,
                'student_id': student_id
            }
            await event.respond('В ответном сообщении напиши новые имя и фамилию студента:')
            await event.delete()


@client.on(events.NewMessage(pattern='Создать новый групповой чат'))
async def button2_handler(event):
    user_id = event.sender_id
    user_stages[user_id] = {
        'state': State.awaiting_group_name,
    }
    await event.respond('В ответном сообщении напиши название группового чата')


def get_user_role(user_id):
    user = User.select().where(User.id == user_id).first()
    return user.role


def get_teacher_bot():
    return User.select().where(User.role == Role.teacher_bot).first()


async def main():
    await client.run_until_disconnected()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
