class Parrot:
    # refers to `Dead Parrot sketch`
    def __init__(self):
        self.does = {
            'pine': self.decease,
            'sleep': self.expire,
        }

    def decease(self):
        return 'go_to_meet_its_maker'

    def expire(self):
        return 'rest_in_peace'


ex_parrot = Parrot()
print(ex_parrot.does['sleep']())  # >>> 'rest_in_peace'
