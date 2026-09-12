/* ============================================================
TELEGRAM MINI APP
============================================================ */

const tg = window.Telegram?.WebApp;

if (tg) {

    tg.ready();

    if (tg.expand) {
        tg.expand();
    }

}



console.log("========== TELEGRAM WEBAPP DEBUG ==========");
console.log("Telegram =", window.Telegram);
console.log("tg =", tg);
console.log("tg.initData =", tg?.initData);
console.log("tg.initDataUnsafe =", tg?.initDataUnsafe);
console.log("tg.initDataUnsafe.user =", tg?.initDataUnsafe?.user);
console.log("============================================");


/* ============================================================
ЭКРАНЫ
============================================================ */

const menuScreen =
    document.getElementById("menuScreen");

const gameScreen =
    document.getElementById("gameScreen");

const analysisScreen =
    document.getElementById("analysisScreen");

const mistakesScreen =
    document.getElementById("mistakesScreen");


/* ============================================================
КНОПКИ МЕНЮ
============================================================ */

const playButton =
    document.getElementById("playButton");

const analysisButton =
    document.getElementById("analysisButton");

const mistakesButton =
    document.getElementById("mistakesButton");

const backFromGameButton =
    document.getElementById("backFromGameButton");

const backFromAnalysisButton =
    document.getElementById(
        "backFromAnalysisButton"
    );

const backFromMistakesButton =
    document.getElementById(
        "backFromMistakesButton"
    );


/* ============================================================
ИГРА — ЭЛЕМЕНТЫ
============================================================ */

const boardElement =
    document.getElementById("board");

const messageElement =
    document.getElementById("message");

const turnElement =
    document.getElementById("turnText");

const hintButton =
    document.getElementById("hintButton");

const newGameButton =
    document.getElementById("newGameButton");


/* ============================================================
АНАЛИЗ — ЭЛЕМЕНТЫ
============================================================ */

const pgnInput =
    document.getElementById("pgnInput");

const analyzeButton =
    document.getElementById("analyzeButton");

const analysisMessage =
    document.getElementById(
        "analysisMessage"
    );

const analysisResult =
    document.getElementById(
        "analysisResult"
    );


/* ============================================================
СОСТОЯНИЕ ИГРЫ
============================================================ */

let board = [];

let selectedSquare = null;

let lastMove = null;

let playerColor = "white";

let playerTurn = true;

let gameOver = false;


/* ============================================================
ДАННЫЕ ПОСЛЕДНЕГО АНАЛИЗА
============================================================ */

let currentAnalysisData = null;


/* ============================================================
ЭКРАН ПОЗИЦИИ ОШИБКИ
============================================================ */

let positionScreen = null;


/* ============================================================
КООРДИНАТЫ
============================================================ */

const FILES = [
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h"
];


/* ============================================================
FEN → ДОСКА
============================================================ */

function fenToBoard(fen) {

    const position =
        fen.split(" ")[0];

    const rows =
        position.split("/");

    const result = [];


    for (
        let row = 0;
        row < 8;
        row++
    ) {

        const resultRow = [];


        for (
            const char of rows[row]
        ) {

            if (!isNaN(char)) {

                const emptyCount =
                    parseInt(char);


                for (
                    let i = 0;
                    i < emptyCount;
                    i++
                ) {

                    resultRow.push(null);

                }

            } else {

                let color;


                if (
                    char ===
                    char.toUpperCase()
                ) {

                    color = "white";

                } else {

                    color = "black";

                }


                const lower =
                    char.toLowerCase();

                let type = null;


                if (lower === "k") {
                    type = "king";
                }

                if (lower === "q") {
                    type = "queen";
                }

                if (lower === "r") {
                    type = "rook";
                }

                if (lower === "b") {
                    type = "bishop";
                }

                if (lower === "n") {
                    type = "knight";
                }

                if (lower === "p") {
                    type = "pawn";
                }


                resultRow.push({
                    type: type,
                    color: color
                });

            }

        }


        result.push(resultRow);

    }


    return result;

}


/* ============================================================
ПОЛУЧИТЬ ФИГУРУ
============================================================ */

function getPiece(squareName) {

    const file =
        FILES.indexOf(
            squareName[0]
        );


    const rank =
        8 - parseInt(
            squareName[1]
        );


    if (
        file < 0 ||
        rank < 0 ||
        rank > 7
    ) {

        return null;

    }


    return board[rank][file];

}


/* ============================================================
ОТРИСОВКА ОСНОВНОЙ ДОСКИ
============================================================ */

function renderBoard() {

    boardElement.innerHTML = "";


    for (
        let row = 0;
        row < 8;
        row++
    ) {

        for (
            let col = 0;
            col < 8;
            col++
        ) {

            const square =
                document.createElement(
                    "button"
                );


            square.classList.add(
                "square"
            );


            /* Цвет клетки */

            if (
                (row + col) % 2 === 0
            ) {

                square.classList.add(
                    "light"
                );

            } else {

                square.classList.add(
                    "dark"
                );

            }


            /* Координата */

            const squareName =
                FILES[col] +
                (8 - row);


            square.dataset.square =
                squareName;


            /* Последний ход */

            if (
                lastMove &&
                (
                    lastMove.from ===
                    squareName ||
                    lastMove.to ===
                    squareName
                )
            ) {

                square.classList.add(
                    "last-move"
                );

            }


            /* Выбранная клетка */

            if (
                selectedSquare ===
                squareName
            ) {

                square.classList.add(
                    "selected"
                );

            }


            /* Фигура */

            const piece =
                board[row][col];


            if (piece) {

                const pieceElement =
                    document.createElement(
                        "img"
                    );


                pieceElement.classList.add(
                    "piece-image"
                );


                pieceElement.src =
                    `pieces/${piece.color}/${piece.type.charAt(0).toUpperCase() + piece.type.slice(1)}.svg?v=2`;


                pieceElement.alt =
                    `${piece.color} ${piece.type}`;


                pieceElement.draggable =
                    false;


                square.appendChild(
                    pieceElement
                );

            }


            /* Нажатие */

            square.addEventListener(
                "click",
                () =>
                    handleSquareClick(
                        squareName
                    )
            );


            boardElement.appendChild(
                square
            );

        }

    }

}


/* ============================================================
НАЖАТИЕ НА КЛЕТКУ
============================================================ */

