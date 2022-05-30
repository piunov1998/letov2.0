import os
import sys
import hashlib


def insert_music(music_dir: str = '../../music'):
    sys.path.append('..')

    from injectors import connections
    from models.music import Song

    block_size = 65536
    pg = connections.accuire_session()
    for file in os.listdir(music_dir):
        spited = file.split('.')
        name, ext = '.'.join(spited[:-1]), spited[-1]
        file_hash = hashlib.md5()
        with open(os.path.join(music_dir, file), 'rb') as stream:
            file_bytes = stream.read(block_size)
            while len(file_bytes) > 0:
                file_hash.update(file_bytes)
                file_bytes = stream.read(block_size)
        filename = f'{file_hash.hexdigest()}.{ext}'
        os.rename(os.path.join(music_dir, file), os.path.join(music_dir, filename))
        song = Song(name, filename)
        pg.add(song)
    pg.commit()


if __name__ == '__main__':
    insert_music()
