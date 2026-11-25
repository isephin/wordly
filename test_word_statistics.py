from advanced_analyzer import options, run, word_statistics


def main():
    cases = [
        ('The apple apple banana 123', {}, (5, 2)),
        ('The apple apple banana 123', {'ngram': 2}, (5, 2)),
        ('The apple apple banana 123', {'ngram': 3}, (5, 2)),
        ('The apple apple banana 123', {'numbers': True}, (5, 1)),
        ('abc123def', {}, (3, 1)),
        ('abc123def', {'numbers': True}, (1, 0)),
        ('apple banana apple', {'exclude': 'apple'}, (3, 2)),
        ('apple banana apple', {'include': 'apple'}, (3, 1)),
        ('apple banana apple', {'frequency': 99}, (3, 0)),
        ('the and', {}, (2, 2)),
    ]
    for text, settings, expected in cases:
        opt = options(settings)
        counts, _ = run([text], opt)
        assert word_statistics([text], opt, counts) == expected, (text, settings)
    print('Word statistics passed (10 cases)')


if __name__ == '__main__':
    main()