function handleSquareClick(squareName) {

    if (gameOver) {

        setMessage(
            "Партия уже закончена."
        );

        return;

    }


    if (!playerTurn) {

        setMessage(
            "Сейчас ход компьютера."
        );

        return;

    }


    const piece =
        getPiece(squareName);


    /* Фигура ещё не выбрана */

    if (selectedSquare === null) {

        if (!piece) {

            setMessage(
                "Здесь нет фигуры."
            );

            return;

        }


        if (
            piece.color !==
            playerColor
        ) {

            setMessage(
                "Это фигура компьютера."
            );

            return;

        }


        selectedSquare =
            squareName;


        setMessage(
            `Выбрана ${squareName}. Выберите клетку назначения.`
        );


        renderBoard();

        return;

    }


    /* Нажали ту же клетку */

    if (
        selectedSquare ===
        squareName
    ) {

        selectedSquare = null;


        setMessage(
            "Выбор отменён."
        );


        renderBoard();

        return;

    }


    /* Другая своя фигура */

    if (
        piece &&
        piece.color ===
        playerColor
    ) {

        selectedSquare =
            squareName;


        setMessage(
            `Выбрана ${squareName}.`
        );


        renderBoard();

        return;

    }


    /* Отправляем ход */

    const from =
        selectedSquare;

    const to =
        squareName;


    const uciMove =
        from + to;


    console.log(
        "Отправляем ход:",
        uciMove
    );


    selectedSquare = null;


    makeMove(uciMove);

}


/* ============================================================
ОТПРАВКА ХОДА
============================================================ */

async function makeMove(uciMove) {

    setMessage(
        "Проверяем ход..."
    );


    try {

        const response =
            await fetch(
                "/move",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        move: uciMove
                    })
                }
            );


        const data =
            await response.json();


        console.log(
            "Ответ Python:",
            data
        );


        if (
            !response.ok ||
            !data.success
        ) {

            setMessage(
                data.error ||
                "Недопустимый ход."
            );


            renderBoard();

            return;

        }


        board =
            fenToBoard(
                data.fen
            );


        lastMove = {

            from:
                data.played_move
                    .substring(0, 2),

            to:
                data.played_move
                    .substring(2, 4)

        };


        playerTurn =
            data.player_turn;

        gameOver =
            data.game_over;


        renderBoard();


        if (data.is_best) {

            setMessage(
                `Отлично! ${data.played_san} — лучший ход.`
            );

        } else {

            setMessage(
                `Вы сыграли ${data.played_san}. Лучший ход: ${data.best_san}`
            );

        }


        updateTurnText();


        if (gameOver) {

            setMessage(
                `Партия закончена: ${data.status}`
            );

        }


    } catch (error) {

        console.error(
            "Ошибка:",
            error
        );


        setMessage(
            "Ошибка соединения с сервером."
        );

    }

}


/* ============================================================
ПОЛУЧИТЬ ТЕКУЩУЮ ИГРУ
============================================================ */

async function loadGame() {

    try {

        const response =
            await fetch("/game");


        const data =
            await response.json();


        console.log(
            "Начальная позиция:",
            data
        );


        board =
            fenToBoard(
                data.fen
            );


        playerTurn =
            data.player_turn;

        gameOver =
            data.game_over;


        renderBoard();

        updateTurnText();


        setMessage(
            "Выберите фигуру"
        );


    } catch (error) {

        console.error(
            "Ошибка загрузки игры:",
            error
        );


        setMessage(
            "Не удалось загрузить игру."
        );

    }

}


/* ============================================================
ТЕКСТ ХОДА
============================================================ */

function updateTurnText() {

    if (gameOver) {

        turnElement.textContent =
            "Партия закончена";

        return;

    }


    if (playerTurn) {

        turnElement.textContent =
            "Ваш ход";

    } else {

        turnElement.textContent =
            "🤖 Ход компьютера";

    }

}


/* ============================================================
СООБЩЕНИЕ
============================================================ */

function setMessage(text) {

    messageElement.textContent =
        text;

}


/* ============================================================
ПОДСКАЗКА
============================================================ */

hintButton.addEventListener(
    "click",
    async () => {

        setMessage(
            "Получаем лучший ход..."
        );


        try {

            const response =
                await fetch("/game");


            const data =
                await response.json();


            if (
                data.legal_moves &&
                data.legal_moves.length > 0
            ) {

                setMessage(
                    "Подсказка: позже здесь покажем лучший ход Stockfish."
                );

            }


        } catch (error) {

            console.error(error);


            setMessage(
                "Ошибка получения подсказки."
            );

        }

    }
);


/* ============================================================
НОВАЯ ИГРА
============================================================ */

newGameButton.addEventListener(
    "click",
    async () => {

        try {

            const response =
                await fetch(
                    "/reset",
                    {
                        method: "POST"
                    }
                );


            const data =
                await response.json();


            board =
                fenToBoard(
                    data.fen
                );


            selectedSquare = null;

            lastMove = null;


            playerTurn =
                data.player_turn;

            gameOver =
                data.game_over;


            renderBoard();

            updateTurnText();


            setMessage(
                "Новая партия. Ваш ход."
            );


        } catch (error) {

            console.error(
                error
            );


            setMessage(
                "Не удалось начать новую игру."
            );

        }

    }
);


/* ============================================================
   ЭКРАН ПОЗИЦИИ ОШИБКИ
============================================================ */

let positionBoardState = null;

let positionSelectedSquare = null;

let positionOrientation = "white";

let positionBestMoveShown = false;

let positionUserMove = null;

let positionCastlingRights = "-";


/* ============================================================
   СОЗДАНИЕ ЭКРАНА ПОЗИЦИИ
============================================================ */

