"""
pv_explainer.py — объяснение ошибки по линии движка (PV).

Идея: никаких «детекторов паттернов». Берём линию, которую движок считает
лучшей после ВАШЕГО хода (played_results[0]["pv"]), проигрываем её на доске
и смотрим, что реально произошло с материалом. То же самое делаем для
ЛУЧШЕГО хода (mistake["pv"]) и сравниваем. Причина считается причиной,
только если после лучшего хода её нет (контрфактическая проверка).

Порядок правил (первое сработавшее побеждает):
  1. mate_allowed     — ваш ход позволяет соперику форсированный мат
  2. missed_mate      — вы упустили мат
  3. material_loss    — по линии движка вы теряете материал, а после лучшего хода — нет
  4. missed_material  — лучший ход выигрывал материал, сыгранный — нет
  5. positional       — материал не затронут: честно говорим только факты (оценка, ответ)

Публичный API:
  analyze(mistake)                -> dict с type / main / secondary / evidence
  generate_explanation_v2(mistake)-> готовый текст (замена generate_explanation)

Формат входа — тот же mistake, что собирает build_mistake():
  position_before   chess.Board ИЛИ FEN-строка
  played_san, best, best_uci, loss, before_score, after_score
  pv                линия лучшего хода (UCI), pv[0] == best_uci
  played_results    список multipv-словарей, [i]["pv"] начинается с ответа соперника
  alternatives, equivalent_best_moves
"""

import logging
import re

import chess

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Настройки
# ----------------------------------------------------------------------

PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

PIECE_ACC = {  # винительный падеж: «забирает ...»
    chess.PAWN: "пешку",
    chess.KNIGHT: "коня",
    chess.BISHOP: "слона",
    chess.ROOK: "ладью",
    chess.QUEEN: "ферзя",
    chess.KING: "короля",
}

PIECE_NOM = {  # именительный: «пешка на f3 атакует ...»
    chess.PAWN: "пешка",
    chess.KNIGHT: "конь",
    chess.BISHOP: "слон",
    chess.ROOK: "ладья",
    chess.QUEEN: "ферзь",
    chess.KING: "король",
}

YOUR_ACC = {  # «... атакует вашего коня»
    chess.PAWN: "вашу пешку",
    chess.KNIGHT: "вашего коня",
    chess.BISHOP: "вашего слона",
    chess.ROOK: "вашу ладью",
    chess.QUEEN: "вашего ферзя",
}

# Ценность атакующего: король может бить только незащищённую фигуру
ATTACK_VALUE = dict(PIECE_VALUE)
ATTACK_VALUE[chess.KING] = 10000

MATERIAL_THRESHOLD = 100     # минимум, чтобы говорить о потере/выигрыше (одна пешка)
MIN_LOSS_FOR_MATERIAL = 60   # если оценка почти не упала — это не материальная потеря
MIN_LOSS_FOR_MISSED = 30     # упущенный выигрыш называем уже при небольшой потере
REPLAY_PLIES = 12            # сколько полуходов линии проигрываем
HORIZON = 8                  # на каком полуходе фиксируем итог по материалу
MATE_MAX_PLIES = 9           # мат дальше этого не рассматриваем
SHOW_MAX_PLIES = 10          # максимум ходов в показываемой линии
SHOW_MAX_EVENTS = 3          # максимум перечисляемых взятий
MAX_LOSS_PLY = 6             # потеря должна начаться не позже этого полухода линии
MAX_GAIN_PLY = 5             # упущенный выигрыш — не позже этого полухода

# ----------------------------------------------------------------------
# Вспомогательное: оценки
# ----------------------------------------------------------------------

_POV_RE = re.compile(r"(Cp|Mate)\(\s*([+-]?\d+)\s*\)\s*,\s*(WHITE|BLACK)", re.I)
_BARE_RE = re.compile(r"^\s*(Cp|Mate)\(\s*([+-]?\d+)\s*\)\s*$", re.I)
_MATE_RE = re.compile(r"^\s*(?:#|Mate\(?|M)\s*([+-]?\d+)\)?\s*$", re.I)


def parse_score(raw, mover_color, default_pov=None):
    """
    Приводит оценку к виду «с точки зрения ходящего».

    default_pov — чья это точка зрения, если в самой оценке цвет не указан
    (chess.WHITE для before_score / best_score_obj в вашем приложении:
    они записаны с точки зрения белых). Если None — считаем, что уже с
    точки зрения ходящего.
    Возвращает ("cp", int) | ("mate", int) | (None, None).
    mate > 0: ходящий матует, mate < 0: ходящего матуют.

    Понимает: числа, "+72", "#+3", "M-2",
              "PovScore(Cp(+10), BLACK)", "PovScore(Mate(-3), WHITE)".
    mover_color — chess.WHITE / chess.BLACK (True / False).
    """
    if raw is None or isinstance(raw, bool):
        return None, None
    flip = default_pov is not None and bool(default_pov) != bool(mover_color)

    if isinstance(raw, (int, float)):
        value = int(round(raw))
        return "cp", (-value if flip else value)

    text = str(raw)

    m = _POV_RE.search(text)
    if m:
        kind = m.group(1).lower()
        value = int(m.group(2))
        pov_is_white = m.group(3).upper() == "WHITE"
        if pov_is_white != bool(mover_color):
            value = -value
        return kind, value

    m = _BARE_RE.match(text)
    if m:
        value = int(m.group(2))
        return m.group(1).lower(), (-value if flip else value)

    m = _MATE_RE.match(text)
    if m:
        value = int(m.group(1))
        return "mate", (-value if flip else value)

    try:
        value = int(round(float(text)))
    except ValueError:
        return None, None
    return "cp", (-value if flip else value)


MATE_SCORE = 10000   # так приложение кодирует мат: 9996 = мат в 4


def fmt_eval(cp):
    if cp is None:
        return "?"
    if abs(cp) >= 9000:
        n = max(MATE_SCORE - int(abs(cp)), 0)
        who = "в вашу пользу" if cp > 0 else "против вас"
        return f"мат в {n} {who}"
    return f"{cp / 100:.2f}"


# ----------------------------------------------------------------------
# Вспомогательное: доска и проигрывание линии (нужен python-chess)
# ----------------------------------------------------------------------

def _to_board(position):
    if position is None:
        return None
    if isinstance(position, chess.Board):
        return position.copy()
    if isinstance(position, str):
        return chess.Board(position)
    return None


def material(board, color):
    """Материальный баланс с точки зрения color (в сотых пешки)."""
    total = 0
    for piece in board.piece_map().values():
        value = PIECE_VALUE.get(piece.piece_type, 0)
        total += value if piece.color == color else -value
    return total


def _as_move(item):
    if isinstance(item, chess.Move):
        return item
    return chess.Move.from_uci(str(item))


