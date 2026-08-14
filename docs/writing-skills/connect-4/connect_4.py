import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PLAYER_MARK = "X"
COMPUTER_MARK = "O"

PLAYER_TURN = "PLAYER_TURN"
COMPUTER_TURN = "COMPUTER_TURN"
GAME_OVER = "GAME_OVER"

THINKING_MESSAGE = "your opponent is thinking. check back in a few seconds."
GAME_OVER_MESSAGE = "the game is over. start a new game to play again."
MOVE_USAGE_MESSAGE = "invalid move. usage: /move?col=<0-6>&row=<0-5>"
OUT_OF_BOUNDS_MESSAGE = "invalid cell: out of bounds. columns are 0-6, rows are 0-5."
OCCUPIED_MESSAGE = "invalid cell: already occupied."
GAP_MESSAGE = "invalid cell: would leave a gap. discs must stack from the bottom up."
UNKNOWN_ENDPOINT_MESSAGE = "unknown endpoint. try /help for instructions"

COLS = 7
ROWS = 6
CONNECT = 4

THINK_DELAY_SECONDS = 2.0

DEFAULT_HOSTNAME = "127.0.0.1"
DEFAULT_PORT = 8000

HELP_TEXT = """\
connect 4 over HTTP. you are X, the computer is O.

endpoints:
  /new                start a new game (coin flip decides who goes first)
  /move?col=C&row=R   place your X at column C (0-6), row R (0-5)
  /board              show the current board (alias: /state)
  /help               show this help

you pick the exact cell. rows are numbered 0-5 from the bottom up,
shown in the left column of the board table; columns 0-6 are in the
header row at the top. empty cells are shown as ·.
a move is rejected if the cell is out of bounds, already occupied,
or would leave a gap (discs must stack from the bottom up).
first to connect four in a row (horizontal, vertical, or diagonal) wins.

example:
  curl localhost:8000/new
  curl "localhost:8000/move?col=3&row=0"
  curl localhost:8000/board

flow: after you move, the computer thinks for a couple of seconds.
poll /board to see when its O appears and it is your turn again.

machine-readable state: every response that shows the board ends with a
JSON object on the last line with two keys:
  valid_moves:    list of {"x": col, "y": row} cells you can legally play
  disc_locations: list of {"x": col, "y": row, "mark": "X"|"O"} for all discs
prefer parsing this JSON over reading the ASCII table.
"""


class Game:
    def __init__(self):
        self.lock = threading.Lock()
        self.columns = [[] for _ in range(COLS)]
        self.state = PLAYER_TURN
        self.winner = None
        self.generation = 0

    def reset(self):
        self.columns = [[] for _ in range(COLS)]
        self.winner = None
        self.generation += 1
        if random.random() < 0.5:
            self.state = PLAYER_TURN
        else:
            self.state = COMPUTER_TURN

    def make_move(self, col, row, mark):
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return False, "out of bounds"
        if row < len(self.columns[col]):
            return False, "occupied"
        if row > len(self.columns[col]):
            return False, "gap"
        self.columns[col].append(mark)
        if self.check_winner(col, row) is not None:
            self.winner = mark
            self.state = GAME_OVER
        elif self.is_stalemate():
            self.winner = "draw"
            self.state = GAME_OVER
        else:
            self.state = COMPUTER_TURN if mark == PLAYER_MARK else PLAYER_TURN
        return True, None

    def drop(self, col, mark):
        return self.make_move(col, len(self.columns[col]), mark)

    def cell(self, col, row):
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return None
        if row >= len(self.columns[col]):
            return None
        return self.columns[col][row]

    def check_winner(self, col, row):
        mark = self.columns[col][row]
        for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
            count = 1
            for sign in (1, -1):
                c, r = col + sign * dc, row + sign * dr
                while self.cell(c, r) == mark:
                    count += 1
                    c += sign * dc
                    r += sign * dr
            if count >= CONNECT:
                return mark
        return None

    def is_stalemate(self):
        return all(len(column) >= ROWS for column in self.columns) and self.winner is None

    def render(self):
        lines = []
        lines.append("| - | " + " | ".join(str(col) for col in range(COLS)) + " |")
        lines.append("|---|" + "---|" * COLS)
        for row in range(ROWS - 1, -1, -1):
            cells = " | ".join(self.cell(col, row) or "·" for col in range(COLS))
            lines.append(f"| {row} | {cells} |")
        return "\n".join(lines) + "\n" + self.status_line() + "\n\n" + self.state_json()

    def state_json(self):
        valid_moves = [
            {"x": col, "y": len(self.columns[col])}
            for col in range(COLS)
            if len(self.columns[col]) < ROWS
        ]
        disc_locations = [
            {"x": col, "y": row, "mark": mark}
            for col in range(COLS)
            for row, mark in enumerate(self.columns[col])
        ]
        return json.dumps({"valid_moves": valid_moves, "disc_locations": disc_locations})

    def status_line(self):
        if self.state == PLAYER_TURN:
            return "your move (X)."
        if self.state == COMPUTER_TURN:
            return "opponent thinking..."
        if self.winner == "draw":
            return "game over: draw."
        return f"game over: {self.winner} wins."


