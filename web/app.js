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

console.log(
    "========== TELEGRAM WEBAPP DEBUG =========="
);

console.log(
    "Telegram =",
    window.Telegram
);

console.log(
    "tg =",
    tg
);

console.log(
    "tg.initData =",
    tg?.initData
);

console.log(
    "tg.initDataUnsafe =",
    tg?.initDataUnsafe
);

console.log(
    "tg.initDataUnsafe.user =",
    tg?.initDataUnsafe?.user
);

console.log(
    "============================================"
);


/* ============================================================
   ЭКРАНЫ
============================================================ */

const menuScreen =
    document.getElementById(
        "menuScreen"
    );

const gameScreen =
    document.getElementById(
        "gameScreen"
    );

const sideSelection =
    document.getElementById(
        "sideSelection"
    );

const playWhiteButton =
    document.getElementById(
        "playWhiteButton"
    );

const playBlackButton =
    document.getElementById(
        "playBlackButton"
    );

const openingSelection =
    document.getElementById(
        "openingSelection"
    );

const backToSideSelectionButton =
    document.getElementById(
        "backToSideSelectionButton"
    );

const openingButtons =
    document.querySelectorAll(
        ".opening-button"
    );

const analysisScreen =
    document.getElementById(
        "analysisScreen"
    );

const mistakesScreen =
    document.getElementById(
        "mistakesScreen"
    );


/* ============================================================
   КНОПКИ МЕНЮ
============================================================ */

const playButton =
    document.getElementById(
        "playButton"
    );

const analysisButton =
    document.getElementById(
        "analysisButton"
    );

const mistakesButton =
    document.getElementById(
        "mistakesButton"
    );

const backFromGameButton =
    document.getElementById(
        "backFromGameButton"
    );

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
    document.getElementById(
        "board"
    );

const messageElement =
    document.getElementById(
        "message"
    );

const turnElement =
    document.getElementById(
        "turnText"
    );

const turnText =
    turnElement;

const hintButton =
    document.getElementById(
        "hintButton"
    );

const newGameButton =
    document.getElementById(
        "newGameButton"
    );


/* ============================================================
   АНАЛИЗ
============================================================ */

const pgnInput =
    document.getElementById(
        "pgnInput"
    );

const deepAnalysisButton =
    document.getElementById(
        "deepAnalysisButton"
    );

const generalAnalysisButton =
    document.getElementById(
        "generalAnalysisButton"
    );

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
   ВЫБРАННЫЙ ДЕБЮТ
============================================================ */

let selectedOpening = "none";


/* ============================================================
   СОСТОЯНИЕ АНАЛИЗА
============================================================ */

let currentAnalysisData = null;

let myMistakesData = [];

let currentMistakeSource =
    "analysis";


/* ============================================================
   СОСТОЯНИЕ ПОЗИЦИИ ОШИБКИ
============================================================ */

let positionScreen = null;

let positionBoardState = null;

let positionSelectedSquare = null;

let positionOrientation = "white";

let positionBestMoveShown = false;

let positionUserMove = null;

let positionWrongMove = false;

