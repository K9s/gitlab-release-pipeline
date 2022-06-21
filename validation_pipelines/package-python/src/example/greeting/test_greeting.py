from datetime import datetime

from example.greeting import greeting, after


def test_can_greet():
    greet_test = greeting('test')
    assert greet_test == 'Hello test!'


def test_can_greet_after():
    start = datetime.utcnow()
    greet_test = after(1, greeting, 'test')
    end_td = datetime.utcnow() - start
    assert greet_test == 'Hello test!'
    assert end_td.total_seconds() >= 1


def test_can_greet_args_and_kwargs():
    args_greet = greeting('args')
    kwargs_greet = greeting(name='kwargs')
    assert args_greet == 'Hello args!'
    assert kwargs_greet == 'Hello kwargs!'
    args_greet = after(1, greeting, 'args')
    kwargs_greet = after(1, greeting, name='kwargs')
    assert args_greet == 'Hello args!'
    assert kwargs_greet == 'Hello kwargs!'


def test_can_greet_args_and_kwargs_after():
    args_greet = after(1, greeting, 'args')
    kwargs_greet = after(1, greeting, name='kwargs')
    assert args_greet == 'Hello args!'
    assert kwargs_greet == 'Hello kwargs!'
