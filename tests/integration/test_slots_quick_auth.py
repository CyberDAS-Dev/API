import pytest
import re
from os import environ
from unittest.mock import ANY, MagicMock, patch
from datetime import datetime, timedelta

import falcon

from cyberdas.models import Queue, Slot
from cyberdas.services import generate_ott


URI = '/queues/music/slots/2/reserve'
delete_mock = MagicMock()
tm_mail_mock = MagicMock()
t_mail_mock = MagicMock()
smtp_mock = MagicMock()


@pytest.fixture()
def queueDB(defaultDB):
    '''
    База данных, содержащая две очереди со слотами
    '''
    living = Queue(
        name = 'living2021', title = 'Заселение 2021', duration = 5,
        description = 'Заселение 2021', waterfall = False, only_once = True
    )
    living_slots = [Slot(queue_name = 'living2021', id = x,
                    time = datetime.now()) for x in range(10)]

    music = Queue(
        name = 'music', title = 'Музкомната', duration = 5,
        description = 'Музкомната', waterfall = True, only_once = False
    )
    base = datetime.now() - timedelta(days = 1)
    datetime_range = [base + timedelta(days = x) for x in range(10)]
    music_slots = [Slot(queue_name = 'music', id = x, time = datetime_range[x])
                   for x in range(10)]

    defaultDB.setup_models([living, *living_slots, music, *music_slots])
    yield defaultDB


@patch('cyberdas.services.mail.Mail.send', new = MagicMock())
def test_post_with_ott(client, dbses, queueDB):
    'Можно зарезервировать слот, использовав одноразовый токен'
    # Генерируем токен и используем его для записи
    ott = generate_ott({'uid': 2})
    resp = client.simulate_post(
        URI,
        headers = {'Authorization': f'Bearer {ott}'}
    )
    assert resp.status == falcon.HTTP_201

    # Проверяем, что мы записались
    with queueDB.session as dbses:
        slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first()
        assert slot.user_id == 2


def test_get_unsupported(client):
    'GET без каких-либо параметров возвращает HTTP 405'
    resp = client.simulate_get(URI)
    assert resp.status == falcon.HTTP_405


@patch('cyberdas.resources.slots.Reserve.on_delete', new = delete_mock)
def test_delete_from_get(client):
    'GET при указании токена совершает внутренний редирект на DELETE'
    client.simulate_get(URI, params = {'token': '123'})
    delete_mock.assert_called_once()


@patch('cyberdas.services.mail.TransactionMail.send', new = t_mail_mock)
def test_email_sent(a_client, queueDB):
    '''
    После успешной записи пользователю отправляется уведомительное письмо,
    в котором есть токен с подписанным эмэйлом и ссылкой на отмену записи
    '''
    resp = a_client.simulate_post(URI)
    assert resp.status == falcon.HTTP_201
    t_mail_mock.assert_called_once_with(
        ANY, environ['REGISTERED_USER_EMAIL'],
        {'email': environ['REGISTERED_USER_EMAIL']},
        template_data = ANY, transaction_url = URI[1:]
    )


@patch('cyberdas.services.mail.Mail.send', new = smtp_mock)
def test_email_link_works(a_client, client, queueDB):
    '''
    Проверка того, что ссылка в уведомительноп письме при брони слота позволяет
    отменить запись даже без аутентификации
    '''
    # Записываемся
    resp = a_client.simulate_post(URI)
    assert resp.status == falcon.HTTP_201

    # Проверяем, что мы записались
    with queueDB.session as dbses:
        slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first()
        assert slot.user_id == 1

    # Извлекаем ссылку на отмену из письма
    message = smtp_mock.call_args[1]['content']['html']
    token_uri = re.findall(rf'{URI}\?token=[\w\.\-\_]+', message)[0]

    # Делаем запрос по ссылке (уже без аутентификации)
    resp = client.simulate_get(token_uri)
    assert resp.status == falcon.HTTP_204

    # Проверяем, что запись отменена
    with queueDB.session as dbses:
        slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first()
        assert slot.user_id is None


@patch('cyberdas.services.mail.TemplateMail.send', new = tm_mail_mock)
def test_delete_email_sent(a_client, queueDB):
    '''
    После отмены записи пользователю отправляется уведомительное письмо
    '''
    resp = a_client.simulate_post(URI)
    assert resp.status == falcon.HTTP_201
    resp = a_client.simulate_delete(URI)
    assert resp.status == falcon.HTTP_204
    tm_mail_mock.assert_called_with(environ['REGISTERED_USER_EMAIL'], ANY,
                                    template_data = ANY)
