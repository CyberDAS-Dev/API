import schemathesis

schema = schemathesis.from_path("openapi-spec.yml", base_url = 'http://127.0.0.1:8000')

# @schema.parametrize()
# def test_api(case):
#    case.call_and_validate()