/* Реальный ошибочный ход из партии */
let positionMistakeMove = null;

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


        while (
            resultRow.length < 8
        ) {

            resultRow.push(null);
        }


        result.push(
            resultRow
        );
    }


    while (
        result.length < 8
    ) {

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


    /* ========================================================
       СОХРАНЯЕМ СТАРУЮ ФИГУРУ ДЛЯ АНИМАЦИИ
    ======================================================== */

    let animationPiece = null;

    let animationFrom = null;

    let animationTo = null;


    if (
        lastMove &&
        lastMove.from &&
        lastMove.to
    ) {

        const moveKey =
            `${lastMove.from}-${lastMove.to}`;


        if (
            renderBoard.lastAnimatedMoveKey !==
            moveKey
        ) {

            const oldSquare =
                boardElement.querySelector(
                    `.square[data-square="${lastMove.from}"]`
                );


            if (oldSquare) {

                const oldPiece =
                    oldSquare.querySelector(
                        ".piece-image"
                    );


                if (oldPiece) {

                    animationPiece =
                        oldPiece.cloneNode(true);

                    animationFrom =
                        oldSquare;

                    animationTo =
                        boardElement.querySelector(
                            `.square[data-square="${lastMove.to}"]`
                        );
                }
            }


            renderBoard.lastAnimatedMoveKey =
                moveKey;
        }
    }


    /* ========================================================
       ОЧИЩАЕМ ДОСКУ
    ======================================================== */

    boardElement.innerHTML = "";


    /* ========================================================
       ОРИЕНТАЦИЯ ДОСКИ
    ======================================================== */

    const rows =
        playerColor === "black"
            ? [
                7,
                6,
                5,
                4,
                3,
                2,
                1,
                0
            ]
            : [
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7
            ];


    const cols =
        playerColor === "black"
            ? [
                7,
                6,
                5,
                4,
                3,
                2,
                1,
                0
            ]
            : [
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7
            ];


    /* ========================================================
       СОЗДАЁМ ДОСКУ
    ======================================================== */

    for (
        let displayRow = 0;
        displayRow < 8;
        displayRow++
    ) {

        const row =
            rows[displayRow];


        for (
            let displayCol = 0;
            displayCol < 8;
            displayCol++
        ) {

            const col =
                cols[displayCol];


            const square =
                document.createElement(
                    "button"
                );


            square.type =
                "button";


            square.classList.add(
                "square"
            );


            /* =================================================
               ЦВЕТ КЛЕТКИ
            ================================================= */

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


            /* =================================================
               НАЗВАНИЕ КЛЕТКИ
            ================================================= */

            const squareName =
                FILES[col] +
                (8 - row);


            square.dataset.square =
                squareName;


            /* =================================================
               ПОСЛЕДНИЙ ХОД
            ================================================= */

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


            /* =================================================
               ВЫБРАННАЯ КЛЕТКА
            ================================================= */

            if (
                selectedSquare ===
                squareName
            ) {

                square.classList.add(
                    "selected"
                );
            }


            /* =================================================
               ФИГУРА
            ================================================= */

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


                /* =============================================
                   СКРЫВАЕМ НОВУЮ ФИГУРУ НА ВРЕМЯ АНИМАЦИИ
                ============================================= */

                if (
                    animationTo &&
                    squareName ===
                        lastMove.to
                ) {

                    pieceElement.classList.add(
                        "piece-animation-target"
                    );
                }


                square.appendChild(
                    pieceElement
                );
            }


            /* =================================================
               КЛИК
            ================================================= */

            square.addEventListener(
                "click",
                () => {

                    handleSquareClick(
                        squareName
                    );
                }
            );


            boardElement.appendChild(
                square
            );
        }
    }


    /* ========================================================
       ЗАПУСКАЕМ НАСТОЯЩУЮ АНИМАЦИЮ
    ======================================================== */

    if (
        animationPiece &&
        animationFrom &&
        animationTo
    ) {

        const newFromSquare =
            boardElement.querySelector(
                `.square[data-square="${lastMove.from}"]`
            );


        const newToSquare =
            boardElement.querySelector(
                `.square[data-square="${lastMove.to}"]`
            );


        if (
            newFromSquare &&
            newToSquare
        ) {

            const boardRect =
                boardElement.getBoundingClientRect();


            const fromRect =
                newFromSquare.getBoundingClientRect();


            const toRect =
                newToSquare.getBoundingClientRect();


            animationPiece.classList.add(
                "piece-moving"
            );


            animationPiece.style.position =
                "absolute";


            animationPiece.style.width =
                `${fromRect.width * 0.82}px`;


            animationPiece.style.height =
                `${fromRect.height * 0.82}px`;


            animationPiece.style.left =
                `${fromRect.left - boardRect.left + fromRect.width * 0.09}px`;


            animationPiece.style.top =
                `${fromRect.top - boardRect.top + fromRect.height * 0.09}px`;


            animationPiece.style.zIndex =
                "100";


            animationPiece.style.pointerEvents =
                "none";


            boardElement.appendChild(
                animationPiece
            );


            const deltaX =
                toRect.left -
                fromRect.left;


            const deltaY =
                toRect.top -
                fromRect.top;


            const animation =
                animationPiece.animate(
                    [
                        {
                            transform:
                                "translate(0px, 0px)"
                        },
                        {
                            transform:
                                `translate(${deltaX}px, ${deltaY}px)`
                        }
                    ],
                    {
                        duration: 220,
                        easing:
                            "cubic-bezier(0.22, 0.61, 0.36, 1)",
                        fill: "forwards"
                    }
                );


            animation.finished
                .then(
                    () => {

                        animationPiece.remove();


                        const target =
                            boardElement.querySelector(
                                `.square[data-square="${lastMove.to}"] .piece-animation-target`
                            );


                        if (target) {

                            target.classList.remove(
                                "piece-animation-target"
                            );
                        }
                    }
                )
                .catch(
                    () => {

                        if (
                            animationPiece &&
                            animationPiece.parentNode
                        ) {

                            animationPiece.remove();
                        }
                    }
                );
        }
    }


    /* ========================================================
       ЦИФРЫ
    ======================================================== */

    const rankLabels =
        document.querySelector(
            "#gameScreen .rank-labels"
        );


    if (rankLabels) {

        rankLabels.innerHTML = "";


        const ranks =
            playerColor === "black"
                ? [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8
                ]
                : [
                    8,
                    7,
                    6,
                    5,
                    4,
                    3,
                    2,
                    1
                ];


        ranks.forEach(
            rank => {

                const span =
                    document.createElement(
                        "span"
                    );


                span.textContent =
                    rank;


                rankLabels.appendChild(
                    span
                );
            }
        );
    }


    /* ========================================================
       БУКВЫ
    ======================================================== */

    const fileLabels =
        document.querySelector(
            "#gameScreen .file-labels"
        );


    if (fileLabels) {

        fileLabels.innerHTML = "";


        const files =
            playerColor === "black"
                ? [
                    "h",
                    "g",
                    "f",
                    "e",
                    "d",
                    "c",
                    "b",
                    "a"
                ]
                : [
                    "a",
                    "b",
                    "c",
                    "d",
                    "e",
                    "f",
                    "g",
                    "h"
                ];


        files.forEach(
            file => {

                const span =
                    document.createElement(
                        "span"
                    );


                span.textContent =
                    file;


                fileLabels.appendChild(
                    span
                );
            }
        );
    }
}


/* ============================================================
   НАЖАТИЕ НА КЛЕТКУ
============================================================ */

function handleSquareClick(
    squareName
) {

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
        getPiece(
            squareName
        );


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


    selectedSquare =
        null;


    makeMove(
        uciMove
    );
}


/* ============================================================
   ОТПРАВКА ХОДА
============================================================ */

