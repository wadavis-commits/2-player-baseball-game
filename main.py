"""
2-Player Baseball Game (Drafter version, second draft)

Advanced Techniques Documentation (per course requirements for code outside basic syllabus):
  - Lambda default factories in dataclass fields (`field(default_factory=lambda: ...)`): 
    Used to dynamically initialize mutable list structures in State.
  - SVG Generation & Data URIs (`urllib.parse.quote`): 
    Used in `diamond_image` to dynamically construct and render vector graphics on the fly.
  - Bakery Testing Suite (`from bakery import assert_equal`): 
    Explicit `assert_equal` statements are placed after all function definitions.
"""
import random
from dataclasses import dataclass, field
from urllib.parse import quote
from bakery import assert_equal
from drafter import *

# ---------------------------------------------------------------------------
# Site-wide look (colors, buttons, text boxes)
# ---------------------------------------------------------------------------
NAVY = "#14213d"
GREEN = "#2e7d32"
GOLD = "#f4b942"
RED = "#c0392b"
BLUE = "#1f5fa8"
PURPLE = "#6a4c93"
GRAY = "#5f6b7a"

set_website_title("Drafter Baseball!")
set_site_information(
    author="William A. Davis",
    description="Organize and execute a 2-player baseball game.",
    sources="Thank you to all of the University of Delaware CISC106 team, especially Proffesor Wassil.",
    planning=["plan.pdf", "design.pdf"],
    links=["https://github.com/your-username/your-repository"]
)
hide_debug_information()
set_website_framed(False)
add_website_css("body", "background-color: #eaf2e3; color: #14213d; "
                        "font-family: 'Segoe UI', Arial, sans-serif; max-width: 760px; "
                        "margin: 0 auto; padding: 16px;")
add_website_css("button, input[type=submit], input[type=button]",
                "background-color: #14213d; color: white; border: none; border-radius: 8px; "
                "padding: 9px 18px; margin: 4px 8px 4px 0; font-size: 1rem; cursor: pointer;")
add_website_css("button, input[type=submit], input[type=button]", "min-width: 110px; "
                "box-shadow: 0 2px 4px rgba(0,0,0,0.25); transition: transform 0.1s;")
add_website_css("button:hover, input[type=submit]:hover", "opacity: 0.9; transform: translateY(-2px);")
add_website_css("tr:nth-child(even) td", "background-color: #f4f8ef;")
add_website_css("h1, h2", "font-family: Georgia, 'Times New Roman', serif; letter-spacing: 0.5px;")
add_website_css("input[type=text], select",
                "padding: 7px 10px; border-radius: 6px; border: 2px solid #b8c4b0; "
                "font-size: 1rem; margin: 4px 0 10px 0;")
add_website_css("table", "border-collapse: collapse; width: 100%;")
add_website_css("th, td", "padding: 6px 10px; border-bottom: 1px solid #d5dcc8; text-align: center;")
add_website_css("th", "background-color: #14213d; color: white;")


# ---------------------------------------------------------------------------
# Settings you can tweak
# ---------------------------------------------------------------------------
INNINGS = 9  # set to 3 while testing so games are short

EMPTY = -1  # marks an empty base in State.bases

# pitch name -> (base chance the pitch is a strike, base chance a swing makes contact)
PITCH_BASE = {
    "Fastball": (0.65, 0.80),
    "Curveball": (0.50, 0.60),
    "Slider": (0.55, 0.65),
    "Changeup": (0.55, 0.55),
}

# Base outcome weights when the batter makes contact (adjusted by player ratings)
CONTACT_RESULTS = {
    "foul": 0.20,
    "out": 0.45,
    "single": 0.25,
    "double": 0.08,
    "triple": 0.01,
    "homer": 0.06,
}

# How many bases each hit moves everyone
ADVANCE = {"single": 1, "double": 2, "triple": 3, "homer": 4}

# Difficulty level -> (low, high) range for randomly generated ratings.
HITTER_RANGE = {1: (55, 99), 2: (40, 85), 3: (25, 70)}
PITCHER_RANGE = {1: (25, 70), 2: (40, 85), 3: (55, 99)}

POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]

FIRST_NAMES = ["Jake", "Mason", "Carlos", "Tyler", "Marcus", "Danny", "Eli", "Ryan", "Diego",
               "Hunter", "Luis", "Owen", "Caleb", "Andre", "Nate", "Sam", "Victor", "Wyatt",
               "Miguel", "Cole", "Trevor", "Jordan", "Felix", "Shane", "Reggie", "Beau"]
LAST_NAMES = ["Johnson", "Ramirez", "Carter", "Nguyen", "Brooks", "Santos", "Miller", "Rivera",
              "Hayes", "Kim", "Foster", "Morales", "Bennett", "Price", "Cruz", "Walker",
              "Dawson", "Ortiz", "Sullivan", "Reed", "Lopez", "Grant", "Murphy", "Vega"]
NAME_POOL = [first + " " + last for first in FIRST_NAMES for last in LAST_NAMES]

# Where batted balls go (position -> weight)
GROUND_SPOTS = {"3B": 0.22, "SS": 0.30, "2B": 0.28, "1B": 0.20}
OUTFIELD_SPOTS = {"LF": 0.33, "CF": 0.34, "RF": 0.33}
LINE_SPOTS = {"3B": 0.15, "SS": 0.18, "2B": 0.17, "1B": 0.15, "LF": 0.12, "CF": 0.12, "RF": 0.11}
POP_SPOTS = {"1B": 0.2, "2B": 0.2, "3B": 0.2, "SS": 0.2, "C": 0.2}
INFIELD_SPOTS = ["1B", "2B", "3B", "SS", "C"]
POSITION_NAMES = {"C": "the catcher", "1B": "first base", "2B": "second base",
                  "3B": "third base", "SS": "shortstop", "LF": "left field",
                  "CF": "center field", "RF": "right field"}
PITCHERS_PER_TEAM = 5  # 1 starter + 4 relievers


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Hitter:
    """A position player. All ratings are ints from 1 to 99."""
    name: str       # the player's name
    position: str   # initials of the position, like "SS"
    number: int     # jersey number (1-99)
    contact: int    # contact rating
    power: int      # power rating
    fielding: int   # fielding rating
    speed: int      # speed rating
    at_bats: int = 0
    hits: int = 0
    home_runs: int = 0
    rbi: int = 0
    walks: int = 0
    strikeouts: int = 0


@dataclass
class Pitcher:
    """A pitcher. All ratings are ints from 1 to 99."""
    name: str       # the pitcher's name
    velocity: int   # pitch velocity rating
    control: int    # pitch control rating
    movement: int   # pitch movement rating
    stamina: int    # pitcher stamina rating
    fielding: int   # fielding rating
    pitches_thrown: int = 0


@dataclass
class Team:
    """One team containing pitchers and position players."""
    pitchers: list[Pitcher]
    catcher: Hitter
    first_base: Hitter
    second_base: Hitter
    third_base: Hitter
    short_stop: Hitter
    left_field: Hitter
    center_field: Hitter
    right_field: Hitter


@dataclass
class State:
    """State dataclass holding all application state across Drafter routes.
    Advanced Technique Note: Uses lambda default factories for lists."""
    away_name: str = "Player 1"
    home_name: str = "Player 2"
    difficulty: int = 2
    teams: list[Team] = field(default_factory=list)
    inning: int = 1
    top_of_inning: bool = True
    outs: int = 0
    balls: int = 0
    strikes: int = 0
    bases: list[int] = field(default_factory=lambda: [EMPTY, EMPTY, EMPTY])
    away_batter: int = 0
    home_batter: int = 0
    away_score: int = 0
    home_score: int = 0
    away_hits: int = 0
    home_hits: int = 0
    away_line: list[int] = field(default_factory=lambda: [0])
    home_line: list[int] = field(default_factory=lambda: [0])
    current_pitch: str = ""
    pending_hit: str = ""
    hit_location: str = ""
    message: str = ""
    play_log: list[str] = field(default_factory=list)
    game_over: bool = False
    home_skipped_last: bool = False


# ---------------------------------------------------------------------------
# Team creation & Function definitions
# ---------------------------------------------------------------------------
def make_hitter(name: str, position: str, number: int, level: int) -> Hitter:
    """
    Create a named hitter with random attributes based on the difficulty level.

    Args:
        name (str): The full name of the hitter.
        position (str): The fielding position abbreviation (e.g., 'SS').
        number (int): The player's jersey number.
        level (int): The difficulty level determining the range of stats.

    Returns:
        Hitter: A newly initialized Hitter dataclass instance with randomized stats.
    """
    low, high = HITTER_RANGE[level]
    return Hitter(name, position, number,
                  random.randint(low, high), random.randint(low, high),
                  random.randint(low, high), random.randint(low, high))


def make_pitcher(name: str, level: int) -> Pitcher:
    """
    Create a named pitcher with random stats bounded by the given difficulty.

    Args:
        name (str): The pitcher's full name.
        level (int): The difficulty level scaling the pitcher's attributes.

    Returns:
        Pitcher: A newly initialized Pitcher dataclass instance with random ratings.
    """
    low, high = PITCHER_RANGE[level]
    return Pitcher(name, random.randint(low, high), random.randint(low, high),
                   random.randint(low, high), random.randint(low, high),
                   random.randint(low, high))


def make_team(level: int, names: list[str]) -> Team:
    """
    Assemble a full team consisting of 8 positional hitters and a pitching staff.

    Args:
        level (int): The difficulty level for player statistics generation.
        names (list[str]): A list of available unique names to assign to team members.

    Returns:
        Team: A fully populated Team instance containing pitchers and position players.
    """
    numbers = random.sample(range(1, 100), len(POSITIONS))
    hitters = [make_hitter(names[i], pos, num, level)
               for i, (pos, num) in enumerate(zip(POSITIONS, numbers))]
    pitchers = [make_pitcher(names[len(POSITIONS) + i], level)
                for i in range(PITCHERS_PER_TEAM)]
    return Team(pitchers, *hitters)


