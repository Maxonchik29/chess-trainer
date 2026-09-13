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
   ИГРА
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
   АНАЛИЗ
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
   СОСТОЯНИЕ АНАЛИЗА
============================================================ */

let currentAnalysisData = null;

let myMistakesData = [];

let currentMistakeSource = "analysis";


/* ============================================================
   СОСТОЯНИЕ ПОЗИЦИИ ОШИБКИ
============================================================ */

let positionScreen = null;

let positionBoardState = null;

let positionSelectedSquare = null;

let positionOrientation = "white";

let positionBestMoveShown = false;

let positionUserMove = null;

let positionLocked = false;

let positionCastlingRights = "-";


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
   TELEGRAM USER
============================================================ */

function getTelegramUser() {

    if (
        tg &&
        tg.initDataUnsafe &&
        tg.initDataUnsafe.user
    ) {
        return tg.initDataUnsafe.user;
    }

    return null;
}


/* ============================================================
   FEN → ДОСКА
============================================================ */

function fenToBoard(fen) {

    if (!fen) {
        return [];
    }

    const position =
        String(fen).split(" ")[0];

    const rows =
        position.split("/");

    const result = [];

    for (
        let row = 0;
        row < 8;
        row++
    ) {

        const resultRow = [];

        const rowText =
            rows[row] || "";

        for (
            const char of rowText
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

        while (resultRow.length < 8) {
            resultRow.push(null);
        }

        result.push(resultRow);
    }

    while (result.length < 8) {
        result.push([
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null
        ]);
    }

    return result;
}


/* ============================================================
   ПОЛУЧИТЬ ФИГУРУ ОСНОВНОЙ ДОСКИ
============================================================ */

function getPiece(squareName) {

    const file =
        FILES.indexOf(
            squareName[0]
        );

    const rank =
        8 -
        parseInt(
            squareName[1]
        );

    if (
        file < 0 ||
        rank < 0 ||
        rank > 7
    ) {
        return null;
    }

    if (
        !board[rank]
    ) {
        return null;
    }

    return board[rank][file];
}


/* ============================================================
   ОТРИСОВКА ОСНОВНОЙ ДОСКИ
============================================================ */

function renderBoard() {

    if (!boardElement) {
        return;
    }

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

            square.type = "button";

            square.classList.add(
                "square"
            );

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

            const squareName =
                FILES[col] +
                (8 - row);

            square.dataset.square =
                squareName;

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

            if (
                selectedSquare ===
                squareName
            ) {

                square.classList.add(
                    "selected"
                );
            }

            const piece =
                board[row]?.[col];

            if (piece) {

                const pieceElement =
                    document.createElement(
                        "img"
                    );

                pieceElement.classList.add(
                    "piece-image"
                );

                pieceElement.src =
                    `pieces/${piece.color}/${piece.type.charAt(0).toUpperCase() + piece.type.slice(1)}.svg?v=5`;

                pieceElement.onerror = () => {
                    console.error(
                        "Не удалось загрузить фигуру:",
                        pieceElement.src
                    );
                };

                pieceElement.alt =
                    `${piece.color} ${piece.type}`;

                pieceElement.draggable =
                    false;

                square.appendChild(
                    pieceElement
                );
            }

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


    if (
        selectedSquare === null
    ) {

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


    const from =
        selectedSquare;

    const to =
        squareName;

    const uciMove =
        from + to;

    selectedSquare = null;

    makeMove(
        uciMove
    );
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

                    body:
                        JSON.stringify({
                            move:
                                uciMove
                        })
                }
            );

        const data =
            await response.json();

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

        if (
            data.played_move
        ) {

            lastMove = {
                from:
                    data.played_move.substring(
                        0,
                        2
                    ),

                to:
                    data.played_move.substring(
                        2,
                        4
                    )
            };

        } else {

            lastMove = null;
        }

        playerTurn =
            Boolean(
                data.player_turn
            );

        gameOver =
            Boolean(
                data.game_over
            );

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
            "Ошибка хода:",
            error
        );

        setMessage(
            "Ошибка соединения с сервером."
        );
    }
}


/* ============================================================
   ЗАГРУЗКА ИГРЫ
============================================================ */