function createPositionScreen() {

    if (positionScreen) {
        return;
    }


    positionScreen =
        document.createElement(
            "section"
        );


    positionScreen.id =
        "positionScreen";


    positionScreen.className =
        "screen position-screen hidden";


    positionScreen.innerHTML = `

        <header class="position-header">

            <button
                id="backFromPositionButton"
                class="back-button"
            >
                ← Назад к ошибкам
            </button>

            <h2>
                Позиция ошибки
            </h2>

        </header>


        <div
            id="positionInfo"
            class="position-info"
        ></div>


        <div
            id="positionResult"
            class="position-result neutral"
        ></div>


        <div class="position-coordinates">

            <div class="position-board-container">

                <div
                    id="positionRanks"
                    class="position-ranks"
                ></div>

                <div
                    id="positionBoard"
                    class="position-board"
                ></div>

            </div>

            <div
                id="positionFiles"
                class="position-files"
            ></div>

        </div>


        <div
            id="bestMoveInfo"
            class="position-result neutral"
        ></div>


        <button
            id="bestMoveButton"
            class="button"
        >
            💡 Показать лучший ход
        </button>


        <div class="position-navigation">

            <button
                id="previousPositionButton"
                class="button secondary"
            >
                ← Предыдущая
            </button>

            <button
                id="nextPositionButton"
                class="button secondary"
            >
                Следующая →
            </button>

        </div>

    `;


    document
        .querySelector(".app")
        .appendChild(
            positionScreen
        );


    /* ========================================================
       НАЗАД
    ======================================================== */

    document
        .getElementById(
            "backFromPositionButton"
        )
        .onclick = () => {

            positionScreen.classList.add(
                "hidden"
            );

            analysisScreen.classList.remove(
                "hidden"
            );

        };


    /* ========================================================
       ЛУЧШИЙ ХОД
    ======================================================== */

    document
        .getElementById(
            "bestMoveButton"
        )
        .onclick = () => {

            showBestMove(
                positionScreen.currentMistake
            );

        };


    /* ========================================================
       ПРЕДЫДУЩАЯ ПОЗИЦИЯ
    ======================================================== */

    document
        .getElementById(
            "previousPositionButton"
        )
        .onclick = () => {

            navigateMistake(-1);

        };


    /* ========================================================
       СЛЕДУЮЩАЯ ПОЗИЦИЯ
    ======================================================== */

    document
        .getElementById(
            "nextPositionButton"
        )
        .onclick = () => {

            navigateMistake(1);

        };

}


/* ============================================================
   НАВИГАЦИЯ ПО ОШИБКАМ
============================================================ */

function navigateMistake(direction) {

    if (
        !currentAnalysisData ||
        !currentAnalysisData.mistakes ||
        !positionScreen.currentMistake
    ) {
        return;
    }


    const mistakes =
        currentAnalysisData.mistakes;


    const currentIndex =
        mistakes.indexOf(
            positionScreen.currentMistake
        );


    if (currentIndex === -1) {
        return;
    }


    const newIndex =
        currentIndex + direction;


    if (
        newIndex < 0 ||
        newIndex >= mistakes.length
    ) {
        return;
    }


    showMistakePosition(
        mistakes[newIndex]
    );

}


/* ============================================================
   ПОЛУЧИТЬ СТОРОНУ ИГРОКА
============================================================ */

function getMistakeSide(mistake) {

    const side =
        String(
            mistake.user_side ??
            mistake.side ??
            mistake.player_color ??
            mistake.color ??
            ""
        ).toLowerCase();


    if (
        side === "black" ||
        side === "b" ||
        side === "черные" ||
        side === "чёрные"
    ) {

        return "black";

    }


    return "white";

}


/* ============================================================
   ПРЕОБРАЗОВАНИЕ КООРДИНАТ
============================================================ */

function getPositionSquareName(
    row,
    col
) {

    if (
        positionOrientation === "white"
    ) {

        return (
            FILES[col] +
            (8 - row)
        );

    }


    return (
        FILES[7 - col] +
        (row + 1)
    );

}


/* ============================================================
   ПОЗИЦИЯ → КЛОН
============================================================ */

function clonePositionBoard(
    source
) {

    return source.map(
        row =>
            row.map(
                piece =>
                    piece
                        ? {
                            type: piece.type,
                            color: piece.color
                        }
                        : null
            )
    );

}


/* ============================================================
   ПОЛУЧИТЬ ФИГУРУ В ПОЗИЦИИ
============================================================ */

function getPositionPiece(
    squareName
) {

    const file =
        FILES.indexOf(
            squareName[0]
        );


    const rank =
        parseInt(
            squareName[1]
        );


    if (
        file < 0 ||
        rank < 1 ||
        rank > 8
    ) {

        return null;

    }


    const row =
        8 - rank;


    return positionBoardState[row][file];

}


/* ============================================================
   УСТАНОВИТЬ ФИГУРУ
============================================================ */

function setPositionPiece(
    squareName,
    piece
) {

    const file =
        FILES.indexOf(
            squareName[0]
        );


    const rank =
        parseInt(
            squareName[1]
        );


    if (
        file < 0 ||
        rank < 1 ||
        rank > 8
    ) {

        return;

    }


    positionBoardState[8 - rank][file] =
        piece;

}


/* ============================================================
   КООРДИНАТЫ → ЧИСЛО
============================================================ */

function squareToCoords(
    squareName
) {

    return {

        file:
            FILES.indexOf(
                squareName[0]
            ),

        rank:
            parseInt(
                squareName[1]
            ) - 1

    };

}


/* ============================================================
   ПРОВЕРКА ПУТИ ФИГУРЫ
============================================================ */

function isPathClear(
    from,
    to
) {

    const a =
        squareToCoords(from);

    const b =
        squareToCoords(to);


    const df =
        Math.sign(
            b.file - a.file
        );

    const dr =
        Math.sign(
            b.rank - a.rank
        );


    let file =
        a.file + df;

    let rank =
        a.rank + dr;


    while (
        file !== b.file ||
        rank !== b.rank
    ) {

        const square =
            FILES[file] +
            (rank + 1);


        if (
            getPositionPiece(square)
        ) {

            return false;

        }


        file += df;
        rank += dr;

    }


    return true;

}


/* ============================================================
   ПРОВЕРКА АТАКИ ПОЛЯ
============================================================ */

