/* All API numbers are parsed as decimal strings before JavaScript can round them. */
'use strict';
const words = {
 en: {dashboard:'⌂ Dashboard',transactions:'⇄ Transactions',statistics:'⌁ Statistics',logout:'Log out',welcomeBack:'✦ Welcome back,',greeting:'Welcome back,',subtitle:"Let's track your finances today.",loading:'Loading your finances…',balance:'Total Balance',income:'Income',expenses:'Expenses',allTime:'All time',history:'Balance history',historyHelp:'Daily closing balance · all transactions',transactionsTitle:'Transactions',add:'Add',quickActions:'⚡ Quick Actions',addIncome:'Add income +',addExpense:'Add expense −',viewStatistics:'View statistics',addTransaction:'Add transaction',editTransaction:'Edit transaction',type:'Type',amount:'Amount (₸)',category:'Category (optional)',description:'Description (optional)',date:'Date',save:'Save transaction',signIn:'Welcome back',signInHelp:'Sign in to your personal finances.',signUp:'Create your account',signUpHelp:'Start tracking your finances today.',usernameLabel:'Username',passwordLabel:'Password',login:'Sign in',register:'Create account',noAccount:'New here?',haveAccount:'Already have an account?',empty:'No transactions yet. Add your first one to get started.',chartEmpty:'Your balance history will appear here after your first transaction.',edit:'Edit',delete:'Delete',deleteConfirm:'Delete this transaction? This cannot be undone.',invalidAmount:'Enter a whole number between 1 and 9223372036854775807.',invalidDate:'Choose a valid date.',invalidLogin:'Use 3–32 letters, numbers or underscores for your username.',invalidPassword:'Password must contain 12–256 characters.',failed:'Something went wrong. Please try again.',network:'Could not connect. Check your connection and try again.',expired:'Your session has expired. Please sign in again.',duplicate:'This username is already taken.',credentials:'Incorrect username or password.',limit:'Too many attempts. Try again in {seconds} seconds.',server:'Service temporarily unavailable. Please try again.',csrf:'Your session changed. Please try again.',registered:'Account created. Please sign in.',saving:'Saving…',noCategory:'Uncategorized',range:'Period',endBalance:'Closing balance',close:'Close',emptyChartDate:'No transactions'},
 ru: {dashboard:'⌂ Обзор',transactions:'⇄ Операции',statistics:'⌁ Статистика',logout:'Выйти',welcomeBack:'✦ С возвращением,',greeting:'С возвращением,',subtitle:'Ваши финансы под контролем.',loading:'Загружаем данные…',balance:'Общий баланс',income:'Доходы',expenses:'Расходы',allTime:'За всё время',history:'История баланса',historyHelp:'Баланс на конец дня · все операции',transactionsTitle:'Операции',add:'Добавить',quickActions:'⚡ Быстрые действия',addIncome:'Добавить доход +',addExpense:'Добавить расход −',viewStatistics:'Посмотреть статистику',addTransaction:'Добавить операцию',editTransaction:'Изменить операцию',type:'Тип',amount:'Сумма (₸)',category:'Категория (необязательно)',description:'Описание (необязательно)',date:'Дата',save:'Сохранить',signIn:'С возвращением',signInHelp:'Войдите, чтобы увидеть свои финансы.',signUp:'Создайте аккаунт',signUpHelp:'Начните вести учёт финансов.',usernameLabel:'Имя пользователя',passwordLabel:'Пароль',login:'Войти',register:'Создать аккаунт',noAccount:'Впервые здесь?',haveAccount:'Уже есть аккаунт?',empty:'Операций пока нет. Добавьте первую.',chartEmpty:'История появится после первой операции.',edit:'Изменить',delete:'Удалить',deleteConfirm:'Удалить операцию? Это действие нельзя отменить.',invalidAmount:'Введите целую сумму от 1 до 9223372036854775807.',invalidDate:'Выберите корректную дату.',invalidLogin:'Имя: 3–32 латинские буквы, цифры или подчёркивание.',invalidPassword:'Пароль должен содержать 12–256 символов.',failed:'Что-то пошло не так. Попробуйте снова.',network:'Не удалось подключиться. Проверьте соединение.',expired:'Сессия завершена. Войдите снова.',duplicate:'Это имя пользователя уже занято.',credentials:'Неверное имя пользователя или пароль.',limit:'Слишком много попыток. Повторите через {seconds} сек.',server:'Сервис временно недоступен.',csrf:'Сессия изменилась. Повторите действие.',registered:'Аккаунт создан. Войдите в него.',saving:'Сохранение…',noCategory:'Без категории',range:'Период',endBalance:'Итоговый баланс',close:'Закрыть',emptyChartDate:'Нет операций'},
 kk: {dashboard:'⌂ Шолу',transactions:'⇄ Операциялар',statistics:'⌁ Статистика',logout:'Шығу',welcomeBack:'✦ Қош келдіңіз,',greeting:'Қош келдіңіз,',subtitle:'Қаржыңызды бірге қадағалайық.',loading:'Деректер жүктелуде…',balance:'Жалпы баланс',income:'Кіріс',expenses:'Шығыс',allTime:'Барлық уақыт',history:'Баланс тарихы',historyHelp:'Күн соңындағы баланс · барлық операциялар',transactionsTitle:'Операциялар',add:'Қосу',quickActions:'⚡ Жылдам әрекеттер',addIncome:'Кіріс қосу +',addExpense:'Шығыс қосу −',viewStatistics:'Статистиканы көру',addTransaction:'Операция қосу',editTransaction:'Операцияны өзгерту',type:'Түрі',amount:'Сома (₸)',category:'Санат (міндетті емес)',description:'Сипаттама (міндетті емес)',date:'Күні',save:'Сақтау',signIn:'Қош келдіңіз',signInHelp:'Қаржыңызды көру үшін кіріңіз.',signUp:'Тіркелгі жасау',signUpHelp:'Қаржыңызды есепке алыңыз.',usernameLabel:'Пайдаланушы аты',passwordLabel:'Құпиясөз',login:'Кіру',register:'Тіркелу',noAccount:'Алғаш рет келдіңіз бе?',haveAccount:'Тіркелгіңіз бар ма?',empty:'Операциялар жоқ. Біріншісін қосыңыз.',chartEmpty:'Алғашқы операциядан кейін баланс тарихы көрсетіледі.',edit:'Өзгерту',delete:'Жою',deleteConfirm:'Операцияны жою керек пе? Бұл әрекет қайтарылмайды.',invalidAmount:'1 мен 9223372036854775807 аралығындағы бүтін сан енгізіңіз.',invalidDate:'Дұрыс күнді таңдаңыз.',invalidLogin:'Аты: 3–32 латын әрпі, сан немесе астын сызу.',invalidPassword:'Құпиясөз 12–256 таңбадан тұруы керек.',failed:'Қате орын алды. Қайта көріңіз.',network:'Қосылу мүмкін болмады. Байланысты тексеріңіз.',expired:'Сеанс аяқталды. Қайта кіріңіз.',duplicate:'Бұл пайдаланушы аты бос емес.',credentials:'Пайдаланушы аты немесе құпиясөз қате.',limit:'Әрекет тым көп. {seconds} секундтан кейін қайталаңыз.',server:'Қызмет уақытша қолжетімсіз.',csrf:'Сеанс өзгерді. Қайта көріңіз.',registered:'Тіркелгі жасалды. Енді кіріңіз.',saving:'Сақталуда…',noCategory:'Санатсыз',range:'Кезең',endBalance:'Қорытынды баланс',close:'Жабу',emptyChartDate:'Операциялар жоқ'}
};
Object.assign(words.en, {spendingByCategory:'Expenses by category', noExpenses:'No expenses yet.'});
Object.assign(words.ru, {spendingByCategory:'Расходы по категориям', noExpenses:'Расходов пока нет.'});
Object.assign(words.kk, {spendingByCategory:'Санаттар бойынша шығыс', noExpenses:'Әзірге шығыс жоқ.'});
let language = localStorage.getItem('finance-language') || 'en';
if (!words[language]) language = 'en';
const t = key => words[language][key] || words.en[key] || key;
const page = document.body.dataset.page;
let csrf = null, items = [], editing = null;
const $ = id => document.getElementById(id);
function translate() {
 document.documentElement.lang = language;
 document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
 $('language').value = language;
}
$('language').addEventListener('change', e => { language = e.target.value; localStorage.setItem('finance-language', language); translate(); if (page === 'dashboard') { renderTransactions(); renderChart(); } });
translate();