async function makeMove(
    uciMove
) {

    /* ========================================================
       ХОД ИГРОКА
    ======================================================== */

    setMessage(
        "Ваш ход принят."
    );

    try {

        /* ====================================================
           ОТПРАВЛЯЕМ ХОД ИГРОКА
        ==================================================== */

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


        /* ====================================================
           ОШИБКА
        ==================================================== */

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


        /* ====================================================
           СОХРАНЯЕМ ХОД ИГРОКА
        ==================================================== */

        let playerMove =
            null;


        if (
            data.played_move
        ) {

            playerMove = {

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
        }


        /* ====================================================
           СОХРАНЯЕМ ФИНАЛЬНУЮ ПОЗИЦИЮ ПОСЛЕ ХОДА ИГРОКА
        ==================================================== */

        const playerBoard =
            fenToBoard(
                data.fen
            );


        /* ====================================================
           СРАЗУ ПОКАЗЫВАЕМ ХОД ИГРОКА
        ==================================================== */

        if (
            playerMove
        ) {

            lastMove =
                playerMove;

            board =
                JSON.parse(
                    JSON.stringify(
                        board
                    )
                );

            applyLocalMove(
                board,
                playerMove
            );

            renderBoard();

            await sleep(
                240
            );
        }


        /* ====================================================
           ЕСЛИ ИГРА ЗАКОНЧИЛАСЬ
        ==================================================== */

        if (
            !data.need_computer_move
        ) {

            board =
                playerBoard;

            playerTurn =
                Boolean(
                    data.player_turn
                );

            gameOver =
                Boolean(
                    data.game_over
                );

            renderBoard();


            if (
                data.is_best
            ) {

                setMessage(
                    `Отлично! ${data.played_san} — лучший ход.`
                );

            } else {

                setMessage(
                    `Вы сыграли ${data.played_san}.`
                );
            }


            updateTurnText();


            if (
                gameOver
            ) {

                setMessage(
                    `Партия закончена: ${data.status}`
                );

                showGameAnalysisButton();
            }

            return;
        }


        /* ====================================================
           ТЕПЕРЬ ХОДИТ КОМПЬЮТЕР
        ==================================================== */

        board =
            playerBoard;

        playerTurn =
            false;

        renderBoard();

        setMessage(
            "⏳ Ход компьютера..."
        );


        /* ====================================================
           ЗАПРАШИВАЕМ ХОД КОМПЬЮТЕРА
        ==================================================== */

        const computerResponse =
            await fetch(
                "/computer_move",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({})
                }
            );


        const computerData =
            await computerResponse.json();


        /* ====================================================
           ОШИБКА ХОДА КОМПЬЮТЕРА
        ==================================================== */

        if (
            !computerResponse.ok ||
            !computerData.success
        ) {

            setMessage(
                computerData.error ||
                "Ошибка хода компьютера."
            );

            return;
        }


        /* ====================================================
           СОХРАНЯЕМ ХОД КОМПЬЮТЕРА
        ==================================================== */

        let computerMove =
            null;


        if (
            computerData.computer_move
        ) {

            computerMove = {

                from:
                    computerData.computer_move.substring(
                        0,
                        2
                    ),

                to:
                    computerData.computer_move.substring(
                        2,
                        4
                    )
            };
        }


        /* ====================================================
           ПОКАЗЫВАЕМ ХОД КОМПЬЮТЕРА
        ==================================================== */

        if (
            computerMove
        ) {

            lastMove =
                computerMove;

            applyLocalMove(
                board,
                computerMove
            );

            renderBoard();

            await sleep(
                240
            );
        }


        /* ====================================================
           УСТАНАВЛИВАЕМ НАСТОЯЩУЮ ПОЗИЦИЮ С СЕРВЕРА
        ==================================================== */

        board =
            fenToBoard(
                computerData.fen
            );

        playerTurn =
            Boolean(
                computerData.player_turn
            );

        gameOver =
            Boolean(
                computerData.game_over
            );


        renderBoard();


        /* ====================================================
           РЕЗУЛЬТАТ
        ==================================================== */

        if (
            data.is_best
        ) {

            setMessage(
                `Отлично! ${data.played_san} — лучший ход.`
            );

        } else {

            setMessage(
                `Вы сыграли ${data.played_san}.`
            );
        }


        updateTurnText();


        /* ====================================================
           КОНЕЦ ИГРЫ
        ==================================================== */

        if (
            gameOver
        ) {

            setMessage(
                `Партия закончена: ${computerData.status}`
            );

            showGameAnalysisButton();

            return;
        }


        /* ====================================================
           СЛЕДУЮЩИЙ ХОД
        ==================================================== */

        setMessage(
            `Вы сыграли ${data.played_san}.`
        );

        updateTurnText();

    } catch (
        error
    ) {

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
   ОЖИДАНИЕ
============================================================ */

function sleep(ms) {

    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                ms
            )
    );
}


/* ============================================================
   ЛОКАЛЬНЫЙ ХОД
============================================================ */

function applyLocalMove(
    currentBoard,
    move
) {

    if (
        !move ||
        !move.from ||
        !move.to
    ) {

        return;
    }


    const fromCol =
        FILES.indexOf(
            move.from[0]
        );


    const fromRow =
        8 -
        Number(
            move.from[1]
        );


    const toCol =
        FILES.indexOf(
            move.to[0]
        );


    const toRow =
        8 -
        Number(
            move.to[1]
        );


    if (
        fromCol < 0 ||
        toCol < 0 ||
        fromRow < 0 ||
        fromRow > 7 ||
        toRow < 0 ||
        toRow > 7
    ) {

        return;
    }


    const piece =
        currentBoard[fromRow]?.[fromCol];


    if (!piece) {

        return;
    }


    currentBoard[toRow][toCol] =
        piece;


    currentBoard[fromRow][fromCol] =
        null;
}


/* ============================================================
   КНОПКА АНАЛИЗА ЗАКОНЧЕННОЙ ПАРТИИ
============================================================ */