def new_game(away_name: str, home_name: str, level: int) -> State:
    """
    Initialize a brand new game state with unique generated teams for away and home sides.

    Args:
        away_name (str): Display name for the away player.
        home_name (str): Display name for the home player.
        level (int): Difficulty setting for both teams.

    Returns:
        State: A fully initialized State dataclass object representing the start of a game.
    """
    per_team = len(POSITIONS) + PITCHERS_PER_TEAM
    names = random.sample(NAME_POOL, per_team * 2)
    return State(away_name=away_name, home_name=home_name, difficulty=level,
                 teams=[make_team(level, names[:per_team]), make_team(level, names[per_team:])])


def roll(weights: dict) -> str:
    """
    Select an outcome randomly based on weighted probabilities.

    Args:
        weights (dict): A dictionary mapping outcomes to their respective relative weights.

    Returns:
        str: The selected outcome key.
    """
    return random.choices(list(weights.keys()), weights=list(weights.values()))[0]


def clamp(value: float, low: float, high: float) -> float:
    """
    Constrain a numerical value within specified minimum and maximum bounds.

    Args:
        value (float): The numeric value to clamp.
        low (float): The minimum allowable lower bound.
        high (float): The maximum allowable upper bound.

    Returns:
        float: The clamped numerical value.
    """
    return max(low, min(high, value))


ROUTINE_PLAYS = ["Ball.", "Called strike.", "Swing and a miss!", "Foul ball."]


def say(state: State, text: str):
    """
    Update the current game message and record non-routine plays into the game play log.

    Args:
        state (State): The current application State object.
        text (str): The description string of the recent play.

    Returns:
        None
    """
    state.message = text
    if text not in ROUTINE_PLAYS:
        half = "Top" if state.top_of_inning else "Bottom"
        state.play_log.append(f"{half} {state.inning}: {text}")
        del state.play_log[:-8]


def lineup(team: Team) -> list[Hitter]:
    """
    Retrieve the ordered list of position players forming a team's batting order.

    Args:
        team (Team): The team instance to extract hitters from.

    Returns:
        list[Hitter]: A list of Hitter instances in batting order.
    """
    return [team.catcher, team.first_base, team.second_base, team.third_base,
            team.short_stop, team.left_field, team.center_field, team.right_field]


def batting_team(state: State) -> Team:
    """
    Determine which team is currently on offense.

    Args:
        state (State): The current game State.

    Returns:
        Team: The Team object currently batting.
    """
    return state.teams[0] if state.top_of_inning else state.teams[1]


def fielding_team(state: State) -> Team:
    """
    Determine which team is currently on defense.

    Args:
        state (State): The current game State.

    Returns:
        Team: The Team object currently on the field.
    """
    return state.teams[1] if state.top_of_inning else state.teams[0]


def batting_name(state: State) -> str:
    """
    Retrieve the display name of the player whose team is currently batting.

    Args:
        state (State): The current game State.

    Returns:
        str: The name of the batting player.
    """
    return state.away_name if state.top_of_inning else state.home_name


def pitching_name(state: State) -> str:
    """
    Retrieve the display name of the player whose team is currently pitching.

    Args:
        state (State): The current game State.

    Returns:
        str: The name of the pitching player.
    """
    return state.home_name if state.top_of_inning else state.away_name


def current_batter(state: State) -> tuple[Hitter, int]:
    """
    Identify the active batter at the plate and their position in the lineup.

    Args:
        state (State): The current game State.

    Returns:
        tuple[Hitter, int]: A tuple containing the active Hitter and their lineup index.
    """
    index = state.away_batter if state.top_of_inning else state.home_batter
    return lineup(batting_team(state))[index], index


def next_batter(state: State):
    """
    Advance the batting order index for the active team to the next hitter.

    Args:
        state (State): The current game State.

    Returns:
        None
    """
    if state.top_of_inning:
        state.away_batter = (state.away_batter + 1) % len(POSITIONS)
    else:
        state.home_batter = (state.home_batter + 1) % len(POSITIONS)


def team_defense(team: Team) -> float:
    """
    Calculate the average defensive rating across all position players and the pitcher.

    Args:
        team (Team): The Team object to evaluate.

    Returns:
        float: The mean fielding rating.
    """
    ratings = [hitter.fielding for hitter in lineup(team)] + [team.pitchers[0].fielding]
    return sum(ratings) / len(ratings)


def stat_line(hitter: Hitter) -> str:
    """
    Generate a formatted summary string of a hitter's current game statistics.

    Args:
        hitter (Hitter): The Hitter instance to summarize.

    Returns:
        str: A formatted text description of hits, at-bats, home runs, RBIs, walks, and strikeouts.
    """
    if hitter.at_bats == 0 and hitter.walks == 0:
        return "No at-bats yet today"
    parts = [f"{hitter.hits}-for-{hitter.at_bats}"]
    if hitter.home_runs:
        parts.append("HR" if hitter.home_runs == 1 else f"{hitter.home_runs} HR")
    if hitter.rbi:
        parts.append(f"{hitter.rbi} RBI")
    if hitter.walks:
        parts.append("BB" if hitter.walks == 1 else f"{hitter.walks} BB")
    if hitter.strikeouts:
        parts.append("K" if hitter.strikeouts == 1 else f"{hitter.strikeouts} K")
    return ", ".join(parts)


def add_runs(state: State, runs: int):
    """
    Add scored runs to the active batting team's total score and inning line score.

    Args:
        state (State): The current game State.
        runs (int): The number of runs to add.

    Returns:
        None
    """
    if runs == 0:
        return
    if state.top_of_inning:
        state.away_score += runs
        state.away_line[state.inning - 1] += runs
    else:
        state.home_score += runs
        state.home_line[state.inning - 1] += runs
        if state.inning >= INNINGS and state.home_score > state.away_score:
            state.game_over = True


def add_hit_to_total(state: State):
    """
    Increment the team hit counter for the currently batting team.

    Args:
        state (State): The current game State.

    Returns:
        None
    """
    if state.top_of_inning:
        state.away_hits += 1
    else:
        state.home_hits += 1


def advance_runners(bases: list, bases_to_move: int, batter_id: int):
    """
    Advance all existing base runners and place the batter on base following a hit.

    Args:
        bases (list): Current occupant indices for bases [1st, 2nd, 3rd].
        bases_to_move (int): Number of bases to advance runners.
        batter_id (int): Lineup index of the batter hitting.

    Returns:
        tuple[list, int]: Updated bases list and total runs scored on the play.
    """
    runs = 0
    new = [EMPTY, EMPTY, EMPTY]
    for i in (2, 1, 0):
        if bases[i] != EMPTY:
            target = i + bases_to_move
            if target >= 3:
                runs += 1
            else:
                new[target] = bases[i]
    if bases_to_move == 4:
        runs += 1
    else:
        new[bases_to_move - 1] = batter_id
    return new, runs


def walk_runners(bases: list, batter_id: int):
    """
    Advance base runners strictly forced forward due to a walk.

    Args:
        bases (list): Current occupant indices for bases.
        batter_id (int): Lineup index of the walking batter.

    Returns:
        tuple[list, int]: Updated bases list and runs scored (if bases were loaded).
    """
    b = bases[:]
    runs = 0
    if b[0] == EMPTY:
        b[0] = batter_id
    elif b[1] == EMPTY:
        b[1] = b[0]
        b[0] = batter_id
    elif b[2] == EMPTY:
        b[2] = b[1]
        b[1] = b[0]
        b[0] = batter_id
    else:
        runs = 1
        b[2] = b[1]
        b[1] = b[0]
        b[0] = batter_id
    return b, runs


def bases_text(bases: list) -> str:
    """
    Generate a text description indicating which bases are currently occupied.

    Args:
        bases (list): Current state of the bases.

    Returns:
        str: Descriptive string of occupied bases.
    """
    names = ["1st", "2nd", "3rd"]
    occupied = [names[i] for i in range(3) if bases[i] != EMPTY]
    return "Runners on: " + ", ".join(occupied) if occupied else "Bases empty"


def lead_runner(bases: list) -> int:
    """
    Find the index of the most advanced base currently holding a runner.

    Args:
        bases (list): Current base occupancies.

    Returns:
        int: Index of the lead base (0, 1, or 2), or -1 if empty.
    """
    for i in (2, 1, 0):
        if bases[i] != EMPTY:
            return i
    return -1


def reset_count(state: State):
    """
    Reset balls and strikes count to zero for the current batter.

    Args:
        state (State): The current game State.

    Returns:
        None
    """
    state.balls = 0
    state.strikes = 0


def end_half_inning_if_needed(state: State):
    """
    Check if three outs have occurred and transition half-innings or conclude the game.

    Args:
        state (State): The current game State.

    Returns:
        None
    """
    if state.outs < 3:
        return
    state.outs = 0
    reset_count(state)
    state.bases = [EMPTY, EMPTY, EMPTY]
    state.pending_hit = ""
    state.hit_location = ""

    if state.top_of_inning:
        if state.inning >= INNINGS and state.home_score > state.away_score:
            state.game_over = True
            state.home_skipped_last = True
        state.top_of_inning = False
    else:
        if state.inning >= INNINGS and state.home_score != state.away_score:
            state.game_over = True
        if not state.game_over:
            state.top_of_inning = True
            state.inning += 1
            state.away_line.append(0)
            state.home_line.append(0)


def record_out(state: State):
    """
    Record an out, reset the ball/strike count, and advance to the next batter.

    Args:
        state (State): The current game State.

    Returns:
        None
    """
    state.outs += 1
    reset_count(state)
    next_batter(state)


def batter_out_message(state: State, text: str):
    """
    Record a batter out event, set the play description message, and check inning status.

    Args:
        state (State): The current game State.
        text (str): Descriptive message of the out.

    Returns:
        None
    """
    record_out(state)
    say(state, text)
    end_half_inning_if_needed(state)


# ---------------------------------------------------------------------------
# Pitch and swing mechanics
# ---------------------------------------------------------------------------
def fatigue(pitcher: Pitcher) -> float:
    """
    Calculate the pitcher fatigue penalty factor based on pitches thrown past stamina limits.

    Args:
        pitcher (Pitcher): The pitching Pitcher instance.

    Returns:
        float: Calculated fatigue value between 0.0 and 0.3.
    """
    limit = 40 + pitcher.stamina
    return clamp((pitcher.pitches_thrown - limit) / 100, 0.0, 0.3)


