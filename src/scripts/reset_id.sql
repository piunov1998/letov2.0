ALTER SEQUENCE music.music_id_seq RESTART WITH 1;
UPDATE music.music SET id=nextval('music.music_id_seq');