function parseExactJSON(text) {
 // JSON string tokens are left untouched; numeric tokens become strings, including 64-bit IDs.
 return JSON.parse(text.replace(/"(?:\\.|[^"\\])*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/g, token => token[0] === '"' ? token : JSON.stringify(token)));
}
class ApiError extends Error { constructor(status, message, retry) { super(message); this.status = status; this.retry = retry; } }
async function api(path, options = {}) {
 let response;
 try { response = await fetch(path, { credentials:'same-origin', cache:'no-store', ...options }); }
 catch { throw new ApiError(0, 'network'); }
 let data = null;
 if (response.status !== 204) { const body = await response.text(); try { data = body ? parseExactJSON(body) : null; } catch { throw new ApiError(response.status, 'failed'); } }
 if (!response.ok) throw new ApiError(response.status, data && data.error, response.headers.get('Retry-After'));
 return data;
}
async function getCsrf() { csrf = (await api('/api/auth/csrf')).csrf_token; return csrf; }
async function mutate(path, method, body) {
 if (!csrf) await getCsrf();
 const headers = {'X-CSRF-Token':csrf};
 if (body !== undefined) headers['Content-Type'] = 'application/json';
 return api(path, {method, headers, ...(body !== undefined ? {body} : {})});
}
function message(error, auth = false) {
 if (error.status === 0) return t('network');
 if (error.status === 429) return t('limit').replace('{seconds}', error.retry || '60');
 if (error.status === 409) return t('duplicate');
 if (error.status === 401) return t(auth ? 'credentials' : 'expired');
 if (error.status === 403) { csrf = null; return t('csrf'); }
 if (error.status === 503) return t('server');
 return t('failed');
}
function dateToday() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function setBusy(button, busy) { button.disabled = busy; button.setAttribute('aria-busy', String(busy)); }
function money(value) { const n = BigInt(value); return `${n < 0n ? '−' : ''}₸${(n < 0n ? -n : n).toLocaleString(language === 'kk' ? 'kk-KZ' : language === 'ru' ? 'ru-RU' : 'en-US')}`; }
function expire(error) { if (error.status !== 401) return false; items = []; document.querySelectorAll('#username,#balance-value,#income-value,#expense-value,#transaction-list,#chart,#chart-labels,#category-breakdown').forEach(el => { el.textContent = ''; }); sessionStorage.setItem('finance-notice','expired'); location.assign('/login'); return true; }