def strike_chance(pitch: str, pitcher: Pitcher) -> float:
    """
    Calculate the probability that a pitch results in a strike when taken.

    Args:
        pitch (str): The name of the pitch thrown.
        pitcher (Pitcher): The pitcher throwing the pitch.

    Returns:
        float: Probability of a strike between 0.30 and 0.85.
    """
    base = PITCH_BASE[pitch][0]
    return clamp(base + (pitcher.control - 50) / 300 - fatigue(pitcher) / 2, 0.30, 0.85)


def contact_chance(pitch: str, pitcher: Pitcher, batter: Hitter) -> float:
    """
    Calculate the probability that the batter makes contact with an incoming pitch.

    Args:
        pitch (str): The pitch name.
        pitcher (Pitcher): The pitcher on the mound.
        batter (Hitter): The batter at the plate.

    Returns:
        float: Contact probability between 0.20 and 0.95.
    """
    base = PITCH_BASE[pitch][1]
    rating = pitcher.velocity if pitch == "Fastball" else pitcher.movement
    return clamp(base + (batter.contact - 50) / 250 - (rating - 50) / 300 + fatigue(pitcher),
                 0.20, 0.95)


def contact_weights(batter: Hitter, defense: float) -> dict:
    """
    Adjust batted-ball outcome weights based on batter power/speed and team defense.

    Args:
        batter (Hitter): The Hitter who made contact.
        defense (float): Average fielding rating of the defense.

    Returns:
        dict: Modified outcome weights dictionary.
    """
    weights = dict(CONTACT_RESULTS)
    power = batter.power / 50
    weights["homer"] *= power
    weights["triple"] *= batter.speed / 50
    weights["double"] *= 0.5 + power / 2
    weights["single"] *= 0.6 + batter.contact / 125
    weights["out"] *= 0.8 + defense / 250
    return weights


def resolve_pitch(state: State, swing: bool):
    """
    Evaluate the result of a pitch based on whether the batter swung or held.

    Args:
        state (State): The current game State.
        swing (bool): True if the batter swung, False if they held.

    Returns:
        None
    """
    pitcher = fielding_team(state).pitchers[0]
    batter, _ = current_batter(state)
    pitcher.pitches_thrown += 1

    if not swing:
        strike = strike_chance(state.current_pitch, pitcher)
        if roll({"strike": strike, "ball": 1 - strike}) == "strike":
            add_strike(state, "Called strike.")
        else:
            add_ball(state)
        return

    if random.random() > contact_chance(state.current_pitch, pitcher, batter):
        add_strike(state, "Swing and a miss!")
        return

    outcome = roll(contact_weights(batter, team_defense(fielding_team(state))))
    if outcome == "foul":
        if state.strikes < 2:
            state.strikes += 1
        say(state, "Foul ball.")
    elif outcome == "out":
        resolve_out_in_play(state)
    else:
        add_hit(state, outcome)


def fielder_at(team: Team, position: str) -> Hitter:
    """
    Locate the specific Hitter playing a given position on a team.

    Args:
        team (Team): The Team to search.
        position (str): The position abbreviation (e.g., 'SS').

    Returns:
        Hitter: The player assigned to that position.
    """
    for hitter in lineup(team):
        if hitter.position == position:
            return hitter
    return team.catcher


def spot_text(position: str, fielder: Hitter) -> str:
    """
    Format descriptive text for a fielding location and fielder name.

    Args:
        position (str): Position abbreviation.
        fielder (Hitter): The fielder playing the position.

    Returns:
        str: Formatted description string.
    """
    return f"{POSITION_NAMES[position]} ({fielder.name})"


def force_advance(bases: list):
    """
    Execute mandatory base advancements when trailing runners are forced forward.

    Args:
        bases (list): Current base occupancies.

    Returns:
        tuple[list, int]: Updated bases list and runs forced in.
    """
    b = bases[:]
    runs = 0
    if b[0] != EMPTY:
        if b[1] != EMPTY:
            if b[2] != EMPTY:
                runs = 1
            b[2] = b[1]
        b[1] = b[0]
        b[0] = EMPTY
    return b, runs


def error_chance(fielder: Hitter, ball: str) -> float:
    """
    Calculate the probability of a defensive error based on fielder rating.

    Args:
        fielder (Hitter): The fielder handling the ball.
        ball (str): Type of batted ball ('ground' or 'fly').

    Returns:
        float: Probability of error.
    """
    chance = clamp(0.04 - (fielder.fielding - 50) / 1000, 0.005, 0.09)
    return chance * (0.5 if ball == "fly" else 1.0)


def double_play_chance(position: str, fielder: Hitter, batter: Hitter) -> float:
    """
    Calculate the probability of turning a double play on a ground ball.

    Args:
        position (str): Fielding position handling the play.
        fielder (Hitter): The fielding player.
        batter (Hitter): The batter running.

    Returns:
        float: Double play probability.
    """
    bonus = {"SS": 0.10, "2B": 0.10, "3B": 0.0, "1B": -0.10}.get(position, 0.0)
    return clamp(0.40 + bonus + (fielder.fielding - 50) / 200 - (batter.speed - 50) / 200,
                 0.10, 0.75)


def finish_play(state: State, batter: Hitter, bases: list, runs: int, outs_added: int,
                message: str, counts_as_at_bat: bool = True, rbi_credit: bool = True):
    """
    Finalize a batted play by updating bases, runs, outs, and batter stats.

    Args:
        state (State): Current game State.
        batter (Hitter): The batter involved.
        bases (list): Updated base configuration.
        runs (int): Runs scored.
        outs_added (int): Number of outs recorded.
        message (str): Play description message.
        counts_as_at_bat (bool): Whether it counts as an official at-bat.
        rbi_credit (bool): Whether RBIs should be credited.

    Returns:
        None
    """
    state.bases = bases
    add_runs(state, runs)
    state.outs += outs_added
    if counts_as_at_bat:
        batter.at_bats += 1
    if rbi_credit:
        batter.rbi += runs
    reset_count(state)
    next_batter(state)
    say(state, message)
    end_half_inning_if_needed(state)


def reach_on_error(state: State, position: str, fielder: Hitter, batter: Hitter, batter_id: int):
    """
    Handle a fielding error allowing the batter to reach base safely and runners to advance.

    Args:
        state (State): Current game State.
        position (str): Position where error occurred.
        fielder (Hitter): Fielder who committed the error.
        batter (Hitter): Batter reaching safely.
        batter_id (int): Batter lineup index.

    Returns:
        None
    """
    new_bases, runs = advance_runners(state.bases, 1, batter_id)
    finish_play(state, batter, new_bases, runs, 0,
                f"Error! {fielder.name} misplays it at {POSITION_NAMES[position]}. "
                f"{batter.name} is safe and the runners move up.", rbi_credit=False)


def resolve_out_in_play(state: State):
    """
    Determine the type of out (ground ball, fly ball, line drive, or pop-up) when an out occurs.

    Args:
        state (State): Current game State.

    Returns:
        None
    """
    batter, _ = current_batter(state)
    shift = (batter.power - 50) / 300
    ball = roll({"ground": 0.45 - shift, "fly": 0.33 + shift, "line": 0.13, "pop": 0.09})
    if ball == "ground":
        resolve_ground_ball(state, roll(GROUND_SPOTS))
    elif ball == "fly":
        resolve_fly_ball(state, roll(OUTFIELD_SPOTS))
    elif ball == "line":
        resolve_line_drive(state, roll(LINE_SPOTS))
    else:
        resolve_pop_up(state, roll(POP_SPOTS))


def resolve_ground_ball(state: State, position: str):
    """
    Process ground ball fielding outcomes including double plays, fielder's choices, and outs.

    Args:
        state (State): Current game State.
        position (str): Fielding position handling the ground ball.

    Returns:
        None
    """
    team = fielding_team(state)
    fielder = fielder_at(team, position)
    batter, batter_id = current_batter(state)
    runners = lineup(batting_team(state))
    bases = state.bases[:]
    outs_before = state.outs
    spot = spot_text(position, fielder)

    if random.random() < error_chance(fielder, "ground"):
        reach_on_error(state, position, fielder, batter, batter_id)
        return

    if bases[0] != EMPTY and outs_before < 2 \
            and random.random() < double_play_chance(position, fielder, batter):
        bases[0] = EMPTY
        runs = 0
        if outs_before == 0:
            if bases[2] != EMPTY:
                runs += 1
                bases[2] = EMPTY
            if bases[1] != EMPTY:
                bases[2] = bases[1]
                bases[1] = EMPTY
        text = f"Double play! {batter.name} grounds to {spot} and two are out."
        if runs:
            text += " A run scores."
        finish_play(state, batter, bases, runs, 2, text, rbi_credit=False)
        return

    if bases[0] != EMPTY and outs_before < 2 and random.random() < 0.35:
        runs = 0
        if bases[1] != EMPTY:
            if bases[2] != EMPTY:
                runs = 1
            bases[2] = bases[1]
            bases[1] = EMPTY
        bases[0] = batter_id
        text = f"Fielder's choice. {spot} gets the runner at second and {batter.name} is safe at first."
        if runs:
            text += " A run scores."
        finish_play(state, batter, bases, runs, 1, text)
        return

    runs = 0
    notes = []
    if outs_before + 1 < 3:
        if bases[2] != EMPTY and not (bases[0] != EMPTY and bases[1] != EMPTY):
            runner = runners[bases[2]]
            chance = clamp(0.70 + (runner.speed - 50) / 200
                           - (0.30 if position == "3B" else 0.0), 0.15, 0.95)
            if random.random() < chance:
                runs += 1
                bases[2] = EMPTY
                notes.append(f"{runner.name} scores from third.")
        if bases[1] != EMPTY and bases[0] == EMPTY and bases[2] == EMPTY:
            runner = runners[bases[1]]
            base_chance = {"1B": 0.85, "2B": 0.90, "SS": 0.30, "3B": 0.15}.get(position, 0.0)
            if random.random() < clamp(base_chance + (runner.speed - 50) / 300, 0.05, 0.95):
                bases[2] = bases[1]
                bases[1] = EMPTY
                notes.append(f"{runner.name} moves up to third.")
        bases, forced_runs = force_advance(bases)
        if forced_runs:
            notes.append("A run is forced in.")
        runs += forced_runs
    text = f"{batter.name} grounds out to {spot}. " + " ".join(notes)
    finish_play(state, batter, bases, runs, 1, text.strip())


