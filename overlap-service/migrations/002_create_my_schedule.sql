-- 002: the user's own week, editable from the UI ("My week").
-- There is one demo user (login is out of scope), so my_settings has exactly one row.
-- Both tables start with the schedule that used to be hard-coded in app/demo_user.py,
-- so suggestions do not change until the user edits their week.

CREATE TABLE my_settings (
    id TINYINT NOT NULL CONSTRAINT pk_my_settings PRIMARY KEY
        CONSTRAINT ck_my_settings_one_row CHECK (id = 1),
    time_zone NVARCHAR(64) NOT NULL,
    sleep_start TIME(0) NOT NULL,
    sleep_end TIME(0) NOT NULL
);

-- Weekly busy times, e.g. "every Monday 09:00-11:00, Class". weekday: 0 = Monday.
CREATE TABLE my_busy_blocks (
    id INT IDENTITY(1,1) CONSTRAINT pk_my_busy_blocks PRIMARY KEY,
    weekday TINYINT NOT NULL CONSTRAINT ck_my_busy_weekday CHECK (weekday BETWEEN 0 AND 6),
    start_time TIME(0) NOT NULL,
    end_time TIME(0) NOT NULL,
    label NVARCHAR(100) NULL,
    CONSTRAINT ck_my_busy_order CHECK (end_time > start_time)
);

INSERT INTO my_settings (id, time_zone, sleep_start, sleep_end)
VALUES (1, 'Europe/Madrid', '23:00', '07:00');

INSERT INTO my_busy_blocks (weekday, start_time, end_time, label) VALUES
    (0, '09:00', '11:00', 'Class'),
    (1, '09:30', '12:30', 'Class'),
    (2, '09:00', '11:00', 'Class'),
    (3, '09:30', '12:30', 'Class');
