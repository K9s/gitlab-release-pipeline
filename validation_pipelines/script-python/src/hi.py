from sys import argv


def say_hi(name='you'):
    print(f'Hi {name}!')


if __name__ == "__main__":
    say_hi(argv[1])