def replay_line(board, line, mover_color, max_plies=REPLAY_PLIES):
    """
    Проигрывает ходы line (UCI-строки или chess.Move) начиная с board.
    Останавливается на первом нелегальном ходе (и пишет это в лог).
    Возвращает список шагов:
      {ply, fullmove, color, uci, san, captured, captured_square,
       is_mate, balance}
    balance — материальный баланс с точки зрения mover_color ПОСЛЕ хода.
    """
    b = board.copy()
    steps = []

    for index, item in enumerate((line or [])[:max_plies]):
        try:
            move = _as_move(item)
        except ValueError:
            log.warning("pv_explainer: плохой ход в линии: %r", item)
            break

        if move not in b.legal_moves:
            log.warning(
                "pv_explainer: нелегальный ход %s в позиции %s", move.uci(), b.fen()
            )
            break

        color = b.turn
        fullmove = b.fullmove_number
        captured = None
        captured_square = None

        if b.is_capture(move):
            if b.is_en_passant(move):
                captured = chess.PAWN
                square = chess.square(
                    chess.square_file(move.to_square),
                    chess.square_rank(move.from_square),
                )
            else:
                captured = b.piece_at(move.to_square).piece_type
                square = move.to_square
            captured_square = chess.square_name(square)

        san = b.san(move)
        b.push(move)

        steps.append(
            {
                "ply": index + 1,
                "fullmove": fullmove,
                "color": color,
                "uci": move.uci(),
                "san": san,
                "captured": captured,
                "captured_square": captured_square,
                "is_mate": b.is_checkmate(),
                "balance": material(b, mover_color),
            }
        )

    return steps


def threatened_pieces(board, color):
    """
    Фигуры и пешки стороны color (кроме короля), которым на доске что-то
    угрожает: их атакует более дешёвая фигура либо они вообще не защищены.
    Это факты доски, а не догадки: чистый подсчёт атак.
    Возвращает {клетка: {piece, attacker, attacker_square, reason}}.
    """
    enemy = not color
    found = {}
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        attackers = list(board.attackers(enemy, square))
        if not attackers:
            continue
        cheapest = min(
            attackers,
            key=lambda a: ATTACK_VALUE.get(board.piece_at(a).piece_type, 0),
        )
        cheapest_type = board.piece_at(cheapest).piece_type
        value = PIECE_VALUE.get(piece.piece_type, 0)
        if ATTACK_VALUE.get(cheapest_type, 0) < value:
            reason = "cheaper"
        elif len(board.attackers(color, square)) == 0:
            reason = "undefended"
        else:
            continue
        found[square] = {
            "piece": piece.piece_type,
            "attacker": cheapest_type,
            "attacker_square": chess.square_name(cheapest),
            "reason": reason,
        }
    return found


def reply_facts(board_after_played, steps, played_to_square=None,
                played_captured=None):
    """
    Одно предложение о сильнейшем ответе соперника (первый ход линии
    после ошибки). Только проверяемое: ответное взятие, размен, взятие, шах,
    новая атака на вашу фигуру. Ничего не домысливает.
    played_to_square — клетка, на которую вы только что сходили;
    played_captured  — тип фигуры, которую взял ваш ход (если взял).
    """
    if not steps:
        return ""
    first = steps[0]
    san = first["san"]
    mover = not first["color"]          # тот, кто ошибся: ходит не соперник
    board = board_after_played.copy()
    before = threatened_pieces(board, mover)
    board.push(chess.Move.from_uci(first["uci"]))
    after = threatened_pieces(board, mover)
    new = {sq: info for sq, info in after.items() if sq not in before}
    # Угроза от фигуры, которую следующим ходом сразу забирают, не считается.
    if len(steps) > 1 and steps[1]["color"] == mover \
            and steps[1]["captured_square"] is not None:
        new = {
            sq: info for sq, info in new.items()
            if info["attacker_square"] != steps[1]["captured_square"]
        }
    check = " с шахом" if board.is_check() else ""

    threat = ""
    just_moved = False
    if new:
        square, info = max(
            new.items(), key=lambda kv: PIECE_VALUE.get(kv[1]["piece"], 0)
        )
        why = ("фигура дороже атакующей" if info["reason"] == "cheaper"
               else "без защиты")
        threat = (
            f"{PIECE_NOM.get(info['attacker'], 'фигура')} на "
            f"{info['attacker_square']} атакует "
            f"{YOUR_ACC.get(info['piece'], 'вашу фигуру')} на "
            f"{chess.square_name(square)} ({why})"
        )
        just_moved = played_to_square is not None and square == played_to_square

    if first["captured"] is not None:
        square_name = first["captured_square"]
        taken = PIECE_ACC.get(first["captured"], "фигуру")
        if (played_captured is not None and played_to_square is not None
                and square_name == chess.square_name(played_to_square)):
            gave = PIECE_ACC.get(played_captured, "фигуру")
            text = (
                f"Сильнейший ответ соперника — {san}{check}: ответное взятие "
                f"(вы взяли {gave}, соперник берёт {taken})"
            )
        elif len(steps) > 1 and steps[1]["captured_square"] == square_name:
            text = (
                f"Сильнейший ответ соперника — {san}{check}, "
                f"затем {steps[1]['san']}: это размен"
            )
        else:
            text = (
                f"Сильнейший ответ соперника — {san}{check}: "
                f"взятие ({taken} на {square_name})"
            )
        if threat:
            text += f"; {threat}"
        text += "."
    elif threat:
        text = f"Сильнейший ответ соперника — {san}{check}: {threat}."
    elif check:
        text = f"Сильнейший ответ соперника — {san} (шах)."
    else:
        text = f"Сильнейший ответ соперника — {san}."

    if just_moved:
        text += " Это фигура, которой вы только что сходили."
    return text


CENTER_SQUARES = {"d4", "e4", "d5", "e5"}
HOME_MINORS = {
    chess.WHITE: {"b1", "g1", "c1", "f1"},
    chess.BLACK: {"b8", "g8", "c8", "f8"},
}


def best_move_fact(board, best_uci):
    """Короткий проверяемый факт о лучшем ходе: рокировка, взятие, шах,
    пешка в центр, развитие фигуры с исходного поля."""
    try:
        move = chess.Move.from_uci(str(best_uci))
    except ValueError:
        return ""
    if move not in board.legal_moves:
        return ""
    if board.is_castling(move):
        return "рокировка"
    if board.is_capture(move):
        if board.is_en_passant(move):
            return "взятие пешки"
        piece = board.piece_at(move.to_square)
        return f"взятие ({PIECE_ACC.get(piece.piece_type, 'фигуры')})"
    after = board.copy()
    after.push(move)
    if after.is_check():
        return "шах"
    piece = board.piece_at(move.from_square)
    to_name = chess.square_name(move.to_square)
    if piece and piece.piece_type == chess.PAWN and to_name in CENTER_SQUARES:
        return f"пешка занимает центр ({to_name})"
    if (piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP)
            and chess.square_name(move.from_square) in HOME_MINORS[piece.color]):
        return f"развитие ({PIECE_NOM[piece.piece_type]} выходит с исходного поля)"
    return ""


STRUCT_WINDOW = 4   # структуру смотрим только в первых полуходах (цепочка разменов):
                    # дальше линия движка гипотетична, и вы такого в партии не увидите
FORK_WINDOW = 4   # вилку соперника ищем в первых полуходах линии

