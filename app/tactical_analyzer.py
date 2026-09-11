import chess


PIECE_NAMES = {
    chess.PAWN: "пешка",
    chess.KNIGHT: "конь",
    chess.BISHOP: "слон",
    chess.ROOK: "ладья",
    chess.QUEEN: "ферзь",
    chess.KING: "король",
}


PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}


PIECE_PRIORITY = {
    "пешка": 1,
    "конь": 3,
    "слон": 3,
    "ладья": 5,
    "ферзь": 9,
}


class TacticalAnalyzer:

    print("!!! ЗАГРУЖЕН НОВЫЙ TACTICAL ANALYZER !!!")

    def __init__(self, board, best_move, played_move):

        self.board = board
        self.best_move = best_move
        self.played_move = played_move

    # ==========================================================
    # ОСНОВНОЙ АНАЛИЗ
    # ==========================================================

    def analyze(self):

        result = {
            "theme": None,

            "captured_piece": None,
            "captured_value": None,

            "hanging_piece": None,
            "hanging_square": None,

            "attacker": None,
            "attacker_square": None,

            "fork": False,
            "pin": False,
            "pin_piece": None,
            "pin_square": None,
            "fork_targets": [],

            # Лучший ход
            "best_move": self.best_move,

            # Равноценный размен
            "best_piece": None,
            "best_square": None,
            "target_piece": None,
            "target_square": None,

            # Атака фигуры пешкой
            "pawn_attack_piece": None,
            "pawn_attack_square": None,
            "pawn_attacker_square": None,
            "new_attack_piece": None,
            "new_attack_square": None,
            "new_attack_attacker": None,
            "new_attack_attacker_square": None,
            # Темповая атака пешкой
            "pawn_tempo_attack": False,
            "pawn_tempo_piece": None,
            "pawn_tempo_square": None,
            "pawn_tempo_move": None,
            "pawn_tempo_explanation": None,

            # Угроза пешкой
            "pawn_threat": False,
            "pawn_threat_piece": None,
            "pawn_threat_square": None,
            "pawn_threat_attacker_square": None,
            "pawn_threat_move": None,
            "pawn_threat_explanation": None,

            # Специальные мотивы
            "pawn_king_attack": False,
            "pawn_king_attack_explanation": None,

            "knight_sacrifice": False,
            "knight_sacrifice_explanation": None,
            "wasted_king_tempo": False,
            "wasted_king_tempo_explanation": None,
            "bad_recapture": False,
            "bad_recapture_explanation": None,
            "free_pawn": False,
            "free_pawn_explanation": None,
            
        }

        # ==========================================================
        # ПОЗИЦИЯ ПОСЛЕ СЫГРАННОГО ХОДА
        # ==========================================================

        position_after_played = self.board.copy()

        try:
            position_after_played.push(self.played_move)
        except ValueError:
            return result

        # ==========================================================
        # ПОЗИЦИЯ ПОСЛЕ ЛУЧШЕГО ХОДА
        # ==========================================================

        board_after_best = self.board.copy()

        try:
            board_after_best.push(self.best_move)
        except ValueError:
            return result

        # ==========================================================
        # ВИСЯЩАЯ ФИГУРА ПОСЛЕ СЫГРАННОГО ХОДА
        # ==========================================================

        self.detect_hanging_piece(
            position_after_played,
            result
        )

        # ==========================================================
        # ЧТО ЛУЧШИЙ ХОД ВЗЯЛ
        # ==========================================================

        self.detect_captured_piece(result)

        # ==========================================================
        # ВИЛКА
        # ==========================================================

        if self.detect_fork():

            result["fork"] = True

        # ==========================================================
        # СВЯЗКА
        # ==========================================================

        pin_info = self.detect_pin()

        if pin_info is not None:

            result["pin"] = True

            result["pin_piece"] = pin_info["piece"]

            result["pin_square"] = pin_info["square"]

        # ==========================================================
        # АТАКА ФИГУРЫ ПЕШКОЙ
        # ==========================================================

        pawn_attack = self.detect_pawn_attack()

        if pawn_attack is not None:

            result["pawn_attack_piece"] = (
                pawn_attack["piece"]
            )

            result["pawn_attack_square"] = (
                pawn_attack["square"]
            )

            result["pawn_attacker_square"] = (
                pawn_attack["attacker_square"]
            )

        # ==========================================================
        # НОВАЯ АТАКА НА ФИГУРУ
        # ==========================================================

        new_attack = self.detect_new_attack()

        if new_attack is not None:

            result["new_attack_piece"] = (
                new_attack["piece"]
            )

            result["new_attack_square"] = (
                new_attack["square"]
            )

            result["new_attack_attacker"] = (
                new_attack["attacker"]
            )

            result["new_attack_attacker_square"] = (
                new_attack["attacker_square"]
            )

        # ==========================================================
        # ТЕМПОВАЯ АТАКА ПЕШКОЙ
        # ==========================================================

        pawn_tempo = self.detect_pawn_tempo_attack()

        print("PAWN TEMPO RESULT:", pawn_tempo)


        if pawn_tempo is not None:

            result["pawn_tempo_attack"] = True

            result["pawn_tempo_piece"] = (
                pawn_tempo["piece"]
            )

            result["pawn_tempo_square"] = (
                pawn_tempo["square"]
            )

            result["pawn_tempo_move"] = (
                pawn_tempo["pawn_move"]
            )

            result["pawn_tempo_explanation"] = (
                pawn_tempo["explanation"]
            )

        # ==========================================================
        # УГРОЗА ПЕШКОЙ НА СЛЕДУЮЩЕМ ХОДУ
        # ==========================================================

        pawn_threat = self.detect_pawn_threat()

        if pawn_threat is not None:

            result["pawn_threat"] = True

            result["pawn_threat_piece"] = (
                pawn_threat["piece"]
            )

            result["pawn_threat_square"] = (
                pawn_threat["square"]
            )

            result["pawn_threat_attacker_square"] = (
                pawn_threat["attacker_square"]
            )

            result["pawn_threat_move"] = (
                chess.square_name(
                    pawn_threat["pawn_move"].from_square
                )
                + "-"
                + chess.square_name(
                    pawn_threat["pawn_move"].to_square
                )
            )

            result["pawn_threat_explanation"] = (
                f"После вашего хода соперник может атаковать "
                f"{pawn_threat['piece']} на "
                f"{pawn_threat['square']} пешкой с "
                f"{pawn_threat['attacker_square']}."
            )

        # ==========================================================
        # ПРОДВИЖЕНИЕ ПЕШКИ И АТАКА НА КОРОЛЯ
        # ==========================================================

        pawn_king_attack = self.detect_pawn_king_attack()

        if pawn_king_attack is not None:

            result["pawn_king_attack"] = True

            result["pawn_king_attack_explanation"] = (
                pawn_king_attack
            )

        # ==========================================================
        # ЖЕРТВА КОНЯ РАДИ ТАКТИЧЕСКОЙ АТАКИ
        # ==========================================================

        knight_sacrifice = self.detect_knight_sacrifice()

        if knight_sacrifice is not None:

            result["knight_sacrifice"] = True

            result["knight_sacrifice_explanation"] = (
                knight_sacrifice
            )

        # ==========================================================
        # ПОТЕРЯ ТЕМПА КОРОЛЁМ
        # ==========================================================

        wasted_king_tempo = self.detect_wasted_king_tempo()

        if wasted_king_tempo is not None:

            result["wasted_king_tempo"] = True

            result["wasted_king_tempo_explanation"] = (
                wasted_king_tempo
            )

        # ==========================================================
        # НЕВЫГОДНОЕ ВЗЯТИЕ ПОСЛЕ РАЗМЕНА
        # ==========================================================

        bad_recapture = self.detect_bad_recapture()

        if bad_recapture is not None:
            result["bad_recapture_explanation"] = bad_recapture

        # ==========================================================
        # УПУЩЕНА БЕСПЛАТНАЯ ПЕШКА
        # ==========================================================

        free_pawn = self.detect_free_pawn()

        if free_pawn is not None:

            result["free_pawn"] = True

            result["free_pawn_explanation"] = (
                free_pawn
            )

            
        # ==========================================================
        # ЦЕЛИ ВИЛКИ
        # ==========================================================

        self.detect_fork_targets(result)

        # ==========================================================
        # ОПРЕДЕЛЯЕМ ТЕМУ
        # ==========================================================

        result["theme"] = self.detect_theme(result)

        return result

    # ==========================================================
    # ВИСЯЩАЯ ФИГУРА
    # ==========================================================

    def detect_hanging_piece(self, board, result):

        side_to_move = board.turn

        for square, piece in board.piece_map().items():

            # Нас интересуют только наши фигуры
            if piece.color != side_to_move:
                continue

            # Короля не считаем висящей фигурой
            if piece.piece_type == chess.KING:
                continue

            # Кто атакует эту фигуру
            attackers = board.attackers(
                not side_to_move,
                square
            )

            # Кто её защищает
            defenders = board.attackers(
                side_to_move,
                square
            )

            # --------------------------------------------------
            # ВАЖНО:
            # Среди атакующих не может быть наш король.
            # Здесь дополнительно проверяем цвет и тип фигуры.
            # --------------------------------------------------

            real_attackers = []

            for attacker_square in attackers:

                attacker_piece = board.piece_at(
                    attacker_square
                )

                if attacker_piece is None:
                    continue

                if attacker_piece.color != side_to_move:

                    if attacker_piece.piece_type != chess.KING:

                        real_attackers.append(
                            attacker_square
                        )

            # Если фигура атакована и не защищена —
            # считаем её висящей
            if real_attackers and not defenders:

                attacker_square = real_attackers[0]

                attacker_piece = board.piece_at(
                    attacker_square
                )

                result["hanging_piece"] = (
                    PIECE_NAMES[piece.piece_type]
                )

                result["hanging_square"] = (
                    chess.square_name(square)
                )

                if attacker_piece:

                    result["attacker"] = (
                        PIECE_NAMES[
                            attacker_piece.piece_type
                        ]
                    )

                    result["attacker_square"] = (
                        chess.square_name(
                            attacker_square
                        )
                    )

                return

    def detect_captured_piece(self, result):

        if not self.board.is_capture(
            self.best_move
        ):
            return

        if self.board.is_en_passant(
            self.best_move
        ):

            result["captured_piece"] = "пешку"
            result["captured_value"] = 1

            return

        piece = self.board.piece_at(
            self.best_move.to_square
        )

        if piece is None:
            return

        result["captured_piece"] = (
            PIECE_NAMES.get(
                piece.piece_type
            )
        )

        result["captured_value"] = (
            PIECE_VALUES.get(
                piece.piece_type
            )
        )

    # ==========================================================
    # ВИЛКА
    # ==========================================================

    def detect_fork(self):

        board_after_best = self.board.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:
            return False

        piece = board_after_best.piece_at(
            self.best_move.to_square
        )

        if piece is None:
            return False

        if piece.piece_type == chess.KING:
            return False

        attacked = []

        for square, target in (
            board_after_best.piece_map().items()
        ):

            if target.color == piece.color:
                continue

            if target.piece_type == chess.KING:
                continue

            if square in board_after_best.attacks(
                self.best_move.to_square
            ):

                attacked.append(square)

        valuable_targets = [
            square
            for square in attacked
            if (
                board_after_best.piece_at(square)
                and PIECE_VALUES.get(
                    board_after_best.piece_at(
                        square
                    ).piece_type,
                    0
                ) >= 3
            )
        ]

        return len(valuable_targets) >= 2

    # ==========================================================
    # СВЯЗКА
    # ==========================================================

    def detect_pin(self):

        board_after_best = self.board.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:
            return None

        attacker_color = not board_after_best.turn

        for square, piece in (
            board_after_best.piece_map().items()
        ):

            if piece.color != attacker_color:
                continue

            if piece.piece_type not in (
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN
            ):
                continue

            directions = []

            if piece.piece_type in (
                chess.BISHOP,
                chess.QUEEN
            ):

                directions.extend([
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                    (-1, -1)
                ])

            if piece.piece_type in (
                chess.ROOK,
                chess.QUEEN
            ):

                directions.extend([
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1)
                ])

            start_file = chess.square_file(
                square
            )

            start_rank = chess.square_rank(
                square
            )

            for df, dr in directions:

                file = start_file + df
                rank = start_rank + dr

                first_square = None
                first_piece = None

                while (
                    0 <= file < 8
                    and 0 <= rank < 8
                ):

                    target_square = chess.square(
                        file,
                        rank
                    )

                    target_piece = (
                        board_after_best.piece_at(
                            target_square
                        )
                    )

                    if target_piece:

                        if first_piece is None:

                            if (
                                target_piece.color
                                == attacker_color
                            ):
                                break

                            first_piece = target_piece
                            first_square = target_square

                        else:

                            if (
                                target_piece.piece_type
                                == chess.KING
                            ):

                                return {
                                    "piece": PIECE_NAMES[
                                        first_piece.piece_type
                                    ],
                                    "square": (
                                        chess.square_name(
                                            first_square
                                        )
                                    )
                                }

                            if (
                                target_piece.color
                                != attacker_color
                            ):
                                break

                            if (
                                PIECE_VALUES.get(
                                    target_piece.piece_type,
                                    0
                                )
                                >
                                PIECE_VALUES.get(
                                    first_piece.piece_type,
                                    0
                                )
                            ):

                                return {
                                    "piece": PIECE_NAMES[
                                        first_piece.piece_type
                                    ],
                                    "square": (
                                        chess.square_name(
                                            first_square
                                        )
                                    )
                                }

                            break

                    file += df
                    rank += dr

        return None

    # ==========================================================
    # АТАКА ФИГУРЫ ПЕШКОЙ
    # ==========================================================

    def detect_pawn_attack(self):

        board_before = self.board.copy()

        board_after_played = board_before.copy()

        try:
            board_after_played.push(
                self.played_move
            )
        except ValueError:
            return None

        board_after_best = board_before.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:
            return None

        opponent_color = board_after_played.turn
        my_color = not opponent_color

        for square, piece in (
            board_after_played.piece_map().items()
        ):

            if piece.color != my_color:
                continue

            if piece.piece_type in (
                chess.KING,
                chess.PAWN
            ):
                continue

            attackers_after_played = (
                board_after_played.attackers(
                    opponent_color,
                    square
                )
            )

            pawn_attacker_square = None

            for attacker_square in (
                attackers_after_played
            ):

                attacker_piece = (
                    board_after_played.piece_at(
                        attacker_square
                    )
                )

                if attacker_piece is None:
                    continue

                if (
                    attacker_piece.color
                    == opponent_color
                    and attacker_piece.piece_type
                    == chess.PAWN
                ):

                    pawn_attacker_square = (
                        attacker_square
                    )

                    break

            if pawn_attacker_square is None:
                continue

            same_piece_square_after_best = None

            for (
                best_square,
                best_piece
            ) in board_after_best.piece_map().items():

                if best_piece.color != my_color:
                    continue

                if (
                    best_piece.piece_type
                    != piece.piece_type
                ):
                    continue

                same_piece_square_after_best = (
                    best_square
                )

                break

            if same_piece_square_after_best is None:
                continue

            attackers_after_best = (
                board_after_best.attackers(
                    opponent_color,
                    same_piece_square_after_best
                )
            )

            pawn_attacks_after_best = any(
                board_after_best.piece_at(
                    attacker_square
                )
                and
                board_after_best.piece_at(
                    attacker_square
                ).color == opponent_color
                and
                board_after_best.piece_at(
                    attacker_square
                ).piece_type == chess.PAWN
                for attacker_square in (
                    attackers_after_best
                )
            )

            if not pawn_attacks_after_best:

                return {
                    "piece": PIECE_NAMES.get(
                        piece.piece_type,
                        "фигура"
                    ),
                    "square": chess.square_name(
                        square
                    ),
                    "attacker_square": (
                        chess.square_name(
                            pawn_attacker_square
                        )
                    )
                }

        return None

    # ==========================================================
    # УГРОЗА ПЕШКОЙ НА СЛЕДУЮЩЕМ ХОДУ
    # ==========================================================

    # ==========================================================
    # ТЕМПОВАЯ АТАКА ПЕШКОЙ
    # ==========================================================

    def detect_pawn_tempo_attack(self):

        board_before = self.board.copy()

        # ------------------------------------------------------
        # 1. Проверяем сыгранный ход
        # ------------------------------------------------------

        played_piece = board_before.piece_at(
            self.played_move.from_square
        )

        if played_piece is None:
            return None

        if played_piece.piece_type not in (
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN
        ):
            return None

        # ------------------------------------------------------
        # 2. Позиция после сыгранного хода
        # ------------------------------------------------------

        board_after_played = board_before.copy()

        try:
            board_after_played.push(
                self.played_move
            )
        except ValueError:
            return None

        opponent_color = board_after_played.turn

        # Клетка, куда пришла наша фигура
        target_square = self.played_move.to_square

        target_piece = board_after_played.piece_at(
            target_square
        )

        if target_piece is None:
            return None

        if target_piece.color == opponent_color:
            return None

        # ------------------------------------------------------
        # 3. Ищем ХОД ПЕШКОЙ, который после своего хода
        #    начнёт атаковать нашу фигуру
        #
        # Пример:
        #
        # Bc4
        #
        # пешка d7 ещё НЕ атакует c4
        #
        # но ход d7-d5 создаёт атаку:
        #
        # d5 -> c4
        # ------------------------------------------------------

        pawn_move = None
        pawn_attacker_square = None

        for move in board_after_played.legal_moves:

            attacker = board_after_played.piece_at(
                move.from_square
            )

            if attacker is None:
                continue

            if attacker.color != opponent_color:
                continue

            if attacker.piece_type != chess.PAWN:
                continue

            # Создаём позицию после хода пешки
            board_after_pawn = board_after_played.copy()

            try:
                board_after_pawn.push(move)
            except ValueError:
                continue

            # Проверяем, атакует ли пешка после своего хода
            # нашу фигуру
            attackers_after_pawn = (
                board_after_pawn.attackers(
                    opponent_color,
                    target_square
                )
            )

            if move.to_square in attackers_after_pawn:
                pawn_move = move
                pawn_attacker_square = move.to_square
                break

        if pawn_move is None:
            print("NO PAWN TEMPO MOVE FOUND")
            return None

        print(
            "FOUND PAWN TEMPO MOVE:",
            board_after_played.san(pawn_move)
        )

        # ------------------------------------------------------
        # 4. Проверяем, не могла ли эта пешка атаковать
        #    нашу фигуру уже ДО нашего хода
        # ------------------------------------------------------

        attackers_before = board_before.attackers(
            opponent_color,
            target_square
        )

        for attacker_square in attackers_before:

            attacker_piece = board_before.piece_at(
                attacker_square
            )

            if (
                attacker_piece is not None
                and attacker_piece.color == opponent_color
                and attacker_piece.piece_type == chess.PAWN
            ):
                return None

        # ------------------------------------------------------
        # 5. Проверяем лучший ход
        # ------------------------------------------------------

        if self.best_move == self.played_move:
            return None

        board_after_best = board_before.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:
            return None

        # ------------------------------------------------------
        # 6. Проверяем, что лучший ход не подставляет
        #    эту же фигуру под темповый удар
        # ------------------------------------------------------

        best_target_square = None

        # Если лучший ход сделан той же фигурой,
        # она находится на поле назначения лучшего хода.
        if self.best_move.from_square == self.played_move.from_square:

            best_piece = board_after_best.piece_at(
                self.best_move.to_square
            )

            if (
                best_piece is not None
                and best_piece.color == played_piece.color
                and best_piece.piece_type == played_piece.piece_type
            ):
                best_target_square = self.best_move.to_square

        # Если лучший ход сделан ДРУГОЙ фигурой,
        # наша фигура остаётся на своей исходной клетке.
        else:

            best_piece = board_after_best.piece_at(
                self.played_move.from_square
            )

            if (
                best_piece is not None
                and best_piece.color == played_piece.color
                and best_piece.piece_type == played_piece.piece_type
            ):
                best_target_square = self.played_move.from_square

        if best_target_square is None:
            print("NO BEST TARGET SQUARE")
            return None

        print(
            "BEST TARGET SQUARE:",
            chess.square_name(best_target_square)
        )

        # ------------------------------------------------------
        # 8. Названия ходов
        # ------------------------------------------------------

        try:
            played_san = board_before.san(
                self.played_move
            )
        except Exception:
            played_san = chess.square_name(
                self.played_move.to_square
            )

        try:
            pawn_san = board_after_played.san(
                pawn_move
            )
        except Exception:
            pawn_san = (
                chess.square_name(
                    pawn_move.from_square
                )
                + "-"
                + chess.square_name(
                    pawn_move.to_square
                )
            )

        try:
            best_san = board_before.san(
                self.best_move
            )
        except Exception:
            best_san = chess.square_name(
                self.best_move.to_square
            )

        pawn_san = pawn_san.rstrip("+#")
        best_san = best_san.rstrip("+#")

        # ------------------------------------------------------
        # 9. Определяем фланг лучшего хода
        # ------------------------------------------------------

        best_file = chess.square_file(
            self.best_move.to_square
        )

        if best_file <= 2:
            flank = "ферзевом фланге"

        elif best_file >= 5:
            flank = "королевском фланге"

        else:
            flank = "в центре"

        # ------------------------------------------------------
        # 10. Формируем объяснение
        # ------------------------------------------------------

        piece_name = PIECE_NAMES.get(
            played_piece.piece_type,
            "фигуру"
        )

        explanation = (
            f"Ход {played_san} подставляет {piece_name} "
            f"под темповый удар ...{pawn_san}, "
            f"позволяя сопернику выиграть темп. "
            f"Сильнее было {best_san} с активной игрой "
            f"на {flank}."
        )

        return {
            "piece": piece_name,
            "square": chess.square_name(
                target_square
            ),
            "pawn_move": pawn_move,
            "explanation": explanation
        }

    def detect_pawn_threat(self):

        board_after_played = self.board.copy()

        try:
            board_after_played.push(
                self.played_move
            )
        except ValueError:
            return None

        opponent_color = board_after_played.turn
        my_color = not opponent_color

        for (
            pawn_square,
            pawn
        ) in board_after_played.piece_map().items():

            if pawn.color != opponent_color:
                continue

            if pawn.piece_type != chess.PAWN:
                continue

            for move in board_after_played.legal_moves:

                if move.from_square != pawn_square:
                    continue

                if (
                    board_after_played.piece_at(
                        move.from_square
                    ) is None
                ):
                    continue

                if (
                    board_after_played.piece_at(
                        move.from_square
                    ).piece_type
                    != chess.PAWN
                ):
                    continue

                test_board = (
                    board_after_played.copy()
                )

                test_board.push(move)

                for (
                    target_square,
                    target_piece
                ) in test_board.piece_map().items():

                    if target_piece.color != my_color:
                        continue

                    if target_piece.piece_type == chess.KING:
                        continue

                    attackers = test_board.attackers(
                        opponent_color,
                        target_square
                    )

                    for attacker_square in attackers:

                        attacker_piece = (
                            test_board.piece_at(
                                attacker_square
                            )
                        )

                        if attacker_piece is None:
                            continue

                        if (
                            attacker_piece.color
                            != opponent_color
                        ):
                            continue

                        if (
                            attacker_piece.piece_type
                            == chess.PAWN
                        ):

                            return {
                                "piece": PIECE_NAMES.get(
                                    target_piece.piece_type,
                                    "фигура"
                                ),
                                "square": (
                                    chess.square_name(
                                        target_square
                                    )
                                ),
                                "attacker_square": (
                                    chess.square_name(
                                        attacker_square
                                    )
                                ),
                                "pawn_move": move
                            }

        return None

    # ==========================================================
    # ПРОДВИЖЕНИЕ ПЕШКИ И АТАКА НА КОРОЛЯ
    # ==========================================================

    def detect_pawn_king_attack(self):

        # ==========================================
        # АНАЛИЗИРУЕМ СЫГРАННЫЙ ХОД
        # ==========================================

        played_pawn = self.board.piece_at(
            self.played_move.from_square
        )

        if played_pawn is None:
            return None

        # Сыгранный ход должен быть ходом пешки
        if played_pawn.piece_type != chess.PAWN:
            return None

        # ==========================================
        # Позиция ДО сыгранного хода
        # ==========================================

        board_before = self.board.copy()

        enemy_color = not played_pawn.color

        enemy_king = board_before.king(
            enemy_color
        )

        if enemy_king is None:
            return None

        # ==========================================
        # Давление на короля ДО хода
        # ==========================================

        pressure_before = self.king_area_pressure(
            board_before,
            enemy_king,
            played_pawn.color
        )

        # ==========================================
        # Позиция ПОСЛЕ сыгранного хода
        # ==========================================

        board_after = board_before.copy()

        try:
            board_after.push(
                self.played_move
            )
        except ValueError:
            return None

        # ==========================================
        # Давление на короля ПОСЛЕ хода
        # ==========================================

        pressure_after = self.king_area_pressure(
            board_after,
            enemy_king,
            played_pawn.color
        )

        pressure_gain = (
            pressure_after - pressure_before
        )

        print("========== ПРОВЕРКА АТАКИ ПЕШКОЙ ==========")
        print("PLAYED MOVE =", self.played_move)
        print("PAWN =", played_pawn)
        print(
            "ENEMY KING =",
            chess.square_name(enemy_king)
        )
        print(
            "PRESSURE BEFORE =",
            pressure_before
        )
        print(
            "PRESSURE AFTER =",
            pressure_after
        )
        print(
            "PRESSURE GAIN =",
            pressure_gain
        )
        print(
            "AFTER MOVE CHECK =",
            board_after.is_check()
        )

        # ==========================================
        # 1. Если ход пешки сразу даёт шах
        # ==========================================

        if board_after.is_check():

            return (
                "Продвижение этой пешки создаёт возможности "
                "для атаки на позицию короля."
            )

        # ==========================================
        # 2. Ищем шахи ДО сыгранного хода
        # ==========================================

        checks_before = set()

        for move in board_before.legal_moves:

            if board_before.gives_check(move):

                checks_before.add(
                    move.uci()
                )

        print(
            "ШАХИ ДО ХОДА =",
            checks_before
        )

        # ==========================================
        # 3. Ищем шахи ПОСЛЕ сыгранного хода
        # ==========================================

        checks_after = set()

        for move in board_after.legal_moves:

            if board_after.gives_check(move):

                checks_after.add(
                    move.uci()
                )

        print(
            "ШАХИ ПОСЛЕ ХОДА =",
            checks_after
        )

        # ==========================================
        # 4. Ищем НОВЫЕ шахи
        # ==========================================

        new_checks = (
            checks_after - checks_before
        )

        print(
            "НОВЫЕ ШАХИ ПОСЛЕ ХОДА =",
            new_checks
        )

        # ==========================================
        # 5. Если после продвижения пешки
        #    появились новые шахи —
        #    это атакующая идея
        # ==========================================

        if new_checks:

            return (
                "Продвижение этой пешки создаёт возможности "
                "для атаки на позицию короля."
            )

        return None


    def king_area_pressure(
        self,
        board,
        king_square,
        attacking_color
    ):

        king_file = chess.square_file(
            king_square
        )

        king_rank = chess.square_rank(
            king_square
        )

        pressure = 0

        for df in (-1, 0, 1):

            for dr in (-1, 0, 1):

                file = king_file + df
                rank = king_rank + dr

                if not (
                    0 <= file < 8
                    and 0 <= rank < 8
                ):
                    continue

                square = chess.square(
                    file,
                    rank
                )

                pressure += len(
                    board.attackers(
                        attacking_color,
                        square
                    )
                )

        return pressure

    # ==========================================================
    # ЖЕРТВА КОНЯ РАДИ АТАКИ
    # ==========================================================

    def detect_knight_sacrifice(self):

        print("========== ПРОВЕРКА ЖЕРТВЫ КОНЯ ==========")
        print("BEST MOVE =", self.best_move)

        # ==========================================
        # Лучшая фигура должна быть конём
        # ==========================================

        knight = self.board.piece_at(
            self.best_move.from_square
        )

        print("BEST PIECE =", knight)

        if knight is None:
            print("ЛУЧШАЯ ФИГУРА НЕ НАЙДЕНА")
            return None

        if knight.piece_type != chess.KNIGHT:
            print("ЛУЧШИЙ ХОД НЕ КОНЁМ")
            return None

        print("ЛУЧШИЙ ХОД ДЕЙСТВИТЕЛЬНО КОНЁМ")

        # ==========================================
        # Позиция после лучшего хода
        # ==========================================

        board_after_best = self.board.copy()

        try:
            board_after_best.push(self.best_move)
        except ValueError:
            return None

        knight_square = self.best_move.to_square

        print(
            "КОНЬ ПОСЛЕ ХОДА НА",
            chess.square_name(knight_square)
        )

        opponent_color = not knight.color

        # ==========================================
        # Может ли соперник сразу взять коня?
        # ==========================================

        knight_attacked = board_after_best.is_attacked_by(
            opponent_color,
            knight_square
        )

        print(
            "КОНЬ ПОД УДАРОМ =",
            knight_attacked
        )

        if not knight_attacked:
            print("КОНЬ НЕ МОЖЕТ БЫТЬ СРАЗУ ВЗЯТ")
            return None

        # ==========================================
        # Ищем конкретный ход соперника,
        # которым он может взять коня
        # ==========================================

        sacrifice_response = None

        for response in board_after_best.legal_moves:

            if response.to_square != knight_square:
                continue

            if not board_after_best.is_capture(response):
                continue

            captured = board_after_best.piece_at(
                knight_square
            )

            if captured is None:
                continue

            if captured.color != knight.color:
                continue

            if captured.piece_type != chess.KNIGHT:
                continue

            sacrifice_response = response
            break

        if sacrifice_response is None:

            print(
                "Ход взятия коня не найден"
            )

            return None

        print(
            "СОПЕРНИК МОЖЕТ ВЗЯТЬ КОНЯ:",
            sacrifice_response
        )

        # ==========================================
        # Проверяем, действительно ли это
        # добровольная жертва.
        #
        # Если конь просто висит после лучшего хода,
        # но сам ход не имеет смысла как жертва,
        # не выдаём сообщение.
        #
        # Главный критерий здесь:
        # лучший ход Stockfish значительно сильнее
        # сыгранного пользователем.
        # ==========================================

        played_board = self.board.copy()

        try:
            played_board.push(self.played_move)
        except ValueError:
            return None

        # ==========================================
        # Смотрим, не был ли конь уже под ударом
        # ДО лучшего хода.
        # ==========================================

        knight_before_attacked = self.board.is_attacked_by(
            opponent_color,
            self.best_move.from_square
        )

        print(
            "КОНЬ БЫЛ ПОД УДАРОМ ДО ЛУЧШЕГО ХОДА =",
            knight_before_attacked
        )

        # Если конь уже был под ударом и просто ушёл,
        # это не жертва.
        if knight_before_attacked:

            print(
                "КОНЬ УЖЕ БЫЛ ПОД УДАРОМ — ЭТО НЕ ЖЕРТВА"
            )

            return None

        # ==========================================
        # Проверяем: сыгранный ход отличается от
        # лучшего и лучший ход действительно
        # значительно сильнее.
        #
        # Значение LOSS уже вычисляется снаружи.
        # Поэтому здесь достаточно самого факта:
        # лучший ход Stockfish выбран вместо сыгранного.
        # ==========================================

        if self.played_move == self.best_move:

            print(
                "ЛУЧШИЙ ХОД УЖЕ БЫЛ СЫГРАН"
            )

            return None

        # ==========================================
        # Проверяем, есть ли реальная компенсация
        # после взятия коня.
        #
        # Сам факт, что коня можно взять, ещё НЕ
        # означает жертву.
        # ==========================================

        compensation_board = board_after_best.copy()

        try:
            compensation_board.push(
                sacrifice_response
            )
        except ValueError:
            return None

        # ==========================================
        # После взятия коня смотрим:
        #
        # 1. есть ли шах;
        # 2. можно ли сразу выиграть материал;
        # 3. есть ли тактический удар.
        #
        # Если ничего конкретного нет —
        # это обычная уязвимость фигуры, а не жертва.
        # ==========================================

        opponent_king = compensation_board.king(
            knight.color
        )

        if opponent_king is None:
            return None

        # ==========================================
        # Проверка шаха
        # ==========================================

        gives_check = compensation_board.is_check()

        print(
            "ПОСЛЕ ВЗЯТИЯ КОНЯ ШАХ =",
            gives_check
        )

        # ==========================================
        # Ищем возможность немедленно выиграть
        # материал следующим ходом.
        # ==========================================

        material_gain = False

        for reply in compensation_board.legal_moves:

            if not compensation_board.is_capture(reply):
                continue

            captured_piece = compensation_board.piece_at(
                reply.to_square
            )

            if captured_piece is None:
                continue

            # Если после жертвы можно забрать фигуру
            # соперника не меньшей ценности, считаем
            # это потенциальной компенсацией.
            if (
                captured_piece.color != knight.color
                and PIECE_VALUES.get(
                    captured_piece.piece_type,
                    0
                ) >= 3
            ):
                material_gain = True

                print(
                    "КОМПЕНСАЦИЯ: МОЖНО ВЫИГРАТЬ",
                    captured_piece,
                    "ХОДОМ",
                    reply
                )

                break

        print(
            "МАТЕРИАЛЬНАЯ КОМПЕНСАЦИЯ =",
            material_gain
        )

        # ==========================================
        # Если после взятия нет ни шаха, ни
        # конкретного выигрыша материала —
        # это НЕ подтверждённая жертва.
        # ==========================================

        if not gives_check and not material_gain:

            print(
                "НЕТ КОНКРЕТНОЙ КОМПЕНСАЦИИ — "
                "ЭТО НЕ ЖЕРТВА КОНЯ"
            )

            return None

        # ==========================================
        # Настоящая жертва подтверждена
        # ==========================================

        print(
            "!!! ЖЕРТВА КОНЯ ПОДТВЕРЖДЕНА !!!"
        )

        return (
            "Лучшим решением было пожертвовать "
            "коня ради тактической атаки."
        )

    # ==========================================================
    # ПОТЕРЯ ТЕМПА ХОДОМ КОРОЛЯ
    # ==========================================================

    def detect_wasted_king_tempo(self):

        print("========== ПРОВЕРКА ПОТЕРИ ТЕМПА ==========")

        played_piece = self.board.piece_at(
            self.played_move.from_square
        )

        best_piece = self.board.piece_at(
            self.best_move.from_square
        )

        if played_piece is None or best_piece is None:
            return None

        print("PLAYED PIECE =", PIECE_NAMES.get(
            played_piece.piece_type
        ))

        print("BEST PIECE =", PIECE_NAMES.get(
            best_piece.piece_type
        ))

        # ----------------------------------------------------------
        # Сыгранный ход должен быть ходом короля
        # ----------------------------------------------------------

        if played_piece.piece_type != chess.KING:
            print("СЫГРАННЫЙ ХОД НЕ КОРОЛЁМ")
            return None

        # ----------------------------------------------------------
        # Лучший ход не должен быть ходом короля
        # ----------------------------------------------------------

        if best_piece.piece_type == chess.KING:
            print("ЛУЧШИЙ ХОД ТОЖЕ КОРОЛЁМ")
            return None

        # ----------------------------------------------------------
        # Не рассматриваем случаи, где король реально спасался
        # от шаха
        # ----------------------------------------------------------

        if self.board.is_check():
            print("КОРОЛЬ БЫЛ ПОД ШАХОМ")
            return None

        # ----------------------------------------------------------
        # Проверяем, был ли сыгранный ход просто перемещением
        # короля без взятия
        # ----------------------------------------------------------

        if self.board.is_capture(self.played_move):
            print("КОРОЛЬ ЧТО-ТО ВЗЯЛ")
            return None

        # ----------------------------------------------------------
        # Лучший ход должен быть активным ходом другой фигуры.
        # Особенно интересны пешки, ферзь, ладья, слон, конь.
        # ----------------------------------------------------------

        if best_piece.piece_type not in (
            chess.PAWN,
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN
        ):
            print("ЛУЧШИЙ ХОД НЕАКТИВНОЙ ФИГУРОЙ")
            return None

        # ----------------------------------------------------------
        # Проверяем, что лучший ход действительно меняет позицию
        # ----------------------------------------------------------

        board_after_best = self.board.copy()

        try:
            board_after_best.push(self.best_move)
        except ValueError:
            return None

        # ----------------------------------------------------------
        # Считаем количество атакованных фигур соперника
        # ДО и ПОСЛЕ лучшего хода.
        #
        # Это не требование "activity gain > 0".
        # Нам достаточно увидеть, что лучший ход создаёт
        # конкретное изменение в позиции.
        # ----------------------------------------------------------

        enemy_color = not best_piece.color

        attacked_before = set()
        attacked_after = set()

        for square, piece in self.board.piece_map().items():

            if piece.color != enemy_color:
                continue

            if piece.piece_type == chess.KING:
                continue

            if self.board.is_attacked_by(
                best_piece.color,
                square
            ):
                attacked_before.add(square)

        for square, piece in board_after_best.piece_map().items():

            if piece.color != enemy_color:
                continue

            if piece.piece_type == chess.KING:
                continue

            if board_after_best.is_attacked_by(
                best_piece.color,
                square
            ):
                attacked_after.add(square)

        new_attacks = attacked_after - attacked_before

        print("НОВЫЕ АТАКИ ПОСЛЕ ЛУЧШЕГО ХОДА =", [
            chess.square_name(square)
            for square in new_attacks
        ])

        # ----------------------------------------------------------
        # Если лучший ход создаёт новые конкретные атаки,
        # считаем, что Kh2 был пассивной потерей темпа.
        # ----------------------------------------------------------

        if new_attacks:

            return (
                "Ход королём потратил темп «вхолостую». "
                "Позиция требовала активности, а лучший ход "
                "позволял создать давление и активизировать фигуры."
            )

        # ----------------------------------------------------------
        # Если лучший ход не создаёт немедленную атаку,
        # но является активным ходом другой фигуры,
        # всё равно считаем ход королём потерей темпа.
        # ----------------------------------------------------------

        if best_piece.piece_type in (
            chess.PAWN,
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN
        ):

            print("ЛУЧШИЙ ХОД АКТИВНОЙ ФИГУРОЙ — ПРОВЕРЯЕМ ПОТЕРЮ ТЕМПА")

            return (
                "Ход королём потратил темп «вхолостую». "
                "Позиция требовала активности на ферзевом фланге "
                "или в центре, чтобы создать встречные угрозы "
                "и не позволить сопернику перехватить инициативу."
            )

        return None

    def detect_bad_recapture(self):

        print("========== ПРОВЕРКА НЕВЫГОДНОГО ВЗЯТИЯ ==========")

        board_before = self.board.copy()

        # ------------------------------------------------------
        # 1. Наш ход должен быть взятием
        # ------------------------------------------------------

        if not board_before.is_capture(self.played_move):
            print("СЫГРАННЫЙ ХОД НЕ ЯВЛЯЕТСЯ ВЗЯТИЕМ")
            return None

        played_piece = board_before.piece_at(
            self.played_move.from_square
        )

        if played_piece is None:
            return None

        print(
            "СЫГРАННАЯ ФИГУРА =",
            PIECE_NAMES.get(played_piece.piece_type)
        )

        # ------------------------------------------------------
        # 2. Определяем, какую фигуру мы забрали
        # ------------------------------------------------------

        captured_piece = board_before.piece_at(
            self.played_move.to_square
        )

        if captured_piece is None:

            # Пока en passant отдельно не рассматриваем
            if board_before.is_en_passant(self.played_move):
                print("EN PASSANT — ПРОПУСКАЕМ")
                return None

            print("ВЗЯТАЯ ФИГУРА НЕ ОПРЕДЕЛЕНА")
            return None

        captured_value = PIECE_VALUES.get(
            captured_piece.piece_type,
            0
        )

        print(
            "ВЗЯТАЯ ФИГУРА =",
            PIECE_NAMES.get(captured_piece.piece_type)
        )

        print(
            "ЦЕННОСТЬ ВЗЯТОЙ ФИГУРЫ =",
            captured_value
        )

        # Пешка или мелкая фигура нас здесь не интересуют
        if captured_value < 3:
            print("ВЗЯТАЯ ФИГУРА СЛИШКОМ МАЛОЦЕННАЯ")
            return None

        # ------------------------------------------------------
        # 3. Позиция после нашего взятия
        # ------------------------------------------------------

        board_after = board_before.copy()

        try:
            board_after.push(self.played_move)
        except ValueError:
            return None

        # ------------------------------------------------------
        # 4. Смотрим шахи соперника после нашего хода
        # ------------------------------------------------------

        opponent_checks = []

        for move in board_after.legal_moves:

            try:
                san = board_after.san(move)
            except Exception:
                continue

            if san.endswith("+"):
                opponent_checks.append(move)

        print(
            "ШАХИ СОПЕРНИКА ПОСЛЕ ВЗЯТИЯ =",
            [
                board_after.san(move)
                for move in opponent_checks
            ]
        )

        # ------------------------------------------------------
        # 5. Если после нашего взятия есть шах,
        #    смотрим, насколько плохой стала позиция.
        #
        #    Это важно: сам факт шаха ещё НЕ означает ошибку.
        # ------------------------------------------------------

        if not opponent_checks:

            print("ПОСЛЕ ВЗЯТИЯ НЕТ ШАХА")
            return None

        # ------------------------------------------------------
        # Получаем оценку позиции после нашего хода.
        #
        # Если у тебя в TacticalAnalyzer уже есть before_score /
        # after_score, используем их.
        # ------------------------------------------------------

        before_score = getattr(
            self,
            "before_score",
            None
        )

        after_score = getattr(
            self,
            "after_score",
            None
        )

        print(
            "BEFORE SCORE =",
            before_score
        )

        print(
            "AFTER SCORE =",
            after_score
        )

        # ------------------------------------------------------
        # Если оценки доступны — проверяем ухудшение.
        # ------------------------------------------------------

        if (
            before_score is not None
            and after_score is not None
        ):

            try:

                score_loss = (
                    float(before_score)
                    - float(after_score)
                )

                print(
                    "ПОТЕРЯ ОТ НЕВЫГОДНОГО ВЗЯТИЯ =",
                    score_loss
                )

                # Если ухудшение маленькое —
                # не называем взятие ошибкой.
                if score_loss < 100:

                    print(
                        "ПОЗИЦИЯ УХУДШИЛАСЬ НЕСУЩЕСТВЕННО"
                    )

                    return None

            except Exception as e:

                print(
                    "ОШИБКА РАСЧЁТА ПОТЕРИ:",
                    e
                )

        # ------------------------------------------------------
        # 6. Наше взятие забрало ценную фигуру,
        #    но после этого соперник получает шах.
        #
        #    Это уже подходящий кандидат.
        # ------------------------------------------------------

        check_san = board_after.san(
            opponent_checks[0]
        )

        captured_name = PIECE_NAMES.get(
            captured_piece.piece_type,
            "фигуру"
        )

        print(
            "!!! НЕВЫГОДНОЕ ВЗЯТИЕ ПОДТВЕРЖДЕНО !!!"
        )

        print(
            "ВЗЯЛИ:",
            captured_name
        )

        print(
            "СОПЕРНИК ОТВЕЧАЕТ:",
            check_san
        )

        return (
            f"Вы забрали {captured_name}, "
            "но это взятие оказалось невыгодным. "
            "После размена соперник получил сильную инициативу "
            f"и смог продолжить с темпом ({check_san}). "
            "В этой позиции важнее было сохранить напряжение "
            "и выбрать более активный ход."
        )

    # ==========================================================
    # УПУЩЕНА БЕСПЛАТНАЯ ПЕШКА
    # ==========================================================

    def detect_free_pawn(self):

        board = self.board.copy()

        # Лучший ход должен быть взятием
        if not board.is_capture(self.best_move):
            return None

        # Определяем, что именно находится на поле взятия
        captured_piece = board.piece_at(
            self.best_move.to_square
        )

        # Если это не пешка — это не наша ситуация
        if captured_piece is None:

            # En passant пока отдельно не рассматриваем
            if board.is_en_passant(self.best_move):
                return None

            return None

        if captured_piece.piece_type != chess.PAWN:
            return None

        # Пешка соперника?
        if captured_piece.color == board.turn:
            return None

        print("========== БЕСПЛАТНАЯ ПЕШКА ==========")

        print(
            "BEST MOVE =",
            self.best_move
        )

        print(
            "BEST MOVE SAN =",
            board.san(self.best_move)
        )

        print(
            "ВЗЯТАЯ ФИГУРА =",
            PIECE_NAMES.get(
                captured_piece.piece_type
            )
        )

        print(
            "ПЕШКА НА:",
            chess.square_name(
                self.best_move.to_square
            )
        )

        # ------------------------------------------------------
        # Проверяем, что пользователь действительно сыграл
        # другой ход
        # ------------------------------------------------------

        if self.played_move == self.best_move:

            print(
                "ПЕШКА УЖЕ БЫЛА ВЗЯТА ЛУЧШИМ ХОДОМ"
            )

            return None

        # ------------------------------------------------------
        # Проверяем позицию после лучшего хода
        # ------------------------------------------------------

        board_after_best = board.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:

            return None

        # ------------------------------------------------------
        # Проверяем: не является ли это взятие ловушкой,
        # после которой наша фигура сразу теряется.
        # ------------------------------------------------------

        our_piece = board_after_best.piece_at(
            self.best_move.to_square
        )

        if our_piece is None:
            return None

        opponent_color = board_after_best.turn

        attackers = board_after_best.attackers(
            opponent_color,
            self.best_move.to_square
        )

        for attacker_square in attackers:

            attacker_piece = (
                board_after_best.piece_at(
                    attacker_square
                )
            )

            if attacker_piece is None:
                continue

            if attacker_piece.piece_type == chess.KING:
                continue

            # Если после взятия пешки нашу фигуру может
            # сразу забрать соперник — проверяем стоимость.
            attacker_value = PIECE_VALUES.get(
                attacker_piece.piece_type,
                0
            )

            our_value = PIECE_VALUES.get(
                our_piece.piece_type,
                0
            )

            if attacker_value > our_value:

                print(
                    "ВЗЯТИЕ ПЕШКИ МОЖЕТ БЫТЬ НЕВЫГОДНЫМ"
                )

                return None

        # ------------------------------------------------------
        # Всё совпало:
        #
        # лучший ход Stockfish = взятие пешки
        # пользователь сыграл другой ход
        #
        # ------------------------------------------------------

        print(
            "!!! УПУЩЕНА БЕСПЛАТНАЯ ПЕШКА !!!"
        )

        return (
            "Вы упустили шанс взять бесплатную пешку."
        )

    def detect_fork_targets(self, result):

        board_after_best = self.board.copy()

        try:
            board_after_best.push(
                self.best_move
            )
        except ValueError:
            return

        attacking_piece = (
            board_after_best.piece_at(
                self.best_move.to_square
            )
        )

        if attacking_piece is None:
            return

        for square, target in (
            board_after_best.piece_map().items()
        ):

            if target.color == attacking_piece.color:
                continue

            if target.piece_type == chess.KING:
                continue

            if board_after_best.is_attacked_by(
                attacking_piece.color,
                square
            ):

                result["fork_targets"].append({
                    "piece": PIECE_NAMES[
                        target.piece_type
                    ],
                    "square": chess.square_name(
                        square
                    )
                })

        result["fork_targets"].sort(
            key=lambda item: PIECE_PRIORITY.get(
                item["piece"],
                0
            ),
            reverse=True
        )

        result["fork_targets"] = (
            result["fork_targets"][:2]
        )

    # ==========================================================
    # НОВАЯ АТАКА НА ФИГУРУ
    # ==========================================================

    def detect_new_attack(self):

        board_after_played = self.board.copy()

        try:
            board_after_played.push(self.played_move)
        except ValueError:
            return None

        opponent_color = board_after_played.turn
        my_color = not opponent_color

        for square, piece in board_after_played.piece_map().items():

            # Ищем только наши фигуры
            if piece.color != my_color:
                continue

            # Короля не учитываем
            if piece.piece_type == chess.KING:
                continue

            # Нас интересуют только слоны
            if piece.piece_type != chess.BISHOP:
                continue

            # Если эта клетка была занята слоном и до хода
            # уже была атакована — это не новая атака
            piece_before = self.board.piece_at(square)

            if piece_before is None:
                continue

            if piece_before.color != my_color:
                continue

            if piece_before.piece_type != chess.BISHOP:
                continue

            attackers_before = self.board.attackers(
                opponent_color,
                square
            )

            if attackers_before:
                continue

            # Проверяем, появилась ли атака после нашего хода
            attackers_after = board_after_played.attackers(
                opponent_color,
                square
            )

            if not attackers_after:
                continue

            # Кто атакует слона?
            attacker_square = next(iter(attackers_after))

            attacker = board_after_played.piece_at(
                attacker_square
            )

            if attacker is None:
                continue

            return {
                "piece": "слон",
                "square": chess.square_name(square),
                "attacker": PIECE_NAMES.get(
                    attacker.piece_type,
                    "фигура"
                ),
                "attacker_square": chess.square_name(
                    attacker_square
                )
            }

        return None

    def detect_equal_exchange(self):

        board = self.board.copy()

        for square, piece in board.piece_map().items():

            if piece.color == board.turn:
                continue

            if piece.piece_type == chess.KING:
                continue

            attackers = board.attackers(
                board.turn,
                square
            )

            for attacker_square in attackers:

                attacker = board.piece_at(
                    attacker_square
                )

                if attacker is None:
                    continue

                attacker_value = PIECE_VALUES.get(
                    attacker.piece_type
                )

                target_value = PIECE_VALUES.get(
                    piece.piece_type
                )

                if (
                    attacker_value is None
                    or target_value is None
                ):
                    continue

                if attacker_value == target_value:

                    return {
                        "piece": PIECE_NAMES.get(
                            attacker.piece_type,
                            "фигуру"
                        ),
                        "square": (
                            chess.square_name(
                                attacker_square
                            )
                        ),
                        "target_piece": (
                            PIECE_NAMES.get(
                                piece.piece_type,
                                "фигуру"
                            )
                        ),
                        "target_square": (
                            chess.square_name(
                                square
                            )
                        )
                    }

        return None

    # ==========================================================
    # ОПРЕДЕЛЕНИЕ ТЕМЫ
    # ==========================================================

    def detect_theme(self, result):

        # =====================================
        # ЖЕРТВА КОНЯ РАДИ АТАКИ
        # =====================================

        if result.get("knight_sacrifice"):
            return "Жертва коня"

        # =====================================
        # ПОТЕРЯ ТЕМПА ХОДОМ КОРОЛЯ
        # =====================================

        if result.get("wasted_king_tempo"):
            return "Потеря темпа"

        # =====================================
        # ПРОДВИЖЕНИЕ ПЕШКИ И АТАКА КОРОЛЯ
        # =====================================

        if result.get("pawn_king_attack"):
            return "Атака на короля"

        # =====================================
        # УГРОЗА ПЕШКОЙ
        # =====================================

        if result.get("pawn_threat", False):
            return "Угроза пешкой"

        # =====================================
        # АТАКА ФИГУРЫ ПЕШКОЙ
        # =====================================

        if result.get("pawn_attack_piece") is not None:
            return "Атака фигуры пешкой"

        # =====================================
        # РАНЕЕ ОПРЕДЕЛЁННАЯ ТЕМА
        # =====================================

        if result["theme"] is not None:
            return result["theme"]

        # =====================================
        # РАВНОЦЕННЫЙ РАЗМЕН
        # =====================================

        exchange = self.detect_equal_exchange()

        if exchange is not None:

            best_move = result.get("best_move")

            if (
                best_move is not None
                and self.board.is_capture(best_move)
            ):

                result["best_piece"] = exchange["piece"]
                result["best_square"] = exchange["square"]

                result["target_piece"] = exchange["target_piece"]
                result["target_square"] = exchange["target_square"]

                return "Равноценный размен"

        # =====================================
        # ПОТЕРЯ ФИГУРЫ
        # =====================================

        if result["captured_piece"]:
            return "Потеря фигуры"

        # =====================================
        # ВИСЯЩАЯ ФИГУРА
        # =====================================

        if result["hanging_piece"]:
            return "Висящая фигура"

        # =====================================
        # ЗАЩИТА КОРОЛЯ
        # =====================================

        if (
            self.best_move
            and self.board.piece_at(self.best_move.from_square)
            and self.board.piece_at(
                self.best_move.from_square
            ).piece_type == chess.ROOK
            and chess.square_rank(self.best_move.to_square) == 0
        ):
            return "Защита короля"

        return "Не определено"