function isSquareAttackedByColor(
    squareName,
    attackerColor
) {

    const target =
        squareToCoords(
            squareName
        );


    const targetFile =
        target.file;

    const targetRank =
        target.rank;


    if (
        targetFile < 0 ||
        targetRank < 0
    ) {

        return false;

    }


    for (
        let rank = 1;
        rank <= 8;
        rank++
    ) {

        for (
            let fileIndex = 0;
            fileIndex < 8;
            fileIndex++
        ) {

            const fromSquare =
                FILES[fileIndex] +
                rank;


            const piece =
                getPositionPiece(
                    fromSquare
                );


            if (
                !piece ||
                piece.color !==
                attackerColor
            ) {

                continue;

            }


            const from =
                squareToCoords(
                    fromSquare
                );


            const dx =
                targetFile -
                from.file;


            const dy =
                targetRank -
                from.rank;


            const absFile =
                Math.abs(dx);


            const absRank =
                Math.abs(dy);


            /* ПЕШКА */

            if (
                piece.type === "pawn"
            ) {

                const direction =
                    attackerColor === "white"
                        ? 1
                        : -1;


                if (
                    absFile === 1 &&
                    dy === direction
                ) {

                    return true;

                }


                continue;

            }


            /* КОНЬ */

            if (
                piece.type === "knight"
            ) {

                if (
                    (
                        absFile === 1 &&
                        absRank === 2
                    ) ||
                    (
                        absFile === 2 &&
                        absRank === 1
                    )
                ) {

                    return true;

                }


                continue;

            }


            /* КОРОЛЬ */

            if (
                piece.type === "king"
            ) {

                if (
                    absFile <= 1 &&
                    absRank <= 1 &&
                    (
                        absFile > 0 ||
                        absRank > 0
                    )
                ) {

                    return true;

                }


                continue;

            }


            /* ЛАДЬЯ / ФЕРЗЬ */

            if (
                piece.type === "rook" ||
                piece.type === "queen"
            ) {

                if (
                    dx !== 0 &&
                    dy !== 0
                ) {

                    continue;

                }


                if (
                    isPathClear(
                        fromSquare,
                        squareName
                    )
                ) {

                    return true;

                }


                continue;

            }


            /* СЛОН / ФЕРЗЬ */

            if (
                piece.type === "bishop" ||
                piece.type === "queen"
            ) {

                if (
                    absFile !== absRank
                ) {

                    continue;

                }


                if (
                    absFile === 0
                ) {

                    continue;

                }


                if (
                    isPathClear(
                        fromSquare,
                        squareName
                    )
                ) {

                    return true;

                }

            }

        }

    }


    return false;

}


/* ============================================================
   ПРОВЕРКА ХОДА
============================================================ */

function isPositionMoveLegal(
    from,
    to
) {

    const piece =
        getPositionPiece(from);


    if (!piece) {
        return false;
    }


    const targetPiece =
        getPositionPiece(to);


    /* Нельзя брать свою фигуру */

    if (
        targetPiece &&
        targetPiece.color ===
        piece.color
    ) {

        return false;

    }


    const fromCoords =
        squareToCoords(from);


    const toCoords =
        squareToCoords(to);


    const dx =
        toCoords.file -
        fromCoords.file;


    const dy =
        toCoords.rank -
        fromCoords.rank;


    const absFile =
        Math.abs(dx);


    const absRank =
        Math.abs(dy);


    /* ПЕШКА */

    if (
        piece.type === "pawn"
    ) {

        const direction =
            piece.color === "white"
                ? 1
                : -1;


        const startRank =
            piece.color === "white"
                ? 1
                : 6;


        /* Обычный ход */

        if (
            dx === 0 &&
            dy === direction &&
            !targetPiece
        ) {

            return true;

        }


        /* Двойной ход */

        if (
            dx === 0 &&
            dy === direction * 2 &&
            fromCoords.rank === startRank &&
            !targetPiece
        ) {

            const middleSquare =
                FILES[fromCoords.file] +
                (
                    fromCoords.rank +
                    direction +
                    1
                );


            if (
                !getPositionPiece(
                    middleSquare
                )
            ) {

                return true;

            }

        }


        /* Взятие */

        if (
            absFile === 1 &&
            dy === direction &&
            targetPiece &&
            targetPiece.color !==
            piece.color
        ) {

            return true;

        }


        return false;

    }


    /* КОНЬ */

    if (
        piece.type === "knight"
    ) {

        return (
            (
                absFile === 1 &&
                absRank === 2
            ) ||
            (
                absFile === 2 &&
                absRank === 1
            )
        );

    }


    /* СЛОН */

    if (
        piece.type === "bishop"
    ) {

        return (
            absFile === absRank &&
            absFile > 0 &&
            isPathClear(
                from,
                to
            )
        );

    }


    /* ЛАДЬЯ */

    if (
        piece.type === "rook"
    ) {

        return (
            (
                dx === 0 ||
                dy === 0
            ) &&
            (
                dx !== 0 ||
                dy !== 0
            ) &&
            isPathClear(
                from,
                to
            )
        );

    }


    /* ФЕРЗЬ */

    if (
        piece.type === "queen"
    ) {

        const straight =
            dx === 0 ||
            dy === 0;


        const diagonal =
            absFile === absRank;


        return (
            (
                straight ||
                diagonal
            ) &&
            (
                dx !== 0 ||
                dy !== 0
            ) &&
            isPathClear(
                from,
                to
            )
        );

    }


    /* КОРОЛЬ */

    if (
        piece.type === "king"
    ) {

        /* Обычный ход */

        if (
            absFile <= 1 &&
            absRank <= 1 &&
            (
                absFile > 0 ||
                absRank > 0
            )
        ) {

            return true;

        }


        /* РОКИРОВКА */

        if (
            absFile !== 2 ||
            absRank !== 0
        ) {

            return false;

        }


        const enemyColor =
            piece.color === "white"
                ? "black"
                : "white";


        const startSquare =
            piece.color === "white"
                ? "e1"
                : "e8";


        if (
            from !== startSquare
        ) {

            return false;

        }


        /* КОРОТКАЯ */

        if (
            dx === 2
        ) {

            const rookSquare =
                piece.color === "white"
                    ? "h1"
                    : "h8";


            const rook =
                getPositionPiece(
                    rookSquare
                );


            const hasRight =
                piece.color === "white"
                    ? positionCastlingRights.includes("K")
                    : positionCastlingRights.includes("k");


            if (!hasRight) {
                return false;
            }


            if (
                !rook ||
                rook.type !== "rook" ||
                rook.color !== piece.color
            ) {

                return false;

            }


            const between1 =
                piece.color === "white"
                    ? "f1"
                    : "f8";


            const between2 =
                piece.color === "white"
                    ? "g1"
                    : "g8";


            if (
                getPositionPiece(between1) ||
                getPositionPiece(between2)
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    startSquare,
                    enemyColor
                )
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    between1,
                    enemyColor
                )
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    between2,
                    enemyColor
                )
            ) {

                return false;

            }


            return true;

        }


        /* ДЛИННАЯ */

        if (
            dx === -2
        ) {

            const rookSquare =
                piece.color === "white"
                    ? "a1"
                    : "a8";


            const rook =
                getPositionPiece(
                    rookSquare
                );


            const hasRight =
                piece.color === "white"
                    ? positionCastlingRights.includes("Q")
                    : positionCastlingRights.includes("q");


            if (!hasRight) {
                return false;
            }


            if (
                !rook ||
                rook.type !== "rook" ||
                rook.color !== piece.color
            ) {

                return false;

            }


            const between1 =
                piece.color === "white"
                    ? "d1"
                    : "d8";


            const between2 =
                piece.color === "white"
                    ? "c1"
                    : "c8";


            const extraSquare =
                piece.color === "white"
                    ? "b1"
                    : "b8";


            if (
                getPositionPiece(between1) ||
                getPositionPiece(between2) ||
                getPositionPiece(extraSquare)
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    startSquare,
                    enemyColor
                )
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    between1,
                    enemyColor
                )
            ) {

                return false;

            }


            if (
                isSquareAttackedByColor(
                    between2,
                    enemyColor
                )
            ) {

                return false;

            }


            return true;

        }


        return false;

    }


    return false;

}