def pawn_weaknesses(board, color):
    """Сдвоенные и изолированные пешки стороны color: {(вид, номер_вертикали)}."""
    counts = {}
    for square, piece in board.piece_map().items():
        if piece.color == color and piece.piece_type == chess.PAWN:
            file_index = chess.square_file(square)
            counts[file_index] = counts.get(file_index, 0) + 1
    found = set()
    for file_index, amount in counts.items():
        if amount >= 2:
            found.add(("doubled", file_index))
        if (file_index - 1) not in counts and (file_index + 1) not in counts:
            found.add(("isolated", file_index))
    return found


def _board_after(board, steps, plies):
    result = board.copy()
    for step in steps[:plies]:
        result.push(chess.Move.from_uci(step["uci"]))
    return result


def structure_fact(board_before, board_after_played, steps_played, steps_best,
                   mover, best_san):
    """
    Новые слабости пешечной структуры, которые появляются у вас в линии
    движка после сыгранного хода, но НЕ появляются после лучшего хода.
    Это контрфактическая проверка: слабость засчитывается, только если
    лучший ход её избегает.
    """
    start_played = pawn_weaknesses(board_after_played, mover)
    end_played = pawn_weaknesses(
        _board_after(board_after_played, steps_played, STRUCT_WINDOW), mover
    )
    end_best = pawn_weaknesses(
        _board_after(board_before, steps_best, STRUCT_WINDOW + 1), mover
    )
    only_played = (end_played - start_played) - end_best

    letters = "abcdefgh"
    doubled = sorted(f for kind, f in only_played if kind == "doubled")
    isolated = sorted(f for kind, f in only_played if kind == "isolated")
    parts = []
    if doubled:
        parts.append("сдвоенные пешки (" + ", ".join(f"{letters[f]}-линия" for f in doubled) + ")")
    if isolated:
        parts.append("изолированная пешка (" + ", ".join(f"{letters[f]}-линия" for f in isolated) + ")")
    if not parts:
        return ""
    return (
        "В линии движка у вас появляются " + " и ".join(parts)
        + f"; после {best_san} этого нет."
    )


def ignored_threat_fact(board_before, played_move, steps_played, steps_best, mover):
    """
    Проигнорированная угроза: первый ответ соперника забирает фигуру, которая
    УЖЕ была под атакой до нашего хода (и наш ход её не касался).
    Лучший ход такую же угрозу устраняет (контрфактическая проверка).

    Возвращает (текст, evidence) либо ("", None).
    """
    if not steps_played:
        return "", None
    first = steps_played[0]
    if first["captured"] is None:
        return "", None
    try:
        first_move = chess.Move.from_uci(first["uci"])
    except ValueError:
        return "", None

    target = chess.parse_square(first["captured_square"])

    # 1) Наш ход не касался клетки угрозы (иначе это обычный размен / своя фигура).
    if played_move.from_square == target or played_move.to_square == target:
        return "", None

    # 2) На клетке угрозы до нашего хода стоит НАША фигура.
    piece_before = board_before.piece_at(target)
    if piece_before is None or piece_before.color != mover:
        return "", None

    # 3) Атакующая фигура — та, которой соперник и забирает.
    attacker_sq = first_move.from_square
    attacker_piece = board_before.piece_at(attacker_sq)
    if attacker_piece is None or attacker_piece.color == mover:
        return "", None

    # 4) Угроза была реальной: если бы был ход соперника, взятие легально.
    probe = board_before.copy()
    probe.turn = not mover
    if first_move not in probe.legal_moves:
        return "", None

    # 5) Контрфактически: после лучшего хода такого же взятия на той же клетке нет.
    if len(steps_best) < 2:
        return "", None
    best_reply = steps_best[1]
    if (best_reply["captured"] is not None
            and best_reply["captured_square"] == first["captured_square"]):
        return "", None

    attacker_name = PIECE_NOM.get(attacker_piece.piece_type, "фигура")
    victim_name = YOUR_ACC.get(piece_before.piece_type, "вашу фигуру")
    target_name = chess.square_name(target)
    attacker_sq_name = chess.square_name(attacker_sq)

    text = (
        f"Угроза была видна уже до вашего хода: "
        f"{attacker_name} на {attacker_sq_name} атакует {victim_name} "
        f"на {target_name}."
    )
    evidence = {
        "square": target_name,
        "victim": piece_before.piece_type,
        "attacker": attacker_piece.piece_type,
        "attacker_square": attacker_sq_name,

    }
    return text, evidence

CENTER_SQUARES_SQ = {chess.D4, chess.E4, chess.D5, chess.E5}


def center_fact(board_before, played_move, best_uci, best_san):
    """
    Мотив «центр»: лучший ход — пешечный ход на центральное поле
    (d4/e4/d5/e5), а сыгранный ход центр не занимает.
    Проверяется по доске и лучшему ходу, без домыслов.
    Возвращает короткий текст или "".
    """
    if board_before is None or played_move is None:
        return ""
    try:
        best_move = chess.Move.from_uci(str(best_uci))
    except (ValueError, TypeError):
        return ""
    if best_move not in board_before.legal_moves:
        return ""
    # Лучший ход должен ставить ПЕШКУ на центральное поле.
    if best_move.to_square not in CENTER_SQUARES_SQ:
        return ""
    if board_before.is_capture(best_move):
        return ""
    piece = board_before.piece_at(best_move.from_square)
    if piece is None or piece.piece_type != chess.PAWN:
        return ""
    # Сыгранный ход уже занимает центр — мотив не срабатывает.
    if played_move.to_square in CENTER_SQUARES_SQ:
        return ""
    field = chess.square_name(best_move.to_square)
    return (
        f"Борьба за центр: лучший ход {best_san} ставит пешку на {field}; "
        f"ваш ход центр не занимает."
    )

def _attacked_enemy_pieces(board, square, mover):
    """
    Какие фигуры соперника бьёт фигура стороны mover с клетки square
    в текущей позиции. Король включается: шах с одновременным нападением
    на фигуру — это классическая вилка «король + фигура».
    Возвращает [(piece_type, square_name), ...].
    """
    result = []
    attacks = board.attacks(square)
    for sq in chess.SQUARES:
        if not (attacks & (1 << sq)):
            continue
        target = board.piece_at(sq)
        if target is None or target.color == mover:
            continue
        result.append((target.piece_type, chess.square_name(sq)))
    return result


def fork_fact(board, steps, mover, window=STRUCT_WINDOW):
    """
    Ищет в линии ход стороны mover, после которого фигура, которой сходили,
    одновременно бьёт ≥2 фигуры соперника (не пешки суммарно, хотя бы одна
    ≥ коня). Это подпись к линии движка, а не детектор по позиции.

    Возвращает (текст, evidence) либо ("", None).
    """
    if not steps:
        return "", None
    current = board.copy()
    limit = min(len(steps), window)
    for i, step in enumerate(steps[:limit]):
        move = chess.Move.from_uci(step["uci"])
        current.push(move)
        if step["color"] != mover or step["captured"] is not None:
            continue
        targets = _attacked_enemy_pieces(current, move.to_square, mover)
        if len(targets) < 2:
            continue
        best_value = max(PIECE_VALUE.get(t, 0) for t, _ in targets)
        if best_value < PIECE_VALUE[chess.KNIGHT]:
            continue
        attacker = current.piece_at(move.to_square)
        attacker_name = PIECE_NOM.get(attacker.piece_type, "фигура")
        square_name = chess.square_name(move.to_square)
        targets_text = ", ".join(
            f"{PIECE_ACC.get(t, 'фигуру')} на {sq}" for t, sq in targets
        )
        text = (
            f"Ход {step['san']} — вилка: "
            f"{attacker_name} на {square_name} одновременно бьёт {targets_text}."
        )
        evidence = {
            "ply": step["ply"],
            "san": step["san"],
            "piece": attacker.piece_type,
            "square": square_name,
            "targets": [(t, sq) for t, sq in targets],
        }
        return text, evidence
    return "", None