def resolve_fly_ball(state: State, position: str):
    """
    Process outfield fly ball outcomes including tag-ups, sacrifice flies, and catches.

    Args:
        state (State): Current game State.
        position (str): Outfield position catching the ball.

    Returns:
        None
    """
    team = fielding_team(state)
    fielder = fielder_at(team, position)
    batter, batter_id = current_batter(state)
    runners = lineup(batting_team(state))
    bases = state.bases[:]
    outs_before = state.outs
    spot = spot_text(position, fielder)

    if random.random() < error_chance(fielder, "fly"):
        reach_on_error(state, position, fielder, batter, batter_id)
        return

    depth = roll({"deep": 0.40, "medium": 0.35, "shallow": 0.25})
    runs = 0
    extra_outs = 0
    notes = []
    if outs_before + 1 < 3:
        arm_term = (fielder.fielding - 50) / 250
        base_chance = {"deep": 0.90, "medium": 0.65, "shallow": 0.25}[depth]
        if bases[2] != EMPTY:
            runner = runners[bases[2]]
            chance = clamp(base_chance + (runner.speed - 50) / 200 - arm_term, 0.05, 0.95)
            if chance >= 0.45:
                bases[2] = EMPTY
                if random.random() < chance + 0.10:
                    runs += 1
                    notes.append(f"{runner.name} tags up and scores.")
                else:
                    extra_outs += 1
                    notes.append(f"{runner.name} is thrown out at the plate!")
        if bases[1] != EMPTY and bases[2] == EMPTY and depth == "deep" \
                and outs_before + 1 + extra_outs < 3:
            runner = runners[bases[1]]
            chance = clamp(0.60 + (runner.speed - 50) / 200 - arm_term, 0.10, 0.90)
            bases[1] = EMPTY
            if random.random() < chance:
                bases[2] = runner_id_of(runners, runner)
                notes.append(f"{runner.name} tags up and moves to third.")
            else:
                extra_outs += 1
                notes.append(f"{runner.name} is thrown out at third!")
    if outs_before + 1 + extra_outs >= 3:
        runs = 0
    sac_fly = runs > 0
    text = (f"Sacrifice fly! {batter.name} flies out to {spot}. " if sac_fly
            else f"{batter.name} flies out to {spot} ({depth} fly ball). ") + " ".join(notes)
    finish_play(state, batter, bases, runs, 1 + extra_outs, text.strip(),
                counts_as_at_bat=not sac_fly)


def runner_id_of(runners: list, runner: Hitter) -> int:
    """
    Find the lineup index of a specific runner Hitter object.

    Args:
        runners (list[Hitter]): List of hitters in the lineup.
        runner (Hitter): The runner to locate.

    Returns:
        int: Lineup index or EMPTY (-1) if not found.
    """
    for index, hitter in enumerate(runners):
        if hitter is runner:
            return index
    return EMPTY


def resolve_line_drive(state: State, position: str):
    """
    Resolve line drive catches and potential double plays on runners at first.

    Args:
        state (State): Current game State.
        position (str): Fielding position making the catch.

    Returns:
        None
    """
    fielder = fielder_at(fielding_team(state), position)
    batter, _ = current_batter(state)
    bases = state.bases[:]
    extra_outs = 0
    text = f"{batter.name} lines out to {spot_text(position, fielder)}."
    if bases[0] != EMPTY and state.outs < 2 and random.random() < 0.12:
        bases[0] = EMPTY
        extra_outs = 1
        text += " The runner at first is doubled off!"
    finish_play(state, batter, bases, 0, 1 + extra_outs, text)


def resolve_pop_up(state: State, position: str):
    """
    Resolve infield pop-up catches and verify application of the infield fly rule.

    Args:
        state (State): Current game State.
        position (str): Infield position catching the pop-up.

    Returns:
        None
    """
    fielder = fielder_at(fielding_team(state), position)
    batter, _ = current_batter(state)
    text = f"{batter.name} pops out to {spot_text(position, fielder)}."
    if state.bases[0] != EMPTY and state.bases[1] != EMPTY and state.outs < 2:
        text += " Infield fly rule: the batter is out and the runners hold."
    finish_play(state, batter, state.bases[:], 0, 1, text)


def pick_hit_spot(outcome: str) -> str:
    """
    Select where a batted hit ball lands on the field.

    Args:
        outcome (str): The hit type (e.g., 'single').

    Returns:
        str: Position code representing the hit location.
    """
    if outcome == "single" and random.random() < 0.20:
        return roll(GROUND_SPOTS)
    return roll(OUTFIELD_SPOTS)


def hit_fielder(state: State):
    """
    Retrieve the fielder who handled the most recent single or double hit.

    Args:
        state (State): Current game State.

    Returns:
        Hitter | None: The fielding Hitter or None.
    """
    if state.hit_location:
        return fielder_at(fielding_team(state), state.hit_location)
    return None


def arm_rating(state: State) -> float:
    """
    Get the arm fielding rating of the player who handled the hit, or outfield average.

    Args:
        state (State): Current game State.

    Returns:
        float: Fielding rating score.
    """
    fielder = hit_fielder(state)
    return fielder.fielding if fielder else outfield_arm(state)


def hit_spot_text(state: State) -> str:
    """
    Generate text describing the exact location where the last hit was fielded.

    Args:
        state (State): Current game State.

    Returns:
        str: Description of hit spot.
    """
    fielder = hit_fielder(state)
    if fielder:
        return spot_text(state.hit_location, fielder)
    return "the outfield"


def add_hit(state: State, outcome: str):
    """
    Record a hit outcome, advance runners, score runs, and set up potential extra base choices.

    Args:
        state (State): Current game State.
        outcome (str): Hit classification ('single', 'double', 'triple', 'homer').

    Returns:
        None
    """
    batter, batter_id = current_batter(state)
    spot = pick_hit_spot(outcome)
    state.bases, runs = advance_runners(state.bases, ADVANCE[outcome], batter_id)
    add_runs(state, runs)
    add_hit_to_total(state)
    batter.at_bats += 1
    batter.hits += 1
    batter.rbi += runs
    if outcome == "homer":
        batter.home_runs += 1
    reset_count(state)
    next_batter(state)

    where = POSITION_NAMES[spot]
    if outcome == "homer":
        text = f"{batter.name} hits a home run over the fence in {where}!"
    elif outcome == "single" and spot in GROUND_SPOTS:
        text = f"{batter.name} beats out an infield single to {where}!"
    else:
        text = f"{batter.name} {'singles' if outcome == 'single' else outcome + 's'} to {where}!"
    say(state, f"{text} ({runs} run(s) scored)")
    if outcome in ("single", "double") and not state.game_over:
        state.pending_hit = outcome
        state.hit_location = spot


def add_strike(state: State, text: str):
    """
    Add a strike to the batter's count, triggering a strikeout if count reaches three.

    Args:
        state (State): Current game State.
        text (str): Play message description.

    Returns:
        None
    """
    state.strikes += 1
    if state.strikes >= 3:
        batter, _ = current_batter(state)
        batter.at_bats += 1
        batter.strikeouts += 1
        batter_out_message(state, text + f" Strike three, {batter.name} is out!")
    else:
        say(state, text)


def add_ball(state: State):
    """
    Add a ball to the count, awarding a walk if balls reach four.

    Args:
        state (State): Current game State.

    Returns:
        None
    """
    state.balls += 1
    if state.balls >= 4:
        batter, batter_id = current_batter(state)
        state.bases, runs = walk_runners(state.bases, batter_id)
        add_runs(state, runs)
        batter.walks += 1
        batter.rbi += runs
        reset_count(state)
        next_batter(state)
        say(state, f"Ball four. {batter.name} takes his base!")
    else:
        say(state, "Ball.")


# ---------------------------------------------------------------------------
# Baserunning helpers
# ---------------------------------------------------------------------------
def can_steal_second(state: State) -> bool:
    """
    Check if a steal attempt of second base is legal (runner on first, second open).

    Args:
        state (State): Current game State.

    Returns:
        bool: True if steal is legal, False otherwise.
    """
    return state.bases[0] != EMPTY and state.bases[1] == EMPTY


def can_steal_third(state: State) -> bool:
    """
    Check if a steal attempt of third base is legal (runner on second, third open).

    Args:
        state (State): Current game State.

    Returns:
        bool: True if steal is legal, False otherwise.
    """
    return state.bases[1] != EMPTY and state.bases[2] == EMPTY


def rating_label(value: int) -> str:
    """
    Convert a numerical player rating (1-99) into a readable descriptive label.

    Args:
        value (int): The rating integer.

    Returns:
        str: Textual description (e.g., 'excellent', 'good').
    """
    if value >= 80:
        return "excellent"
    if value >= 65:
        return "good"
    if value >= 45:
        return "average"
    if value >= 30:
        return "below average"
    return "poor"


def percent(chance: float) -> str:
    """
    Format a probability float (0.0 to 1.0) as a whole-number percentage string.

    Args:
        chance (float): Probability value.

    Returns:
        str: Formatted percentage string (e.g., '50%').
    """
    return f"{round(chance * 100)}%"


def runner_on(state: State, base: int) -> Hitter:
    """
    Retrieve the Hitter occupying a specific base.

    Args:
        state (State): Current game State.
        base (int): Base index (0 for 1st, 1 for 2nd, 2 for 3rd).

    Returns:
        Hitter: The player standing on that base.
    """
    return lineup(batting_team(state))[state.bases[base]]


def runner_lines(state: State) -> list:
    """
    Generate display text lines detailing each runner currently on base.

    Args:
        state (State): Current game State.

    Returns:
        list: List of text strings and line breaks describing base runners.
    """
    names = ["1st", "2nd", "3rd"]
    lines = []
    for base in range(3):
        if state.bases[base] != EMPTY:
            runner = runner_on(state, base)
            lines += [f"{names[base]}: {runner.name} (#{runner.number} {runner.position}), "
                      f"SPD {runner.speed} ({rating_label(runner.speed)})",
                      LineBreak()]
    return lines