/* ============================================================
   ВЫПОЛНИТЬ ХОД НА ДОСКЕ ПОЗИЦИИ
============================================================ */

function makePositionMove(
    from,
    to
) {

    const originalBoard =
        clonePositionBoard(
            positionBoardState
        );


    const piece =
        getPositionPiece(from);


    if (!piece) {
        return;
    }


    /* Убираем фигуру */

    setPositionPiece(
        from,
        null
    );


    /* ========================================================
       РОКИРОВКА
    ======================================================== */

    if (
        piece.type === "king" &&
        Math.abs(
            FILES.indexOf(to[0]) -
            FILES.indexOf(from[0])
        ) === 2
    ) {

        const fromFile =
            FILES.indexOf(
                from[0]
            );


        const toFile =
            FILES.indexOf(
                to[0]
            );


        /* Короткая */

        if (
            toFile > fromFile
        ) {

            const rookFrom =
                piece.color === "white"
                    ? "h1"
                    : "h8";


            const rookTo =
                piece.color === "white"
                    ? "f1"
                    : "f8";


            const rook =
                getPositionPiece(
                    rookFrom
                );


            setPositionPiece(
                rookFrom,
                null
            );


            setPositionPiece(
                rookTo,
                rook
            );

        }


        /* Длинная */

        else {

            const rookFrom =
                piece.color === "white"
                    ? "a1"
                    : "a8";


            const rookTo =
                piece.color === "white"
                    ? "d1"
                    : "d8";


            const rook =
                getPositionPiece(
                    rookFrom
                );


            setPositionPiece(
                rookFrom,
                null
            );


            setPositionPiece(
                rookTo,
                rook
            );

        }

    }


    /* ========================================================
       АВТОПРЕВРАЩЕНИЕ ПЕШКИ
    ======================================================== */

    let movedPiece =
        piece;


    const destinationRank =
        parseInt(
            to[1]
        );


    if (
        piece.type === "pawn" &&
        (
            destinationRank === 8 ||
            destinationRank === 1
        )
    ) {

        movedPiece = {

            type: "queen",

            color: piece.color

        };

    }


    /* Ставим фигуру */

    setPositionPiece(
        to,
        movedPiece
    );


    /* Запоминаем ход */

    positionUserMove = {

        from: from,

        to: to

    };


    positionSelectedSquare =
        null;


    positionBestMoveShown =
        false;


    renderPositionBoard();


    /* ========================================================
       ПРОВЕРКА ЛУЧШЕГО ХОДА
    ======================================================== */

    const mistake =
        positionScreen.currentMistake;


    const bestMove =
        String(
            mistake.best_move || ""
        )
        .trim()
        .toLowerCase();


    const playedMove =
        (
            from +
            to
        ).toLowerCase();


    const resultElement =
        document.getElementById(
            "positionResult"
        );


    /* Сравниваем первые 4 символа */

    const isCorrect =
        bestMove.length >= 4 &&
        playedMove.length >= 4 &&
        playedMove.substring(0, 4) ===
        bestMove.substring(0, 4);


    if (isCorrect) {

        resultElement.className =
            "position-result success";


        resultElement.textContent =
            `✅ Правильно! ${mistake.best_san || bestMove} — лучший ход.`;


        return;

    }


    /* ========================================================
       НЕПРАВИЛЬНЫЙ ХОД
    ======================================================== */

    resultElement.className =
        "position-result error";


    resultElement.textContent =
        `❌ Неправильно. Лучший ход: ${mistake.best_san || bestMove}`;


    /* Через полсекунды возвращаем позицию */

    setTimeout(() => {

        positionBoardState =
            clonePositionBoard(
                originalBoard
            );


        positionSelectedSquare =
            null;


        positionUserMove =
            null;


        positionBestMoveShown =
            false;


        renderPositionBoard();


        resultElement.className =
            "position-result neutral";


        resultElement.textContent =
            "Выберите фигуру и попробуйте найти лучший ход.";

    }, 500);

}


/* ============================================================
   НАЖАТИЕ НА КЛЕТКУ ПОЗИЦИИ
============================================================ */

function handlePositionSquareClick(
    squareName
) {

    const piece =
        getPositionPiece(
            squareName
        );


    /* Фигура не выбрана */

    if (
        positionSelectedSquare === null
    ) {

        if (!piece) {
            return;
        }


        const mistake =
            positionScreen.currentMistake;


        const playerSide =
            getMistakeSide(
                mistake
            );


        if (
            piece.color !==
            playerSide
        ) {

            setPositionResult(
                "neutral",
                "Это фигура соперника."
            );


            return;

        }


        positionSelectedSquare =
            squareName;


        renderPositionBoard();


        return;

    }


    /* Нажали ту же клетку */

    if (
        positionSelectedSquare ===
        squareName
    ) {

        positionSelectedSquare =
            null;


        renderPositionBoard();


        return;

    }


    /* Другая своя фигура */

    if (
        piece &&
        piece.color ===
        getMistakeSide(
            positionScreen.currentMistake
        )
    ) {

        positionSelectedSquare =
            squareName;


        renderPositionBoard();


        return;

    }


    const from =
        positionSelectedSquare;


    const to =
        squareName;


    if (
        !isPositionMoveLegal(
            from,
            to
        )
    ) {

        setPositionResult(
            "wrong",
            "Такой ход невозможен."
        );


        return;

    }


    makePositionMove(
        from,
        to
    );

}