def _safe_fork(board, steps, mover):
    try:
        return fork_fact(board, steps, mover)
    except Exception:
        log.exception("pv_explainer: не удалось проверить вилку")
        return "", None

def _winning_targets(board, from_square, mover):
    """
    Какие фигуры соперника бьёт фигура стороны mover (стоящая на from_square)
    ВЫГОДНО: король (шах) или фигура, взятие которой выигрывает материал по SEE
    (не меньше MATERIAL_THRESHOLD). Защищённая фигура, которая просто
    разменивается, целью вилки не считается.
    Возвращает [(piece_type, square_name), ...].
    """
    targets = []
    for piece_type, name in _attacked_enemy_pieces(board, from_square, mover):
        if piece_type == chess.KING:
            targets.append((piece_type, name))
            continue
        see = static_exchange(
            board, chess.Move(from_square, chess.parse_square(name))
        )
        if see is not None and see >= MATERIAL_THRESHOLD:
            targets.append((piece_type, name))
    return targets


def _opponent_fork(board_after, steps, mover, window):
    """
    Первая вилка соперника в линии, где steps[0] — ход соперника: фигура,
    которой сходили (не взятием), выгодно бьёт ≥2 цели (_winning_targets),
    хотя бы одна из них ≥ коня.
    Возвращает (шаг, фигура, цели) либо None.
    """
    current = board_after.copy()
    opponent = not mover
    for step in steps[:window]:
        move = chess.Move.from_uci(step["uci"])
        current.push(move)
        if step["color"] != opponent or step["captured"] is not None:
            continue
        targets = _winning_targets(current, move.to_square, opponent)
        if len(targets) < 2:
            continue
        if max(PIECE_VALUE.get(t, 0) for t, _ in targets) < PIECE_VALUE[chess.KNIGHT]:
            continue
        return step, current.piece_at(move.to_square), targets
    return None


def fork_played_fact(board_after_played, steps_played, mover, window=FORK_WINDOW,
                     board_before=None, steps_best=None):
    """
    Ищет в линии ПОСЛЕ сыгранного хода ход СОПЕРНИКА, после которого его
    фигура одновременно и выгодно (SEE) бьёт ≥2 ваши цели. Контрфактика: если
    такая же вилка возможна в линии после лучшего хода (board_before и
    steps_best заданы), она не следствие сыгранного хода и не называется.
    Возвращает (текст, evidence) либо ("", None).
    """
    if not steps_played:
        return "", None
    found = _opponent_fork(board_after_played, steps_played, mover, window)
    if found is None:
        return "", None
    if board_before is not None and steps_best and len(steps_best) >= 2:
        board_best = board_before.copy()
        board_best.push(chess.Move.from_uci(steps_best[0]["uci"]))
        if _opponent_fork(board_best, steps_best[1:], mover, window) is not None:
            return "", None
    step, attacker, targets = found
    attacker_name = PIECE_NOM.get(attacker.piece_type, "фигура")
    square_name = chess.square_name(chess.parse_square(step["uci"][2:4]))
    targets_text = ", ".join(
        f"{PIECE_ACC.get(t, 'фигуру')} на {sq}" for t, sq in targets
    )
    text = (
        f"В линии после вашего хода соперник получает вилку: "
        f"{step['san']} — {attacker_name} на {square_name} "
        f"одновременно бьёт {targets_text}."
    )
    return text, {
        "ply": step["ply"],
        "san": step["san"],
        "piece": attacker.piece_type,
        "square": square_name,
        "targets": list(targets),
    }


def _safe_fork_played(board_after_played, steps_played, mover,
                      board_before=None, steps_best=None):
    try:
        return fork_played_fact(
            board_after_played, steps_played, mover,
            board_before=board_before, steps_best=steps_best,
        )
    except Exception:
        log.exception("pv_explainer: не удалось найти вилку соперника")
        return "", None


def castling_fact(board_before, board_after_played, played_move, best_uci, mover):
    """Ход лишает права на рокировку, а лучший ход его сохраняет."""
    if board_before.is_castling(played_move):
        return ""
    if not board_before.has_castling_rights(mover):
        return ""
    if board_after_played.has_castling_rights(mover):
        return ""
    try:
        move = chess.Move.from_uci(str(best_uci))
    except ValueError:
        return ""
    if move not in board_before.legal_moves:
        return ""
    after_best = board_before.copy()
    after_best.push(move)
    if after_best.has_castling_rights(mover):
        return "Ваш ход лишает вас права на рокировку, а лучший ход его сохраняет."
    return ""


def static_exchange(board, move):
    """
    Статический размен (SEE) на клетке взятия: выигрыш (в сотых пешки) для
    того, кто берёт, если обе стороны будут брать наименьшей фигурой.
    < 0 означает: простое взятие невыгодно. None — если посчитать нельзя
    (например, взятие на проходе).
    """
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim is None or attacker is None:
        return None

    gain = [PIECE_VALUE.get(victim.piece_type, 0)]
    on_square = ATTACK_VALUE.get(attacker.piece_type, 0)
    sim = board.copy()
    sim.remove_piece_at(move.from_square)
    sim.set_piece_at(move.to_square, attacker)
    side = not attacker.color

    while len(gain) < 32:
        attackers = list(sim.attackers(side, move.to_square))
        if not attackers:
            break
        square = min(
            attackers,
            key=lambda sq: ATTACK_VALUE.get(sim.piece_at(sq).piece_type, 0),
        )
        piece = sim.piece_at(square)
        gain.append(on_square - gain[-1])
        on_square = ATTACK_VALUE.get(piece.piece_type, 0)
        sim.remove_piece_at(square)
        sim.set_piece_at(move.to_square, piece)
        side = not side

    while len(gain) > 1:
        gain[-2] = -max(-gain[-2], gain[-1])
        gain.pop()
    return gain[0]


def _side_pieces(board, color, square):
    """
    Фигуры стороны color, которые бьют клетку square: [(тип, клетка)].
    Порядок явный: сначала дешёвые (так их вводят в размен), затем по клетке.
    Не зависит от того, в каком порядке библиотека отдаёт атакующих.
    """
    pieces = [
        (board.piece_at(sq).piece_type, chess.square_name(sq))
        for sq in board.attackers(color, square)
    ]
    return sorted(pieces, key=lambda p: (ATTACK_VALUE.get(p[0], 0), p[1]))