function showGameAnalysisButton() {

    if (
        document.getElementById(
            "gameAnalysisButton"
        )
    ) {

        return;
    }


    const button =
        document.createElement(
            "button"
        );


    button.id =
        "gameAnalysisButton";


    button.textContent =
        "📊 Начать анализ";


    button.className =
        "main-button";


    button.addEventListener(
        "click",
        analyzeFinishedGame
    );


    if (
        messageElement
    ) {

        messageElement.parentNode.insertBefore(
            button,
            messageElement.nextSibling
        );
    }
}


/* ============================================================
   АНАЛИЗ ЗАКОНЧЕННОЙ ПАРТИИ
============================================================ */

async function analyzeFinishedGame() {

    const button =
        document.getElementById(
            "gameAnalysisButton"
        );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "⏳ Анализируем...";
    }


    setMessage(
        "⏳ Подготовка анализа..."
    );


    try {

        /* ----------------------------------------------------
           ПОЛУЧАЕМ PGN ЗАКОНЧЕННОЙ ПАРТИИ
        ---------------------------------------------------- */

        const pgnResponse =
            await fetch(
                "/game_pgn"
            );


        const pgnData =
            await pgnResponse.json();


        if (
            !pgnResponse.ok ||
            !pgnData.success
        ) {

            throw new Error(
                pgnData.error ||
                "Не удалось получить PGN."
            );
        }


        const pgn =
            pgnData.pgn;


        if (
            !pgn ||
            !pgn.trim()
        ) {

            throw new Error(
                "PGN партии пустой."
            );
        }


        /* ----------------------------------------------------
           ПОЛУЧАЕМ TELEGRAM USER
        ---------------------------------------------------- */

        const user =
            getTelegramUser();


        /* ----------------------------------------------------
           ЗАПУСКАЕМ ФОНОВЫЙ АНАЛИЗ
        ---------------------------------------------------- */

        setMessage(
            "⏳ Запускаем анализ..."
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


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.error ||
                "Не удалось запустить анализ."
            );
        }


        /* ----------------------------------------------------
           ПОЛУЧАЕМ ID ФОНОВОЙ ЗАДАЧИ
        ---------------------------------------------------- */

        const jobId =
            data.job_id;


        if (!jobId) {

            throw new Error(
                "Сервер не вернул ID задачи анализа."
            );
        }


        /* ----------------------------------------------------
           ОПРАШИВАЕМ ПРОГРЕСС
        ---------------------------------------------------- */

        let analysisFinished =
            false;


        while (!analysisFinished) {

            await new Promise(
                resolve =>
                    setTimeout(
                        resolve,
                        500
                    )
            );


            const progressResponse =
                await fetch(
                    `/analyze/progress/${jobId}`
                );


            const progressData =
                await progressResponse.json();

            console.log(
                "========== ANALYSIS PROGRESS =========="
            );

            console.log(
                "JOB ID:",
                jobId
            );

            console.log(
                "HTTP STATUS:",
                progressResponse.status
            );

            console.log(
                "PROGRESS DATA:",
                progressData
            );

            console.log(
                "STATUS:",
                progressData.status
            );

            console.log(
                "PROGRESS:",
                progressData.progress
            );

            console.log(
                "RESULT:",
                progressData.result
            );

            console.log(
                "========================================"
            );


            if (
                !progressResponse.ok ||
                !progressData.success
            ) {

                throw new Error(
                    progressData.error ||
                    "Не удалось получить прогресс анализа."
                );
            }


            /* ------------------------------------------------
               ПРОГРЕСС
            ------------------------------------------------ */

            const progress =
                Number(
                    progressData.progress
                );


            if (
                Number.isFinite(progress)
            ) {

                const safeProgress =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            Math.round(progress)
                        )
                    );


                if (button) {

                    button.textContent =
                        `⏳ Анализируем... ${safeProgress}%`;
                }


                setMessage(
                    `⏳ Анализ партии Stockfish... ${safeProgress}%`
                );
            }


            /* ------------------------------------------------
               АНАЛИЗ ЗАВЕРШЁН
            ------------------------------------------------ */

            if (
                progressData.status ===
                "completed"
            ) {

                analysisFinished =
                    true;


                const result =
                    progressData.result;


                if (!result) {

                    throw new Error(
                        "Сервер завершил анализ, но не вернул результат."
                    );
                }


                /* --------------------------------------------
                   СОХРАНЯЕМ НАСТОЯЩИЙ РЕЗУЛЬТАТ
                -------------------------------------------- */

                currentAnalysisData =
                    result;


                currentMistakeSource =
                    "analysis";


                const mistakes =
                    Array.isArray(
                        result.mistakes
                    )
                        ? result.mistakes
                        : [];


                /* --------------------------------------------
                   УБИРАЕМ КНОПКУ "НАЧАТЬ АНАЛИЗ"
                -------------------------------------------- */

                if (button) {

                    button.remove();
                }


                /* --------------------------------------------
                   ПОКАЗЫВАЕМ РЕЗУЛЬТАТ
                -------------------------------------------- */

                setMessage(
                    `✅ Анализ завершён. Найдено ошибок: ${mistakes.length}`
                );


                /* --------------------------------------------
                   ПОКАЗЫВАЕМ КНОПКУ "МОИ ОШИБКИ"
                -------------------------------------------- */

                showGameMistakesButton();


                break;
            }


            /* ------------------------------------------------
               ОШИБКА ФОНОВОЙ ЗАДАЧИ
            ------------------------------------------------ */

            if (
                progressData.status ===
                "error"
            ) {

                throw new Error(
                    progressData.error ||
                    "Ошибка фонового анализа."
                );
            }
        }


    } catch (error) {

        console.error(
            "Ошибка анализа партии:",
            error
        );


        setMessage(
            `❌ Ошибка анализа партии: ${error.message}`
        );


        if (button) {

            button.disabled =
                false;

            button.textContent =
                "📊 Начать анализ";
        }
    }
}