def steal_chance(state: State, from_base: int) -> float:
    """
    Calculate the success probability for a base stealing attempt.

    Args:
        state (State): Current game State.
        from_base (int): Base origin index.

    Returns:
        float: Success probability bounded between 0.20 and 0.90.
    """
    runner = runner_on(state, from_base)
    catcher = fielding_team(state).catcher
    return clamp(0.55 + (runner.speed - 50) / 150 - (catcher.fielding - 50) / 200, 0.20, 0.90)


def outfield_arm(state: State) -> float:
    """
    Calculate the average fielding arm rating of the three outfielders.

    Args:
        state (State): Current game State.

    Returns:
        float: Average outfield fielding rating.
    """
    team = fielding_team(state)
    return (team.left_field.fielding + team.center_field.fielding
            + team.right_field.fielding) / 3


def send_chance(state: State, base: int) -> float:
    """
    Calculate the probability that a runner successfully takes an extra base after a hit.

    Args:
        state (State): Current game State.
        base (int): Base index of the runner.

    Returns:
        float: Success probability.
    """
    runner = runner_on(state, base)
    chance = 0.50 + (runner.speed - 50) / 150 - (arm_rating(state) - 50) / 200
    if state.hit_location in GROUND_SPOTS:
        chance -= 0.15
    if state.outs == 2:
        chance += 0.10
    return clamp(chance, 0.15, 0.90)


def attempt_steal(state: State, from_base: int):
    """
    Execute a base-stealing attempt, resulting in either a safe steal or a caught-stealing out.

    Args:
        state (State): Current game State.
        from_base (int): Origin base index.

    Returns:
        None
    """
    runner_id = state.bases[from_base]
    runner = runner_on(state, from_base)
    chance = steal_chance(state, from_base)
    state.bases[from_base] = EMPTY
    if random.random() < chance:
        state.bases[from_base + 1] = runner_id
        say(state, f"Stolen base! {runner.name} is safe.")
    else:
        state.outs += 1
        say(state, f"Caught stealing! {runner.name} is out.")
        end_half_inning_if_needed(state)


def pitcher_status(pitcher: Pitcher) -> str:
    """
    Describe a pitcher's stamina and fatigue status based on pitches thrown.

    Args:
        pitcher (Pitcher): The Pitcher to evaluate.

    Returns:
        str: Status message description.
    """
    limit = 40 + pitcher.stamina
    left = limit - pitcher.pitches_thrown
    if left < 0:
        return "TIRED - his pitches are getting worse"
    if left <= 15:
        return f"getting tired (about {left} pitches until he tires)"
    return "fresh"


def pitcher_label(number: int, pitcher: Pitcher) -> str:
    """
    Format a description string for a pitcher option in selection menus.

    Args:
        number (int): Pitcher bullpen index number.
        pitcher (Pitcher): The Pitcher instance.

    Returns:
        str: Formatted label string.
    """
    return (f"Reliever {number}: {pitcher.name} - VEL {pitcher.velocity}, CTL {pitcher.control}, "
            f"MOV {pitcher.movement}, STA {pitcher.stamina}")


def pitching_options(team: Team) -> list[str]:
    """
    Generate a list of formatted string options for available relief pitchers in the bullpen.

    Args:
        team (Team): The fielding Team.

    Returns:
        list[str]: List of reliever descriptions.
    """
    options = []
    for number, pitcher in enumerate(team.pitchers):
        if number == 0:
            continue
        options.append(pitcher_label(number, pitcher))
    return options


# ---------------------------------------------------------------------------
# UI Page-building helpers
# ---------------------------------------------------------------------------
def banner(title: str, subtitle: str = "", color: str = GREEN, text_color: str = "white"):
    """
    Create a styled title header banner container element.

    Args:
        title (str): Main title text.
        subtitle (str): Optional subtitle text.
        color (str): Background CSS color hex code.
        text_color (str): Text CSS color code.

    Returns:
        Div: Drafter Div component containing the banner.
    """
    parts: list[Component] = [Header(title, 1, style_color=text_color, style_margin="0")]
    if subtitle:
        parts.append(Div(subtitle, style_color=text_color, style_margin_top="4px"))
    return Div(*parts, style_background_color=color, style_padding="16px 22px",
               style_border_radius="12px", style_margin_bottom="14px",
               style_box_shadow="0 3px 8px rgba(0,0,0,0.25)")


def card(*content, color: str = "white", border: str = "#d5dcc8", **extra_style):
    """
    Create a styled rounded container card element.

    Args:
        *content: Elements to place inside the card.
        color (str): Card background color.
        border (str): Border color style.
        **extra_style: Additional CSS styling parameters.

    Returns:
        Div: Drafter Div container card.
    """
    return Div(*content, style_background_color=color, style_border=f"2px solid {border}",
               style_border_radius="12px", style_padding="12px 18px", style_margin="10px 0",
               style_box_shadow="0 1px 4px rgba(0,0,0,0.12)", **extra_style)


def pill(text: str, color: str = NAVY, text_color: str = "white"):
    """
    Create a small rounded badge/pill label component.

    Args:
        text (str): Label text.
        color (str): Background color.
        text_color (str): Text color.

    Returns:
        Span: Drafter Span component.
    """
    return Span(text, style_background_color=color, style_color=text_color,
                style_padding="3px 12px", style_border_radius="999px",
                style_margin_right="6px", style_font_weight="bold",
                style_display="inline-block")


def dots(filled: int, total: int, color: str):
    """
    Render a row of filled and empty indicator circles (scoreboard lights).

    Args:
        filled (int): Number of filled circles.
        total (int): Total number of circles.
        color (str): Color of filled circles.

    Returns:
        Span: Drafter Span containing indicator dots.
    """
    circles = [Span("\u25cf" if i < filled else "\u25cb", style_color=color,
                    style_font_size="1.4rem", style_margin_right="4px")
               for i in range(total)]
    return Span(*circles)


def energy_bar(pitcher: Pitcher):
    """
    Render a progress bar displaying a pitcher's remaining stamina energy.

    Args:
        pitcher (Pitcher): The Pitcher instance.

    Returns:
        Div: Drafter Div energy bar component.
    """
    limit = 40 + pitcher.stamina
    energy = clamp(100 * (limit - pitcher.pitches_thrown) / limit, 0, 100)
    color = GREEN if energy > 40 else (GOLD if energy > 15 else RED)
    return Div(Div("", style_width=f"{round(energy)}%", style_height="10px",
                   style_background_color=color, style_border_radius="999px"),
               style_width="100%", style_background_color="#e3e8dc",
               style_border_radius="999px", style_margin_top="4px")


def diamond_image(state: State):
    """
    Generate an SVG image depicting the baseball diamond with current base runner indicators.

    Args:
        state (State): Current game State.

    Returns:
        Image: Drafter Image component containing the SVG data URI.
    """
    runners = lineup(batting_team(state))
    spots = [(168, 104), (100, 36), (32, 104)]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 190">',
             '<rect width="200" height="190" rx="14" fill="#3f8f3f"/>',
             '<polygon points="100,172 168,104 100,36 32,104" fill="#d9b382" '
             'stroke="white" stroke-width="3"/>',
             '<circle cx="100" cy="104" r="9" fill="#c49a68"/>']
    for i, (x, y) in enumerate(spots):
        runner_id = state.bases[i]
        fill = "#f4b942" if runner_id != EMPTY else "white"
        parts.append(f'<rect x="{x - 11}" y="{y - 11}" width="22" height="22" fill="{fill}" '
                     f'stroke="#14213d" stroke-width="2" transform="rotate(45 {x} {y})"/>')
        if runner_id != EMPTY:
            parts.append(f'<text x="{x}" y="{y + 4}" font-size="11" font-weight="bold" '
                         f'text-anchor="middle" fill="#14213d" font-family="Arial">'
                         f'{runners[runner_id].number}</text>')
    parts.append('<polygon points="100,164 108,171 105,180 95,180 92,171" fill="white" '
                 'stroke="#14213d" stroke-width="2"/>')
    parts.append("</svg>")
    return Image("data:image/svg+xml;utf8," + quote("".join(parts)), width=190,
                 alt="Baseball diamond showing the runners on base")


def score_box(name: str, score: int, is_batting: bool):
    """
    Create a scoreboard team box highlighting the batting team in gold.

    Args:
        name (str): Team name label.
        score (int): Current runs score.
        is_batting (bool): Whether this team is currently batting.

    Returns:
        Div: Drafter Div component.
    """
    return Div(Div(name, style_font_size="0.95rem"),
               Div(str(score), style_font_size="2.2rem", style_font_weight="bold"),
               style_flex="1", style_text_align="center", style_padding="8px",
               style_background_color=GOLD if is_batting else "white",
               style_border=f"2px solid {NAVY}", style_border_radius="10px",
               style_box_shadow="0 1px 4px rgba(0,0,0,0.15)")


def scoreboard(state: State) -> list:
    """
    Render the complete game scoreboard including scores, inning indicator, counts, and diamond.

    Args:
        state (State): Current game State.

    Returns:
        list: List of Drafter UI components representing the scoreboard.
    """
    arrow = "\u25b2 Top" if state.top_of_inning else "\u25bc Bottom"
    middle = Div(Div(arrow), Div(f"Inning {state.inning}", style_font_weight="bold"),
                 Div(f"of {INNINGS}", style_font_size="0.85rem"),
                 style_flex="1", style_text_align="center", style_padding="8px",
                 style_background_color=NAVY, style_color="white", style_border_radius="10px")
    score_row = Row(score_box(state.away_name + " (away)", state.away_score, state.top_of_inning),
                    middle,
                    score_box(state.home_name + " (home)", state.home_score, not state.top_of_inning),
                    style_gap="10px", style_margin="10px 0")
    count_card = card(
        Div(Strong("Balls   "), dots(state.balls, 3, GREEN)),
        Div(Strong("Strikes "), dots(state.strikes, 2, RED)),
        Div(Strong("Outs     "), dots(state.outs, 2, NAVY)),
        style_flex="1")
    field_row = Row(count_card, Div(diamond_image(state), style_text_align="center"),
                    style_gap="10px", style_align_items="center")
    return [score_row, field_row]