def capture_contexts(board, steps, start_board):
    """
    Для каждого взятия в линии: что происходило на клетке взятия НА МОМЕНТ
    хода — сколько фигур атаковало и сколько защищало, чем кончается простой
    размен (SEE) и сколько защитников было в начале линии.
    Возвращает {полуход: информация}. Всё — подсчёт атак на доске.
    """
    info = {}
    current = board.copy()
    for step in steps:
        move = chess.Move.from_uci(step["uci"])
        if step["captured"] is not None and not current.is_en_passant(move):
            victim = current.piece_at(move.to_square)
            capturer_color = current.turn
            start_defenders = None
            at_start = start_board.piece_at(move.to_square)
            if (at_start is not None and victim is not None
                    and at_start.piece_type == victim.piece_type
                    and at_start.color == victim.color):
                start_defenders = len(
                    start_board.attackers(victim.color, move.to_square)
                )
            info[step["ply"]] = {
                "san": step["san"],
                "square": chess.square_name(move.to_square),
                "attackers": _side_pieces(current, capturer_color, move.to_square),
                "defenders": _side_pieces(current, not capturer_color, move.to_square),
                "see": static_exchange(current, move),
                "start_defenders": start_defenders,
            }
        current.push(move)
    return info


def severity(loss):
    if loss < 100:
        return "небольшая неточность"
    if loss < 250:
        return "заметная неточность"
    if loss < 500:
        return "серьёзная ошибка"
    return "грубая ошибка"


def status_phrase(before, after):
    """Как изменилась общая ситуация (оценки с точки зрения ходящего)."""
    if before is None or after is None:
        return ""
    if before >= 150 and after < 50:
        return "Вы упустили преимущество."
    if before >= 150 and after >= 150:
        return "Преимущество у вас остаётся, но стало меньше."
    if before >= 150:
        return "Преимущество заметно уменьшилось."
    if before > -50 and after <= -150:
        return "Из ровной позиции вы перешли в заметно худшую."
    if -50 < before and after <= -50:
        return "Позиция стала хуже."
    if before <= -300 and after <= -300:
        return "Позиция была тяжёлой и стала ещё тяжелее."
    if before <= -50 and after <= before:
        return "Положение, и так неудобное, ухудшилось."
    return ""


# ----------------------------------------------------------------------
# Чистая логика (не требует python-chess: работает со списком шагов)
# ----------------------------------------------------------------------

def settled_index(steps, horizon=HORIZON):
    """
    Индекс шага, на котором фиксируем итог: горизонт, но не посреди размена
    (пока следующий ход — тоже взятие, двигаемся дальше).
    """
    if not steps:
        return None
    # Не уходим дальше SHOW_MAX_PLIES: всё, что называется в тексте,
    # должно быть видно в показанной линии.
    limit = min(len(steps), SHOW_MAX_PLIES)
    i = min(horizon, limit) - 1
    while i + 1 < limit and steps[i + 1]["captured"] is not None:
        i += 1
    return i


def settled_gain(steps, bal0, bal_default):
    """Итог по материалу относительно bal0 на «успокоившейся» позиции."""
    i = settled_index(steps)
    if i is None:
        return bal_default - bal0
    return steps[i]["balance"] - bal0


def cut_at_desperado(steps, first_index=0):
    """
    Обрезает линию там, где одна из сторон просто отдаёт фигуру: ход НЕ
    взятием на клетку, где фигуру тут же берут, и взявшего не берут обратно.
    В проигранных позициях движок «доигрывает» линию такими ходами; всё, что
    дальше, — не следствие сыгранного хода.
    Размен (фигуру берут и тут же возвращают) обрезкой не считается.
    first_index=1 для линии лучшего хода: сам лучший ход не трогаем.
    Возвращает (обрезанные_шаги, шаг_отдачи | None).
    """
    for i in range(first_index, len(steps) - 2):
        move, taken, after = steps[i], steps[i + 1], steps[i + 2]
        square = move["uci"][2:4]
        gives_piece = (
            move["captured"] is None
            and taken["captured"] is not None
            and taken["color"] != move["color"]
            and taken["captured_square"] == square
            and not (after["captured"] is not None
                     and after["captured_square"] == square)
        )
        if gives_piece:
            return steps[:i], move
    return steps, None


def step_label(step):
    """'23.Qc7' или '22...Be4' — подпись одного хода."""
    if step["color"] == chess.WHITE:
        return f"{step['fullmove']}.{step['san']}"
    return f"{step['fullmove']}...{step['san']}"


def window_events(steps, mover_color):
    """
    Все взятия в окне до «успокоившейся» позиции.
    Возвращает (потеряли_мы, забрали_мы, индекс_последнего_взятия | None).
    """
    lost, gained, last = [], [], None
    end = settled_index(steps)
    if end is None:
        return lost, gained, last
    for i, step in enumerate(steps[: end + 1]):
        if step["captured"] is None:
            continue
        last = i
        event = {
            "piece": step["captured"],
            "square": step["captured_square"],
            "san": step["san"],
            "ply": step["ply"],
        }
        (gained if step["color"] == mover_color else lost).append(event)
    return lost, gained, last


def net_events(lost, gained):
    """
    Сокращает простые размены: взятие и ответное взятие равной ценности
    НА ОДНОЙ КЛЕТКЕ (конь за коня на e4, слон за слона на c3) не показываются.
    Взятия на разных клетках и размены неравной ценности остаются как есть:
    нельзя «гасить» потерю на 1-м ходу взятием на 10-м.
    Возвращает (остаток_потерь, остаток_приобретений).
    """
    lost, gained = list(lost), list(gained)

    for l in list(lost):
        for g in gained:
            same_square = l["square"] == g["square"]
            same_value = PIECE_VALUE.get(l["piece"], 0) == PIECE_VALUE.get(g["piece"], 0)
            if same_square and same_value:
                lost.remove(l)
                gained.remove(g)
                break
    return lost, gained

def _own_piece_map(board, mover):
    """
    {имя клетки: тип фигуры} для фигур стороны mover в данной позиции.
    Нужно, чтобы отличить «наша фигура стояла здесь с начала линии» от
    «фигура пришла на эту клетку уже во время линии».
    """
    return {
        chess.square_name(sq): piece.piece_type
        for sq, piece in board.piece_map().items()
        if piece.color == mover
    }


def filter_late_events(lost, gained, own_map):
    """
    Убирает «поздние» потери: те, где наша фигура оказалась на клетке
    взятия уже во время линии (в начале линии там стояла не она).
    Вместе с потерей уходит и парное приобретение на той же клетке —
    это один эпизод линии, а не следствие сыгранного хода.

    own_map — {имя клетки: тип фигуры} на начало линии.
    Возвращает (оставшиеся_потери, оставшиеся_приобретения, меняли_ли).
    """
    late_squares = set()
    for event in lost:
        if own_map.get(event["square"]) != event["piece"]:
            late_squares.add(event["square"])
    if not late_squares:
        return lost, gained, False
    kept_lost = [e for e in lost if e["square"] not in late_squares]
    kept_gained = [e for e in gained if e["square"] not in late_squares]
    return kept_lost, kept_gained, True


