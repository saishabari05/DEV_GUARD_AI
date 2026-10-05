from app.orders import total

def test_total():
    assert total() == 2
