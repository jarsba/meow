import string
import random


def generate_random_string(length=8):
    random_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
    return random_string