CENTER_FIRST_ORDER = (3, 2, 4, 1, 5, 0, 6)


def cell_at(columns, col, row):
    if not (0 <= col < COLS and 0 <= row < ROWS):
        return None
    if row >= len(columns[col]):
        return None
    return columns[col][row]


def drop_in(columns, col, mark):
    after = [list(column) for column in columns]
    after[col].append(mark)
    return after


def has_four(columns, col, row, mark):
    for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        for sign in (1, -1):
            c, r = col + sign * dc, row + sign * dr
            while cell_at(columns, c, r) == mark:
                count += 1
                c += sign * dc
                r += sign * dr
        if count >= CONNECT:
            return True
    return False


def is_winning_move(columns, col, mark):
    after = drop_in(columns, col, mark)
    return has_four(after, col, len(after[col]) - 1, mark)


def winning_column(columns, mark):
    for col in CENTER_FIRST_ORDER:
        if len(columns[col]) < ROWS and is_winning_move(columns, col, mark):
            return col
    return None


def available_columns(columns, ordered=False):
    order = CENTER_FIRST_ORDER if ordered else range(COLS)
    return [col for col in order if len(columns[col]) < ROWS]


def score_windows(columns, mark):
    score = 2 * sum(1 for piece in columns[COLS // 2] if piece == mark)
    for col in range(COLS):
        for row in range(ROWS):
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                end_col = col + (CONNECT - 1) * dc
                end_row = row + (CONNECT - 1) * dr
                if not (0 <= end_col < COLS and 0 <= end_row < ROWS):
                    continue
                window = [cell_at(columns, col + i * dc, row + i * dr) for i in range(CONNECT)]
                own = window.count(mark)
                empty = window.count(None)
                other = CONNECT - own - empty
                if other == 0:
                    if own == 3 and empty == 1:
                        score += 3
                    elif own == 2 and empty == 2:
                        score += 1
                elif own == 0 and other == 3 and empty == 1:
                    score -= 4
    return score


class Opponent:
    def choose_move(self, columns):
        raise NotImplementedError


class RandomOpponent(Opponent):
    def choose_move(self, columns):
        time.sleep(THINK_DELAY_SECONDS)
        winning = winning_column(columns, COMPUTER_MARK)
        if winning is not None:
            return winning
        return random.choice(available_columns(columns))


class HeuristicOpponent(Opponent):
    def choose_move(self, columns):
        time.sleep(THINK_DELAY_SECONDS)
        winning = winning_column(columns, COMPUTER_MARK)
        if winning is not None:
            return winning
        block = winning_column(columns, PLAYER_MARK)
        if block is not None:
            return block
        best_score = None
        best_columns = []
        for col in available_columns(columns, ordered=True):
            after = drop_in(columns, col, COMPUTER_MARK)
            if winning_column(after, PLAYER_MARK) is not None:
                continue
            score = score_windows(after, COMPUTER_MARK)
            if best_score is None or score > best_score:
                best_score = score
                best_columns = [col]
            elif score == best_score:
                best_columns.append(col)
        if not best_columns:
            best_columns = available_columns(columns)
        return random.choice(best_columns)


class MinimaxOpponent(Opponent):
    MAX_DEPTH = 5
    WIN_SCORE = 10000

    def choose_move(self, columns):
        time.sleep(THINK_DELAY_SECONDS)
        winning = winning_column(columns, COMPUTER_MARK)
        if winning is not None:
            return winning
        board = [list(column) for column in columns]
        best_score = -float("inf")
        best_col = None
        for col in CENTER_FIRST_ORDER:
            if len(board[col]) >= ROWS:
                continue
            board[col].append(COMPUTER_MARK)
            score = self._search(board, self.MAX_DEPTH - 1, 1, -float("inf"), float("inf"))
            board[col].pop()
            if score > best_score:
                best_score = score
                best_col = col
        return best_col

    def _search(self, board, depth, ply, alpha, beta):
        maximizing = ply % 2 == 0
        if depth == 0 or all(len(column) >= ROWS for column in board):
            return score_windows(board, COMPUTER_MARK)
        mark = COMPUTER_MARK if maximizing else PLAYER_MARK
        best = -float("inf") if maximizing else float("inf")
        for col in CENTER_FIRST_ORDER:
            if len(board[col]) >= ROWS:
                continue
            board[col].append(mark)
            if has_four(board, col, len(board[col]) - 1, mark):
                score = (self.WIN_SCORE - ply) if maximizing else -(self.WIN_SCORE - ply)
            else:
                score = self._search(board, depth - 1, ply + 1, alpha, beta)
            board[col].pop()
            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)
            if beta <= alpha:
                break
        return best


STRATEGIES = {
    "random": RandomOpponent,
    "heuristic": HeuristicOpponent,
    "minimax": MinimaxOpponent,
}


def run_opponent_turn(game, opponent, generation):
    with game.lock:
        if game.generation != generation or game.state != COMPUTER_TURN:
            return
        snapshot = [list(column) for column in game.columns]
    col = opponent.choose_move(snapshot)
    with game.lock:
        if game.generation != generation or game.state != COMPUTER_TURN:
            return
        game.drop(col, COMPUTER_MARK)


class Connect4Handler(BaseHTTPRequestHandler):
    game = None
    opponent = None

    def log_message(self, format, *args):
        pass

    def respond(self, text, status=200):
        if not text.endswith("\n"):
            text += "\n"
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/new":
            self.handle_new()
        elif path == "/move":
            self.handle_move(params)
        elif path in ("/board", "/state"):
            self.handle_board()
        elif path == "/help":
            self.respond(HELP_TEXT)
        else:
            self.respond(UNKNOWN_ENDPOINT_MESSAGE, status=404)

    def handle_new(self):
        game = self.game
        with game.lock:
            if game.state == COMPUTER_TURN:
                self.respond(THINKING_MESSAGE)
                return
            game.reset()
            goes_first = "you go first (X)." if game.state == PLAYER_TURN else "computer goes first (O)."
            if game.state == COMPUTER_TURN:
                self.spawn_worker()
            self.respond(f"new game started. {goes_first}\n\n{game.render()}")

    def handle_move(self, params):
        game = self.game
        with game.lock:
            if game.state == COMPUTER_TURN:
                self.respond(THINKING_MESSAGE)
                return
            if game.state == GAME_OVER:
                self.respond(GAME_OVER_MESSAGE)
                return
            try:
                col = int(params["col"][0])
                row = int(params["row"][0])
            except (KeyError, IndexError, ValueError):
                self.respond(MOVE_USAGE_MESSAGE, status=400)
                return
            ok, reason = game.make_move(col, row, PLAYER_MARK)
            if not ok:
                if reason == "out of bounds":
                    self.respond(OUT_OF_BOUNDS_MESSAGE, status=400)
                elif reason == "occupied":
                    self.respond(OCCUPIED_MESSAGE, status=400)
                else:
                    self.respond(GAP_MESSAGE, status=400)
                return
            if game.state == COMPUTER_TURN:
                self.spawn_worker()
            self.respond(game.render())

    def handle_board(self):
        with self.game.lock:
            self.respond(self.game.render())

    def spawn_worker(self):
        thread = threading.Thread(
            target=run_opponent_turn,
            args=(self.game, self.opponent, self.game.generation),
            daemon=True,
        )
        thread.start()


def main():
    parser = argparse.ArgumentParser(description="Connect 4 over HTTP (stdlib only).")
    parser.add_argument("--hostname", default=DEFAULT_HOSTNAME)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--strategy", choices=sorted(STRATEGIES), default="random",
                        help="opponent strategy (default: random)")
    args = parser.parse_args()

    game = Game()
    Connect4Handler.game = game
    Connect4Handler.opponent = STRATEGIES[args.strategy]()

    with game.lock:
        game.reset()
        computer_starts = game.state == COMPUTER_TURN
    if computer_starts:
        thread = threading.Thread(
            target=run_opponent_turn,
            args=(game, Connect4Handler.opponent, game.generation),
            daemon=True,
        )
        thread.start()

    server = ThreadingHTTPServer((args.hostname, args.port), Connect4Handler)
    print(f"serving connect 4 on http://{args.hostname}:{args.port} (strategy: {args.strategy})")
    print(f"  curl {args.hostname}:{args.port}/new")
    print(f"  curl {args.hostname}:{args.port}/help")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
