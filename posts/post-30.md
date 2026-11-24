---
date: 2026-11-24T07:08:56+00:00
slides: 5
style: findoc
---

# Два транша по 6 млн на остаток 10 млн:

---
marp: true
theme: fin-doc
size: carousel
lang: ru
title: "Два транша по 6 млн на остаток 10 млн:"
style: |
  section .slide {font-family:Arial,sans-serif}
  section .slide h3, section .slide .stat-card b, section .slide .cta-word {font-family:Georgia,'Liberation Serif',serif}
  section .slide .content {position:absolute;top:85px;left:18px;right:18px;bottom:auto;display:flex;gap:12px;justify-content:flex-start}
  section .slide .kicker {font:700 10px/1.2 Arial,sans-serif;letter-spacing:0}
  section .slide h3 {font-size:23px;line-height:1.08;letter-spacing:-.025em;margin:0}
  section .slide.dark h3.hero {font-size:28px}
  section .slide .content p,section .slide .tl-item {font:400 12.3px/1.22 Arial,sans-serif}
  section .slide .tl-item {padding:7px 0;gap:9px}
  section .slide .idx {font-size:10px;min-width:21px}
  section .slide .cta-word {font-size:17px;padding:6px 11px}
  section .slide .foot {margin-top:auto}
  section .slide .stat-card b {font-size:24px}
  section .slide .track {height:6px}
---

<article class="slide dark">
<div class="head"><span>@fin_doc_</span><span>01/05</span></div>
<div class="content">
<div class="kicker">Кредитный лимит</div>
<h3 class="hero">Два транша по 6 млн на остаток 10 млн:</h3>
<p>Почему каждая заявка укладывается в лимит, а вместе они превышают его на 2 млн?</p>
<div>
<div class="bar-row">
<div class="pair"><span>Доступно</span><b>10 млн</b></div>
<div class="track" style="background:#354459"><i class="fill" style="width:83.333%;background:#cbd3de"></i></div></div>
<div class="bar-row">
<div class="pair"><span>Запрошено</span><b>12 млн</b></div>
<div class="track" style="background:#354459"><i class="fill" style="width:100%;background:#416fdf"></i></div></div></div></div>
<div class="foot"><span></span><span>Листай →</span></div>
</article>

---

<article class="slide">
<div class="head"><span>@fin_doc_</span><span>02/05</span></div>
<div class="content">
<div class="kicker">Параллельные заявки</div>
<h3>Как один остаток посчитали дважды?</h3>
<div>
<div class="tl-item"><span class="idx">01</span>
<div>Первый менеджер запрашивает 6 млн. Система видит свободные 10 млн.</div></div>
<div class="tl-item"><span class="idx">02</span>
<div>До записи резерва второй менеджер запрашивает ещё 6 млн. Остаток на экране тот же.</div></div>
<div class="tl-item"><span class="idx">03</span>
<div>Обе проверки проходят. На доступные 10 млн приходится 12 млн заявок.</div></div></div></div>
<div class="foot"><span></span><span>Листай →</span></div>
</article>

---

<article class="slide">
<div class="head"><span>@fin_doc_</span><span>03/05</span></div>
<div class="content">
<div class="kicker">Резервирование</div>
<h3>Сколько доступно после первого резерва?</h3>
<div class="grid">
<div class="stat-card"><b >6 млн</b>Занял первый транш</div>
<div class="stat-card"><b style="color:#245bd6">4 млн</b>Осталось в лимите</div></div>
<p>Проверяйте остаток и ставьте резерв одной операцией. Тогда для второй заявки доступны 4 млн. На транш в 6 млн их уже не хватит.</p></div>
<div class="foot"><span></span><span>Листай →</span></div>
</article>

---

<article class="slide">
<div class="head"><span>@fin_doc_</span><span>04/05</span></div>
<div class="content">
<div class="kicker">Снятие резерва</div>
<h3>Когда освободить 6 млн?</h3>
<p>Если выдача не состоялась, сумма может остаться занятой. Предусмотрите два случая.</p>
<div>
<div class="tl-item"><span class="idx">01</span>
<div>Клиент отказался от транша. Снимите резерв при закрытии заявки.</div></div>
<div class="tl-item"><span class="idx">02</span>
<div>Срок резерва истёк. Освободите сумму, если выдача ещё не началась.</div></div></div></div>
<div class="foot"><span></span><span>Листай →</span></div>
</article>

---

<article class="slide">
<div class="head"><span>@fin_doc_</span><span>05/05</span></div>
<div class="content">
<div class="kicker">Проверка перед запуском</div>
<h3>Что покажет ваш конвейер?</h3>
<p>Отправьте одновременно две заявки по 6 млн при остатке 10 млн. Получит ли резерв только одна из них?</p>
<div class="cta-word">Подписаться</div>
<p>В @fin_doc_ разбираем, как проверить резерв, отмену заявки и доступный лимит до первой выдачи.</p></div>
</article>
