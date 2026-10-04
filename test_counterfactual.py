import json
import chess

from dataclasses import dataclass

from app.explanation_counterfactual import (
    build_explanation_context,
    get_played_pv,
    get_best_pv,
    compare_pv_consequences,
    find_material_consequence,
    find_exact_material_consequence,
    build_material_consequence_fact,
    find_direct_material_consequence,
    find_material_sequence_consequence,
    _analyze_material_sequence,
    _find_material_sequences,
    pv_first_move,
    find_causal_material_consequence,
    _find_first_opponent_material_sequence,
        check_material_sequence_causal_connection,
    _material_swing_for_our_side,
    _pv_move_to_board_move,
    check_direct_capture_of_played_piece,
    check_played_move_removed_defender,
    debug_played_move_removed_defender,
    get_causal_material_reason,
)

from app.explanation_engine import generate_explanation


import os

PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    PROJECT_ROOT,
    "data"
)


def load_mistake(filename):
    path = os.path.join(
        PROJECT_ROOT,
        filename
    )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    data["position_before"] = chess.Board(
        data["position_before"]
    )

    return data


def test_mistake_22_nc3_context():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    assert ctx is not None

    assert ctx.played_san == "Nc3"
    assert ctx.best_san == "Rhe1"

    assert ctx.played_move.uci() == "b5c3"
    assert ctx.best_move.uci() == "h1e1"

    assert (
        ctx.board_after_played.fen()
        == mistake["position_after"]
    )

    assert (
        len(ctx.played_results) > 0
    )

    assert (
        ctx.played_results[0]["pv"][0]
        == "g7h6"
    )

    assert (
        ctx.best_pv[0]
        == "h1e1"
    )


def test_mistake_15_bd3_context():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    assert ctx is not None

    assert ctx.played_san == "Bd3"
    assert ctx.best_san == "Bxa6"

    assert ctx.played_move.uci() == "f1d3"
    assert ctx.best_move.uci() == "f1a6"

    assert (
        ctx.board_after_played.fen()
        == mistake["position_after"]
    )

    assert (
        ctx.played_results[0]["pv"][0]
        == "g7c3"
    )

    assert (
        ctx.best_pv[0]
        == "f1a6"
    )

def test_mistake_22_nc3_pv():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    played_first, best_first = pv_first_move(ctx)

    assert played_first == "g7h6"
    assert best_first == "h1e1"


def test_mistake_15_bd3_pv():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    played_first, best_first = pv_first_move(ctx)

    assert played_first == "g7c3"
    assert best_first == "f1a6"

def test_mistake_15_bd3_pv_consequences():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = compare_pv_consequences(
        ctx
    )

    assert result is not None

    played_events = result["played"]["events"]

    assert len(played_events) > 0

    # В сыгранной линии должно быть
    # конкретное взятие материала.
    assert any(
        event["captured_value"] > 0
        for event in played_events
    )


def test_mistake_22_nc3_pv_consequences():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = compare_pv_consequences(
        ctx
    )

    assert result is not None

    played_events = result["played"]["events"]

    assert len(played_events) > 0

    assert any(
        event["captured_value"] > 0
        for event in played_events
    )

def test_mistake_15_bd3_material_consequence():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_material_consequence(
        ctx
    )

    assert result is not None

    assert result["found"] is True

    assert result["played_loss"] > 0

    assert result["additional_loss"] >= 1

    # В сыгранной линии должна быть
    # конкретная материальная потеря.
    assert len(
        result["played_events"]
    ) > 0


def test_mistake_22_nc3_material_consequence():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_material_consequence(
        ctx
    )

    assert result is not None

    assert result["found"] is True

    assert result["played_loss"] > 0

    assert result["additional_loss"] >= 1

    assert len(
        result["played_events"]
    ) > 0

def test_mistake_15_bd3_exact_material_consequence():
    mistake = load_mistake("mistake_15_Bd3.json")

    ctx = build_explanation_context(mistake)

    result = find_exact_material_consequence(ctx)

    assert result is not None
    assert result["found"] is True

    # В сыгранной линии должен быть конкретный
    # дополнительный материальный ущерб.
    assert result["additional_loss"] >= 1

    # Должно быть хотя бы одно конкретное
    # взятие нашего материала.
    assert len(result["causal_events"]) > 0

    # В этой позиции ожидаем потерю пешки/материала
    # через Qxc3.
    causal_sans = [
        event["san"]
        for event in result["causal_events"]
    ]

    assert any(
        "Qxc3" in san
        for san in causal_sans
    )