def play_colors(text: str) -> tuple:
    """
    Determine color theme (background and border) based on play outcome description.

    Args:
        text (str): Play description message.

    Returns:
        tuple[str, str]: Tuple of color hex strings (background, border).
    """
    bad = ["Double play", "Caught stealing", "thrown out", "doubled off", "Strike three"]
    good = ["scores", "home run", "singles", "doubles", "triples", "beats out", "Stolen base",
            "extra base", "Ball four", "Error"]
    if any(word in text for word in bad):
        return "#fdecea", RED
    if any(word in text for word in good):
        return "#e8f5e9", GREEN
    if " out" in text or "Fielder's choice" in text:
        return "#fdecea", RED
    return "#fff8e1", GOLD


def last_play_card(state: State) -> list:
    """
    Render a color-coded summary card for the most recent play event.

    Args:
        state (State): Current game State.

    Returns:
        list: List containing the card component if a message exists.
    """
    if not state.message:
        return []
    background, border = play_colors(state.message)
    return [card(Strong("Last play: "), state.message, color=background, border=border)]


def recent_plays_card(state: State) -> list:
    """
    Render a scroll log card showing recent notable plays prior to the last one.

    Args:
        state (State): Current game State.

    Returns:
        list: List containing the play log card component.
    """
    earlier = state.play_log[-6:-1][::-1]
    if not earlier:
        return []
    lines = []
    for entry in earlier:
        lines += [SmallText(entry), LineBreak()]
    return [card(Strong("Earlier plays"), LineBreak(), *lines, color="#f4f8ef")]


def player_of_the_game(state: State) -> Hitter:
    """
    Determine the best-performing player of the game based on offensive statistics.

    Args:
        state (State): Current game State.

    Returns:
        Hitter: The standout Hitter instance.
    """
    everyone = lineup(state.teams[0]) + lineup(state.teams[1])
    return max(everyone, key=lambda h: h.hits + 2 * h.home_runs + h.rbi + 0.5 * h.walks)


# ---------------------------------------------------------------------------
# Drafter Routes
# ---------------------------------------------------------------------------
@route
def index(state: State) -> Page:
    """
    Title screen route where players enter their names and select difficulty settings.

    Args:
        state (State): Current game State.

    Returns:
        Page: Drafter Page object for the title screen.
    """
    content = [banner("Drafter Baseball", "Two players. One screen. Nine innings.")]
    if state.message:
        content += [card(Strong(state.message), color="#fdecea", border=RED)]
    content += [
        card(
            Strong("Player 1 (away, bats first)"),
            LineBreak(),
            TextBox("away_name", state.away_name),
            LineBreak(),
            Strong("Player 2 (home)"),
            LineBreak(),
            TextBox("home_name", state.home_name),
            LineBreak(),
            Strong("Difficulty"),
            " (type 1 = easy, 2 = medium, 3 = hard)",
            LineBreak(),
            TextBox("difficulty", str(state.difficulty)),
            LineBreak(),
            Button("Start game", start_game, style_background_color=GREEN),
        ),
        card(
            Strong("How to play"),
            BulletedList([
                "The player on defense picks the pitch.",
                "The player on offense chooses to swing or hold.",
                "On offense you can also steal and send or hold runners.",
                "On defense you can change pitchers when yours gets tired.",
            ]),
            color="#f4f8ef",
        ),
    ]
    return Page(state, content)


@route
def start_game(state: State, away_name: str, home_name: str, difficulty: str) -> Page:
    """
    Validate input parameters, generate teams, and start the game at the lineup setup screen.

    Args:
        state (State): Current game State.
        away_name (str): Away player input name.
        home_name (str): Home player input name.
        difficulty (str): Difficulty level input string.

    Returns:
        Page: Lineup setup page or title screen if invalid.
    """
    away_name = away_name.strip() or "Player 1"
    home_name = home_name.strip() or "Player 2"
    if difficulty.strip() not in ("1", "2", "3"):
        state.away_name = away_name
        state.home_name = home_name
        state.message = "Difficulty must be 1, 2, or 3. Please try again."
        return index(state)
    fresh = new_game(away_name, home_name, int(difficulty.strip()))
    return lineup_setup(fresh)


@route
def lineup_setup(state: State) -> Page:
    """
    Display team rosters, player ratings, and starting pitchers before starting play.

    Args:
        state (State): Current game State.

    Returns:
        Page: Lineup preview Page object.
    """
    content = [
        banner("Lineups", f"Difficulty level {state.difficulty}"),
        SmallText("Ratings are 1-99: CON = contact, PWR = power, FLD = fielding, SPD = speed."),
    ]
    names = [state.away_name, state.home_name]
    for team_number, team in enumerate(state.teams):
        rows: list[list[Component | str | int | float | bool]] = []
        for hitter in lineup(team):
            hitter_row: list[Component | str | int | float | bool] = [
                f"#{hitter.number}", hitter.name, hitter.position, hitter.contact,
                hitter.power, hitter.fielding, hitter.speed,
            ]
            rows.append(hitter_row)
        starter = team.pitchers[0]
        content += [card(
            Header(f"{names[team_number]}'s team", 2, style_margin_top="0"),
            Table(rows, header=["No.", "Name", "Pos", "CON", "PWR", "FLD", "SPD"]),
            LineBreak(),
            Strong("Starting pitcher: "),
            f"{starter.name} - VEL {starter.velocity}, CTL {starter.control}, "
            f"MOV {starter.movement}, STA {starter.stamina}",
            LineBreak(),
            f"Relievers available: {len(team.pitchers) - 1}",
        )]
    content += [Button("Play ball!", pitch_select, style_background_color=GREEN)]
    return Page(state, content)


@route
def pitch_select(state: State) -> Page:
    """
    Display the defense pitch selection screen, scoreboard, counts, and pitcher energy.

    Args:
        state (State): Current game State.

    Returns:
        Page: Pitch selection Page object.
    """
    if state.game_over:
        return game_over(state)

    batter, _ = current_batter(state)
    pitcher = fielding_team(state).pitchers[0]

    content = [banner("Pitch select", f"{pitching_name(state)} is pitching")]
    content += scoreboard(state)
    content += last_play_card(state)
    content += [Row(
        card(Strong("At bat: "), batter.name, LineBreak(),
             f"#{batter.number} {batter.position} ({batting_name(state)}'s team)", LineBreak(),
             f"CON {batter.contact}, PWR {batter.power}, SPD {batter.speed}", LineBreak(),
             Strong("Today: "), stat_line(batter),
             style_flex="1"),
        card(Strong("On the mound: "), pitcher.name, LineBreak(),
             f"VEL {pitcher.velocity}, CTL {pitcher.control}, MOV {pitcher.movement}", LineBreak(),
             f"{pitcher.pitches_thrown} pitches ({pitcher_status(pitcher)})",
             energy_bar(pitcher)),
        style_gap="10px", style_align_items="stretch")]
    if lead_runner(state.bases) != -1:
        content += [card(Strong("Runners on base"), LineBreak(), *runner_lines(state))]
    content += [card(
        Strong(f"{pitching_name(state)}, choose a pitch"),
        LineBreak(),
        Button("Fastball", throw_fastball, style_background_color=RED),
        Button("Curveball", throw_curveball, style_background_color=BLUE),
        Button("Slider", throw_slider, style_background_color=GREEN),
        Button("Changeup", throw_changeup, style_background_color=PURPLE),
        LineBreak(),
        SmallText("Fastball: most strikes, but easier to hit. Curveball: hard to hit, fewer "
                  "strikes. Slider: a balance of both. Changeup: hardest to hit."),
    )]

    options = []
    if can_steal_second(state) or can_steal_third(state):
        options += [Button("Baserunning options (steal)", baserunning_choice,
                           style_background_color=GOLD, style_color=NAVY)]
    if len(fielding_team(state).pitchers) > 1:
        options += [Button("Pitching change", substitutions,
                           style_background_color=GRAY)]
    if options:
        content += [card(Strong("Other options"), LineBreak(), *options)]

    content += recent_plays_card(state)
    return Page(state, content)


def choose_pitch(state: State, pitch: str) -> Page:
    """
    Record the chosen pitch in state and advance to the offensive swing/hold screen.

    Args:
        state (State): Current game State.
        pitch (str): Name of the selected pitch.

    Returns:
        Page: Swing or hold Page object.
    """
    state.current_pitch = pitch
    return swing_or_hold(state)


@route
def throw_fastball(state: State) -> Page:
    """Route handler for throwing a Fastball."""
    return choose_pitch(state, "Fastball")


@route
def throw_curveball(state: State) -> Page:
    """Route handler for throwing a Curveball."""
    return choose_pitch(state, "Curveball")


@route
def throw_slider(state: State) -> Page:
    """Route handler for throwing a Slider."""
    return choose_pitch(state, "Slider")


@route
def throw_changeup(state: State) -> Page:
    """Route handler for throwing a Changeup."""
    return choose_pitch(state, "Changeup")


@route
def swing_or_hold(state: State) -> Page:
    """
    Display the offensive swing or hold decision screen for the batter.

    Args:
        state (State): Current game State.

    Returns:
        Page: Swing or hold decision Page object.
    """
    batter, _ = current_batter(state)
    content = [banner("Swing or hold", f"{batting_name(state)}, you're up. "
                                       "(Pitcher: look away!)", color=BLUE)]
    content += scoreboard(state)
    content += [
        card(Strong("At the plate: "), batter.name, LineBreak(),
             f"#{batter.number} {batter.position}: CON {batter.contact}, PWR {batter.power}, "
             f"SPD {batter.speed}",
             LineBreak(),
             Strong("Today: "), stat_line(batter)),
        card(Strong("The pitch is on its way..."), LineBreak(),
             Button("Swing", do_swing, style_background_color=GREEN),
             Button("Hold", do_hold, style_background_color=GRAY),
             LineBreak(),
             SmallText("Tip: holding can draw a walk, but a strike you hold on still "
                       "counts against you.")),
    ]
    return Page(state, content)


