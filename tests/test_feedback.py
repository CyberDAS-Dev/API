import pytest
import json
from datetime import datetime, timedelta

import falcon

from cyberdas.models import Recipient, FeedbackCategory, Feedback


@pytest.fixture(scope = 'class')
def feedbackDB(defaultDB):
    '''
    База данных, содержащая двух получателей обратной связи с двумя категориями
    и двумя обращениями по каждой из категорий
    '''
    base = datetime.now() - timedelta(days = 1)
    datetime_range = [base + timedelta(days = x) for x in range(10)]

    admin = Recipient(
        name = 'admin', title = 'Администрация',
        description = 'Администрация сайта'
    )
    admin_categories = [
        FeedbackCategory(recipient_name = 'admin', name = 'жалоба'),
        FeedbackCategory(recipient_name = 'admin', name = 'предложение')
    ]
    admin_feedbacks = [
        Feedback(id = 1, recipient_name = 'admin', category = 'жалоба',
                 text = 'blabla', email = 'blabla@mail.com',
                 created_at = datetime_range[0]),
        Feedback(id = 2, recipient_name = 'admin', category = 'предложение',
                 text = 'blabla', created_at = datetime_range[2]),
    ]

    studcom = Recipient(
        name = 'studcom', title = 'Студком',
        description = 'Студенческий комитет', email = 'studcom@mail.com'
    )
    studcom_categories = [
        FeedbackCategory(recipient_name = 'studcom', name = 'жалоба'),
        FeedbackCategory(recipient_name = 'studcom', name = 'предложение')
    ]
    studcom_feedbacks = [
        Feedback(recipient_name = 'studcom', category = 'жалоба',
                 text = 'blabla', email = 'blabla2@mail.com',
                 created_at = datetime_range[2]),
        Feedback(recipient_name = 'studcom', category = 'предложение',
                 text = 'blabla', created_at = datetime_range[4]),
    ]

    defaultDB.setup_models([
        admin, *admin_categories,
        studcom, *studcom_categories,
    ])
    defaultDB.setup_models([*admin_feedbacks, *studcom_feedbacks])
    yield defaultDB


class TestRecipientCollection:

    URI = '/feedback'

    def test_get(self, client, feedbackDB):
        'На GET-запрос возвращается 200 OK со списком получателей'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200
        assert len(json.loads(resp.text)) == 2

    def test_post(self, client):
        'POST-запрос не поддерживается коллекцией'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get_content(self, client, feedbackDB):
        'Содержимое в коллекции совпадает с содержимым по индивидуальному запросу' # noqa
        resp1 = client.simulate_get(self.URI)
        resp2 = client.simulate_get(self.URI.replace('/feedback', '/feedback/admin')) # noqa
        assert json.loads(resp1.text)[0] == json.loads(resp2.text)


class TestRecipientItem:

    URI = '/feedback/admin'

    def test_post(self, client):
        'POST-запрос не поддерживается предметом'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get_404(self, client, feedbackDB):
        'В случае отсутствия запрашиваемого предмета возвращается 404 Not Found'
        resp = client.simulate_get(self.URI.replace('admin', 'onetwo'))
        assert resp.status == falcon.HTTP_404

    def test_get(self, client, feedbackDB):
        'На GET-запрос возвращается 200 OK'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200

    @pytest.fixture(scope = 'class')
    def valid_get(self, client, feedbackDB):
        resp = client.simulate_get(self.URI)
        yield json.loads(resp.text)

    def test_get_content(self, valid_get):
        assert 'name' in valid_get
        assert 'title' in valid_get
        assert 'description' in valid_get
        assert 'categories' in valid_get
        assert isinstance(valid_get['categories'], list)
        assert 'email' not in valid_get

    def test_get_categories(self, valid_get, dbses):
        'В категории не должно попадать ничего, кроме указанного в БД'
        cat = dbses.query(FeedbackCategory).filter_by(recipient_name = 'admin')
        cat_names = [category.name for category in cat.all()]
        assert valid_get['categories'] == cat_names


class TestFeedbackCollection:

    URI = '/feedback/admin/items'

    @pytest.mark.parametrize('data', [
        {'category': 'жалоба'},
        {'text': 'blabla'},
        {'email': 'mail@asd.com', 'text': 'blabla'},
        {'email': 'blabl@asd.com', 'category': 'жалоба'},
        {'email': 'not_an_email', 'category': 'жалоба', 'text': 'blabla'},
    ])
    def test_post_schema(self, client, data):
        'Запрос с недостаточными или некорректными данными возвращает HTTP 400'
        resp = client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_400

    def test_post(self, client, feedbackDB, dbses):
        'POST создаёт новый предмет в коллекции'
        email, text, category = 'user@mail.com', 'bla? bla!', 'жалоба'
        data = {'email': email, 'text': text, 'category': category}
        resp = client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_201

        item = dbses.query(Feedback).filter_by(recipient_name = 'admin', id = 3).first() # noqa
        assert item is not None
        assert item.email == email
        assert item.text == text
        assert item.category == category

    def test_post_without_email(self, client, feedbackDB, dbses):
        'При отправке запроса необязательно указывать адрес почты'
        text, category = 'bla-bla-bla!', 'предложение'
        data = {'text': text, 'category': category}
        resp = client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_201

        item = dbses.query(Feedback).filter_by(recipient_name = 'admin', id = 4)
        assert item.first().email is None

    def test_post_category(self, client, feedbackDB):
        'Запрос с несуществующей категорией возвращает HTTP 400'
        data = {'text': 'bla', 'category': 'bla'}
        resp = client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_400

    def test_post_recipient(self, client, feedbackDB):
        'Запрос на имя несуществующего получателя возвращает HTTP 404'
        data = {'text': 'bla', 'category': 'bla'}
        resp = client.simulate_post(self.URI.replace('/admin/', '/bla/'),
                                    json = data)
        assert resp.status == falcon.HTTP_404
