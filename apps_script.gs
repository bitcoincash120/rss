function colByHeader(sheet, names, fallback) {
  const last = Math.max(sheet.getLastColumn(), 1);
  const headers = sheet.getRange(1, 1, 1, last).getValues()[0];
  const wanted = names.map(function (name) {
    return String(name).trim().toLowerCase();
  });
  for (var i = 0; i < headers.length; i++) {
    if (wanted.indexOf(String(headers[i]).trim().toLowerCase()) >= 0) return i + 1;
  }
  return fallback || 0;
}

function markImported(params) {
  params = params || {};
  const row = Number(params.row);
  const url = String(params.url || "");
  const status = String(params.status || "импортирован");
  if (!row || row < 2) {
    return { ok: false, error: "Нужен номер строки" };
  }
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const statusCol = colByHeader(sheet, ["статус", "status"], 0);
  const linkCol = colByHeader(sheet, ["ссылка", "link", "url", "пост"], 0);
  if (!statusCol || !linkCol) {
    return { ok: false, error: "Нет колонок Статус и Ссылка" };
  }
  sheet.getRange(row, statusCol).setValue(status);
  if (url) sheet.getRange(row, linkCol).setValue(url);
  return {
    ok: true,
    row: row,
    status: status,
    url: url,
    statusCol: statusCol,
    linkCol: linkCol,
  };
}

function doGet(e) {
  const params = (e && e.parameter) || {};
  const payload = params.action === "reshape" ? reshapeLayout() : markImported(params);
  const body = JSON.stringify(payload);
  const cb = params.callback;
  if (cb) {
    return ContentService.createTextOutput(cb + "(" + body + ")").setMimeType(
      ContentService.MimeType.JAVASCRIPT
    );
  }
  return ContentService.createTextOutput(body).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const params = (e && e.parameter) || {};
  if (e && e.postData && e.postData.contents) {
    try {
      const json = JSON.parse(e.postData.contents);
      for (const key in json) params[key] = json[key];
    } catch (err) {}
  }
  const payload = params.action === "reshape" ? reshapeLayout() : markImported(params);
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function padRow(values) {
  const row = values.slice();
  while (row.length < 13) row.push("");
  return row.slice(0, 13);
}

function seedBankingArticles() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const header = [
    "Статус",
    "Ссылка",
    "Заголовок",
    "Карточка 1",
    "Карточка 2",
    "Карточка 3",
    "Карточка 4",
    "Карточка 5",
    "Карточка 6",
    "Карточка 7",
    "Карточка 8",
    "Карточка 9",
    "Карточка 10",
  ];
  const rows = [
    header,
    padRow([
      "",
      "",
      "Платежи больше не ждут ручной сверки",
      "Робот сверяет входящие переводы за минуты и сразу готовит проводку.",
      "Несовпадение реквизитов останавливает платёж до ошибочного счёта.",
      "Операционист видит только исключения, а не тысячу одинаковых строк.",
    ]),
    padRow([
      "",
      "",
      "Кредитное решение собирается само",
      "Скоринг, бюро и внутренние лимиты складываются в одно решение без перекладывания файлов.",
      "Аналитик подключается, когда модель сомневается, а не на каждом заявлении.",
    ]),
    padRow([
      "",
      "",
      "Клиент проходит KYC без очереди в отделении",
      "Паспорт, селфи и анкета проверяются автоматически, пока клиент ещё в приложении.",
      "Совпадения в списках и повторные документы всплывают сразу, а не через неделю.",
      "Комплаенс разбирает только спорные кейсы, а не весь поток анкет.",
    ]),
    padRow([
      "",
      "",
      "Чат-бот закрывает типовые запросы до оператора",
      "Баланс, справки и блокировка карты уходят в сценарий, а не в очередь колл-центра.",
      "Сложный кейс вместе с историей диалога передаётся человеку без повторных вопросов.",
      "В пиковые часы бот держит нагрузку, операторы не тонут в «какой у меня лимит».",
      "Банк видит, какие формулировки путают клиентов, и правит сценарий в тот же день.",
    ]),
    padRow([
      "",
      "",
      "Документы читает машина, а не стажёр",
      "OCR разбирает платёжки, уставы и сканы быстрее, чем их успевают распечатать.",
      "Поля уходят сразу в карточку сделки, без ручного набора и опечаток в ИНН.",
      "Сомнительный скан попадает человеку с подсветкой полей, а не с пустой формой.",
    ]),
    padRow([
      "",
      "",
      "Антифрод смотрит операции в момент, а не утром",
      "Правила и модели оценивают перевод, пока клиент ещё держит телефон.",
      "Ложное срабатывание снимается одним экраном, а не цепочкой писем между отделами.",
    ]),
    padRow([
      "",
      "",
      "Отчётность больше не собирается из десяти Excel",
      "Проводки, лимиты и комиссии стекаются в витрину без ночных выгрузок.",
      "Контролёр видит расхождение в тот же день, а не в пятницу перед регулятором.",
      "Филиалы перестают присылать файл «последняя_версия_final2».",
    ]),
    padRow([
      "",
      "",
      "Кредитный конвейер ведёт заявку сам",
      "От анкеты до выдачи заявка не теряется между почтой, чатом и папкой на диске.",
      "Каждый этап ставит отметку: документы, решение, договор, зачисление.",
      "Клиент видит статус в приложении, менеджер — только то, что требует подписи.",
      "Узкое место видно по очереди задач, а не по жалобам «где моя заявка».",
    ]),
  ];
  sheet.clear();
  sheet.getRange(1, 1, rows.length, header.length).setValues(rows);
  sheet.getRange(1, 1, 1, header.length).setFontWeight("bold");
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  return { ok: true, rows: rows.length - 1, cols: header.length };
}

