"""Initialize the database by creating all ORM-defined tables."""

import os
import sys

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from parser.models.orm import Base, engine


def main():
    print("Creating tables…")
    Base.metadata.create_all(engine)
    print("Done. Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  ✓ {table.name}")


if __name__ == "__main__":
    main()
