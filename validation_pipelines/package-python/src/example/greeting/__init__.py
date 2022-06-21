from time import sleep


def greeting(name):
    return f'Hello {name}!'


def after(seconds, func, *args, **kwargs):
    sleep(seconds)
    return func(*args, **kwargs)