/* ============================================================
   КНОПКА "МОИ ОШИБКИ" ПОСЛЕ АНАЛИЗА
============================================================ */

function showGameMistakesButton() {

    if (
        document.getElementById(
            "gameMistakesButton"
        )
    ) {
        return;
    }


    const button =
        document.createElement(
            "button"
        );


    button.id =
        "gameMistakesButton";


    button.textContent =
        "♟ Мои ошибки";


    button.className =
        "main-button";


    button.addEventListener(
        "click",
        async () => {

            await loadMyMistakes();

        }
    );


    if (messageElement) {

        messageElement.parentNode.insertBefore(
            button,
            messageElement.nextSibling
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

    playButton.addEventListener("click", () => {

        showScreen(gameScreen);

        // Показываем выбор стороны
        sideSelection.classList.remove("hidden");

        // Скрываем выбор дебюта
        openingSelection.classList.add("hidden");

        // Скрываем саму шахматную доску
        document
            .querySelector("#gameScreen main")
            .classList.add("hidden");

        document
            .querySelector("#gameScreen .info")
            .classList.add("hidden");

        document
            .querySelector("#gameScreen .buttons")
            .classList.add("hidden");

        turnText.textContent =
            "Выберите сторону";
    });

}

// ============================================================
// ВЫБОР СТОРОНЫ
// ============================================================

playWhiteButton.addEventListener(
    "click",
    () => {

        playerColor = "white";

        sideSelection.classList.add(
            "hidden"
        );

        openingSelection.classList.remove(
            "hidden"
        );

        turnText.textContent =
            "Выберите дебют";
    }
);


playBlackButton.addEventListener(
    "click",
    () => {

        playerColor = "black";

        sideSelection.classList.add(
            "hidden"
        );

        openingSelection.classList.remove(
            "hidden"
        );

        turnText.textContent =
            "Выберите дебют";
    }
);

// ============================================================
// ВЫБОР ДЕБЮТА
// ============================================================

openingButtons.forEach(
    (button) => {

        button.addEventListener(
            "click",
            () => {

                // --------------------------------------------
                // Снимаем выбор со всех кнопок
                // --------------------------------------------

                openingButtons.forEach(
                    (item) => {
                        item.classList.remove(
                            "selected"
                        );
                    }
                );

                // --------------------------------------------
                // Выбираем текущую кнопку
                // --------------------------------------------

                button.classList.add(
                    "selected"
                );

                // --------------------------------------------
                // Сохраняем выбранный дебют
                // --------------------------------------------

                selectedOpening =
                    button.dataset.opening;

                console.log(
                    "Выбран дебют:",
                    selectedOpening
                );

                // --------------------------------------------
                // Сразу запускаем партию
                // --------------------------------------------

                startGame(
                    playerColor
                );
            }
        );

    }
);

async function startGame(color) {

    playerColor = color;

    selectedSquare = null;
    lastMove = null;
    gameOver = false;

    try {

        const response = await fetch(
            "/reset",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    player_color: color,
                    opening: selectedOpening
                })
            }
        );

        const data =
            await response.json();

        if (!data.success) {

            setMessage(
                data.error ||
                "Не удалось начать игру."
            );

            return;
        }

        // ---------------------------------------------
        // СКРЫВАЕМ ВЫБОР СТОРОНЫ
        // ---------------------------------------------

        sideSelection.classList.add(
            "hidden"
        );

        openingSelection.classList.add(
            "hidden"
        );
        document.querySelector(
            "#gameScreen main"
        ).classList.remove("hidden");

        document.querySelector(
            "#gameScreen .info"
        ).classList.remove("hidden");

        document.querySelector(
            "#gameScreen .buttons"
        ).classList.remove("hidden");

        // ---------------------------------------------
        // ЗАПИСЫВАЕМ ЦВЕТ ИГРОКА
        // ---------------------------------------------

        playerColor =
            data.player_color ||
            color;

        // ---------------------------------------------
        // ЗАГРУЖАЕМ FEN
        // ---------------------------------------------

        board =
            fenToBoard(data.fen);

        // ---------------------------------------------
        // СБРАСЫВАЕМ СОСТОЯНИЕ
        // ---------------------------------------------

        selectedSquare = null;
        lastMove = null;
        gameOver =
            data.game_over;

        // ---------------------------------------------
        // РИСУЕМ ДОСКУ
        // ---------------------------------------------

        renderBoard();

        // ---------------------------------------------
        // ТЕКСТ ХОДА
        // ---------------------------------------------

        if (data.game_over) {

            setMessage(
                `Партия закончена: ${data.status}`
            );

        } else if (data.player_turn) {

            turnText.textContent =
                "Ваш ход";

            setMessage(
                "Ваш ход"
            );

        } else {

            turnText.textContent =
                "Ход компьютера";

            setMessage(
                "Ход компьютера"
            );
        }

    } catch (error) {

        console.error(
            "Ошибка запуска игры:",
            error
        );

        setMessage(
            "Ошибка соединения с сервером."
        );
    }
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


        <!-- Только один блок кнопок -->

        <div class="position-buttons compact-buttons">

            <button
                type="button"
                id="showBestMoveButton"
                class="compact-action-button"
            >
                💡 Лучший ход
            </button>

            <button
                type="button"
                id="deleteMistakeButton"
                class="compact-action-button delete-mistake-button"
            >
                🗑 Удалить
            </button>

        </div>


        <!-- Навигация -->

        <div class="mistake-navigation compact-navigation">

            <button
                type="button"
                id="previousMistakeButton"
                class="navigation-arrow-button"
            >
                ←
            </button>

            <span
                id="mistakeCounter"
                class="mistake-counter"
            >
                1 / 1
            </span>

            <button
                type="button"
                id="nextMistakeButton"
                class="navigation-arrow-button"
            >
                →
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


    /* ========================================================
       ЛУЧШИЙ ХОД
    ======================================================== */

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


    /* ========================================================
       УДАЛИТЬ ОШИБКУ
    ======================================================== */

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


    /* ========================================================
       ПРЕДЫДУЩАЯ ОШИБКА
    ======================================================== */

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


    /* ========================================================
       СЛЕДУЮЩАЯ ОШИБКА
    ======================================================== */

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
   СЧЁТЧИК ОШИБОК