def _gain_from_events(lost, gained):
    """Суммарный материальный итог по уже отобранным событиям (сотые пешки)."""
    lost_value = sum(PIECE_VALUE.get(e["piece"], 0) for e in lost)
    gained_value = sum(PIECE_VALUE.get(e["piece"], 0) for e in gained)
    return gained_value - lost_value


def find_mate(steps):
    """(кто_матует, полуход) если линия заканчивается матом достаточно быстро."""
    for step in steps[:MATE_MAX_PLIES]:
        if step["is_mate"]:
            return step["color"], step["ply"]
    return None


def format_line(steps):
    """['17...Qg8', '18.Rxd5', 'Rhd1'] — как в шахматной записи."""
    out = []
    for i, s in enumerate(steps[:SHOW_MAX_PLIES]):
        if s["color"] == chess.WHITE:
            out.append(f"{s['fullmove']}.{s['san']}")
        elif i == 0:
            out.append(f"{s['fullmove']}...{s['san']}")
        else:
            out.append(s["san"])
    return " ".join(out)


def _events_text(events):
    shown = events[:SHOW_MAX_EVENTS]
    text = ", ".join(
        f"{PIECE_ACC.get(e['piece'], 'фигуру')} на {e['square']} ({e['san']})"
        for e in shown
    )
    if len(events) > len(shown):
        text += f" и ещё {len(events) - len(shown)}"
    return text


def _pieces_text(pieces):
    return ", ".join(f"{PIECE_NOM.get(t, 'фигура')} {sq}" for t, sq in pieces)


def capture_sentence(info):
    """Почему взятие возможно: сколько атакующих и защитников на клетке."""
    if not info:
        return ""
    attackers, defenders = info["attackers"], info["defenders"]
    text = f"Перед {info['san']} на клетку {info['square']}: атакующих — {len(attackers)}"
    if attackers:
        text += f" ({_pieces_text(attackers)})"
    text += f", защитников — {len(defenders)}"
    if defenders:
        text += f" ({_pieces_text(defenders)})"
    text += "."
    start = info.get("start_defenders")
    if start is not None and start != len(defenders):
        text += f" В начале линии защитников было {start}."
    if info.get("see") is not None and info["see"] < 0:
        text += (
            " Простое взятие здесь невыгодно: результат держится на "
            "дальнейших ходах линии."
        )
    return text


def played_line_note(played, played_capture, lost_p):
    """
    Почему у сыгранного хода итог по материалу ниже: что соперник забирает в
    линии движка после него. Если сыгранный ход сам брал материал, это
    названо («берёт пешку, но соперник забирает пешку»). Пусто, если по линии
    соперник ничего не забирает.
    """
    if not lost_p:
        return ""
    taken = _events_text(lost_p)
    if played_capture:
        piece, square = played_capture
        return (
            f"Сыгранный {played} берёт {PIECE_ACC.get(piece, 'фигуру')} "
            f"на {square}, но по линии движка соперник забирает {taken}."
        )
    return f"По линии движка после {played} соперник забирает {taken}."


def first_by_ply(events):
    return min(events, key=lambda e: e["ply"]) if events else None


