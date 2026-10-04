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
}
 
PIECE_NOM = {  # именительный: «пешка на f3 атакует ...»
    chess.PAWN: "пешка",
    chess.KNIGHT: "конь",
    chess.BISHOP: "слон",
    chess.ROOK: "ладья",
    chess.QUEEN: "ферзь",
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
 
 
STRUCT_WINDOW = 6   # сколько полуходов линии смотрим на пешечную структуру
 
 
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
 
 
def classify(c):
    """
    Выбор причины. Чистая функция: на входе словарь c, на выходе результат.
 
    Ключи c:
      mover (bool), played, best, loss, before, after,
      bal0, bal_after_played,
      steps_played, steps_best,
      played_score (kind, value), best_score (kind, value)
    """
    mover = c["mover"]
    played, best = c["played"], c["best"]
    loss = c.get("loss") or 0
    before, after = c.get("before"), c.get("after")
    sp, sb = c["steps_played"], c["steps_best"]
    bal0 = c["bal0"]
 
    p_kind, p_val = c["played_score"]
    b_kind, b_val = c["best_score"]
 
    g_p = settled_gain(sp, bal0, c["bal_after_played"])
    g_b = settled_gain(sb, bal0, sb[0]["balance"] if sb else bal0)
    all_lost_p, all_gained_p, last_p = window_events(sp, mover)
    all_lost_b, all_gained_b, last_b = window_events(sb, mover)
    lost_p, gained_p = net_events(all_lost_p, all_gained_p)
    lost_b, gained_b = net_events(all_lost_b, all_gained_b)
 
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
    }
 
    secondary = None
    if before is not None and before <= -300:
        secondary = (
            f"Позиция и до этого хода была сильно хуже (оценка {fmt_eval(before)})."
        )
 
    def result(kind, main):
        evidence["type"] = kind
        return {"type": kind, "main": main, "secondary": secondary,
                "evidence": evidence}
 
    # --- 1. нам дают мат ------------------------------------------------
    mate_p = find_mate(sp)
    mate_b = find_mate(sb)
    opp_mates_after_played = (mate_p and mate_p[0] != mover) or (
        p_kind == "mate" and p_val < 0
    )
    opp_mates_after_best = (mate_b and mate_b[0] != mover) or (
        b_kind == "mate" and b_val < 0
    )
    if opp_mates_after_played and not opp_mates_after_best:
        if mate_p and mate_p[0] != mover:
            n = (mate_p[1] + 1) // 2
            line = format_line(sp[: mate_p[1]])
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
            line = format_line(sb[: mate_b[1]])
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
        main += f" Итог по материалу: {g_p / 100:+.0f}."
        main += f" Линия: {format_line(sp[:end])}."
        if g_b > -MATERIAL_THRESHOLD:
            main += f" После {best} такой потери нет."
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
        main = (
            f"Вы упустили выигрыш материала: по линии движка после {best} "
            f"вы забираете {_events_text(gained_b)}."
        )
        main += f" Итог по материалу: {g_b / 100:+.0f}"
        main += f" (после {played}: {g_p / 100:+.0f})."
        main += f" Линия: {format_line(sb[:end])}."
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
 
    fact = c.get("best_fact")
    if fact:
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
 
    steps_played = replay_line(after_board, _main_played_line(played_results), mover)
    steps_best = replay_line(board, best_line, mover)
 
    played_captured = None
    if board.is_capture(played_move):
        played_captured = (
            chess.PAWN if board.is_en_passant(played_move)
            else board.piece_at(played_move.to_square).piece_type
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
        "reply_text": reply_text,
        "structure_text": structure_text,
        "castling_text": castling_text,
        "best_fact": best_fact,
        "played_score": parse_score(_main_played_score(played_results), mover),
        "best_score": parse_score(
            mistake.get("best_score_obj"), mover, default_pov=chess.WHITE
        ),
    }
    return classify(ctx)
 
 
def _safe(func):
    """Необязательные факты не должны ломать объяснение, но ошибка пишется в лог."""
    try:
        return func()
    except Exception:
        log.exception("pv_explainer: не удалось собрать дополнительный факт")
        return ""
 
 
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
 