/* ============================================================
   РЕЗУЛЬТАТ
============================================================ */

function setPositionResult(
    type,
    text
) {

    const result =
        document.getElementById(
            "positionResult"
        );


    if (!result) {
        return;
    }


    result.className =
        "position-result " +
        type;


    result.textContent =
        text;

}


/* ============================================================
   ПРОВЕРКА ХОДА
============================================================ */

function checkPositionMove(
    playedUci
) {

    const mistake =
        positionScreen.currentMistake;


    if (!mistake) {
        return;
    }


    const bestMove =
        mistake.best_move ??
        mistake.best_move_uci ??
        mistake.move_best ??
        null;


    const bestSan =
        mistake.best_san ??
        mistake.best_move_san ??
        mistake.best_move_text ??
        "—";


    if (!bestMove) {

        setPositionResult(
            "neutral",
            "Лучший ход для проверки не найден."
        );


        return;

    }


    const normalizedPlayed =
        String(
            playedUci
        ).toLowerCase();


    const normalizedBest =
        String(
            bestMove
        )
        .toLowerCase()
        .substring(
            0,
            4
        );


    if (
        normalizedPlayed.substring(
            0,
            4
        ) === normalizedBest
    ) {

        setPositionResult(
            "correct",
            `✅ Правильно! ${bestSan} — лучший ход.`
        );


        positionBestMoveShown =
            false;


        return;

    }


    setPositionResult(
        "wrong",
        `❌ Неправильно. Лучший ход: ${bestSan}`
    );

}


/* ============================================================
   ОТРИСОВКА КООРДИНАТ
============================================================ */

function renderPositionCoordinates() {

    const ranks =
        document.getElementById(
            "positionRanks"
        );


    const files =
        document.getElementById(
            "positionFiles"
        );


    if (!ranks || !files) {
        return;
    }


    ranks.innerHTML = "";

    files.innerHTML = "";


    for (
        let row = 0;
        row < 8;
        row++
    ) {

        const span =
            document.createElement(
                "span"
            );


        if (
            positionOrientation ===
            "white"
        ) {

            span.textContent =
                8 - row;

        } else {

            span.textContent =
                row + 1;

        }


        ranks.appendChild(
            span
        );

    }


    for (
        let col = 0;
        col < 8;
        col++
    ) {

        const span =
            document.createElement(
                "span"
            );


        if (
            positionOrientation ===
            "white"
        ) {

            span.textContent =
                FILES[col];

        } else {

            span.textContent =
                FILES[7 - col];

        }


        files.appendChild(
            span
        );

    }

}


/* ============================================================
   ОТРИСОВКА ДОСКИ ПОЗИЦИИ
============================================================ */

function renderPositionBoard() {

    const positionBoard =
        document.getElementById(
            "positionBoard"
        );


    if (!positionBoard) {
        return;
    }


    positionBoard.innerHTML = "";


    positionBoard.style.width =
        "min(92vw, 520px)";


    positionBoard.style.height =
        "min(92vw, 520px)";


    for (
        let row = 0;
        row < 8;
        row++
    ) {

        for (
            let col = 0;
            col < 8;
            col++
        ) {

            const square =
                document.createElement(
                    "div"
                );


            square.classList.add(
                "position-square"
            );


            /* Цвет клетки */

            if (
                (row + col) % 2 === 0
            ) {

                square.classList.add(
                    "position-light"
                );

            } else {

                square.classList.add(
                    "position-dark"
                );

            }


            const squareName =
                getPositionSquareName(
                    row,
                    col
                );


            square.dataset.square =
                squareName;


            /* Выбранная клетка */

            if (
                positionSelectedSquare ===
                squareName
            ) {

                square.classList.add(
                    "position-selected"
                );

            }


            /* =================================================
               ПОКАЗ ЛУЧШЕГО ХОДА
            ================================================= */

            const mistake =
                positionScreen.currentMistake;


            const bestMove =
                mistake?.best_move ??
                mistake?.best_move_uci ??
                mistake?.move_best ??
                null;


            if (
                positionBestMoveShown &&
                bestMove
            ) {

                const from =
                    bestMove.substring(
                        0,
                        2
                    );


                const to =
                    bestMove.substring(
                        2,
                        4
                    );


                if (
                    squareName === from
                ) {

                    square.classList.add(
                        "position-best-from"
                    );

                }


                if (
                    squareName === to
                ) {

                    square.classList.add(
                        "position-best-to"
                    );

                }

            }


            /* =================================================
               ПОКАЗ ПОСЛЕДНЕГО ХОДА
            ================================================= */

            if (
                positionUserMove
            ) {

                if (
                    squareName ===
                    positionUserMove.from
                ) {

                    square.classList.add(
                        "position-user-from"
                    );

                }


                if (
                    squareName ===
                    positionUserMove.to
                ) {

                    square.classList.add(
                        "position-user-to"
                    );

                }

            }


            /* =================================================
               ФИГУРА
            ================================================= */

            const piece =
                getPositionPiece(
                    squareName
                );


            if (piece) {

                const image =
                    document.createElement(
                        "img"
                    );


                image.classList.add(
                    "piece-image"
                );


                image.src =
                    `pieces/${piece.color}/${piece.type.charAt(0).toUpperCase() + piece.type.slice(1)}.svg?v=2`;


                image.alt =
                    `${piece.color} ${piece.type}`;


                image.draggable =
                    false;


                image.style.pointerEvents =
                    "none";


                square.appendChild(
                    image
                );

            }


            /* =================================================
               КЛИК
            ================================================= */

            square.addEventListener(
                "click",
                () => {

                    handlePositionSquareClick(
                        squareName
                    );

                }
            );


            positionBoard.appendChild(
                square
            );

        }

    }


    renderPositionCoordinates();

}


/* ============================================================
   ФОРМАТ ОЦЕНКИ
============================================================ */

function formatPositionEvaluation(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "—";

    }


    const number =
        Number(value);


    if (
        !Number.isFinite(number)
    ) {

        return "—";

    }


    const pawns =
        number / 100;


    if (
        pawns > 0
    ) {

        return `+${pawns.toFixed(2)}`;

    }


    return pawns.toFixed(2);

}


/* ============================================================
   ОБНОВИТЬ ОЦЕНКУ
============================================================ */

