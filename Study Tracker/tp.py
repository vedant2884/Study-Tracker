def create_profile_table():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,

        display_name TEXT,
        bio TEXT,
        skills TEXT,
        interests TEXT,
        college TEXT,
        image TEXT,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
create_profile_table()