def test_mistake_22_nc3_exact_material_consequence():
    mistake = load_mistake("mistake_22_Nc3.json")

    ctx = build_explanation_context(mistake)

    result = find_exact_material_consequence(ctx)

    assert result is not None
    assert result["found"] is True

    assert result["additional_loss"] >= 1
    assert len(result["causal_events"]) > 0

    causal_sans = [
        event["san"]
        for event in result["causal_events"]
    ]

    # В этой линии должен присутствовать
    # конкретный захват материала соперником.
    assert any(
        san.startswith("Qxb2")
        for san in causal_sans
    ) or any(
        san.startswith("Qxh1")
        for san in causal_sans
    )

def test_mistake_15_bd3_material_consequence_fact():
    mistake = load_mistake("mistake_15_Bd3.json")

    ctx = build_explanation_context(mistake)

    result = find_exact_material_consequence(ctx)

    fact = build_material_consequence_fact(
        ctx,
        result,
    )

    assert fact is not None
    assert fact["type"] == "material_loss"

    assert fact["played_move"] == "Bd3"

    assert fact["sequence"]

    assert fact["additional_loss"] >= 1
    assert fact["causal_loss"] >= 1

    assert fact["first_capture"]["san"]

    # В этой ошибке конечным конкретным
    # материальным последствием является Qxc3.
    assert any(
        "Qxc3" in san
        for san in fact["sequence"]
    )


def test_mistake_22_nc3_material_consequence_fact():
    mistake = load_mistake("mistake_22_Nc3.json")

    ctx = build_explanation_context(mistake)

    result = find_exact_material_consequence(ctx)

    fact = build_material_consequence_fact(
        ctx,
        result,
    )

    assert fact is not None
    assert fact["type"] == "material_loss"

    assert fact["played_move"] == "Nc3"

    assert fact["sequence"]

    assert fact["additional_loss"] >= 1
    assert fact["causal_loss"] >= 1

    assert any(
        "Qxb2" in san
        or "Qxh1" in san
        for san in fact["sequence"]
    )