function updatePositionEvaluation(
    value,
    afterMove = false
) {

    const label =
        document.getElementById(
            "positionEvaluationLabel"
        );


    const element =
        document.getElementById(
            "positionEvaluationValue"
        );


    if (
        !label ||
        !element
    ) {

        return;

    }


    label.textContent =
        afterMove
            ? "Оценка после хода:"
            : "Оценка позиции:";


    element.textContent =
        formatPositionEvaluation(
            value
        );

}


/* ============================================================
   ПОКАЗ ПОЗИЦИИ ОШИБКИ
============================================================ */

function showMistakePosition(
    mistake
) {

    createPositionScreen();


    positionScreen.currentMistake =
        mistake;


    positionOrientation =
        getMistakeSide(
            mistake
        );


    positionSelectedSquare =
        null;


    positionBestMoveShown =
        false;


    positionUserMove =
        null;


    analysisScreen.classList.add(
        "hidden"
    );


    positionScreen.classList.remove(
        "hidden"
    );


    const positionInfo =
        document.getElementById(
            "positionInfo"
        );


    const bestMoveInfo =
        document.getElementById(
            "bestMoveInfo"
        );


    const positionResult =
        document.getElementById(
            "positionResult"
        );


    /* ========================================================
       ИНФОРМАЦИЯ ОБ ОШИБКЕ
    ======================================================== */

    const moveNumber =
        mistake.move_number ??
        mistake.move ??
        "?";


    const playedSan =
        mistake.position_played_san ??
        mistake.played_move_san ??
        mistake.played_san ??
        mistake.move_san ??
        "—";


    const loss =
        mistake.loss ??
        mistake.evaluation_loss ??
        null;


    /* ========================================================
       ОЦЕНКА ДО РЕАЛЬНОГО ХОДА
    ======================================================== */

    const positionEvaluationBefore =
        mistake.position_evaluation_before ??
        mistake.position_evaluation ??
        mistake.before_score ??
        null;


    /* ========================================================
       ОЦЕНКА ПОСЛЕ РЕАЛЬНОГО ОШИБОЧНОГО ХОДА
    ======================================================== */

    const positionEvaluationAfter =
        mistake.position_evaluation_after ??
        mistake.after_score ??
        null;


    console.log(
        "Оценка ошибки:",
        {
            before:
                positionEvaluationBefore,

            after:
                positionEvaluationAfter,

            mistake:
                mistake
        }
    );


    /* ========================================================
       ВЫВОД ИНФОРМАЦИИ
    ======================================================== */

    positionInfo.innerHTML = `

        <div>
            <strong>
                Ход ${moveNumber}
            </strong>
        </div>


        <div>
            Сыграно:

            <strong>
                ${playedSan}
            </strong>
        </div>


        ${
            positionEvaluationBefore !== null
            ?
            `
            <div>
                <span id="positionEvaluationLabel">
                    Оценка до хода:
                </span>

                <strong id="positionEvaluationValue">
                    ${formatPositionEvaluation(
                        positionEvaluationBefore
                    )}
                </strong>
            </div>
            `
            :
            ""
        }


        ${
            positionEvaluationAfter !== null
            ?
            `
            <div>
                Оценка после хода:

                <strong>
                    ${formatPositionEvaluation(
                        positionEvaluationAfter
                    )}
                </strong>
            </div>
            `
            :
            ""
        }


        ${
            loss !== null
            ?
            `
            <div>
                Потеря:

                <strong>
                    ${loss}
                </strong>
            </div>
            `
            :
            ""
        }

    `;


    bestMoveInfo.innerHTML =
        "";


    positionResult.className =
        "position-result neutral";


    positionResult.textContent =
        "Выберите фигуру и попробуйте найти лучший ход.";


    /* ========================================================
       FEN
    ======================================================== */

    if (
        !mistake.position_fen
    ) {

        document
            .getElementById(
                "positionBoard"
            )
            .innerHTML = `

                <div class="position-error">

                    Позиция для этой ошибки
                    не найдена.

                </div>

            `;


        return;

    }


    positionBoardState =
        fenToBoard(
            mistake.position_fen
        );


    positionCastlingRights =
        String(
            mistake.position_fen
        )
        .split(" ")[2] || "-";


    renderPositionBoard();

}


/* ============================================================
   ПОКАЗ ЛУЧШЕГО ХОДА
============================================================ */

function showBestMove(
    mistake
) {

    const bestMove =
        mistake.best_move ??
        mistake.best_move_uci ??
        mistake.move_best ??
        null;


    const bestSan =
        mistake.best_san ??
        mistake.best_move_san ??
        mistake.best_move_text ??
        "—";


    const bestMoveInfo =
        document.getElementById(
            "bestMoveInfo"
        );


    if (!bestMove) {

        bestMoveInfo.innerHTML = `

            <div>
                Лучший ход не найден.
            </div>

        `;


        return;

    }


    const from =
        bestMove.substring(
            0,
            2
        );


    const to =
        bestMove.substring(
            2,
            4
        );


    bestMoveInfo.innerHTML = `

        <div>

            Лучший ход:

            <strong>
                ${bestSan}
            </strong>

        </div>

    `;


    positionBestMoveShown =
        true;


    positionUserMove =
        null;


    positionSelectedSquare =
        null;


    renderPositionBoard();

}


/* ============================================================
ПЕРЕКЛЮЧЕНИЕ ЭКРАНОВ
============================================================ */

function showScreen(
    screen
) {

    menuScreen.classList.add(
        "hidden"
    );


    gameScreen.classList.add(
        "hidden"
    );


    analysisScreen.classList.add(
        "hidden"
    );


    mistakesScreen.classList.add(
        "hidden"
    );


    if (positionScreen) {

        positionScreen.classList.add(
            "hidden"
        );

    }


    screen.classList.remove(
        "hidden"
    );

}


/* ============================================================
МЕНЮ → ИГРА
============================================================ */

playButton.addEventListener(
    "click",
    () => {

        showScreen(
            gameScreen
        );


        loadGame();

    }
);


/* ============================================================
МЕНЮ → АНАЛИЗ
============================================================ */

analysisButton.addEventListener(
    "click",
    () => {

        showScreen(
            analysisScreen
        );


        analysisMessage.textContent =
            "Вставьте PGN партии.";

    }
);


/* ============================================================
МЕНЮ → МОИ ОШИБКИ
============================================================ */

mistakesButton.addEventListener(
    "click",
    () => {

        showScreen(
            mistakesScreen
        );

    }
);