def next_page(state: State) -> Page:
    """
    Determine the next screen route following a pitch resolution (game over, baserunning, or pitch select).

    Args:
        state (State): Current game State.

    Returns:
        Page: The next Page object.
    """
    if state.game_over:
        return game_over(state)
    if state.pending_hit:
        return baserunning_choice(state)
    return pitch_select(state)


@route
def do_swing(state: State) -> Page:
    """Route handler when the batter chooses to swing."""
    resolve_pitch(state, swing=True)
    return next_page(state)


@route
def do_hold(state: State) -> Page:
    """Route handler when the batter chooses to hold."""
    resolve_pitch(state, swing=False)
    return next_page(state)


@route
def baserunning_choice(state: State) -> Page:
    """
    Display base stealing options or extra-base send/hold decisions following a hit.

    Args:
        state (State): Current game State.

    Returns:
        Page: Baserunning choices Page object.
    """
    content = [banner("Baserunning choice", f"{batting_name(state)}, your call", color=GOLD,
                      text_color=NAVY)]
    content += scoreboard(state)

    if state.pending_hit and lead_runner(state.bases) != -1:
        lead = lead_runner(state.bases)
        runner = runner_on(state, lead)
        arm = arm_rating(state)
        two_outs = " (two outs, so runners are going)" if state.outs == 2 else ""
        content += last_play_card(state)
        content += [card(
            Strong("Your lead runner can try for an extra base"),
            LineBreak(),
            f"Runner: {runner.name} (#{runner.number} {runner.position}), SPD {runner.speed} "
            f"({rating_label(runner.speed)})",
            LineBreak(),
            f"Ball hit to {hit_spot_text(state)}: arm {round(arm)} ({rating_label(round(arm))})",
            LineBreak(),
            Strong(f"Chance he makes it: {percent(send_chance(state, lead))}"),
            two_outs,
            LineBreak(),
            SmallText("If he is thrown out, it counts as an out. Holding him is always safe."),
            LineBreak(),
            Button("Send the runner", send_runner, style_background_color=GREEN),
            Button("Hold the runner", hold_runner, style_background_color=GRAY),
        )]
        return Page(state, content)

    if can_steal_second(state) or can_steal_third(state):
        catcher = fielding_team(state).catcher
        content += [card(Strong("Catcher's arm: "),
                         f"{catcher.name}, {catcher.fielding} ({rating_label(catcher.fielding)})")]
        if can_steal_second(state):
            runner = runner_on(state, 0)
            content += [card(
                Strong("Runner on 1st: "), runner.name, LineBreak(),
                f"#{runner.number} {runner.position}, SPD {runner.speed} "
                f"({rating_label(runner.speed)})",
                LineBreak(),
                Button(f"Steal second ({percent(steal_chance(state, 0))} chance)",
                       steal_second, style_background_color=GREEN))]
        if can_steal_third(state):
            runner = runner_on(state, 1)
            content += [card(
                Strong("Runner on 2nd: "), runner.name, LineBreak(),
                f"#{runner.number} {runner.position}, SPD {runner.speed} "
                f"({rating_label(runner.speed)})",
                LineBreak(),
                Button(f"Steal third ({percent(steal_chance(state, 1))} chance)",
                       steal_third, style_background_color=GREEN))]
        content += [SmallText("If a runner is caught, it is an out."), LineBreak(),
                    Button("No steal", pitch_select, style_background_color=GRAY)]
    else:
        content += [card("No steal is possible right now."),
                    Button("Back", pitch_select, style_background_color=GRAY)]
    return Page(state, content)


@route
def steal_second(state: State) -> Page:
    """Route handler for attempting a steal of second base."""
    if can_steal_second(state):
        attempt_steal(state, 0)
    return pitch_select(state)


@route
def steal_third(state: State) -> Page:
    """Route handler for attempting a steal of third base."""
    if can_steal_third(state):
        attempt_steal(state, 1)
    return pitch_select(state)


@route
def send_runner(state: State) -> Page:
    """Route handler when the offense chooses to send the runner for an extra base."""
    lead = lead_runner(state.bases)
    if state.pending_hit and lead != -1:
        runner_id = state.bases[lead]
        runner = runner_on(state, lead)
        chance = send_chance(state, lead)
        state.pending_hit = ""
        state.hit_location = ""
        state.bases[lead] = EMPTY
        if random.random() < chance:
            if lead == 2:
                add_runs(state, 1)
                say(state, f"{runner.name} is sent home and scores!")
            else:
                state.bases[lead + 1] = runner_id
                say(state, f"{runner.name} is sent and takes the extra base!")
        else:
            state.outs += 1
            say(state, f"{runner.name} is thrown out trying for the extra base!")
            end_half_inning_if_needed(state)
    return next_page(state)


@route
def hold_runner(state: State) -> Page:
    """Route handler when the offense chooses to hold runners after a hit."""
    state.pending_hit = ""
    state.hit_location = ""
    state.message += " Runners hold."
    if state.play_log:
        state.play_log[-1] += " Runners hold."
    return pitch_select(state)


@route
def substitutions(state: State) -> Page:
    """
    Display the pitching change substitution screen to select a reliever from the bullpen.

    Args:
        state (State): Current game State.

    Returns:
        Page: Substitution menu Page object.
    """
    team = fielding_team(state)
    options = pitching_options(team)
    current = team.pitchers[0]

    content = [
        banner("Pitching change", f"{pitching_name(state)}, choose your reliever", color=GRAY),
        card(Strong("Pitcher on the mound: "), current.name, LineBreak(),
             f"VEL {current.velocity}, CTL {current.control}, MOV {current.movement}, "
             f"STA {current.stamina}",
             LineBreak(),
             f"Pitches thrown: {current.pitches_thrown} ({pitcher_status(current)})",
             energy_bar(current)),
    ]
    if options:
        content += [card(
            Strong("Choose a relief pitcher"),
            LineBreak(),
            SmallText("The pitcher you replace cannot come back."),
            LineBreak(),
            SelectBox("new_pitcher", options, options[0]),
            LineBreak(),
            Button("Make the change", make_pitching_change, style_background_color=GREEN),
            Button("Cancel", pitch_select, style_background_color=GRAY),
        )]
    else:
        content += [card("There are no relievers left."),
                    Button("Back", pitch_select, style_background_color=GRAY)]
    return Page(state, content)


@route
def make_pitching_change(state: State, new_pitcher: str) -> Page:
    """
    Swap out the current pitcher for the selected relief pitcher from the bullpen.

    Args:
        state (State): Current game State.
        new_pitcher (str): Selected reliever label string.

    Returns:
        Page: Return to pitch select Page.
    """
    team = fielding_team(state)
    for number, pitcher in enumerate(team.pitchers):
        if number > 0 and pitcher_label(number, pitcher) == new_pitcher:
            chosen = team.pitchers.pop(number)
            team.pitchers.pop(0)
            team.pitchers.insert(0, chosen)
            say(state, f"{pitching_name(state)} brings in {chosen.name} to pitch.")
            break
    return pitch_select(state)


@route
def game_over(state: State) -> Page:
    """
    Display the final game summary screen, winner announcement, box score table, and player of the game.

    Args:
        state (State): Current game State.

    Returns:
        Page: Game over summary Page object.
    """
    if state.away_score > state.home_score:
        winner, loser = state.away_name, state.home_name
    elif state.home_score > state.away_score:
        winner, loser = state.home_name, state.away_name
    else:
        winner, loser = "", ""

    if winner:
        content = [banner(f"{winner} wins!", f"Better luck next time, {loser}.",
                          color=GOLD, text_color=NAVY)]
    else:
        content = [banner("It's a tie!", "What a game.", color=GOLD, text_color=NAVY)]

    star = player_of_the_game(state)
    innings = len(state.away_line)
    header = ["Team"] + [str(i + 1) for i in range(innings)] + ["R", "H"]

    # Each row is declared with the exact type that Table expects, so the type checker
    # does not have to guess (it would otherwise infer list[int | str]).
    away_row: list[Component | str | int | float | bool] = [state.away_name]
    home_row: list[Component | str | int | float | bool] = [state.home_name]
    for inning_index in range(innings):
        away_row.append(str(state.away_line[inning_index]))
        if state.home_skipped_last and inning_index == innings - 1:
            home_row.append("X")  # the home team did not need to bat
        else:
            home_row.append(str(state.home_line[inning_index]))
    away_row.append(state.away_score)
    away_row.append(state.away_hits)
    home_row.append(state.home_score)
    home_row.append(state.home_hits)
    rows: list[list[Component | str | int | float | bool]] = [away_row, home_row]
    content += [
        card(Div(f"{state.away_name} {state.away_score}  -  {state.home_score} {state.home_name}",
                 style_font_size="1.8rem", style_font_weight="bold", style_text_align="center")),
        card(Header("Box score", 2, style_margin_top="0"), Table(rows, header=header)),
        card(Strong("Player of the game: "), star.name, LineBreak(), stat_line(star),
             color="#fff8e1", border=GOLD),
        Button("Play again", play_again, style_background_color=GREEN),
    ]
    return Page(state, content)


@route
def play_again(state: State) -> Page:
    """
    Reset game state and return to the title screen to start a new game match.

    Args:
        state (State): Current game State.

    Returns:
        Page: Title screen index Page object.
    """
    fresh = State(away_name=state.away_name, home_name=state.home_name,
                  difficulty=state.difficulty)
    return index(fresh)


# ---------------------------------------------------------------------------
# Unit Tests (placed after all function definitions to prevent NameError)
# ---------------------------------------------------------------------------
_rand_hitter = make_hitter("Jake", "SS", 10, 2)
assert_equal(type(_rand_hitter), Hitter)
assert_equal(_rand_hitter.name, "Jake")

_rand_pitcher = make_pitcher("Mason", 2)
assert_equal(type(_rand_pitcher), Pitcher)
assert_equal(_rand_pitcher.name, "Mason")

# Deterministic baseline fixtures (ratings = 50) for probability/formula assertions
_test_hitter = Hitter("Jake", "SS", 10, 50, 50, 50, 50)
_test_pitcher = Pitcher("Mason", 50, 50, 50, 50, 50)

_test_team = make_team(2, NAME_POOL[:13])
assert_equal(type(_test_team), Team)
assert_equal(len(_test_team.pitchers), 5)

