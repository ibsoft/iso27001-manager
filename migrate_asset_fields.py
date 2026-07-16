"""Add picture and barcode columns to existing asset table if missing."""
import sqlite3
import os


def migrate(db_path):
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("PRAGMA table_info(asset)")
    cols = {row[1] for row in c.fetchall()}
    if "picture" not in cols:
        c.execute("ALTER TABLE asset ADD COLUMN picture VARCHAR(256)")
        print(f"  + Added 'picture' column to {db_path}")
    if "barcode" not in cols:
        c.execute("ALTER TABLE asset ADD COLUMN barcode VARCHAR(256)")
        print(f"  + Added 'barcode' column to {db_path}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    instance_dir = os.path.join(os.path.dirname(__file__), "instance")
    if os.path.isdir(instance_dir):
        for f in os.listdir(instance_dir):
            if f.endswith(".db") or f.endswith(".sqlite3"):
                migrate(os.path.join(instance_dir, f))
    print("Done.")