def classify(c):
    """
    Выбор причины. Чистая функция: на входе словарь c, на выходе результат.

    Ключи c:
      mover (bool), played, best, loss, before, after,
      bal0, bal_after_played,
      steps_played, steps_best,
      played_score (kind, value), best_score (kind, value),
      ignored_threat_text, ignored_threat_evidence,      
      own_played_map (dict | None) — что у ходящего стояло в начале линии
      played_capture ((тип, клетка) | None) — что взял сам сыгранный ход
    """
    mover = c["mover"]
    played, best = c["played"], c["best"]
    loss = c.get("loss") or 0
    before, after = c.get("before"), c.get("after")
    sp, sb = c["steps_played"], c["steps_best"]
    bal0 = c["bal0"]

    p_kind, p_val = c["played_score"]
    b_kind, b_val = c["best_score"]

    all_lost_p, all_gained_p, last_p = window_events(sp, mover)
    all_lost_b, all_gained_b, last_b = window_events(sb, mover)

    own_map = c.get("own_played_map")
    if own_map is None:
        filtered_p = False
    else:
        all_lost_p, all_gained_p, filtered_p = filter_late_events(
            all_lost_p, all_gained_p, own_map
        )

    lost_p, gained_p = net_events(all_lost_p, all_gained_p)
    lost_b, gained_b = net_events(all_lost_b, all_gained_b)

    settled_p = settled_gain(sp, bal0, c["bal_after_played"])
    if filtered_p:
        # Фильтр «поздней потери» может только уменьшить ущерб: если он
        # дал более отрицательный итог, чем реальный материальный перевес,
        # значит, заодно выкинулись и приобретения на поздних клетках,
        # и доверять этой сумме нельзя.
        g_p = max(_gain_from_events(lost_p, gained_p), settled_p)
    else:
        g_p = settled_p
    g_b = settled_gain(sb, bal0, sb[0]["balance"] if sb else bal0)

    evidence = {
        "played": played,
        "best": best,
        "loss": loss,
        "before": before,
        "after": after,
        "gain_played": g_p,
        "gain_best": g_b,
        "line_played": format_line(sp),
        "line_best": format_line(sb),
        "lost": lost_p,
        "gained": gained_p,
        "ignored_threat": c.get("ignored_threat_evidence"),
        "fork_best": c.get("fork_best_evidence"),
        "fork_played": c.get("fork_played_evidence"),
    }

    secondary = None
    if before is not None and before <= -300:
        secondary = (
            f"Позиция и до этого хода была сильно хуже (оценка {fmt_eval(before)})."
        )

    desperado = c.get("desperado_played")
    tail_note = ""
    if desperado is not None and desperado["color"] == mover:
        tail_note = (
            " Дальше в линии движка вам приходится отдавать материал "
            f"(ход {step_label(desperado)}), положение уже близко к "
            "безнадёжному, поэтому дальнейшие потери в линию не включены."
        )
        evidence["desperado"] = step_label(desperado)

    def result(kind, main):
        evidence["type"] = kind
        return {"type": kind, "main": main + (tail_note if kind in
                ("material_loss", "positional") else ""),
                "secondary": secondary, "evidence": evidence}

    # --- 1. нам дают мат ------------------------------------------------
    full_p = c.get("steps_played_full") or sp
    full_b = c.get("steps_best_full") or sb
    mate_p = find_mate(full_p)
    mate_b = find_mate(full_b)
    opp_mates_after_played = (mate_p and mate_p[0] != mover) or (
        p_kind == "mate" and p_val < 0
    )
    opp_mates_after_best = (mate_b and mate_b[0] != mover) or (
        b_kind == "mate" and b_val < 0
    )
    if opp_mates_after_played and not opp_mates_after_best:
        if mate_p and mate_p[0] != mover:
            n = (mate_p[1] + 1) // 2
            line = format_line(full_p[: mate_p[1]])
            evidence["mate_in"] = n
            return result(
                "mate_allowed",
                f"После {played} у соперника форсированный мат в {n}. "
                f"Линия: {line}.",
            )
        n = -p_val
        first = f" Начинается с {sp[0]['san']}." if sp else ""
        evidence["mate_in"] = n
        return result(
            "mate_allowed",
            f"После {played} у соперника форсированный мат в {n}.{first}",
        )

    # --- 2. мы упустили мат ---------------------------------------------
    we_mate_best = (mate_b and mate_b[0] == mover) or (
        b_kind == "mate" and b_val > 0
    )
    we_mate_played = (mate_p and mate_p[0] == mover) or (
        p_kind == "mate" and p_val > 0
    )
    if we_mate_best and not we_mate_played:
        if mate_b and mate_b[0] == mover:
            n = (mate_b[1] + 1) // 2
            line = format_line(full_b[: mate_b[1]])
            evidence["mate_in"] = n
            return result(
                "missed_mate", f"Вы упустили мат в {n}: {best}. Линия: {line}."
            )
        n = b_val
        evidence["mate_in"] = n
        return result("missed_mate", f"Вы упустили мат в {n}: {best}.")

    # --- 3. потеря материала (контрфактически подтверждённая) ------------
    if (
        g_p <= -MATERIAL_THRESHOLD
        and g_b - g_p >= MATERIAL_THRESHOLD
        and lost_p
        and min(e["ply"] for e in lost_p) <= MAX_LOSS_PLY
        and loss >= MIN_LOSS_FOR_MATERIAL
    ):
        end = last_p + 1
        main = (
            f"По линии движка после {played} соперник выигрывает материал: "
            f"забирает {_events_text(lost_p)}."
        )
        if gained_p:
            main += f" Взамен вы забираете {_events_text(gained_p)}."
        first = first_by_ply(lost_p)
        why_possible = capture_sentence(
            (c.get("capture_info_played") or {}).get(first["ply"])
        ) if first else ""
        if why_possible:
            main += " " + why_possible
        main += f" Изменение материала: {g_p / 100:+.0f}."
        main += f" Линия: {format_line(sp[:end])}."
        if g_b > -MATERIAL_THRESHOLD:
            main += f" После {best} такой потери нет."

        # Проигнорированная угроза — идёт ПЕРЕД разбором потери материала.
        it_text = c.get("ignored_threat_text")
        if it_text:
            main = it_text + " " + main

        fork_played_text = c.get("fork_played_text")
        if fork_played_text:
            main += " " + fork_played_text

        return result("material_loss", main)

    # --- 4. упущенный выигрыш материала ----------------------------------
    if (
        g_b >= MATERIAL_THRESHOLD
        and g_b - g_p >= MATERIAL_THRESHOLD
        and gained_b
        and min(e["ply"] for e in gained_b) <= MAX_GAIN_PLY
        and loss >= MIN_LOSS_FOR_MISSED
    ):
        end = last_b + 1
        after_best = bal0 + g_b
        gains_text = _events_text(gained_b)
        if lost_b:
            gains_text += f"; при этом соперник забирает {_events_text(lost_b)}"
        if bal0 < 0 and after_best < 0:
            head = (
                f"Лучший ход {best} позволял сократить отставание "
                f"в материале: вы забираете {gains_text}."
            )
        else:
            head = (
                f"Вы упустили выигрыш материала: по линии движка после "
                f"{best} вы забираете {gains_text}."
            )
        main = head
        first = first_by_ply(gained_b)
        why_possible = capture_sentence(
            (c.get("capture_info_best") or {}).get(first["ply"])
        ) if first else ""
        if why_possible:
            main += " " + why_possible
        main += f" Изменение материала: {g_b / 100:+.0f}"
        main += f" (после {played}: {g_p / 100:+.0f})."
        if after_best < 0:
            main += f" По абсолютному балансу вы всё ещё в минусе на {abs(after_best) / 100:.0f}."
        main += f" Линия: {format_line(sb[:end])}."

        note = played_line_note(played, c.get("played_capture"), lost_p)
        if note and last_p is not None:
            main += f" {note} Линия после {played}: {format_line(sp[:last_p + 1])}."
            evidence["played_note"] = note
        evidence["lost_best"] = lost_b

        fork_text = c.get("fork_best_text")
        if fork_text:
            main += " " + fork_text

        fork_played_text = c.get("fork_played_text")
        if fork_played_text:
            main += " " + fork_played_text

        return result("missed_material", main)

    # --- 5. остальное: только проверяемые факты ---------------------------
    parts = []
    default_branch = False
    if g_p <= -MATERIAL_THRESHOLD and g_b - g_p < MATERIAL_THRESHOLD:
        parts.append(
            "Материал теряется и после лучшего хода, так что это не следствие "
            "вашего хода, но ход всё равно ухудшил оценку."
        )
    elif g_p <= -MATERIAL_THRESHOLD and loss < MIN_LOSS_FOR_MATERIAL:
        if g_b > -MATERIAL_THRESHOLD:
            parts.append(
                "По линии движка вы отдаёте материал, но оценка почти не "
                "меняется: похоже на допустимую жертву."
            )
        else:
            parts.append(
                f"По линии движка вы теряете материал (итог {g_p / 100:+.0f}), "
                f"но и после {best} итог {g_b / 100:+.0f}, поэтому оценка "
                "меняется мало."
            )
    else:
        default_branch = True
        if loss < MIN_LOSS_FOR_MATERIAL:
            parts.append(
                f"Ход разумный: разница с лучшим всего {loss / 100:.2f} пешки, "
                "это скорее нюанс, чем ошибка."
            )
        else:
            parts.append(
                f"{severity(loss).capitalize()}: оценка падает на "
                f"{loss / 100:.2f} пешки."
            )

    if default_branch:
        status = status_phrase(before, after)
        if status:
            parts.append(status)

    reply = c.get("reply_text") or (
        f"Сильнейший ответ соперника — {sp[0]['san']}." if sp else ""
    )
    if reply:
        parts.append(reply)

    for extra in (c.get("structure_text"), c.get("castling_text")):
        if extra:
            parts.append(extra)

    center_text = c.get("center_text")
    if center_text:
        parts.append(center_text)

    fact = c.get("best_fact")
    if fact and not center_text:
        parts.append(f"Ход {best} — {fact}.")

    def ev(value):
        return f" ({fmt_eval(value)})" if value is not None else ""

    best_cp = b_val if b_kind == "cp" else None
    if sp:
        parts.append(f"Линия после вашего хода{ev(after)}: {format_line(sp[:4])}.")
    if len(sb) >= 2:
        parts.append(f"Линия после {best}{ev(best_cp)}: {format_line(sb[:4])}.")

    return result("positional", " ".join(parts))


# ----------------------------------------------------------------------
# Склейка: mistake -> результат -> текст
# ----------------------------------------------------------------------

def _main_played_line(played_results):
    """PV из основной (multipv == 1) строки анализа сыгранного хода."""
    if not played_results:
        return []
    for entry in played_results:
        if isinstance(entry, dict) and entry.get("multipv") == 1:
            return entry.get("pv") or []
    first = played_results[0]
    return (first.get("pv") or []) if isinstance(first, dict) else []


def _main_played_score(played_results):
    if not played_results:
        return None
    for entry in played_results:
        if isinstance(entry, dict) and entry.get("multipv") == 1:
            return entry.get("score")
    first = played_results[0]
    return first.get("score") if isinstance(first, dict) else None


