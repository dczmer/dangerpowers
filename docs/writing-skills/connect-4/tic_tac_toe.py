import argparse
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
CELL_TAKEN_MESSAGE = "cell already taken"
UNKNOWN_ENDPOINT_MESSAGE = "unknown endpoint. try /help for instructions"

THINK_DELAY_SECONDS = 2.0

DEFAULT_HOSTNAME = "127.0.0.1"
DEFAULT_PORT = 8000

HELP_TEXT = """\
tic-tac-toe over HTTP. you are X, the computer is O.

endpoints:
  /new                 start a new game (coin flip decides who goes first)
  /move?row=R&col=C    place your X at row R, column C (both 0-2)
  /board               show the current board (alias: /state)
  /help                show this help

coordinates: row and col are 0, 1, or 2, counting from the top-left.

example:
  curl localhost:8000/new
  curl "localhost:8000/move?row=1&col=1"
  curl localhost:8000/board

flow: after you move, the computer thinks for a couple of seconds.
poll /board to see when its O appears and it is your turn again.
"""


class Game:
    def __init__(self):
        self.lock = threading.Lock()
        self.board = [None] * 9
        self.state = PLAYER_TURN
        self.winner = None
        self.generation = 0

    def reset(self):
        self.board = [None] * 9
        self.winner = None
        self.generation += 1
        if random.random() < 0.5:
            self.state = PLAYER_TURN
        else:
            self.state = COMPUTER_TURN

    def make_move(self, row, col, mark):
        if not (0 <= row <= 2 and 0 <= col <= 2):
            return False, "out of range"
        index = row * 3 + col
        if self.board[index] is not None:
            return False, "occupied"
        self.board[index] = mark
        winner = self.check_winner()
        if winner is not None:
            self.winner = winner
            self.state = GAME_OVER
        elif self.is_stalemate():
            self.winner = "draw"
            self.state = GAME_OVER
        else:
            self.state = COMPUTER_TURN if mark == PLAYER_MARK else PLAYER_TURN
        return True, None

    def check_winner(self):
        lines = (
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        )
        for a, b, c in lines:
            if self.board[a] is not None and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def is_stalemate(self):
        return all(cell is not None for cell in self.board) and self.check_winner() is None

    def render(self):
        def cell(i):
            return self.board[i] if self.board[i] is not None else " "

        rows = [" | ".join(cell(r * 3 + c) for c in range(3)) for r in range(3)]
        board_text = ("\n--+---+--\n").join(rows)
        return board_text + "\n" + self.status_line()

    def status_line(self):
        if self.state == PLAYER_TURN:
            return "your move (X)."
        if self.state == COMPUTER_TURN:
            return "opponent thinking..."
        if self.winner == "draw":
            return "game over: draw."
        return f"game over: {self.winner} wins."


class Opponent:
    def choose_move(self, board):
        raise NotImplementedError


class RandomOpponent(Opponent):
    def choose_move(self, board):
        time.sleep(THINK_DELAY_SECONDS)
        empty = [i for i, cell in enumerate(board) if cell is None]
        index = random.choice(empty)
        return index // 3, index % 3


class MinimaxOpponent(Opponent):
    def choose_move(self, board):
        best_score = -2
        best_index = None
        for i, cell in enumerate(board):
            if cell is None:
                board[i] = COMPUTER_MARK
                score = self._minimax(board, maximizing=False)
                board[i] = None
                if score > best_score:
                    best_score = score
                    best_index = i
        return best_index // 3, best_index % 3

    def _minimax(self, board, maximizing):
        winner = self._winner(board)
        if winner == COMPUTER_MARK:
            return 1
        if winner == PLAYER_MARK:
            return -1
        if all(cell is not None for cell in board):
            return 0
        scores = []
        for i, cell in enumerate(board):
            if cell is None:
                board[i] = COMPUTER_MARK if maximizing else PLAYER_MARK
                scores.append(self._minimax(board, not maximizing))
                board[i] = None
        return max(scores) if maximizing else min(scores)

    @staticmethod
    def _winner(board):
        lines = (
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        )
        for a, b, c in lines:
            if board[a] is not None and board[a] == board[b] == board[c]:
                return board[a]
        return None


STRATEGIES = {
    "random": RandomOpponent,
    "minimax": MinimaxOpponent,
}


def run_opponent_turn(game, opponent, generation):
    with game.lock:
        if game.generation != generation or game.state != COMPUTER_TURN:
            return
        snapshot = list(game.board)
    row, col = opponent.choose_move(snapshot)
    with game.lock:
        if game.generation != generation or game.state != COMPUTER_TURN:
            return
        game.make_move(row, col, COMPUTER_MARK)


class TicTacToeHandler(BaseHTTPRequestHandler):
    game = None
    opponent = None

    def log_message(self, format, *args):
        pass

    def respond(self, text, status=200):
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
                row = int(params["row"][0])
                col = int(params["col"][0])
            except (KeyError, IndexError, ValueError):
                self.respond("invalid move. usage: /move?row=<0-2>&col=<0-2>", status=400)
                return
            if not (0 <= row <= 2 and 0 <= col <= 2):
                self.respond("row and col must be between 0 and 2.", status=400)
                return
            ok, reason = game.make_move(row, col, PLAYER_MARK)
            if not ok:
                if reason == "occupied":
                    self.respond(CELL_TAKEN_MESSAGE)
                else:
                    self.respond(f"invalid move: {reason}", status=400)
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
    parser = argparse.ArgumentParser(description="Tic-tac-toe over HTTP (stdlib only).")
    parser.add_argument("--hostname", default=DEFAULT_HOSTNAME)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--strategy", choices=sorted(STRATEGIES), default="random",
                        help="opponent strategy (default: random)")
    args = parser.parse_args()

    game = Game()
    TicTacToeHandler.game = game
    TicTacToeHandler.opponent = STRATEGIES[args.strategy]()

    with game.lock:
        game.reset()
        computer_starts = game.state == COMPUTER_TURN
    if computer_starts:
        thread = threading.Thread(
            target=run_opponent_turn,
            args=(game, TicTacToeHandler.opponent, game.generation),
            daemon=True,
        )
        thread.start()

    server = ThreadingHTTPServer((args.hostname, args.port), TicTacToeHandler)
    print(f"serving tic-tac-toe on http://{args.hostname}:{args.port} (strategy: {args.strategy})")
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