def test_material_fact_regression_report():
    filenames = [
        "mistake_5_f3.json",
        "mistake_8_Be3.json",
        "mistake_13_dxc6.json",
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_16_Nd5.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_22_Nc3.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:
        mistake = load_mistake(filename)
        ctx = build_explanation_context(mistake)

        result = find_exact_material_consequence(ctx)

        fact = build_material_consequence_fact(
            ctx,
            result,
        )

        print(
            "\n===",
            filename,
            "===",
        )

        if fact is None:
            print("MATERIAL FACT: NONE")
            continue

        print(
            "PLAYED:",
            fact["played_move"],
        )

        print(
            "SEQUENCE:",
            fact["sequence"],
        )

        print(
            "ADDITIONAL LOSS:",
            fact["additional_loss"],
        )

        print(
            "CAUSAL LOSS:",
            fact["causal_loss"],
        )

        print(
            "FIRST CAPTURE:",
            fact["first_capture"],
        )

def test_direct_material_consequence_regression_report():
    filenames = [
        "mistake_5_f3.json",
        "mistake_8_Be3.json",
        "mistake_13_dxc6.json",
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_16_Nd5.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_22_Nc3.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:

        mistake = load_mistake(filename)

        ctx = build_explanation_context(
            mistake
        )

        result = find_direct_material_consequence(
            ctx
        )

        print(
            "\n===",
            filename,
            "==="
        )

        if result is None:
            print(
                "DIRECT MATERIAL: NONE"
            )
            continue

        print(
            "DIRECT MATERIAL:",
            result["capture_san"]
        )

        print(
            "PIECE:",
            result["captured_piece_name"]
        )

        print(
            "SQUARE:",
            result["square"]
        )

        print(
            "VALUE:",
            result["captured_value"]
        )

def test_mistake_15_bd3_material_sequence():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_material_sequence_consequence(
        ctx
    )

    assert result is not None
    assert result["found"] is True

    assert result["swing"] < 0

    sequence = result["sequence"]

    assert "Bxc3" in sequence
    assert "Qxc3" in sequence


def test_mistake_22_nc3_material_sequence():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_material_sequence_consequence(
        ctx
    )

    assert result is not None
    assert result["found"] is True

    assert result["swing"] < 0

    sequence = result["sequence"]

    assert any(
        "Qxb2" in san
        or "Qxh1" in san
        for san in sequence
    )

def test_material_sequence_regression_report():

    filenames = [
        "mistake_5_f3.json",
        "mistake_8_Be3.json",
        "mistake_13_dxc6.json",
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_16_Nd5.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_22_Nc3.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:

        mistake = load_mistake(
            filename
        )

        ctx = build_explanation_context(
            mistake
        )

        result = (
            find_material_sequence_consequence(
                ctx
            )
        )

        print(
            "\n===",
            filename,
            "==="
        )

        if result is None:
            print(
                "MATERIAL SEQUENCE: NONE"
            )
            continue

        print(
            "MATERIAL SEQUENCE:",
            result["sequence"]
        )

        print(
            "SWING:",
            result["swing"]
        )

def test_debug_mistake_15_bd3_full_pv():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    print("\n")
    print("=" * 70)
    print("DEBUG 15.Bd3")
    print("=" * 70)

    print("\nPLAYED SAN:")
    print(ctx.played_san)

    print("\nBEST SAN:")
    print(ctx.best_san)

    print("\nPLAYED PV:")
    for i, move in enumerate(
        get_played_pv(ctx)
    ):
        print(i, move)

    print("\nBEST PV:")
    for i, move in enumerate(
        get_best_pv(ctx)
    ):
        print(i, move)

    print("\nMATERIAL EVENTS — PLAYED:")

    played_events = _analyze_material_sequence(
        ctx.board_after_played,
        get_played_pv(ctx),
        ctx.board_before.turn,
    )

    for event in played_events:
        print(
            event["ply"],
            event["san"],
            "swing=",
            event["swing"],
            "piece=",
            event["captured_piece_name"],
            "value=",
            event["captured_value"],
        )

    print("\nMATERIAL EVENTS — BEST:")

    best_events = _analyze_material_sequence(
        ctx.board_before,
        get_best_pv(ctx),
        ctx.board_before.turn,
    )

    for event in best_events:
        print(
            event["ply"],
            event["san"],
            "swing=",
            event["swing"],
            "piece=",
            event["captured_piece_name"],
            "value=",
            event["captured_value"],
        )

    print("\nMATERIAL SEQUENCES — PLAYED:")

    sequences = _find_material_sequences(
        ctx.board_after_played,
        get_played_pv(ctx),
        ctx.board_before.turn,
    )

    for sequence in sequences:
        print(
            "start=",
            sequence["start_ply"],
            "end=",
            sequence["end_ply"],
            "swing=",
            sequence["swing"],
            "sequence=",
            sequence["sequence"],
        )

    print("=" * 70)

def test_mistake_15_bd3_causal_material():
    mistake = load_mistake(
        "mistake_15_Bd3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_causal_material_consequence(
        ctx
    )

    assert result is not None
    assert result["found"] is True
    assert result["swing"] < 0

    sequence = result["sequence"]

    assert "Bxc3" in sequence
    assert "Qxc3" in sequence


def test_mistake_22_nc3_causal_material():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    result = find_causal_material_consequence(
        ctx
    )

    assert result is not None
    assert result["found"] is True
    assert result["swing"] < 0

    sequence = result["sequence"]

    assert any(
        "Qxb2" in san
        for san in sequence
    )

    assert any(
        "Qxh1" in san
        for san in sequence
    )

def test_causal_material_regression_report():

    filenames = [
        "mistake_5_f3.json",
        "mistake_8_Be3.json",
        "mistake_13_dxc6.json",
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_16_Nd5.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_22_Nc3.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:

        mistake = load_mistake(
            filename
        )

        ctx = build_explanation_context(
            mistake
        )

        result = (
            find_causal_material_consequence(
                ctx
            )
        )

        print(
            "\n===",
            filename,
            "==="
        )

        if result is None:
            print(
                "CAUSAL MATERIAL: NONE"
            )
            continue

        print(
            "CAUSAL MATERIAL:",
            result["sequence"]
        )

        print(
            "SWING:",
            result["swing"]
        )

        print(
            "RECOVERED:",
            result["recovered"]
        )

def test_debug_22_nc3_causal():
    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    print("\n")
    print("=" * 70)
    print("DEBUG CAUSAL 22.Nc3")
    print("=" * 70)

    print("PLAYED SAN:", ctx.played_san)
    print("BEST SAN:", ctx.best_san)

    print("\nPLAYED PV:")
    for i, move in enumerate(
        get_played_pv(ctx)
    ):
        print(i, move)

    print("\nBEST PV:")
    for i, move in enumerate(
        get_best_pv(ctx)
    ):
        print(i, move)

    print("\nMATERIAL EVENTS — PLAYED:")

    events_played = _analyze_material_sequence(
        ctx.board_after_played,
        get_played_pv(ctx),
        ctx.board_before.turn,
    )

    for event in events_played:
        print(
            event["ply"],
            event["san"],
            "swing=",
            event["swing"],
            "piece=",
            event["captured_piece_name"],
            "square=",
            event["square"]
            if "square" in event
            else "?",
        )

    print("\nMATERIAL EVENTS — BEST:")

    events_best = _analyze_material_sequence(
        ctx.board_before,
        get_best_pv(ctx),
        ctx.board_before.turn,
    )

    for event in events_best:
        print(
            event["ply"],
            event["san"],
            "swing=",
            event["swing"],
            "piece=",
            event["captured_piece_name"],
        )

    print("\nFIRST OPPONENT SEQUENCE:")

    sequence = (
        _find_first_opponent_material_sequence(
            ctx.board_after_played,
            get_played_pv(ctx),
            ctx.board_before.turn,
        )
    )

    print(
        repr(sequence)
    )

    print("\nFINAL DETECTOR:")

    result = find_causal_material_consequence(
        ctx
    )

    print(
        repr(result)
    )

    print("=" * 70)

    assert True

def test_material_swing_signs_22_nc3():

    mistake = load_mistake(
        "mistake_22_Nc3.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    our_color = ctx.board_before.turn

    played_pv = get_played_pv(ctx)

    events = _analyze_material_sequence(
        ctx.board_after_played,
        played_pv,
        our_color,
    )

    qxb2 = None
    rxc3 = None
    qxh1 = None

    for event in events:

        san = event["san"]

        if san.startswith("Qxb2"):
            qxb2 = event

        elif san.startswith("Rxc3"):
            rxc3 = event

        elif san.startswith("Qxh1"):
            qxh1 = event

    # --------------------------------------------------------
    # ...Qxb2+
    # Чёрные забирают белую пешку.
    # Для White: -1
    # --------------------------------------------------------

    assert qxb2 is not None
    assert qxb2["swing"] == -1

    # --------------------------------------------------------
    # ...Rxc3
    # Чёрные забирают белого коня.
    # Для White: -3
    # --------------------------------------------------------

    assert rxc3 is not None
    assert rxc3["swing"] == -3

    # --------------------------------------------------------
    # ...Qxh1
    # Чёрные забирают белую ладью.
    # Для White: -5
    # --------------------------------------------------------

    assert qxh1 is not None
    assert qxh1["swing"] == -5

    # --------------------------------------------------------
    # Общая потеря:
    #
    # -1 - 3 - 5 = -9
    # --------------------------------------------------------

    assert (
        qxb2["swing"]
        + rxc3["swing"]
        + qxh1["swing"]
        == -9
    )

def test_debug_all_causal_positions():
    filenames = [
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:
        mistake = load_mistake(filename)
        ctx = build_explanation_context(mistake)

        print("\n")
        print("=" * 70)
        print(filename)
        print("=" * 70)

        print("PLAYED:", ctx.played_san)
        print("BEST:", ctx.best_san)

        print("\nPLAYED PV:")
        for i, move in enumerate(get_played_pv(ctx)):
            print(i, move)

        print("\nBEST PV:")
        for i, move in enumerate(get_best_pv(ctx)):
            print(i, move)

        result = find_causal_material_consequence(ctx)

        print("\nCAUSAL RESULT:")
        print(result)

def test_causal_connection_regression_report():

    filenames = [
        "mistake_14_cxb7.json",
        "mistake_15_Bd3.json",
        "mistake_18_Ne2.json",
        "mistake_20_Nc3.json",
        "mistake_21_Nb5.json",
        "mistake_22_Nc3.json",
        "mistake_32_Kf3.json",
    ]

    for filename in filenames:

        print()
        print("=" * 60)
        print(filename)

        mistake = load_mistake(filename)

        ctx = build_explanation_context(
            mistake
        )

        consequence = (
            find_causal_material_consequence(
                ctx
            )
        )

        if consequence is None:

            print(
                "MATERIAL CONSEQUENCE: NONE"
            )

            continue

        connection = (
            check_material_sequence_causal_connection(
                ctx,
                consequence,
            )
        )

        print(
            "SEQUENCE:",
            consequence.get(
                "sequence"
            )
        )

        print(
            "CONNECTION:",
            connection
        )

def test_direct_capture_of_played_piece_regression():
    cases = [
        ("mistake_14_cxb7.json", False),
        ("mistake_15_Bd3.json", False),
        ("mistake_18_Ne2.json", False),
        ("mistake_20_Nc3.json", False),
        ("mistake_21_Nb5.json", True),
        ("mistake_22_Nc3.json", True),
        ("mistake_32_Kf3.json", False),
    ]

    print()
    print("========================================")
    print("DIRECT CAPTURE OF PLAYED PIECE")
    print("========================================")

    for filename, expected in cases:

        mistake = load_mistake(filename)

        ctx = build_explanation_context(
            mistake
        )

        consequence = find_causal_material_consequence(
            ctx
        )

        result = check_direct_capture_of_played_piece(
            ctx,
            consequence,
        )

        print(
            filename,
            "→",
            result,
            "EXPECTED:",
            expected,
        )

        assert result == expected

def test_played_move_removed_defender_regression():
    cases = [
        ("mistake_14_cxb7.json", False),
        ("mistake_15_Bd3.json", False),
        ("mistake_18_Ne2.json", False),
        ("mistake_20_Nc3.json", False),
        ("mistake_21_Nb5.json", True),
        ("mistake_22_Nc3.json", False),
        ("mistake_32_Kf3.json", True),
    ]

    print()
    print("========================================")
    print("PLAYED MOVE REMOVED DEFENDER")
    print("========================================")

    for filename, expected in cases:

        mistake = load_mistake(filename)

        ctx = build_explanation_context(
            mistake
        )

        consequence = find_causal_material_consequence(
            ctx
        )

        result = check_played_move_removed_defender(
            ctx,
            consequence,
        )

        print(
            filename,
            "→",
            result,
            "EXPECTED:",
            expected,
        )

        assert result == expected

def test_debug_21_nb5_removed_defender():

    mistake = load_mistake(
        "mistake_21_Nb5.json"
    )

    ctx = build_explanation_context(
        mistake
    )

    consequence = find_causal_material_consequence(
        ctx
    )

    debug_played_move_removed_defender(
        ctx,
        consequence,
    )

def test_debug_defender_cases():

    cases = [
        "mistake_15_Bd3.json",
        "mistake_18_Ne2.json",
        "mistake_32_Kf3.json",
    ]

    print()
    print("========================================")
    print("DEBUG DEFENDER CASES")
    print("========================================")

    for filename in cases:

        print()
        print("########", filename, "########")

        mistake = load_mistake(
            filename
        )

        ctx = build_explanation_context(
            mistake
        )

        consequence = find_causal_material_consequence(
            ctx
        )

        print(
            "PLAYED:",
            ctx.played_san
        )

        print(
            "BEST:",
            ctx.best_san
        )

        print(
            "SEQUENCE:",
            consequence.get("sequence")
            if consequence
            else None
        )

        debug_played_move_removed_defender(
            ctx,
            consequence,
        )

def test_causal_material_reason_regression():

    cases = [
        (
            "mistake_14_cxb7.json",
            None,
        ),
        (
            "mistake_15_Bd3.json",
            None,
        ),
        (
            "mistake_18_Ne2.json",
            None,
        ),
        (
            "mistake_20_Nc3.json",
            None,
        ),
        (
            "mistake_21_Nb5.json",
            "direct_capture_of_played_piece",
        ),
        (
            "mistake_22_Nc3.json",
            "direct_capture_of_played_piece",
        ),
        (
            "mistake_32_Kf3.json",
            "played_move_removed_defender",
        ),
    ]

    print()
    print("========================================")
    print("CAUSAL MATERIAL REASON")
    print("========================================")

    for filename, expected in cases:

        mistake = load_mistake(
            filename
        )

        ctx = build_explanation_context(
            mistake
        )

        consequence = find_causal_material_consequence(
            ctx
        )

        result = get_causal_material_reason(
            ctx,
            consequence,
        )

        result_type = (
            result.get("type")
            if result
            else None
        )

        print(
            filename,
            "→",
            result_type,
            "EXPECTED:",
            expected,
        )

        assert result_type == expected

def test_full_generate_explanation_regression():

    test_cases = [
        ("mistake_15_Bd3.json", "15.Bd3"),
        ("mistake_18_Ne2.json", "18.Ne2"),
        ("mistake_20_Nc3.json", "20.Nc3"),
        ("mistake_21_Nb5.json", "21.Nb5"),
        ("mistake_22_Nc3.json", "22.Nc3"),
        ("mistake_32_Kf3.json", "32.Kf3"),
    ]

    print()
    print("=" * 80)
    print("FULL GENERATE_EXPLANATION REGRESSION")
    print("=" * 80)

    for filename, label in test_cases:

        mistake = load_mistake(filename)

        explanation = generate_explanation(
            mistake
        )

        print()
        print("-" * 80)
        print(label)
        print("-" * 80)
        print(explanation)

        assert explanation