def analyze(mistake):
    """Полный разбор одной ошибки. Бросает исключение при неверных данных."""
    board = _to_board(mistake.get("position_before"))
    played = mistake.get("played_san") or mistake.get("played") or ""
    best = mistake.get("best") or ""
    if board is None or not played:
        return {"type": "no_position", "main": "", "secondary": None,
                "evidence": {}}

    mover = board.turn
    played_move = board.parse_san(played)
    after_board = board.copy()
    after_board.push(played_move)

    best_line = mistake.get("pv") or []
    best_uci = mistake.get("best_uci")
    if not best_line or (best_uci and str(best_line[0]) != str(best_uci)):
        best_line = [best_uci] if best_uci else []

    played_results = mistake.get("played_results") or []

    steps_played_full = replay_line(after_board, _main_played_line(played_results), mover)
    steps_best_full = replay_line(board, best_line, mover)
    steps_played, desperado_played = cut_at_desperado(steps_played_full, 0)
    steps_best, _desperado_best = cut_at_desperado(steps_best_full, 1)

    played_captured = None
    if board.is_capture(played_move):
        played_captured = (
            chess.PAWN if board.is_en_passant(played_move)
            else board.piece_at(played_move.to_square).piece_type
        )

    played_capture = (
        (played_captured, _captured_square(board, played_move))
        if played_captured is not None else None
    )

    reply_text = _safe(lambda: reply_facts(
        after_board, steps_played, played_move.to_square, played_captured
    ))
    structure_text = _safe(lambda: structure_fact(
        board, after_board, steps_played, steps_best, mover, best
    ))
    castling_text = _safe(lambda: castling_fact(
        board, after_board, played_move, best_uci, mover
    ))
    best_fact = _safe(lambda: best_move_fact(board, best_uci))
    capture_info_played = _safe_dict(
        lambda: capture_contexts(after_board, steps_played, after_board)
    )
    capture_info_best = _safe_dict(
        lambda: capture_contexts(board, steps_best, board)
    )

    # <<< НОВОЕ: считаем факт «проигнорированная угроза» >>>
    ignored_threat_text, ignored_threat_evidence = _safe_ignored_threat(
        board, played_move, steps_played, steps_best, mover
    )
    
    center_text = _safe(lambda: center_fact(board, played_move, best_uci, best))

    fork_best_text, fork_best_evidence = _safe_fork(board, steps_best, mover)

    fork_played_text, fork_played_evidence = _safe_fork_played(
        after_board, steps_played, mover, board, steps_best
    )

    own_played_map = _own_piece_map(after_board, mover)

    ctx = {
        "mover": mover,
        "played": played,
        "best": best,
        "loss": _num(mistake.get("loss"), 0),
        "before": _white_pov_to_mover(mistake.get("before_score"), mover),
        "after": _white_pov_to_mover(mistake.get("after_score"), mover),
        "bal0": material(board, mover),
        "bal_after_played": material(after_board, mover),
        "steps_played": steps_played,
        "steps_best": steps_best,
        "steps_played_full": steps_played_full,
        "steps_best_full": steps_best_full,
        "desperado_played": desperado_played,
        "reply_text": reply_text,
        "structure_text": structure_text,
        "castling_text": castling_text,
        "best_fact": best_fact,
        "capture_info_played": capture_info_played,
        "capture_info_best": capture_info_best,
        "played_score": parse_score(_main_played_score(played_results), mover),
        # <<< НОВОЕ: передаём факт в classify >>>
        "ignored_threat_text": ignored_threat_text,
        "ignored_threat_evidence": ignored_threat_evidence,
        "center_text": center_text,
        "fork_best_text": fork_best_text,
        "fork_best_evidence": fork_best_evidence,
        "fork_played_text": fork_played_text,
        "fork_played_evidence": fork_played_evidence,
        "own_played_map": own_played_map,
        "played_capture": played_capture,
        "best_score": parse_score(
            mistake.get("best_score_obj"), mover, default_pov=chess.WHITE
        ),
    }
    return classify(ctx)


def _captured_square(board, move):
    """Клетка, где стояла взятая фигура (при взятии на проходе — не клетка хода)."""
    if board.is_en_passant(move):
        return chess.square_name(
            chess.square(chess.square_file(move.to_square),
                         chess.square_rank(move.from_square))
        )
    return chess.square_name(move.to_square)


def _safe(func):
    """Необязательные факты не должны ломать объяснение, но ошибка пишется в лог."""
    try:
        return func()
    except Exception:
        log.exception("pv_explainer: не удалось собрать дополнительный факт")
        return ""


def _safe_dict(func):
    try:
        return func()
    except Exception:
        log.exception("pv_explainer: не удалось посчитать контекст взятий")
        return {}


def _safe_ignored_threat(board_before, played_move, steps_played, steps_best, mover):
    try:
        return ignored_threat_fact(
            board_before, played_move, steps_played, steps_best, mover
        )
    except Exception:
        log.exception("pv_explainer: не удалось проверить проигнорированную угрозу")
        return "", None


def _white_pov_to_mover(value, mover):
    """before_score / after_score в приложении — с точки зрения БЕЛЫХ."""
    number = _num(value)
    if number is None:
        return None
    return number if mover == chess.WHITE else -number


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _other_moves(mistake, result):
    """Альтернативы без сыгранного и лучшего ходов."""
    played = mistake.get("played_san") or mistake.get("played")
    best = mistake.get("best")
    skip = {played, best}

    equivalent = []
    for item in mistake.get("equivalent_best_moves") or []:
        san = item.get("san") if isinstance(item, dict) else None
        if san and san not in skip and san not in equivalent:
            equivalent.append(san)

    others = []
    for san in mistake.get("alternatives") or []:
        if isinstance(san, str) and san not in skip and san not in equivalent \
                and san not in others:
            others.append(san)
    return equivalent[:2], others[:2]


def render(mistake, result):
    played = mistake.get("played_san") or mistake.get("played") or ""
    best = mistake.get("best") or ""

    head = f"Вы сыграли {played}, но сильнее было {best}." if played and best \
        else (f"Вы сыграли {played}." if played else f"Лучшим ходом было {best}.")

    if not result or not result.get("main"):
        return head

    parts = [head, f"**Почему это ошибка:** {result['main']}"]
    if result.get("secondary"):
        parts.append(result["secondary"])

    evidence = result.get("evidence") or {}
    before, after = evidence.get("before"), evidence.get("after")
    if before is not None and after is not None:
        parts.append(
            f"**Оценка позиции (с вашей стороны):** "
            f"{fmt_eval(before)} → {fmt_eval(after)}."
        )

    equivalent, others = _other_moves(mistake, result)
    if equivalent:
        parts.append("**Практически равноценный вариант:** " + ", ".join(equivalent) + ".")
    if others:
        parts.append("**Другие хорошие варианты:** " + ", ".join(others) + ".")

    return "\n\n".join(parts)


def generate_explanation_v2(mistake):
    """Замена generate_explanation(mistake). Ошибки не глотаются: пишутся в лог."""
    try:
        result = analyze(mistake)
    except Exception:
        log.exception("pv_explainer: не удалось разобрать ошибку")
        result = None
    return render(mistake, result)