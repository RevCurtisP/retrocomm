PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
INSERT INTO EMAIL VALUES('curtis','jaidex',1541039603.0,'hello',replace('hey man\nwazzup>\nlater!','\n',char(10)));
INSERT INTO EMAIL VALUES('jaidex','curtis',1541042241.0,'hey',replace('not much\nwhat''s up with you?','\n',char(10)));
INSERT INTO EMAIL VALUES('curtis','varden',1541199898.9999999999,'welcome',replace('Welcome to my BBS\nHow do you like it?','\n',char(10)));
INSERT INTO EMAIL VALUES('curtis','fred',1541200302.9999999999,'t',replace('line1\nline 2\nline 3','\n',char(10)));
COMMIT;
