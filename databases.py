import io
import platform

if platform.system() == "Windows":
    import psycopg2
    from psycopg2.errors import UniqueViolation
    import psycopg2.extras as psycopg2extras

    IP = "localhost"
else:
    import psycopg2cffi as psycopg2
    from psycopg2cffi._impl.exceptions import OperationalError as UniqueViolation
    import psycopg2cffi.extras as psycopg2extras

    import re

    # grep nameserver /etc/resolv.conf | awk '{print $2}'
    with open("/etc/resolv.conf") as f:
        IP = re.search(r"nameserver\s+(\d+\.\d+\.\d+\.\d+)", f.read()).group(1)


class VoiceAudioDatabase:
    def __init__(self) -> None:
        self.con = psycopg2.connect(
            host=IP,
            database="voicefinder",
            user="postgres",
            password="root",
            cursor_factory=psycopg2extras.DictCursor,
        )

        self.create_tables()

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "VoiceAudioDatabase":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def create_tables(self) -> None:
        c = self.con.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS audios (
                audio_id SERIAL PRIMARY KEY,
                audio_name VARCHAR(128) NOT NULL UNIQUE,
                processed BOOLEAN NOT NULL DEFAULT FALSE
            )"""
        )

        VOICE_ACTIVITY_TABLE = """CREATE TABLE IF NOT EXISTS {} (
                audio_id INTEGER NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,

                CONSTRAINT fk_audio_id
                    FOREIGN KEY (audio_id)
                    REFERENCES audios (audio_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            )"""
        c.execute(VOICE_ACTIVITY_TABLE.format("voice_activity"))

        c.execute(VOICE_ACTIVITY_TABLE.format("voice_activity_processed"))

        self.con.commit()

    def insert_audio(self, audio_name: str) -> None:
        c = self.con.cursor()

        c.execute(
            """INSERT INTO audios (audio_name) VALUES (%s) 
                RETURNING audio_id
                """,
            (audio_name,),
        )

        self.con.commit()

        return c.fetchone()["audio_id"]

    def insert_voice_activity(
        self, audio_id: int, voice_activity: list[tuple[int, int]]
    ) -> None:
        c = self.con.cursor()

        # create in memory file
        file = io.StringIO()

        # write data to file
        for voice in voice_activity:
            file.write(f"{audio_id}\t{voice[0]}\t{voice[1]}\n")

        # set file position to start
        file.seek(0)

        c.copy_from(
            file, "voice_activity", columns=("audio_id", "start_time", "end_time")
        )

        self.con.commit()

    def get_audio_id(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute("SELECT audio_id FROM audios WHERE audio_name = %s", (audio_name,))

        if c.rowcount == 0:
            return None

        return c.fetchone()["audio_id"]

    def audio_is_processed(self, audio_id: int) -> bool:
        c = self.con.cursor()

        c.execute("SELECT processed FROM audios WHERE audio_id = %s", (audio_id,))

        return c.fetchone()["processed"]

    def set_processed(self, audio_id: int) -> None:
        c = self.con.cursor()

        c.execute("UPDATE audios SET processed = TRUE WHERE audio_id = %s", (audio_id,))

        self.con.commit()

    def delete_voice_activity(self, audio_id: int) -> None:
        c = self.con.cursor()

        c.execute("DELETE FROM voice_activity WHERE audio_id = %s", (audio_id,))

        self.con.commit()

    def process_voice_activity(self) -> None:
        c = self.con.cursor()

        c.execute("""DELETE FROM voice_activity_processed""")

        c.execute("""SELECT * FROM voice_activity ORDER BY audio_id, start_time""")

        voice_activity = c.fetchall()

        # add one second to start and end time and merge overlapping voice activity
        voice_activity_processed = []
        for voice in voice_activity:
            start_time = voice["start_time"] - 1
            end_time = voice["end_time"] + 1

            if len(voice_activity_processed) == 0:
                voice_activity_processed.append(
                    (voice["audio_id"], start_time, end_time)
                )
                continue

            last_voice = voice_activity_processed[-1]

            if last_voice[0] == voice["audio_id"] and last_voice[2] >= start_time:
                voice_activity_processed[-1] = (
                    last_voice[0],
                    last_voice[1],
                    end_time,
                )
            else:
                voice_activity_processed.append(
                    (voice["audio_id"], start_time, end_time)
                )

        # create in memory file
        file = io.StringIO()

        # write data to file
        for voice in voice_activity_processed:
            file.write(f"{voice[0]}\t{voice[1]}\t{voice[2]}\n")

        # set file position to start
        file.seek(0)

        c.copy_from(
            file,
            "voice_activity_processed",
            columns=("audio_id", "start_time", "end_time"),
        )

        self.con.commit()

    def get_audios(self) -> list[dict]:
        c = self.con.cursor()

        c.execute("SELECT * FROM audios")

        return c.fetchall()

    def get_voice_activity_processed(self, audio_id: int) -> list[tuple[int, int]]:
        c = self.con.cursor()

        c.execute(
            "SELECT start_time, end_time FROM voice_activity_processed WHERE audio_id = %s",
            (audio_id,),
        )

        return c.fetchall()


class FingerPrintDatabase:
    def __init__(self) -> None:
        self.con = psycopg2.connect(
            host=IP,
            database="audiofingerprint",
            user="postgres",
            password="root",
            cursor_factory=psycopg2extras.DictCursor,
        )

        # c = self.con.cursor()
        # c.execute("SET synchronous_commit TO OFF")

        self.create_tables()

    def close(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def create_tables(self) -> None:
        c = self.con.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS audios (
                audio_id SERIAL PRIMARY KEY,
                audio_name VARCHAR(128) NOT NULL UNIQUE,
                fingerprinted BOOLEAN NOT NULL DEFAULT FALSE
            )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS fingerprints (
                id SERIAL PRIMARY KEY,
                hash UUID NOT NULL,
                audio_id INTEGER NOT NULL,
                offset_time INTEGER NOT NULL
            )"""
        )

        self.con.commit()

    def create_index(self) -> None:
        c = self.con.cursor()

        c.execute("CREATE INDEX IF NOT EXISTS hash_index ON fingerprints (hash)")

        self.con.commit()

    def drop_indexes(self) -> None:
        c = self.con.cursor()

        c.execute("DROP INDEX IF EXISTS hash_index")

        self.con.commit()

    def insert_fingerprints(
        self, audio_id: int, fingerprints: list[tuple[str, int]]
    ) -> None:
        c = self.con.cursor()

        # create in memory file
        file = io.StringIO()

        # write data to file
        for fingerprint in fingerprints:
            file.write(f"{fingerprint[0]}\t{fingerprint[1]}\t{audio_id}\n")

        # set file position to start
        file.seek(0)

        # copy from if collison use psycopg2.extras.execute_values
        c.copy_from(
            file,
            "fingerprints",
            columns=("hash", "offset_time", "audio_id"),
        )

        self.con.commit()

    def insert_audio(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute(
            """INSERT INTO audios (audio_name)
            VALUES (%s)
            RETURNING audio_id""",
            (audio_name,),
        )

        self.con.commit()

        return c.fetchone()["audio_id"]

    def get_audio_id(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute(
            """SELECT audio_id
            FROM audios
            WHERE audio_name = %s""",
            (audio_name,),
        )

        if c.rowcount == 0:
            return None

        return c.fetchone()["audio_id"]

    def audio_set_fingerprinted(self, audio_id: int) -> None:
        c = self.con.cursor()

        c.execute(
            """UPDATE audios
            SET fingerprinted = True
            WHERE audio_id = %s""",
            (audio_id,),
        )

        self.con.commit()

    def audio_is_fingerprinted(self, audio_id: int) -> bool:
        c = self.con.cursor()

        c.execute(
            """SELECT fingerprinted
            FROM audios
            WHERE audio_id = %s""",
            (audio_id,),
        )

        return c.fetchone()["fingerprinted"]

    def create_indexes(self) -> None:
        c = self.con.cursor()

        c.execute("CREATE INDEX IF NOT EXISTS hash_index ON fingerprints (hash)")
        c.execute(
            "CREATE INDEX IF NOT EXISTS audio_id_index ON fingerprints (audio_id)"
        )

        self.con.commit()

    def alter_unique(self) -> None:
        c = self.con.cursor()

        self.con.commit()

        # remove duplicates from fingerprints efficiently
        c.execute(
            """DELETE FROM fingerprints
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY hash, audio_id, offset_time ORDER BY id) AS rnum
                    FROM fingerprints
                ) t
                WHERE t.rnum > 1
            )"""
        )

        # add unique constraint
        c.execute("ALTER TABLE fingerprints ADD UNIQUE (hash, audio_id, offset_time)")

        self.con.commit()

    def alter_forgien_key(self) -> None:
        c = self.con.cursor()

        c.execute(
            "ALTER TABLE fingerprints ADD FOREIGN KEY (audio_id) REFERENCES audios (audio_id) ON DELETE CASCADE"
        )

        self.con.commit()

    # finds hashes that have the same hash as the audio id,
    # ignores any audio with lower id than the audio id
    def find_matches(self, audio_id: int) -> list[tuple[int, int]]:
        c = self.con.cursor()

        c.execute(
            """SELECT audio_id, offset_time
            FROM fingerprints
            WHERE hash IN (
                SELECT hash
                FROM fingerprints
                WHERE audio_id = %s
            )
            AND audio_id > %s
            ORDER BY audio_id, offset_time""",
            (audio_id, audio_id),
        )

        return c.fetchall()


class SpeakerDatabase:
    def __init__(self) -> None:
        self.con = psycopg2.connect(
            host=IP,
            database="speakerdiarization",
            user="postgres",
            password="root",
            cursor_factory=psycopg2extras.DictCursor,
        )

        self.create_tables()

    def close(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def create_tables(self) -> None:
        c = self.con.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS audios (
                audio_id SERIAL PRIMARY KEY,
                audio_name VARCHAR(128) NOT NULL UNIQUE,
                dialized BOOLEAN NOT NULL DEFAULT FALSE
            )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS dialization (
                id SERIAL PRIMARY KEY,
                audio_id INTEGER NOT NULL,
                speaker_id INTEGER NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,

                CONSTRAINT fk_audio_id
                    FOREIGN KEY (audio_id)
                    REFERENCES audios (audio_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            )"""
        )

        self.con.commit()

    def insert_audio(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute(
            """INSERT INTO audios (audio_name)
            VALUES (%s)
            RETURNING audio_id""",
            (audio_name,),
        )

        self.con.commit()

        return c.fetchone()["audio_id"]

    def get_audio_id(self, audio_name: str) -> int:
        c = self.con.cursor()

        c.execute(
            """SELECT audio_id
            FROM audios
            WHERE audio_name = %s""",
            (audio_name,),
        )

        if c.rowcount == 0:
            return None

        return c.fetchone()["audio_id"]

    def audio_is_diarized(self, audio_id: int) -> bool:
        c = self.con.cursor()

        c.execute(
            """SELECT dialized
            FROM audios
            WHERE audio_id = %s""",
            (audio_id,),
        )

        return c.fetchone()["dialized"]

    def audio_set_dialized(self, audio_id: int) -> None:
        c = self.con.cursor()

        c.execute(
            """UPDATE audios
            SET dialized = True
            WHERE audio_id = %s""",
            (audio_id,),
        )

        self.con.commit()

    def delete_diarization(self, audio_id: int) -> None:
        c = self.con.cursor()

        c.execute(
            """DELETE FROM dialization
            WHERE audio_id = %s""",
            (audio_id,),
        )

        self.con.commit()

    def insert_speaker_diarization(
        self, audio_id: int, diarization: list[int, float, float]
    ) -> None:
        c = self.con.cursor()

        c.executemany(
            """INSERT INTO dialization (audio_id, speaker_id, start_time, end_time)
            VALUES (%s, %s, %s, %s)""",
            [(audio_id, d[0], int(d[1] * 1000), int(d[2] * 1000)) for d in diarization],
        )

        self.con.commit()