============================================================ */

function updateMistakeCounter() {

    const counter =
        document.getElementById(
            "mistakeCounter"
        );

    if (!counter) {
        return;
    }

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

    const current =
        positionScreen?.currentMistake;

    const index =
        mistakes.indexOf(
            current
        );

    if (
        index >= 0 &&
        mistakes.length > 0
    ) {

        counter.textContent =
            `${index + 1} / ${mistakes.length}`;

    } else {

        counter.textContent =
            `— / ${mistakes.length}`;
    }
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

        /* ====================================================
        РОКИРОВКА
        ==================================================== */

        if (
            !attackOnly &&
            absDr === 0 &&
            absDc === 2
        ) {

            const isWhite =
                piece.color === "white";

            const homeRow =
                isWhite
                    ? 7
                    : 0;

            /* Король должен находиться
            на начальной клетке */

            if (
                from.row !== homeRow ||
                from.col !== 4
            ) {
                return false;
            }

            /* -----------------------------------------------
            КОРОТКАЯ РОКИРОВКА
            e1-g1 / e8-g8
            ----------------------------------------------- */

            if (
                to.col === 6
            ) {

                const requiredRight =
                    isWhite ? "K" : "k";

                if (
                    !positionCastlingRights.includes(
                        requiredRight
                    )
                ) {
                    return false;
                }

                /* Между королём и ладьёй
                не должно быть фигур */

                if (
                    boardState[homeRow][5] ||
                    boardState[homeRow][6]
                ) {
                    return false;
                }

                /* На h1/h8 должна быть ладья */

                const rook =
                    boardState[homeRow][7];

                if (
                    !rook ||
                    rook.type !== "rook" ||
                    rook.color !== piece.color
                ) {
                    return false;
                }

                /* Король не может:
                - находиться под шахом
                - проходить через битое поле
                - оказаться на битом поле */

                const kingSquare =
                    isWhite ? "e1" : "e8";

                const middleSquare =
                    isWhite ? "f1" : "f8";

                const targetSquare =
                    isWhite ? "g1" : "g8";

                const enemyColor =
                    isWhite ? "black" : "white";

                if (
                    isSquareAttackedByColor(
                        boardState,
                        kingSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                if (
                    isSquareAttackedByColor(
                        boardState,
                        middleSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                if (
                    isSquareAttackedByColor(
                        boardState,
                        targetSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                return true;
            }


            /* -----------------------------------------------
            ДЛИННАЯ РОКИРОВКА
            e1-c1 / e8-c8
            ----------------------------------------------- */

            if (
                to.col === 2
            ) {

                const requiredRight =
                    isWhite ? "Q" : "q";

                if (
                    !positionCastlingRights.includes(
                        requiredRight
                    )
                ) {
                    return false;
                }

                /* Между королём и ладьёй
                не должно быть фигур */

                if (
                    boardState[homeRow][1] ||
                    boardState[homeRow][2] ||
                    boardState[homeRow][3]
                ) {
                    return false;
                }

                /* На a1/a8 должна быть ладья */

                const rook =
                    boardState[homeRow][0];

                if (
                    !rook ||
                    rook.type !== "rook" ||
                    rook.color !== piece.color
                ) {
                    return false;
                }

                /* Проверяем e, d и c */

                const kingSquare =
                    isWhite ? "e1" : "e8";

                const middleSquare =
                    isWhite ? "d1" : "d8";

                const targetSquare =
                    isWhite ? "c1" : "c8";

                const enemyColor =
                    isWhite ? "black" : "white";

                if (
                    isSquareAttackedByColor(
                        boardState,
                        kingSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                if (
                    isSquareAttackedByColor(
                        boardState,
                        middleSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                if (
                    isSquareAttackedByColor(
                        boardState,
                        targetSquare,
                        enemyColor
                    )
                ) {
                    return false;
                }

                return true;
            }


            /* Обычный ход короля */

            return false;
        }


        /* Обычный ход короля */

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
                * Показываем неправильный ход красным
                */

                positionWrongMove =
                    true;

                renderPositionBoard();

                /*
                * Через некоторое время
                * возвращаем исходную позицию
                */

                setTimeout(
                    () => {

                        positionBoardState =
                            oldBoard;

                        positionUserMove =
                            null;

                        positionWrongMove =
                            false;

                        renderPositionBoard();

                    },
                    800
                );

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

            /* ========================================================
            РЕАЛЬНЫЙ ОШИБОЧНЫЙ ХОД ИЗ ПАРТИИ
            ======================================================== */

            if (
                positionMistakeMove &&
                !positionBestMoveShown
            ) {

                if (
                    positionMistakeMove.from ===
                        squareName ||
                    positionMistakeMove.to ===
                        squareName
                ) {

                    square.classList.add(
                        "mistake-move"
                    );
                }
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

                    if (positionWrongMove) {

                        square.classList.add(
                            "wrong-move"
                        );

                    } else {

                        square.classList.add(
                            "user-move"
                        );
                    }
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

function formatPositionEvaluation(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    const pawns = number / 100;

    if (pawns > 0) {
        return "+" + pawns.toFixed(2);
    }

    return pawns.toFixed(2);
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
            
    updateMistakeCounter();

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

    positionWrongMove =
        false;

    /* ========================================================
    РЕАЛЬНЫЙ ОШИБОЧНЫЙ ХОД ИЗ ПАРТИИ
    ======================================================== */

    positionMistakeMove = null;

    const playedMoveUci =
        mistake.position_played_uci ??
        mistake.played_move_uci ??
        mistake.played_move ??
        mistake.played_uci;

    if (
        playedMoveUci &&
        String(playedMoveUci).length >= 4
    ) {

        const normalizedPlayedMove =
            String(playedMoveUci)
                .substring(0, 4)
                .toLowerCase();

        positionMistakeMove = {

            from:
                normalizedPlayedMove.substring(
                    0,
                    2
                ),

            to:
                normalizedPlayedMove.substring(
                    2,
                    4
                )
        };
    }

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


    /* --------------------------------------------------------
       БЛОКИРУЕМ КНОПКУ НА ВРЕМЯ УДАЛЕНИЯ
    -------------------------------------------------------- */

    if (deleteButton) {

        deleteButton.disabled =
            true;

        deleteButton.textContent =
            "⏳ Удаляем...";
    }


    /*
     * Запоминаем индекс текущей ошибки
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


        /* ----------------------------------------------------
           УДАЛЯЕМ ИЗ ЛОКАЛЬНОГО МАССИВА
        ---------------------------------------------------- */

        myMistakesData =
            myMistakesData.filter(
                item =>
                    String(
                        item.id ??
                        item.mistake_id
                    ) !==
                    String(mistakeId)
            );


        /* ----------------------------------------------------
           ЕСЛИ ОШИБОК БОЛЬШЕ НЕТ
        ---------------------------------------------------- */

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


        /* ----------------------------------------------------
           ОПРЕДЕЛЯЕМ СЛЕДУЮЩУЮ ОШИБКУ
        ---------------------------------------------------- */

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


        /*
         * Показываем следующую ошибку.
         * showMistakePosition() создаст
         * новую кнопку удаления.
         */

        showMistakePosition(
            myMistakesData[
                nextIndex
            ]
        );


        /* ----------------------------------------------------
           ДОПОЛНИТЕЛЬНО ГАРАНТИРУЕМ,
           ЧТО НОВАЯ КНОПКА АКТИВНА
        ---------------------------------------------------- */

        const newDeleteButton =
            document.getElementById(
                "deleteMistakeButton"
            );

        if (newDeleteButton) {

            newDeleteButton.disabled =
                false;

            newDeleteButton.textContent =
                "🗑 Удалить эту ошибку";
        }


    } catch (error) {

        console.error(
            "Ошибка удаления:",
            error
        );


        setPositionResult(
            error.message ||
            "Не удалось удалить ошибку."
        );


        /* ----------------------------------------------------
           ЕСЛИ УДАЛЕНИЕ НЕ УДАЛОСЬ —
           ВОЗВРАЩАЕМ КНОПКУ
        ---------------------------------------------------- */

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

            /*
            * Сначала создаём нормальный список ошибок.
            * Он будет скрыт при открытии позиции,
            * но останется готовым для кнопки "Назад".
            */
            renderMyMistakes();

            /*
            * Затем открываем первую ошибку.
            */
            showMistakePosition(
                myMistakesData[0]
            );
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

async function startPgnAnalysis(
    analysisMode
) {

    const pgn =
        pgnInput
            ?.value
            ?.trim() ||
        "";


    /* ========================================================
       ПРОВЕРЯЕМ PGN
    ======================================================== */

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


    /* ========================================================
       НАЗВАНИЕ РЕЖИМА
    ======================================================== */

    const modeText =
        analysisMode === "general"
            ? "Общий анализ"
            : "Глубокий анализ";


    const thresholdText =
        analysisMode === "general"
            ? "150 cp"
            : "40 cp";


    /* ========================================================
       НАЧАЛО
    ======================================================== */

    if (analysisMessage) {

        analysisMessage.textContent =
            `⏳ ${modeText}: запускаем анализ...`;
    }


    if (analysisResult) {

        analysisResult.classList.add(
            "hidden"
        );

        analysisResult.innerHTML =
            "";
    }


    try {

        const user =
            getTelegramUser();


        /* ====================================================
           ЗАПУСКАЕМ ФОНОВЫЙ АНАЛИЗ
        ==================================================== */

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
                                user,

                            analysis_mode:
                                analysisMode

                        })
                }
            );


        const data =
            await response.json();


        console.log(
            "========================================"
        );

        console.log(
            "ЗАПУСК АНАЛИЗА"
        );

        console.log(
            "Режим:",
            modeText
        );

        console.log(
            "Порог:",
            thresholdText
        );

        console.log(
            "Ответ сервера:",
            data
        );

        console.log(
            "========================================"
        );


        if (
            !response.ok ||
            !data.success
        ) {

            if (analysisMessage) {

                analysisMessage.textContent =
                    data.error ||
                    "Не удалось запустить анализ.";
            }

            return;
        }


        /* ====================================================
           ПОЛУЧАЕМ ID ЗАДАЧИ
        ==================================================== */

        const jobId =
            data.job_id;


        if (!jobId) {

            throw new Error(
                "Сервер не вернул ID задачи анализа."
            );
        }


        /* ====================================================
           ЖДЁМ ЗАВЕРШЕНИЯ
        ==================================================== */

        let result =
            null;

        let finished =
            false;


        while (
            !finished
        ) {

            await new Promise(
                resolve =>
                    setTimeout(
                        resolve,
                        500
                    )
            );


            const progressResponse =
                await fetch(
                    `/analyze/progress/${jobId}`
                );


            const progressData =
                await progressResponse.json();


            console.log(
                "Прогресс анализа:",
                progressData
            );


            if (
                !progressResponse.ok ||
                !progressData.success
            ) {

                throw new Error(
                    progressData.error ||
                    "Не удалось получить прогресс анализа."
                );
            }


            /* =================================================
               ПРОГРЕСС
            ================================================= */

            const progress =
                Number(
                    progressData.progress
                );


            if (
                Number.isFinite(progress)
            ) {

                const safeProgress =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            Math.round(
                                progress
                            )
                        )
                    );


                if (analysisMessage) {

                    analysisMessage.textContent =
                        `⏳ ${modeText} (${thresholdText})... ${safeProgress}%`;
                }
            }


            /* =================================================
               ЗАВЕРШЕНО
            ================================================= */

            if (
                progressData.status ===
                "completed"
            ) {

                result =
                    progressData.result;

                finished =
                    true;

                break;
            }


            /* =================================================
               ОШИБКА
            ================================================= */

            if (
                progressData.status ===
                "error"
            ) {

                throw new Error(
                    progressData.error ||
                    "Ошибка фонового анализа."
                );
            }
        }


        /* ====================================================
           ПРОВЕРЯЕМ РЕЗУЛЬТАТ
        ==================================================== */

        if (!result) {

            throw new Error(
                "Анализ завершён, но результат не получен."
            );
        }


        console.log(
            "Результат анализа:",
            result
        );


        /* ====================================================
           СОХРАНЯЕМ РЕЗУЛЬТАТ
        ==================================================== */

        currentAnalysisData =
            result;


        currentMistakeSource =
            "analysis";


        let html =
            "";


        /* ====================================================
           ОСНОВНАЯ ИНФОРМАЦИЯ
        ==================================================== */

        html += `
            <div
                class="analysis-summary"
            >

                <h3>
                    ${modeText}
                </h3>

                <p>
                    <strong>
                        Порог ошибок:
                    </strong>
                    ${thresholdText}
                </p>

                <p>
                    <strong>
                        Белые:
                    </strong>
                    ${
                        result.white ||
                        "—"
                    }
                </p>

                <p>
                    <strong>
                        Чёрные:
                    </strong>
                    ${
                        result.black ||
                        "—"
                    }
                </p>

                <p>
                    <strong>
                        Результат:
                    </strong>
                    ${
                        result.result ||
                        "—"
                    }
                </p>

                <p>
                    <strong>
                        Точность:
                    </strong>
                    ${
                        result.accuracy ??
                        "—"
                    }
                </p>

            </div>
        `;


        /* ====================================================
           ОШИБКИ
        ==================================================== */

        if (
            !result.mistakes ||
            result.mistakes.length === 0
        ) {

            html += `
                <div
                    class="analysis-empty"
                >

                    <strong>
                        Ошибок не найдено.
                    </strong>

                    <p>
                        В этом режиме не найдено
                        ошибок с потерей
                        от ${thresholdText}.
                    </p>

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


            result.mistakes.forEach(
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
                        mistake.best_move ??
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


        /* ====================================================
           СТАТИСТИКА
        ==================================================== */

        if (
            result.statistics
        ) {

            html += `
                <div
                    class="analysis-statistics"
                >

                    <h3>
                        Статистика
                    </h3>

                    <pre>${JSON.stringify(
                        result.statistics,
                        null,
                        2
                    )}</pre>

                </div>
            `;
        }


        /* ====================================================
           ПОКАЗЫВАЕМ РЕЗУЛЬТАТ
        ==================================================== */

        if (analysisResult) {

            analysisResult.innerHTML =
                html;

            analysisResult.classList.remove(
                "hidden"
            );
        }


        /* ====================================================
           КНОПКИ "ПОКАЗАТЬ ПОЗИЦИЮ"
        ==================================================== */

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
                                result.mistakes[
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


        /* ====================================================
           ЗАВЕРШЕНИЕ
        ==================================================== */

        if (analysisMessage) {

            analysisMessage.textContent =
                `✅ ${modeText} завершён. Найдено ошибок: ${
                    result.mistakes
                        ?.length || 0
                }`;
        }

    } catch (error) {

        console.error(
            "Ошибка анализа:",
            error
        );


        if (analysisMessage) {

            analysisMessage.textContent =
                `❌ Ошибка анализа: ${error.message}`;
        }
    }
}


/* ============================================================
   КНОПКА — ГЛУБОКИЙ АНАЛИЗ
============================================================ */

if (
    deepAnalysisButton
) {

    deepAnalysisButton.addEventListener(
        "click",
        () => {

            startPgnAnalysis(
                "deep"
            );

        }
    );
}


/* ============================================================
   КНОПКА — ОБЩИЙ АНАЛИЗ
============================================================ */

if (
    generalAnalysisButton
) {

    generalAnalysisButton.addEventListener(
        "click",
        () => {

            startPgnAnalysis(
                "general"
            );

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