if (page === 'login' || page === 'register') {
 const notice = sessionStorage.getItem('finance-notice');
 if (notice) { $('auth-error').textContent = t(notice); sessionStorage.removeItem('finance-notice'); }
 $('auth-form').addEventListener('submit', async e => {
  e.preventDefault(); const form = e.currentTarget, error = $('auth-error'), button = form.querySelector('button'); error.textContent = '';
  const username = form.elements.username.value.trim(), password = form.elements.password.value;
  if (!/^[a-zA-Z0-9_]{3,32}$/.test(username)) { error.textContent = t('invalidLogin'); return; }
  if (password.length > 256 || (page === 'register' && password.length < 12) || !password) { error.textContent = t('invalidPassword'); return; }
  setBusy(button,true);
  try { await mutate(`/api/auth/${page}`, 'POST', JSON.stringify({username,password})); csrf = null;
    if (page === 'register') { sessionStorage.setItem('finance-notice','registered'); location.assign('/login'); } else location.assign('/dashboard');
  } catch (err) { error.textContent = message(err,true); } finally { setBusy(button,false); }
 });
}

if (page === 'dashboard') {
 const status = $('dashboard-status'), list = $('transaction-list'), dialog = $('transaction-dialog'), form = $('transaction-form');
 function button(text, action, id) { const el = document.createElement('button'); el.type = 'button'; el.className = 'row-button'; el.textContent = t(text); el.addEventListener('click', () => action(id)); return el; }
 function renderTransactions() {
  list.replaceChildren();
  if (!items.length) { const p = document.createElement('p'); p.className='muted'; p.textContent=t('empty'); list.append(p); return; }
  [...items].sort((a,b) => b.date.localeCompare(a.date) || (BigInt(a.id) < BigInt(b.id) ? 1 : -1)).forEach(item => {
   const row = document.createElement('div'); row.className='transaction';
   const info = document.createElement('div'), title = document.createElement('strong'), detail = document.createElement('p');
   title.textContent = item.category || t('noCategory'); detail.className='transaction-detail'; detail.textContent = [item.date, item.description].filter(Boolean).join(' · '); info.append(title,detail);
   const side = document.createElement('div'), value = document.createElement('strong'), actions = document.createElement('div'); side.className='transaction-side'; value.className=item.type === 'income' ? 'positive' : ''; value.textContent=(item.type === 'income' ? '+' : '−') + money(item.amount); actions.className='row-actions'; actions.append(button('edit',editItem,item.id),button('delete',deleteItem,item.id)); side.append(value,actions); row.append(info,side); list.append(row);
  });
 }
 function renderChart() {
  const chart = $('chart'), labels = $('chart-labels'); chart.replaceChildren(); labels.replaceChildren();
  const breakdown = $('category-breakdown'); breakdown.replaceChildren();
  const categories = new Map(); for (const item of items) if (item.type === 'expense') { const name = item.category || t('noCategory'); categories.set(name, (categories.get(name) || 0n) + BigInt(item.amount)); }
  if (!categories.size) { const p=document.createElement('p'); p.className='muted'; p.textContent=t('noExpenses'); breakdown.append(p); }
  else [...categories.entries()].sort((a,b)=>a[1]===b[1] ? a[0].localeCompare(b[0]) : a[1]>b[1] ? -1 : 1).forEach(([name,value])=>{ const row=document.createElement('div'), label=document.createElement('span'), amount=document.createElement('strong'); row.className='breakdown-row'; label.textContent=name; amount.textContent=money(value); row.append(label,amount); breakdown.append(row); });
  if (!items.length) { const p=document.createElement('p'); p.className='muted'; p.textContent=t('chartEmpty'); chart.append(p); return; }
  const days = new Map(); for (const item of items) days.set(item.date, (days.get(item.date)||0n) + BigInt(item.amount) * (item.type === 'income' ? 1n : -1n));
  let total=0n; const points = [...days.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([date,change])=>({date,value:total += change}));
  let min=points.reduce((a,p)=>p.value<a?p.value:a,0n), max=points.reduce((a,p)=>p.value>a?p.value:a,0n); if (min===max) max=min+1n;
  const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg'); svg.setAttribute('viewBox','0 0 600 200'); svg.setAttribute('preserveAspectRatio','none'); svg.setAttribute('role','img'); svg.setAttribute('aria-label',`${t('history')}: ${money(points[points.length-1].value)}`);
  const coords = points.map((p,i) => `${points.length===1 ? 300 : Math.round(i*600/(points.length-1))},${190-Number((p.value-min)*18000n/(max-min))/100}`);
  const line=document.createElementNS(ns,'polyline'); line.setAttribute('points',coords.join(' ')); line.setAttribute('fill','none'); line.setAttribute('stroke','#913cff'); line.setAttribute('stroke-width','3'); line.setAttribute('vector-effect','non-scaling-stroke'); svg.append(line);
  if (points.length === 1) { const circle=document.createElementNS(ns,'circle'); const [x,y]=coords[0].split(','); circle.setAttribute('cx',x); circle.setAttribute('cy',y); circle.setAttribute('r','5'); circle.setAttribute('fill','#913cff'); svg.append(circle); }
  chart.append(svg); const first=document.createElement('span'), last=document.createElement('span'); first.textContent=points[0].date; last.textContent=points[points.length-1].date; labels.append(first,last);
 }
 async function refresh() {
  status.textContent=t('loading');
  try { const [user, balance, transactions] = await Promise.all([api('/api/auth/me'),api('/api/balance'),api('/api/transactions')]); $('username').textContent=user.username; $('profile').textContent=user.username.slice(0,1).toUpperCase(); $('balance-value').textContent=money(balance.balance); $('income-value').textContent=money(balance.income); $('expense-value').textContent=money(balance.expense); items=transactions; renderTransactions(); renderChart(); status.textContent=''; }
  catch(err) { if (!expire(err)) status.textContent=message(err); }
 }
 function openForm(type, item=null) { editing=item; form.reset(); $('form-error').textContent=''; $('form-title').textContent=t(item?'editTransaction':'addTransaction'); form.elements.type.value=item ? item.type : type; form.elements.amount.value=item ? item.amount : ''; form.elements.category.value=item?.category || ''; form.elements.description.value=item?.description || ''; form.elements.date.value=item?.date || dateToday(); dialog.showModal(); }
 function editItem(id) { const item=items.find(x=>x.id===id); if (item) openForm(item.type,item); }
 async function deleteItem(id) { if (!confirm(t('deleteConfirm'))) return; try { await mutate(`/api/transactions/${encodeURIComponent(id)}`,'DELETE'); await refresh(); } catch(err) { if (!expire(err)) status.textContent=message(err); } }
 $('add-transaction').addEventListener('click',()=>openForm('expense')); $('add-income').addEventListener('click',()=>openForm('income')); $('add-expense').addEventListener('click',()=>openForm('expense')); $('close-dialog').addEventListener('click',()=>dialog.close());
 form.addEventListener('submit',async e => { e.preventDefault(); const error=$('form-error'), button=form.querySelector('[type=submit]'); error.textContent=''; const amount=form.elements.amount.value.trim();
  if (!/^\d+$/.test(amount) || BigInt(amount)<1n || BigInt(amount)>9223372036854775807n) { error.textContent=t('invalidAmount'); return; }
  if (!form.elements.date.value || !form.elements.date.checkValidity()) { error.textContent=t('invalidDate'); return; }
  const fields={type:form.elements.type.value,category:form.elements.category.value || null,description:form.elements.description.value || null,date:form.elements.date.value};
  if (!form.reportValidity()) return;
  // Embed the validated integer directly into JSON so Python receives an exact integer.
  const body=JSON.stringify(fields).slice(0,-1)+',"amount":'+BigInt(amount).toString()+'}'; setBusy(button,true);
  try { await mutate(editing ? `/api/transactions/${encodeURIComponent(editing.id)}` : '/api/transactions', editing?'PUT':'POST',body); dialog.close(); await refresh(); } catch(err) { if (!expire(err)) error.textContent=message(err); } finally { setBusy(button,false); }
 });
 $('logout').addEventListener('click',async e=>{ setBusy(e.currentTarget,true); try { await mutate('/api/auth/logout','POST'); csrf=null; items=[]; location.assign('/login'); } catch(err) { if (!expire(err)) status.textContent=message(err); } finally { setBusy(e.currentTarget,false); } });
 refresh();
}
