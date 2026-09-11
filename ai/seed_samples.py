"""Dev seeder: create a handful of Title_Year.txt transcript files with iconic
movie lines, so you can populate LanceDB for integration testing WITHOUT the
full 2.3GB Kaggle download.

Usage:
    python seed_samples.py                      # writes ./sample_movies/
    SAMPLE_DIR=./sample_movies INGEST_LIMIT=15 python ingest.py   # loads them

For the real dataset, just run `python ingest.py` (downloads via kagglehub)."""
import os

MOVIES = {
    "The_Dark_Knight_2008.txt": [
        "Why so serious?",
        "Do you want to know why I use a knife?",
        "This town deserves a better class of criminal.",
        "Some men just want to watch the world burn.",
        "You either die a hero or you live long enough to see yourself become the villain.",
        "Introduce a little anarchy. Upset the established order.",
    ],
    "Inception_2010.txt": [
        "You mustn't be afraid to dream a little bigger, darling.",
        "Your mind is the scene of the crime.",
        "Downwards is the only way forwards.",
        "Dreams feel real while we're in them.",
        "What is the most resilient parasite? An idea.",
    ],
    "Titanic_1997.txt": [
        "I'm the king of the world!",
        "I'll never let go, Jack. I'll never let go.",
        "A woman's heart is a deep ocean of secrets.",
        "I figure life is a gift and I don't intend on wasting it.",
    ],
    "Star_Wars_1977.txt": [
        "May the Force be with you.",
        "These aren't the droids you're looking for.",
        "I find your lack of faith disturbing.",
        "Help me, Obi-Wan Kenobi. You're my only hope.",
        "The Force will be with you, always.",
    ],
    "The_Empire_Strikes_Back_1980.txt": [
        "No. I am your father.",
        "Do. Or do not. There is no try.",
        "Never tell me the odds.",
        "Fear leads to anger. Anger leads to hate.",
    ],
    "Forrest_Gump_1994.txt": [
        "Life is like a box of chocolates. You never know what you're gonna get.",
        "Run, Forrest, run!",
        "Stupid is as stupid does.",
        "My mama always said you can tell a lot about a person by their shoes.",
    ],
    "The_Terminator_1984.txt": [
        "I'll be back.",
        "Come with me if you want to live.",
        "The future is not set. There is no fate but what we make for ourselves.",
    ],
    "Toy_Story_1995.txt": [
        "To infinity and beyond!",
        "There's a snake in my boot!",
        "You've got a friend in me.",
        "The word I'm searching for I can't say because there's preschool toys present.",
    ],
    "The_Godfather_1972.txt": [
        "I'm gonna make him an offer he can't refuse.",
        "Leave the gun. Take the cannoli.",
        "It's not personal, it's strictly business.",
        "A man who doesn't spend time with his family can never be a real man.",
    ],
    "The_Matrix_1999.txt": [
        "There is no spoon.",
        "I know kung fu.",
        "Welcome to the real world.",
        "You take the red pill, you stay in Wonderland.",
        "Unfortunately, no one can be told what the Matrix is. You have to see it for yourself.",
    ],
    "Jaws_1975.txt": [
        "You're gonna need a bigger boat.",
        "We're gonna need a bigger boat to catch that shark.",
        "It's only an island if you look at it from the water.",
    ],
    "The_Wizard_of_Oz_1939.txt": [
        "Toto, I've a feeling we're not in Kansas anymore.",
        "There's no place like home.",
        "Follow the yellow brick road.",
        "Pay no attention to that man behind the curtain.",
    ],
}

os.makedirs("sample_movies", exist_ok=True)
for fname, lines in MOVIES.items():
    with open(os.path.join("sample_movies", fname), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
print(f"Wrote {len(MOVIES)} sample transcripts to ./sample_movies/")
