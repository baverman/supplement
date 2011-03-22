from supplement.remote import Environment

def test_project_token():
    env = Environment()
    env.run()

    p1 = env.get_project_token('.')
    p2 = env.get_project_token('.')

    assert p1 != p2