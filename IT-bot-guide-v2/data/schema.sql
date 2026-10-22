CREATE TABLE questions(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, subject_id INT REFERENCES subjects(id),
        question TEXT, options TEXT, correct_index INT, explanation TEXT, needs_review INT DEFAULT 0,
        answer_source INT DEFAULT 0, image TEXT, long_question INT DEFAULT 0, excluded INT DEFAULT 0, pre_text TEXT);

CREATE TABLE subjects(id INTEGER PRIMARY KEY, year INT, semester INT, name TEXT, track TEXT);