async function loadGame() {

    try {

        const response =
            await fetch(
                "/game"
            );

        const data =
            await response.json();

        board =
            fenToBoard(
                data.fen
            );

        playerTurn =
            Boolean(
                data.player_turn
            );

        gameOver =
            Boolean(
                data.game_over
            );

        selectedSquare = null;

        lastMove = null;

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

    if (!turnElement) {
        return;
    }

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

    if (!messageElement) {
        return;
    }

    messageElement.textContent =
        text;
}


/* ============================================================
   ПОДСКАЗКА
============================================================ */

if (hintButton) {

    hintButton.addEventListener(
        "click",
        async () => {

            setMessage(
                "Получаем лучший ход..."
            );

            try {

                const response =
                    await fetch(
                        "/game"
                    );

                const data =
                    await response.json();

                if (
                    data.legal_moves &&
                    data.legal_moves.length
                ) {

                    setMessage(
                        "Подсказка: позже здесь покажем лучший ход Stockfish."
                    );
                }

            } catch (error) {

                console.error(
                    error
                );

                setMessage(
                    "Ошибка получения подсказки."
                );
            }
        }
    );
}


/* ============================================================
   НОВАЯ ИГРА
============================================================ */

if (newGameButton) {

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
                    Boolean(
                        data.player_turn
                    );

                gameOver =
                    Boolean(
                        data.game_over
                    );

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
}


/* ============================================================
   ПОКАЗ ЭКРАНА
============================================================ */

function showScreen(screen) {

    if (menuScreen) {
        menuScreen.classList.add(
            "hidden"
        );
    }

    if (gameScreen) {
        gameScreen.classList.add(
            "hidden"
        );
    }

    if (analysisScreen) {
        analysisScreen.classList.add(
            "hidden"
        );
    }

    if (mistakesScreen) {
        mistakesScreen.classList.add(
            "hidden"
        );
    }

    if (positionScreen) {
        positionScreen.classList.add(
            "hidden"
        );
    }

    if (screen) {
        screen.classList.remove(
            "hidden"
        );
    }
}


/* ============================================================
   МЕНЮ → ИГРА
============================================================ */

if (playButton) {

    playButton.addEventListener(
        "click",
        () => {

            showScreen(
                gameScreen
            );

            loadGame();
        }
    );
}


/* ============================================================
   МЕНЮ → АНАЛИЗ
============================================================ */

if (analysisButton) {

    analysisButton.addEventListener(
        "click",
        () => {

            showScreen(
                analysisScreen
            );

            if (analysisMessage) {

                analysisMessage.textContent =
                    "Вставьте PGN партии.";
            }
        }
    );
}


/* ============================================================
   МЕНЮ → МОИ ОШИБКИ
============================================================ */

if (mistakesButton) {

    mistakesButton.addEventListener(
        "click",
        () => {

            showScreen(
                mistakesScreen
            );

            loadMyMistakes();
        }
    );
}


/* ============================================================
   НАЗАД ИЗ ИГРЫ
============================================================ */

if (backFromGameButton) {

    backFromGameButton.addEventListener(
        "click",
        () => {

            showScreen(
                menuScreen
            );
        }
    );
}


/* ============================================================
   НАЗАД ИЗ АНАЛИЗА
============================================================ */

if (backFromAnalysisButton) {

    backFromAnalysisButton.addEventListener(
        "click",
        () => {

            showScreen(
                menuScreen
            );
        }
    );
}


/* ============================================================
   НАЗАД ИЗ МОИХ ОШИБОК
============================================================ */

if (backFromMistakesButton) {

    backFromMistakesButton.addEventListener(
        "click",
        () => {

            showScreen(
                menuScreen
            );
        }
    );
}


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
        "screen hidden";

    positionScreen.innerHTML = `

        <div class="position-header">

            <button
                type="button"
                id="backFromPositionButton"
                class="menu-button"
            >
                ← Назад
            </button>

            <h2 id="positionTitle">
                Позиция ошибки
            </h2>

        </div>


        <div
            id="positionInfo"
            class="position-info"
        ></div>


        <div
            id="positionResult"
            class="position-result"
        ></div>


       <div
            id="positionBoardWrapper"
            class="position-board-wrapper"
        >

            <div
                id="positionBoard"
                class="position-board"
            ></div>

            <div
                id="positionCoordinates"
                class="position-coordinates"
            ></div>

        </div>


        <div
            id="positionBestMoveInfo"
            class="position-best-move-info"
        ></div>


        <div
            class="position-buttons"
        >

            <button
                type="button"
                id="showBestMoveButton"
                class="menu-button"
            >
                💡 Показать лучший ход
            </button>

            <button
                type="button"
                id="deleteMistakeButton"
                class="menu-button delete-mistake-button"
            >
                🗑 Удалить эту ошибку
            </button>

        </div>

        <div
            class="mistake-navigation"
        >

            <button
                type="button"
                id="previousMistakeButton"
                class="menu-button"
            >
                ← Предыдущая
            </button>

            <button
                type="button"
                id="nextMistakeButton"
                class="menu-button"
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


    document
        .getElementById(
            "backFromPositionButton"
        )
        .addEventListener(
            "click",
            () => {

                positionScreen.classList.add(
                    "hidden"
                );

                if (
                    currentMistakeSource ===
                    "mistakes"
                ) {

                    mistakesScreen.classList.remove(
                        "hidden"
                    );

                } else {

                    analysisScreen.classList.remove(
                        "hidden"
                    );
                }
            }
        );


    document
        .getElementById(
            "showBestMoveButton"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    positionScreen &&
                    positionScreen.currentMistake
                ) {

                    showBestMove(
                        positionScreen.currentMistake
                    );
                }
            }
        );

    document
        .getElementById(
            "deleteMistakeButton"
        )
        .addEventListener(
            "click",
            () => {

                deleteCurrentMistake();
            }
        );

    document
        .getElementById(
            "previousMistakeButton"
        )
        .addEventListener(
            "click",
            () => {

                navigateMistake(
                    -1
                );
            }
        );


    document
        .getElementById(
            "nextMistakeButton"
        )
        .addEventListener(
            "click",
            () => {

                navigateMistake(
                    1
                );
            }
        );
}


/* ============================================================
   ОПРЕДЕЛЕНИЕ СТОРОНЫ ОШИБКИ
============================================================ */

function getMistakeSide(mistake) {

    if (!mistake) {
        return "white";
    }

    const side =
        mistake.user_side ??
        mistake.side ??
        mistake.player_color ??
        mistake.color;

    if (
        String(side)
            .toLowerCase()
            .trim()
            .includes("black") ||
        String(side)
            .toLowerCase()
            .trim() === "b" ||
        String(side)
            .toLowerCase()
            .trim() === "черные" ||
        String(side)
            .toLowerCase()
            .trim() === "чёрные"
    ) {

        return "black";
    }

    const fen =
        mistake.position_fen ??
        mistake.fen;

    if (fen) {

        const parts =
            String(fen).split(" ");

        if (
            parts[1] === "b"
        ) {

            return "black";
        }
    }

    return "white";
}


/* ============================================================
   ПОЛУЧИТЬ ИМЯ КЛЕТКИ ПО КООРДИНАТАМ
============================================================ */

function getPositionSquareName(
    row,
    col
) {

    let realRow = row;
    let realCol = col;

    if (
        positionOrientation ===
        "black"
    ) {

        realRow =
            7 - row;

        realCol =
            7 - col;
    }

    return (
        FILES[realCol] +
        (8 - realRow)
    );
}


/* ============================================================
   КЛОНИРОВАНИЕ ПОЗИЦИИ
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
                            type:
                                piece.type,
                            color:
                                piece.color
                        }
                        : null
            )
    );
}


/* ============================================================
   ПОЛУЧИТЬ ФИГУРУ ПОЗИЦИИ
============================================================ */

function getPositionPiece(
    squareName
) {

    const coords =
        squareToCoords(
            squareName
        );

    if (!coords) {
        return null;
    }

    return (
        positionBoardState
            ?.[
                coords.row
            ]
            ?.[
                coords.col
            ] ??
        null
    );
}


/* ============================================================
   УСТАНОВИТЬ ФИГУРУ
============================================================ */

function setPositionPiece(
    boardState,
    squareName,
    piece
) {

    const coords =
        squareToCoords(
            squareName
        );

    if (!coords) {
        return;
    }

    boardState[
        coords.row
    ][
        coords.col
    ] = piece;
}


/* ============================================================
   SANDBOX КООРДИНАТЫ
============================================================ */

function squareToCoords(
    squareName
) {

    if (
        !squareName ||
        squareName.length < 2
    ) {
        return null;
    }

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

    return {
        row:
            8 - rank,

        col:
            file
    };
}


/* ============================================================
   ПРОВЕРКА ПУТИ ФИГУРЫ
============================================================ */

function isPathClear(
    boardState,
    fromRow,
    fromCol,
    toRow,
    toCol
) {

    const rowStep =
        Math.sign(
            toRow - fromRow
        );

    const colStep =
        Math.sign(
            toCol - fromCol
        );

    let row =
        fromRow + rowStep;

    let col =
        fromCol + colStep;

    while (
        row !== toRow ||
        col !== toCol
    ) {

        if (
            boardState[row]?.[col]
        ) {
            return false;
        }

        row += rowStep;
        col += colStep;
    }

    return true;
}


/* ============================================================
   АТАКОВАНА ЛИ КЛЕТКА
============================================================ */

function isSquareAttackedByColor(
    boardState,
    squareName,
    attackingColor
) {

    const target =
        squareToCoords(
            squareName
        );

    if (!target) {
        return false;
    }

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

            const piece =
                boardState[row][col];

            if (
                !piece ||
                piece.color !==
                    attackingColor
            ) {
                continue;
            }

            const fromSquare =
                FILES[col] +
                (8 - row);

            const toSquare =
                squareName;

            if (
                isPositionMoveLegal(
                    boardState,
                    fromSquare,
                    toSquare,
                    true
                )
            ) {
                return true;
            }
        }
    }

    return false;
}


/* ============================================================
   ПРОВЕРКА ХОДА ПОЗИЦИИ
============================================================ */

function isPositionMoveLegal(
    boardState,
    fromSquare,
    toSquare,
    attackOnly = false
) {

    const from =
        squareToCoords(
            fromSquare
        );

    const to =
        squareToCoords(
            toSquare
        );

    if (!from || !to) {
        return false;
    }

    const piece =
        boardState[from.row]?.[
            from.col
        ];

    if (!piece) {
        return false;
    }

    const target =
        boardState[to.row]?.[
            to.col
        ];

    if (
        !attackOnly &&
        target &&
        target.color ===
            piece.color
    ) {
        return false;
    }

    const dr =
        to.row -
        from.row;

    const dc =
        to.col -
        from.col;

    const absDr =
        Math.abs(dr);

    const absDc =
        Math.abs(dc);


    /* --------------------------------------------------------
       ПЕШКА
    -------------------------------------------------------- */

    if (
        piece.type ===
        "pawn"
    ) {

        const direction =
            piece.color ===
            "white"
                ? -1
                : 1;

        if (
            attackOnly
        ) {

            return (
                dr === direction &&
                absDc === 1
            );
        }

        if (
            dc === 0 &&
            dr === direction &&
            !target
        ) {
            return true;
        }

        if (
            dc === 0 &&
            dr === 2 * direction &&
            !target
        ) {

            const startRow =
                piece.color ===
                "white"
                    ? 6
                    : 1;

            if (
                from.row ===
                startRow
            ) {

                const middleRow =
                    from.row +
                    direction;

                if (
                    !boardState[
                        middleRow
                    ][from.col]
                ) {
                    return true;
                }
            }
        }

        if (
            absDc === 1 &&
            dr === direction &&
            target
        ) {
            return true;
        }

        return false;
    }


    /* --------------------------------------------------------
       КОНЬ
    -------------------------------------------------------- */

    if (
        piece.type ===
        "knight"
    ) {

        return (
            (
                absDr === 2 &&
                absDc === 1
            ) ||
            (
                absDr === 1 &&
                absDc === 2
            )
        );
    }


    /* --------------------------------------------------------
       КОРОЛЬ
    -------------------------------------------------------- */

    if (
        piece.type ===
        "king"
    ) {

        return (
            absDr <= 1 &&
            absDc <= 1 &&
            (
                absDr !== 0 ||
                absDc !== 0
            )
        );
    }


    /* --------------------------------------------------------
       ЛАДЬЯ
    -------------------------------------------------------- */

    if (
        piece.type ===
        "rook"
    ) {

        if (
            dr !== 0 &&
            dc !== 0
        ) {
            return false;
        }

        return isPathClear(
            boardState,
            from.row,
            from.col,
            to.row,
            to.col
        );
    }


    /* --------------------------------------------------------
       СЛОН
    -------------------------------------------------------- */

    if (
        piece.type ===
        "bishop"
    ) {

        if (
            absDr !== absDc
        ) {
            return false;
        }

        return isPathClear(
            boardState,
            from.row,
            from.col,
            to.row,
            to.col
        );
    }


    /* --------------------------------------------------------
       ФЕРЗЬ
    -------------------------------------------------------- */

    if (
        piece.type ===
        "queen"
    ) {

        const straight =
            dr === 0 ||
            dc === 0;

        const diagonal =
            absDr === absDc;

        if (
            !straight &&
            !diagonal
        ) {
            return false;
        }

        return isPathClear(
            boardState,
            from.row,
            from.col,
            to.row,
            to.col
        );
    }

    return false;
}


/* ============================================================
   СДЕЛАТЬ ХОД НА ДОСКЕ ПОЗИЦИИ
============================================================ */

function makePositionMove(
    fromSquare,
    toSquare
) {

    const from =
        squareToCoords(
            fromSquare
        );

    const to =
        squareToCoords(
            toSquare
        );

    if (!from || !to) {
        return;
    }

    const movingPiece =
        positionBoardState[
            from.row
        ][
            from.col
        ];

    if (!movingPiece) {
        return;
    }

    const newBoard =
        clonePositionBoard(
            positionBoardState
        );

    let piece =
        newBoard[
            from.row
        ][
            from.col
        ];

    newBoard[
        from.row
    ][
        from.col
    ] = null;

    /* Простейшая рокировка */

    if (
        piece.type === "king" &&
        Math.abs(
            to.col - from.col
        ) === 2
    ) {

        if (
            to.col >
            from.col
        ) {

            newBoard[
                from.row
            ][7] = null;

            newBoard[
                from.row
            ][5] = {
                type: "rook",
                color: piece.color
            };

        } else {

            newBoard[
                from.row
            ][0] = null;

            newBoard[
                from.row
            ][3] = {
                type: "rook",
                color: piece.color
            };
        }
    }


    /* Превращение пешки */

    if (
        piece.type ===
            "pawn" &&
        (
            to.row === 0 ||
            to.row === 7
        )
    ) {

        piece = {
            type: "queen",
            color: piece.color
        };
    }

    newBoard[
        to.row
    ][
        to.col
    ] = piece;

    positionBoardState =
        newBoard;
}

/* ============================================================
   НАЖАТИЕ НА ДОСКУ ПОЗИЦИИ
============================================================ */

function handlePositionSquareClick(
    squareName
) {

    if (positionLocked) {
        return;
    }

    if (positionBestMoveShown) {
        return;
    }

    const piece =
        getPositionPiece(
            squareName
        );


    /* ========================================================
       ВЫБОР ФИГУРЫ
    ======================================================== */

    if (
        positionSelectedSquare ===
        null
    ) {

        if (!piece) {

            setPositionResult(
                "Здесь нет фигуры."
            );

            return;
        }

        /* Только фигуры пользователя */

        if (
            piece.color !==
            positionOrientation
        ) {

            setPositionResult(
                "Можно двигать только свои фигуры."
            );

            return;
        }

        positionSelectedSquare =
            squareName;

        setPositionResult(
            `Выбрана ${squareName}. Выберите клетку назначения.`
        );

        renderPositionBoard();

        return;
    }


    /* ========================================================
       ОТМЕНА ВЫБОРА
    ======================================================== */

    if (
        positionSelectedSquare ===
        squareName
    ) {

        positionSelectedSquare =
            null;

        setPositionResult(
            ""
        );

        renderPositionBoard();

        return;
    }


    const from =
        positionSelectedSquare;

    const to =
        squareName;

    const movingPiece =
        getPositionPiece(
            from
        );


    /* ========================================================
       ВЫБРАЛИ ДРУГУЮ СВОЮ ФИГУРУ
    ======================================================== */

    if (
        piece &&
        movingPiece &&
        piece.color ===
            positionOrientation
    ) {

        positionSelectedSquare =
            squareName;

        setPositionResult(
            `Выбрана ${squareName}.`
        );

        renderPositionBoard();

        return;
    }


    if (!movingPiece) {

        positionSelectedSquare =
            null;

        renderPositionBoard();

        return;
    }


    /* ========================================================
       ПРОВЕРЯЕМ, ВООБЩЕ ДОПУСТИМ ЛИ ХОД
    ======================================================== */

    if (
        !isPositionMoveLegal(
            positionBoardState,
            from,
            to,
            false
        )
    ) {

        setPositionResult(
            "✗ Так сходить нельзя."
        );

        return;
    }


    /* ========================================================
       СОХРАНЯЕМ СТАРУЮ ПОЗИЦИЮ
    ======================================================== */

    const oldBoard =
        clonePositionBoard(
            positionBoardState
        );


    /* ========================================================
       ПОЛУЧАЕМ ЛУЧШИЙ ХОД
    ======================================================== */

    const mistake =
        positionScreen?.currentMistake;

    const bestMove =
        mistake?.best_move_uci ??
        mistake?.best_move ??
        mistake?.best_uci;


    const playedMove =
        String(from + to)
            .toLowerCase();

    const normalizedBestMove =
        bestMove
            ? String(bestMove)
                .substring(0, 4)
                .toLowerCase()
            : null;


    /* ========================================================
       СНАЧАЛА ВИЗУАЛЬНО ДЕЛАЕМ ХОД
    ======================================================== */

    positionUserMove = {
        from: from,
        to: to
    };

    makePositionMove(
        from,
        to
    );

    positionSelectedSquare =
        null;

    renderPositionBoard();


    /* ========================================================
       НЕБОЛЬШАЯ ЗАДЕРЖКА
       Чтобы пользователь увидел свой ход
    ======================================================== */

    setTimeout(
        () => {

            /* ==================================================
               НЕПРАВИЛЬНЫЙ ХОД
            ================================================== */

            if (
                !normalizedBestMove ||
                playedMove !==
                    normalizedBestMove
            ) {

                setPositionResult(
                    "✗ Неверный ход. Попробуйте ещё раз."
                );


                /*
                 * Возвращаем исходную позицию
                 */

                positionBoardState =
                    oldBoard;

                positionUserMove =
                    null;


                renderPositionBoard();


                return;
            }


            /* ==================================================
               ПРАВИЛЬНЫЙ ХОД
            ================================================== */

            setPositionResult(
                "✓ Правильно! Это лучший ход."
            );


            /*
             * Оставляем новую позицию
             * и блокируем доску.
             */

            positionLocked =
                true;


            renderPositionBoard();

        },

        450
    );
}

/* ============================================================
   ТЕКСТ РЕЗУЛЬТАТА ПОЗИЦИИ
============================================================ */

function setPositionResult(
    text
) {

    const element =
        document.getElementById(
            "positionResult"
        );

    if (element) {
        element.textContent =
            text || "";
    }
}


/* ============================================================
   ПРОВЕРКА ХОДА В ПОЗИЦИИ
============================================================ */

function checkPositionMove(
    mistake
) {

    if (
        !mistake
    ) {
        return;
    }

    const played =
        mistake.position_played_uci ??
        mistake.played_move ??
        mistake.played_uci;

    if (!played) {
        return;
    }

    const best =
        mistake.best_move_uci ??
        mistake.best_move ??
        mistake.best_uci;

    if (!best) {
        return;
    }

    if (
        played === best
    ) {

        setPositionResult(
            "✓ Это лучший ход."
        );

    } else {

        setPositionResult(
            `Ваш ход: ${played}. Лучший ход: ${best}.`
        );
    }
}


/* ============================================================
   КООРДИНАТЫ ПОЗИЦИИ
============================================================ */

function renderPositionCoordinates() {

    const element =
        document.getElementById(
            "positionCoordinates"
        );

    if (!element) {
        return;
    }

    element.innerHTML = "";

    const files =
        positionOrientation ===
        "white"
            ? FILES
            : [...FILES].reverse();

    const ranks =
        positionOrientation ===
        "white"
            ? [
                8,7,6,5,
                4,3,2,1
            ]
            : [
                1,2,3,4,
                5,6,7,8
            ];

    element.innerHTML = `
        <div class="position-files">
            ${files
                .map(
                    file =>
                        `<span>${file}</span>`
                )
                .join("")
            }
        </div>

        <div class="position-ranks">
            ${ranks
                .map(
                    rank =>
                        `<span>${rank}</span>`
                )
                .join("")
            }
        </div>
    `;
}


/* ============================================================
   ОТРИСОВКА ДОСКИ ПОЗИЦИИ
============================================================ */

function renderPositionBoard() {

    const boardElement =
        document.getElementById(
            "positionBoard"
        );

    if (
        !boardElement ||
        !positionBoardState
    ) {
        return;
    }

    boardElement.innerHTML = "";

    const boardSize =
        Math.min(
            window.innerWidth * 0.92,
            520
        );

    boardElement.style.width =
        `${boardSize}px`;

    boardElement.style.height =
        `${boardSize}px`;

    boardElement.style.display =
        "grid";

    boardElement.style.gridTemplateColumns =
        "repeat(8, 1fr)";

    boardElement.style.gridTemplateRows =
        "repeat(8, 1fr)";


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

            let realRow =
                row;

            let realCol =
                col;

            if (
                positionOrientation ===
                "black"
            ) {

                realRow =
                    7 - row;

                realCol =
                    7 - col;
            }


            const squareName =
                FILES[realCol] +
                (8 - realRow);


            const square =
                document.createElement(
                    "button"
                );

            square.type =
                "button";

            square.classList.add(
                "position-square"
            );


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


            square.dataset.square =
                squareName;


            if (
                positionSelectedSquare ===
                squareName
            ) {

                square.classList.add(
                    "position-selected"
                );
            }


            if (
                positionBestMoveShown &&
                positionScreen &&
                positionScreen.bestMove
            ) {

                const bestMove =
                    positionScreen.bestMove;

                if (
                    bestMove.from ===
                        squareName
                ) {

                    square.classList.add(
                        "best-move-from"
                    );
                }

                if (
                    bestMove.to ===
                        squareName
                ) {

                    square.classList.add(
                        "best-move-to"
                    );
                }
            }


            if (
                positionUserMove
            ) {

                if (
                    positionUserMove.from ===
                        squareName ||
                    positionUserMove.to ===
                        squareName
                ) {

                    square.classList.add(
                        "user-move"
                    );
                }
            }


            const piece =
                positionBoardState[
                    realRow
                ][
                    realCol
                ];


            if (piece) {

                const pieceElement =
                    document.createElement(
                        "img"
                    );

                pieceElement.classList.add(
                    "position-piece"
                );

                pieceElement.src =
                    `pieces/${piece.color}/${piece.type.charAt(0).toUpperCase() + piece.type.slice(1)}.svg?v=5`;

                pieceElement.onerror = () => {
                    console.error(
                        "Не удалось загрузить фигуру:",
                        pieceElement.src
                    );
                };

                pieceElement.alt =
                    `${piece.color} ${piece.type}`;

                pieceElement.draggable =
                    false;

                square.appendChild(
                    pieceElement
                );
            }


            square.addEventListener(
                "click",
                () =>
                    handlePositionSquareClick(
                        squareName
                    )
            );


            boardElement.appendChild(
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
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    const number =
        Number(value);

    if (
        Number.isNaN(number)
    ) {
        return String(value);
    }

    if (
        Math.abs(number) >= 100
    ) {

        return (
            number / 100
        ).toFixed(2);
    }

    return number.toFixed(2);
}


/* ============================================================
   ОЦЕНКА ПОЗИЦИИ
============================================================ */

function updatePositionEvaluation(
    mistake
) {

    const element =
        document.getElementById(
            "positionInfo"
        );

    if (!element) {
        return;
    }

    const before =
        mistake.evaluation_before ??
        mistake.before_score;

    const after =
        mistake.evaluation_after ??
        mistake.after_score;

    const loss =
        mistake.loss ??
        mistake.evaluation_loss;


    element.innerHTML = `

        <div>
            <strong>
                Сыграно:
            </strong>

            ${
                mistake.played_move_san ??
                mistake.played_san ??
                mistake.played_move ??
                "—"
            }
        </div>


        <div>
            <strong>
                Оценка до:
            </strong>

            ${formatPositionEvaluation(
                before
            )}
        </div>


        <div>
            <strong>
                Оценка после:
            </strong>

            ${formatPositionEvaluation(
                after
            )}
        </div>


        <div>
            <strong>
                Потеря:
            </strong>

            ${
                loss !== null &&
                loss !== undefined
                    ? loss
                    : "—"
            }
        </div>
    `;
}

/* ============================================================
   ПОКАЗ ПОЗИЦИИ ОШИБКИ
============================================================ */

function showMistakePosition(
    mistake
) {

    if (!mistake) {
        return;
    }

    createPositionScreen();

    positionScreen.currentMistake =
        mistake;
    
    const positionTitle =
        document.getElementById(
            "positionTitle"
        );

    if (positionTitle) {

        let mistakes = [];

        if (currentMistakeSource === "mistakes") {
            mistakes = myMistakesData;
        } else if (
            currentAnalysisData &&
            Array.isArray(currentAnalysisData.mistakes)
        ) {
            mistakes = currentAnalysisData.mistakes;
        }

        const index =
            mistakes.indexOf(mistake);

        if (index >= 0) {

            positionTitle.textContent =
                `Ошибка ${index + 1} из ${mistakes.length}`;

        } else {

            positionTitle.textContent =
                "Позиция ошибки";
        }
    }

    positionScreen.currentMistakeIndex =
        currentMistakeSource === "mistakes"
            ? myMistakesData.indexOf(mistake)
            : (
                currentAnalysisData?.mistakes
                    ? currentAnalysisData.mistakes.indexOf(mistake)
                    : 0
            );

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

    positionLocked =
        false;

    positionScreen.bestMove =
        null;


    /* Очень важно:
       скрываем ВСЕ остальные экраны */

    if (menuScreen) {
        menuScreen.classList.add(
            "hidden"
        );
    }

    if (gameScreen) {
        gameScreen.classList.add(
            "hidden"
        );
    }

    if (analysisScreen) {
        analysisScreen.classList.add(
            "hidden"
        );
    }

    if (mistakesScreen) {
        mistakesScreen.classList.add(
            "hidden"
        );
    }

    positionScreen.classList.remove(
        "hidden"
    );


    const fen =
        mistake.position_fen ??
        mistake.fen;


    if (!fen) {

        document.getElementById(
            "positionBoard"
        ).innerHTML = `
            <div class="position-error">
                Позиция для этой ошибки
                не найдена.
            </div>
        `;

        return;
    }


    positionBoardState =
        fenToBoard(
            fen
        );


    positionCastlingRights =
        String(fen)
            .split(" ")[2] ||
        "-";


    updatePositionEvaluation(
        mistake
    );


    const info =
        document.getElementById(
            "positionBestMoveInfo"
        );

    if (info) {

        info.textContent = "";
    }


    setPositionResult(
        "Попробуйте найти лучший ход."
    );


    renderPositionBoard();
}


/* ============================================================
   ПОКАЗ ЛУЧШЕГО ХОДА
============================================================ */

function showBestMove(
    mistake
) {

    if (!mistake) {
        return;
    }

    const bestMove =
        mistake.best_move_uci ??
        mistake.best_move ??
        mistake.best_uci;


    if (!bestMove) {

        setPositionResult(
            "Лучший ход для этой ошибки не найден."
        );

        return;
    }


    if (
        String(bestMove).length < 4
    ) {

        setPositionResult(
            `Некорректный лучший ход: ${bestMove}`
        );

        return;
    }


    const from =
        String(bestMove)
            .substring(
                0,
                2
            );

    const to =
        String(bestMove)
            .substring(
                2,
                4
            );


    positionScreen.bestMove = {
        from: from,
        to: to
    };


    positionBestMoveShown =
        true;


    /* Не показываем текст над доской */
    setPositionResult(
        ""
    );


    /* Показываем лучший ход только под доской */

    const info =
        document.getElementById(
            "positionBestMoveInfo"
        );

    if (info) {

        info.innerHTML =
            `
            <strong>
                Лучший ход:
            </strong>
            ${bestMove}
            `;
    }


    renderPositionBoard();
}

/* ============================================================
   УДАЛЕНИЕ ТЕКУЩЕЙ ОШИБКИ
============================================================ */

async function deleteCurrentMistake() {

    const mistake =
        positionScreen?.currentMistake;

    if (!mistake) {
        return;
    }

    const mistakeId =
        mistake.id ??
        mistake.mistake_id;

    if (!mistakeId) {

        setPositionResult(
            "Не удалось определить ID ошибки."
        );

        console.error(
            "У ошибки отсутствует id:",
            mistake
        );

        return;
    }


    const user =
        getTelegramUser();

    if (!user) {

        setPositionResult(
            "Telegram пользователь не определён."
        );

        return;
    }


    const confirmed =
        window.confirm(
            "Удалить эту ошибку?"
        );

    if (!confirmed) {
        return;
    }


    const deleteButton =
        document.getElementById(
            "deleteMistakeButton"
        );


    if (deleteButton) {

        deleteButton.disabled =
            true;

        deleteButton.textContent =
            "⏳ Удаляем...";
    }


    /*
     * Запоминаем позицию текущей ошибки
     * ДО удаления.
     */

    const currentIndex =
        myMistakesData.indexOf(
            mistake
        );


    try {

        const response =
            await fetch(
                `/mistakes/${mistakeId}`,
                {
                    method: "DELETE",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            telegram_user:
                                user
                        })
                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.ok
        ) {

            throw new Error(
                data.error ||
                "Не удалось удалить ошибку."
            );
        }


        /*
         * Удаляем ошибку из локального массива
         */

        myMistakesData =
            myMistakesData.filter(
                item =>
                    String(
                        item.id ??
                        item.mistake_id
                    ) !==
                    String(mistakeId)
            );


        /*
         * Если ошибок больше нет
         */

        if (
            myMistakesData.length === 0
        ) {

            positionScreen.classList.add(
                "hidden"
            );

            mistakesScreen.classList.remove(
                "hidden"
            );


            mistakesScreen.innerHTML = `

                <div class="analysis-empty">

                    <h2>
                        Мои ошибки
                    </h2>

                    <strong>
                        Ошибок больше нет.
                    </strong>

                    <p>
                        Все ошибки удалены.
                    </p>

                    <button
                        type="button"
                        id="backAfterDeleteButton"
                        class="menu-button"
                    >
                        ← Назад
                    </button>

                </div>

            `;


            document
                .getElementById(
                    "backAfterDeleteButton"
                )
                ?.addEventListener(
                    "click",
                    () => {

                        showScreen(
                            menuScreen
                        );
                    }
                );


            return;
        }


        /*
         * После удаления открываем следующую
         * ошибку.
         *
         * Если удалили последнюю,
         * открываем предыдущую.
         */

        const nextIndex =
            Math.min(
                Math.max(
                    currentIndex,
                    0
                ),
                myMistakesData.length - 1
            );


        currentMistakeSource =
            "mistakes";


        showMistakePosition(
            myMistakesData[
                nextIndex
            ]
        );


    } catch (error) {

        console.error(
            "Ошибка удаления:",
            error
        );


        setPositionResult(
            error.message ||
            "Не удалось удалить ошибку."
        );


        if (deleteButton) {

            deleteButton.disabled =
                false;

            deleteButton.textContent =
                "🗑 Удалить эту ошибку";
        }
    }
}

/* ============================================================
   НАВИГАЦИЯ МЕЖДУ ОШИБКАМИ
============================================================ */

function navigateMistake(
    direction
) {

    let mistakes = [];


    if (
        currentMistakeSource ===
        "mistakes"
    ) {

        mistakes =
            myMistakesData;

    } else if (
        currentAnalysisData &&
        Array.isArray(
            currentAnalysisData.mistakes
        )
    ) {

        mistakes =
            currentAnalysisData.mistakes;
    }


    if (
        !mistakes.length
    ) {
        return;
    }


    const current =
        positionScreen
            ?.currentMistake;


    let currentIndex =
        mistakes.indexOf(
            current
        );


    if (
        currentIndex < 0
    ) {

        currentIndex = 0;
    }


    let newIndex =
        currentIndex +
        direction;


    if (
        newIndex < 0
    ) {

        newIndex =
            mistakes.length - 1;
    }


    if (
        newIndex >=
        mistakes.length
    ) {

        newIndex = 0;
    }


    showMistakePosition(
        mistakes[newIndex]
    );
}


/* ============================================================
   ЗАГРУЗКА МОИХ ОШИБОК
============================================================ */

async function loadMyMistakes() {

    if (!mistakesScreen) {
        return;
    }


    mistakesScreen.innerHTML = `
        <div class="loading">
            ⏳ Загружаем ваши ошибки...
        </div>
    `;


    try {

        const user =
            getTelegramUser();


        if (!user) {

            mistakesScreen.innerHTML = `
                <div class="analysis-empty">
                    Telegram пользователь
                    не определён.
                </div>
            `;

            return;
        }


        const response =
            await fetch(
                "/mistakes",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            telegram_user:
                                user
                        })
                }
            );


        const data =
            await response.json();


        console.log(
            "МОИ ОШИБКИ:",
            data
        );


        if (
            !response.ok ||
            !data.ok
        ) {

            mistakesScreen.innerHTML = `
                <div class="analysis-empty">
                    ${
                        data.error ||
                        "Не удалось загрузить ошибки."
                    }
                </div>
            `;

            return;
        }


        myMistakesData =
            (
                data.mistakes ||
                []
            ).map(
                mistake => ({

                    ...mistake,

                    position_fen:
                        mistake.position_fen ??
                        mistake.fen,

                    position_played_uci:
                        mistake.position_played_uci ??
                        mistake.played_move,

                    best_move_uci:
                        mistake.best_move_uci ??
                        mistake.best_move,

                    user_side:
                        mistake.user_side ??
                        (
                            String(
                                mistake.fen ||
                                ""
                            ).split(" ")[1] ===
                            "b"
                                ? "black"
                                : "white"
                        )
                })
            );


        if (myMistakesData.length === 0) {
            renderMyMistakes();
        } else {
            currentMistakeSource = "mistakes";
            showMistakePosition(myMistakesData[0]);
        }


    } catch (error) {

        console.error(
            "Ошибка загрузки моих ошибок:",
            error
        );


        mistakesScreen.innerHTML = `
            <div class="analysis-empty">
                Ошибка соединения
                с сервером.
            </div>
        `;
    }
}


/* ============================================================
   РЕНДЕР МОИХ ОШИБОК
============================================================ */

function renderMyMistakes() {

    if (!mistakesScreen) {
        return;
    }


    let html = "";


    html += `
        <div class="mistakes-header">

            <h2>
                Мои ошибки
            </h2>

            <p>
                Найдено ошибок:
                <strong>
                    ${myMistakesData.length}
                </strong>
            </p>

            <button
                type="button"
                id="backFromMistakesButtonInner"
                class="menu-button"
            >
                ← Назад
            </button>

        </div>
    `;


    if (
        myMistakesData.length === 0
    ) {

        html += `
            <div class="analysis-empty">

                <strong>
                    Ошибок пока нет.
                </strong>

                <p>
                    Сначала проанализируйте
                    несколько партий.
                </p>

            </div>
        `;

        mistakesScreen.innerHTML =
            html;


        const back =
            document.getElementById(
                "backFromMistakesButtonInner"
            );

        if (back) {

            back.addEventListener(
                "click",
                () => {

                    showScreen(
                        menuScreen
                    );
                }
            );
        }

        return;
    }


    html += `
        <div class="mistakes-list">
    `;


    myMistakesData.forEach(
        (
            mistake,
            index
        ) => {

            const moveNumber =
                mistake.move_number ??
                mistake.move ??
                "—";


            const played =
                mistake.played_move_san ??
                mistake.played_san ??
                mistake.played_move ??
                "—";


            const best =
                mistake.best_move_san ??
                mistake.best_san ??
                mistake.best_move ??
                "—";


            const loss =
                mistake.loss ??
                "—";

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
                            ${played}
                        </strong>
                    </div>


                    <div>
                        Лучший ход:
                        <strong>
                            ${best}
                        </strong>
                    </div>


                    <div>
                        Потеря:
                        <strong>
                            ${loss}
                        </strong>
                    </div>

                    <button
                        type="button"
                        class="show-my-mistake-button"
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


    mistakesScreen.innerHTML =
        html;


    const back =
        document.getElementById(
            "backFromMistakesButtonInner"
        );


    if (back) {

        back.addEventListener(
            "click",
            () => {

                showScreen(
                    menuScreen
                );
            }
        );
    }


    const buttons =
        mistakesScreen.querySelectorAll(
            ".show-my-mistake-button"
        );


    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    const index =
                        Number(
                            button.dataset
                                .mistakeIndex
                        );


                    const mistake =
                        myMistakesData[
                            index
                        ];


                    if (!mistake) {

                        alert(
                            "Ошибка: позиция не найдена."
                        );

                        return;
                    }


                    console.log(
                        "ОТКРЫВАЕМ ОШИБКУ:",
                        mistake
                    );


                    currentMistakeSource =
                        "mistakes";


                    showMistakePosition(
                        mistake
                    );
                }
            );
        }
    );
}


/* ============================================================
   АНАЛИЗ PGN
============================================================ */

if (analyzeButton) {

    analyzeButton.addEventListener(
        "click",
        async () => {

            const pgn =
                pgnInput
                    ?.value
                    ?.trim() ||
                "";


            if (!pgn) {

                if (analysisMessage) {

                    analysisMessage.textContent =
                        "Сначала вставьте PGN партии.";
                }

                if (analysisResult) {

                    analysisResult.classList.add(
                        "hidden"
                    );
                }

                return;
            }


            if (analysisMessage) {

                analysisMessage.textContent =
                    "⏳ Анализируем партию...";
            }


            if (analysisResult) {

                analysisResult.classList.add(
                    "hidden"
                );
            }


            try {

                const user =
                    getTelegramUser();


                const response =
                    await fetch(
                        "/analyze",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({

                                    pgn:
                                        pgn,

                                    telegram_user:
                                        user

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

                    if (analysisMessage) {

                        analysisMessage.textContent =
                            data.error ||
                            "Не удалось проанализировать партию.";
                    }

                    return;
                }


                currentAnalysisData =
                    data;


                currentMistakeSource =
                    "analysis";


                let html = "";


                /* ------------------------------------------------
                   ОСНОВНАЯ ИНФОРМАЦИЯ
                ------------------------------------------------ */

                html += `
                    <div
                        class="analysis-summary"
                    >

                        <h3>
                            Результат анализа
                        </h3>

                        <p>
                            <strong>
                                Белые:
                            </strong>
                            ${
                                data.white ||
                                "—"
                            }
                        </p>

                        <p>
                            <strong>
                                Чёрные:
                            </strong>
                            ${
                                data.black ||
                                "—"
                            }
                        </p>

                        <p>
                            <strong>
                                Результат:
                            </strong>
                            ${
                                data.result ||
                                "—"
                            }
                        </p>

                        <p>
                            <strong>
                                Точность:
                            </strong>
                            ${
                                data.accuracy ??
                                "—"
                            }
                        </p>

                    </div>
                `;


                /* ------------------------------------------------
                   ОШИБКИ
                ------------------------------------------------ */

                if (
                    !data.mistakes ||
                    data.mistakes.length === 0
                ) {

                    html += `
                        <div
                            class="analysis-empty"
                        >

                            <strong>
                                Ошибок не найдено.
                            </strong>

                        </div>
                    `;

                } else {

                    html += `
                        <div
                            class="mistakes-list"
                        >

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
                                mistake.played_move_san ??
                                mistake.played_san ??
                                mistake.move_san ??
                                "—";


                            const bestSan =
                                mistake.best_move_san ??
                                mistake.best_san ??
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

                                    <div>
                                        Лучший ход:
                                        <strong>
                                            ${bestSan}
                                        </strong>
                                    </div>

                                    ${
                                        loss !== null
                                            ? `
                                                <div>
                                                    Потеря:
                                                    <strong>
                                                        ${loss}
                                                    </strong>
                                                </div>
                                            `
                                            : ""
                                    }

                                    <button
                                        type="button"
                                        class="show-analysis-mistake-button"
                                        data-analysis-mistake-index="${index}"
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


                /* ------------------------------------------------
                   СТАТИСТИКА
                ------------------------------------------------ */

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

                            <pre>${JSON.stringify(
                                data.statistics,
                                null,
                                2
                            )}</pre>

                        </div>
                    `;
                }


                if (analysisResult) {

                    analysisResult.innerHTML =
                        html;

                    analysisResult.classList.remove(
                        "hidden"
                    );
                }


                /* ------------------------------------------------
                   КНОПКИ ПОЗИЦИЙ
                ------------------------------------------------ */

                const analysisMistakeButtons =
                    analysisResult
                        ?.querySelectorAll(
                            ".show-analysis-mistake-button"
                        );


                if (
                    analysisMistakeButtons
                ) {

                    analysisMistakeButtons.forEach(
                        button => {

                            button.addEventListener(
                                "click",
                                () => {

                                    const index =
                                        Number(
                                            button.dataset
                                                .analysisMistakeIndex
                                        );


                                    const mistake =
                                        data.mistakes[
                                            index
                                        ];


                                    if (
                                        !mistake
                                    ) {
                                        return;
                                    }


                                    currentMistakeSource =
                                        "analysis";


                                    showMistakePosition(
                                        mistake
                                    );
                                }
                            );
                        }
                    );
                }


                if (analysisMessage) {

                    analysisMessage.textContent =
                        "✅ Анализ завершён.";
                }


            } catch (error) {

                console.error(
                    "Ошибка анализа:",
                    error
                );


                if (analysisMessage) {

                    analysisMessage.textContent =
                        "Ошибка соединения с сервером.";
                }
            }
        }
    );
}


/* ============================================================
   ИЗМЕНЕНИЕ РАЗМЕРА ДОСКИ ПОЗИЦИИ
============================================================ */

window.addEventListener(
    "resize",
    () => {

        if (
            positionScreen &&
            !positionScreen.classList.contains(
                "hidden"
            ) &&
            positionBoardState
        ) {

            renderPositionBoard();
        }
    }
);


/* ============================================================
   ЗАПУСК
============================================================ */

showScreen(
    menuScreen
);