/* ============================================================
ИГРА → МЕНЮ
============================================================ */

backFromGameButton.addEventListener(
    "click",
    () => {

        showScreen(
            menuScreen
        );

    }
);


/* ============================================================
АНАЛИЗ → МЕНЮ
============================================================ */

backFromAnalysisButton.addEventListener(
    "click",
    () => {

        showScreen(
            menuScreen
        );

    }
);


/* ============================================================
ОШИБКИ → МЕНЮ
============================================================ */

backFromMistakesButton.addEventListener(
    "click",
    () => {

        showScreen(
            menuScreen
        );

    }
);


/* ============================================================
АНАЛИЗ PGN
============================================================ */

analyzeButton.addEventListener(
    "click",
    async () => {

        const pgn =
            pgnInput.value.trim();


        if (!pgn) {

            analysisMessage.textContent =
                "Сначала вставьте PGN партии.";


            analysisResult.classList.add(
                "hidden"
            );


            return;

        }


        analysisMessage.textContent =
            "⏳ Анализируем партию...";


        analysisResult.classList.add(
            "hidden"
        );


        try {

            console.log(
                "========== TELEGRAM DEBUG =========="
            );

            console.log(
                "tg =",
                tg
            );

            console.log(
                "initData =",
                tg?.initData
            );

            console.log(
                "initDataUnsafe =",
                tg?.initDataUnsafe
            );

            console.log(
                "telegram user =",
                tg?.initDataUnsafe?.user
            );

            console.log(
                "===================================="
            );

            const response =
                await fetch(
                    "/analyze",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            pgn: pgn,

                            telegram_user:
                                tg?.initDataUnsafe?.user
                                    ? {
                                        id:
                                            tg.initDataUnsafe.user.id,

                                        username:
                                            tg.initDataUnsafe.user.username || null,

                                        first_name:
                                            tg.initDataUnsafe.user.first_name || null
                                    }
                                    : null

                        })
                    }
                );


            const data =
                await response.json();


            console.log(
                "Результат анализа:",
                data
            );


            if (
                !response.ok ||
                !data.success
            ) {

                analysisMessage.textContent =
                    data.error ||
                    "Не удалось проанализировать партию.";


                return;

            }


            /* ==================================================
               СОХРАНЯЕМ РЕЗУЛЬТАТ
            ================================================== */

            currentAnalysisData =
                data;


            /* ==================================================
               ОСНОВНАЯ ИНФОРМАЦИЯ
            ================================================== */

            let html = "";


            html += `

                <div class="analysis-summary">

                    <h3>
                        Результат анализа
                    </h3>


                    <p>

                        <strong>
                            Белые:
                        </strong>

                        ${data.white || "—"}

                    </p>


                    <p>

                        <strong>
                            Чёрные:
                        </strong>

                        ${data.black || "—"}

                    </p>


                    <p>

                        <strong>
                            Результат:
                        </strong>

                        ${data.result || "—"}

                    </p>


                    <p>

                        <strong>
                            Точность:
                        </strong>

                        ${data.accuracy ?? "—"}

                    </p>

                </div>

            `;


            /* ==================================================
               ОШИБКИ
            ================================================== */

            if (
                !data.mistakes ||
                data.mistakes.length === 0
            ) {

                html += `

                    <div class="analysis-empty">

                        <strong>
                            Ошибок не найдено.
                        </strong>

                    </div>

                `;

            } else {

                html += `

                    <div class="mistakes-list">

                        <h3>
                            Найденные ошибки:
                        </h3>

                `;


                data.mistakes.forEach(
                    (
                        mistake,
                        index
                    ) => {

                        const moveNumber =
                            mistake.move_number ??
                            mistake.move ??
                            (
                                index + 1
                            );


                        const playedSan =
                            mistake.position_played_san ??
                            mistake.played_move_san ??
                            mistake.played_san ??
                            mistake.move_san ??
                            "—";


                        const loss =
                            mistake.loss ??
                            mistake.evaluation_loss ??
                            null;


                        html += `

                            <div
                                class="mistake-card"
                            >

                                <div>

                                    <strong>
                                        Ход ${moveNumber}
                                    </strong>

                                </div>


                                <div>

                                    Сыграно:

                                    <strong>
                                        ${playedSan}
                                    </strong>

                                </div>


                                ${
                                    loss !== null
                                    ?
                                    `
                                    <div>

                                        Потеря:

                                        <strong>
                                            ${loss}
                                        </strong>

                                    </div>
                                    `
                                    :
                                    ""
                                }


                                <button
                                    type="button"
                                    class="show-position-button"
                                    data-mistake-index="${index}"
                                >

                                    Показать позицию

                                </button>

                            </div>

                        `;

                    }
                );


                html += `

                    </div>

                `;

            }


            /* ==================================================
               СТАТИСТИКА
            ================================================== */

            if (
                data.statistics
            ) {

                html += `

                    <div
                        class="analysis-statistics"
                    >

                        <h3>
                            Статистика
                        </h3>


                        <pre>
${JSON.stringify(
    data.statistics,
    null,
    2
)}
                        </pre>

                    </div>

                `;

            }


            analysisResult.innerHTML =
                html;


            analysisResult.classList.remove(
                "hidden"
            );


            /* ==================================================
               КНОПКИ «ПОКАЗАТЬ ПОЗИЦИЮ»
            ================================================== */

            const positionButtons =
                analysisResult.querySelectorAll(
                    ".show-position-button"
                );


            positionButtons.forEach(
                (button) => {

                    button.addEventListener(
                        "click",
                        () => {

                            const index =
                                Number(
                                    button.dataset
                                        .mistakeIndex
                                );


                            if (
                                !currentAnalysisData ||
                                !currentAnalysisData.mistakes
                            ) {

                                return;

                            }


                            const mistake =
                                currentAnalysisData
                                    .mistakes[index];


                            if (!mistake) {

                                return;

                            }


                            showMistakePosition(
                                mistake
                            );

                        }
                    );

                }
            );


            analysisMessage.textContent =
                "✅ Анализ завершён.";


        } catch (error) {

            console.error(
                "Ошибка анализа:",
                error
            );


            analysisMessage.textContent =
                "Ошибка соединения с сервером.";

        }

    }

);


/* ============================================================
ЗАПУСК
============================================================ */

/*
Игру специально НЕ загружаем при запуске.

Она загрузится только после нажатия
«Играть».
*/

showScreen(
    menuScreen
);