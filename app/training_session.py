class TrainingSession:

    def __init__(self):

        self.results = []

    def add_result(self, mistakes_before_success):

        self.results.append(mistakes_before_success)

    def total(self):

        return len(self.results)

    def first_try(self):

        return sum(1 for x in self.results if x == 0)

    def after_mistakes(self):

        return sum(1 for x in self.results if x > 0)

    def accuracy(self):

        if not self.results:
            return 0

        return round(self.first_try() / len(self.results) * 100)