function reshapeLayout() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const lastRow = Math.max(sheet.getLastRow(), 1);
  const lastCol = Math.max(sheet.getLastColumn(), 1);
  const values = sheet.getRange(1, 1, lastRow, lastCol).getValues();
  const headers = values[0].map(function (h) {
    return String(h || "").trim().toLowerCase().replace(/\s+/g, " ");
  });

  function idx(names, fallback) {
    for (var i = 0; i < names.length; i++) {
      var found = headers.indexOf(String(names[i]).toLowerCase());
      if (found >= 0) return found;
    }
    return fallback;
  }

  const CARD_COUNT = 10;
  const statusI = idx(["статус", "status"], -1);
  const linkI = idx(["ссылка", "link", "url", "пост"], -1);
  const titleI = idx(["заголовок", "title", "headline", "тема"], -1);
  const cardIs = {};
  headers.forEach(function (h, i) {
    var match = String(h).match(/^(карточка|card|текст|slide)\s*(\d+)$/);
    if (match) cardIs[Number(match[2])] = i;
  });
  const extra = Object.keys(cardIs)
    .map(Number)
    .filter(function (n) {
      return n > CARD_COUNT;
    })
    .sort(function (a, b) {
      return a - b;
    });

  const headerRow = ["Статус", "Ссылка", "Заголовок"];
  for (var n = 1; n <= CARD_COUNT; n++) headerRow.push("Карточка " + n);
  extra.forEach(function (n) {
    headerRow.push("Карточка " + n);
  });

  const out = [headerRow];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var next = [
      statusI >= 0 ? row[statusI] : "",
      linkI >= 0 ? row[linkI] : "",
      titleI >= 0 ? row[titleI] : "",
    ];
    for (var c = 1; c <= CARD_COUNT; c++) {
      next.push(cardIs[c] != null ? row[cardIs[c]] : "");
    }
    extra.forEach(function (n) {
      next.push(row[cardIs[n]]);
    });
    var empty = next.every(function (cell) {
      return String(cell || "").trim() === "";
    });
    if (!empty) out.push(next);
  }

  sheet.clear();
  sheet.getRange(1, 1, out.length, headerRow.length).setValues(out);
  sheet.getRange(1, 1, 1, headerRow.length).setFontWeight("bold");
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  return { ok: true, rows: out.length, cols: headerRow.length };
}