_test_state = new_game("Player A", "Player B", 2)
assert_equal(_test_state.away_name, "Player A")
assert_equal(_test_state.home_name, "Player B")

assert_equal(roll({"test": 1.0}), "test")
assert_equal(clamp(5.0, 0.0, 10.0), 5.0)
assert_equal(clamp(-2.0, 0.0, 10.0), 0.0)

_say_state = State()
say(_say_state, "Ball.")
assert_equal(_say_state.message, "Ball.")

assert_equal(len(lineup(_test_team)), 8)
assert_equal(batting_team(_test_state), _test_state.teams[0])
assert_equal(fielding_team(_test_state), _test_state.teams[1])
assert_equal(batting_name(_test_state), "Player A")
assert_equal(pitching_name(_test_state), "Player B")

_cb_batter, _cb_idx = current_batter(_test_state)
assert_equal(_cb_idx, 0)
assert_equal(_cb_batter, _test_state.teams[0].catcher)

_nb_state = State(away_batter=0, top_of_inning=True)
next_batter(_nb_state)
assert_equal(_nb_state.away_batter, 1)

assert_equal(team_defense(_test_team),
             sum([h.fielding for h in lineup(_test_team)]
                 + [_test_team.pitchers[0].fielding]) / 9)
assert_equal(stat_line(_test_hitter), "No at-bats yet today")

_ar_state = State(top_of_inning=True, away_score=0, away_line=[0])
add_runs(_ar_state, 2)
assert_equal(_ar_state.away_score, 2)

_aht_state = State(top_of_inning=True, away_hits=0)
add_hit_to_total(_aht_state)
assert_equal(_aht_state.away_hits, 1)

_adv_bases, _adv_runs = advance_runners([-1, -1, -1], 1, 0)
assert_equal(_adv_bases, [0, -1, -1])
assert_equal(_adv_runs, 0)

_walk_b, _walk_r = walk_runners([-1, -1, -1], 0)
assert_equal(_walk_b, [0, -1, -1])
assert_equal(_walk_r, 0)

assert_equal(bases_text([-1, -1, -1]), "Bases empty")
assert_equal(bases_text([0, -1, -1]), "Runners on: 1st")
assert_equal(lead_runner([-1, -1, -1]), -1)
assert_equal(lead_runner([0, 1, -1]), 1)

_rc_state = State(balls=3, strikes=2)
reset_count(_rc_state)
assert_equal(_rc_state.balls, 0)
assert_equal(_rc_state.strikes, 0)

_eh_state = State(outs=3, top_of_inning=True, inning=1)
end_half_inning_if_needed(_eh_state)
assert_equal(_eh_state.outs, 0)
assert_equal(_eh_state.top_of_inning, False)

_ro_state = State(outs=0, balls=2, strikes=2)
record_out(_ro_state)
assert_equal(_ro_state.outs, 1)
assert_equal(_ro_state.balls, 0)

_bom_state = State(outs=2)
batter_out_message(_bom_state, "Strikeout!")
assert_equal(_bom_state.message, "Strikeout!")

assert_equal(fatigue(_test_pitcher), 0.0)
assert_equal(round(strike_chance("Fastball", _test_pitcher), 2), 0.65)
assert_equal(round(contact_chance("Fastball", _test_pitcher, _test_hitter), 2), 0.8)

_cw = contact_weights(_test_hitter, 50.0)
assert_equal(_cw["foul"], 0.2)

_rp_state = new_game("P1", "P2", 2)
_rp_state.current_pitch = "Fastball"
resolve_pitch(_rp_state, False)
assert_equal(_rp_state.teams[1].pitchers[0].pitches_thrown, 1)

assert_equal(fielder_at(_test_team, "C"), _test_team.catcher)
assert_equal(spot_text("SS", _test_hitter), "shortstop (Jake)")

_fa_bases, _fa_runs = force_advance([0, -1, -1])
assert_equal(_fa_bases[1], 0)
assert_equal(_fa_runs, 0)

assert_equal(round(error_chance(_test_hitter, "ground"), 4), 0.04)
assert_equal(double_play_chance("SS", _test_hitter, _test_hitter), 0.5)

_fp_state = new_game("A", "B", 2)
finish_play(_fp_state, _test_hitter, [-1, -1, -1], 0, 1, "Out!")
assert_equal(_fp_state.outs, 1)

_roe_state = new_game("A", "B", 2)
reach_on_error(_roe_state, "SS", _test_hitter, _test_hitter, 0)
assert_equal(_roe_state.bases[0], 0)

_roip_state = new_game("A", "B", 2)
resolve_out_in_play(_roip_state)
assert_equal(_roip_state.outs, 1)

_rgb_state = new_game("A", "B", 2)
resolve_ground_ball(_rgb_state, "SS")
assert_equal(_rgb_state.outs, 1)

_rfb_state = new_game("A", "B", 2)
resolve_fly_ball(_rfb_state, "LF")
assert_equal(_rfb_state.outs, 1)

assert_equal(runner_id_of([_test_hitter], _test_hitter), 0)

_rld_state = new_game("A", "B", 2)
resolve_line_drive(_rld_state, "LF")
assert_equal(_rld_state.outs, 1)

_rpu_state = new_game("A", "B", 2)
resolve_pop_up(_rpu_state, "1B")
assert_equal(_rpu_state.outs, 1)

assert_equal(pick_hit_spot("homer") in OUTFIELD_SPOTS, True)

_hf_state = new_game("A", "B", 2)
_hf_state.hit_location = "LF"
assert_equal(hit_fielder(_hf_state), _hf_state.teams[1].left_field)
assert_equal(arm_rating(_hf_state), _hf_state.teams[1].left_field.fielding)
assert_equal(hit_spot_text(_hf_state), spot_text("LF", _hf_state.teams[1].left_field))

_ah_state = new_game("A", "B", 2)
add_hit(_ah_state, "single")
assert_equal(_ah_state.away_hits, 1)

_ast_state = State(strikes=1)
add_strike(_ast_state, "Strike!")
assert_equal(_ast_state.strikes, 2)

_ab_state = State(balls=1)
add_ball(_ab_state)
assert_equal(_ab_state.balls, 2)

_css_state = State(bases=[0, -1, -1])
assert_equal(can_steal_second(_css_state), True)

_cst_state = State(bases=[-1, 1, -1])
assert_equal(can_steal_third(_cst_state), True)

assert_equal(rating_label(85), "excellent")
assert_equal(rating_label(50), "average")
assert_equal(percent(0.50), "50%")

_ro_state2 = new_game("A", "B", 2)
_ro_state2.bases[0] = 0
assert_equal(runner_on(_ro_state2, 0), lineup(batting_team(_ro_state2))[0])

_rl_state = new_game("A", "B", 2)
_rl_state.bases[0] = 0
assert_equal(len(runner_lines(_rl_state)), 2)

_sc_state = new_game("A", "B", 2)
_sc_state.bases[0] = 0
assert_equal(0.20 <= steal_chance(_sc_state, 0) <= 0.90, True)

assert_equal(outfield_arm(_test_state), (
    _test_state.teams[1].left_field.fielding +
    _test_state.teams[1].center_field.fielding +
    _test_state.teams[1].right_field.fielding
) / 3)

_snd_state = new_game("A", "B", 2)
_snd_state.bases[0] = 0
_snd_state.hit_location = "LF"
assert_equal(0.15 <= send_chance(_snd_state, 0) <= 0.90, True)

_ast_state2 = new_game("A", "B", 2)
_ast_state2.bases[0] = 0
attempt_steal(_ast_state2, 0)
assert_equal(_ast_state2.bases[0], EMPTY)

assert_equal(pitcher_status(_test_pitcher), "fresh")
assert_equal(pitcher_label(1, _test_pitcher),
             f"Reliever 1: {_test_pitcher.name} - VEL {_test_pitcher.velocity}, "
             f"CTL {_test_pitcher.control}, MOV {_test_pitcher.movement}, "
             f"STA {_test_pitcher.stamina}")
assert_equal(len(pitching_options(_test_team)), 4)

assert_equal(type(banner("Test")), Div)
assert_equal(type(card("Test")), Div)
assert_equal(type(pill("Test")), Span)
assert_equal(type(dots(1, 2, GREEN)), Span)
assert_equal(type(energy_bar(_test_pitcher)), Div)
assert_equal(type(diamond_image(_test_state)), Image)
assert_equal(type(score_box("Away", 0, True)), Div)
assert_equal(type(scoreboard(_test_state)), list)
assert_equal(play_colors("home run"), ("#e8f5e9", GREEN))
assert_equal(type(last_play_card(_test_state)), list)
assert_equal(type(recent_plays_card(_test_state)), list)
assert_equal(type(player_of_the_game(_test_state)), Hitter)

assert_equal(type(index(_test_state)), Page)
assert_equal(type(start_game(_test_state, "A", "B", "2")), Page)
assert_equal(type(lineup_setup(_test_state)), Page)
assert_equal(type(pitch_select(_test_state)), Page)
assert_equal(type(choose_pitch(_test_state, "Fastball")), Page)
assert_equal(type(throw_fastball(_test_state)), Page)
assert_equal(type(throw_curveball(_test_state)), Page)
assert_equal(type(throw_slider(_test_state)), Page)
assert_equal(type(throw_changeup(_test_state)), Page)
assert_equal(type(swing_or_hold(_test_state)), Page)
assert_equal(type(next_page(_test_state)), Page)
assert_equal(type(do_swing(_test_state)), Page)
assert_equal(type(do_hold(_test_state)), Page)
assert_equal(type(baserunning_choice(_test_state)), Page)
assert_equal(type(steal_second(_test_state)), Page)
assert_equal(type(steal_third(_test_state)), Page)
assert_equal(type(send_runner(_test_state)), Page)
assert_equal(type(hold_runner(_test_state)), Page)
assert_equal(type(substitutions(_test_state)), Page)

_opts = pitching_options(_test_team)
assert_equal(type(make_pitching_change(_test_state, _opts[0] if _opts else "")), Page)
assert_equal(type(game_over(_test_state)), Page)
assert_equal(type(play_again(_test_state)), Page)


if __name__ == "__main__":
    start_server(State())

