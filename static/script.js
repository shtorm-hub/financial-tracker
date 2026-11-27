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
Object.assign(words.en, {languageLabel:'Language', navigationLabel:'Main navigation', summaryLabel:'Account summary'});
Object.assign(words.ru, {languageLabel:'Язык', navigationLabel:'Основная навигация', summaryLabel:'Сводка счёта'});
Object.assign(words.kk, {languageLabel:'Тіл', navigationLabel:'Негізгі навигация', summaryLabel:'Шоттың қысқаша мазмұны'});
Object.assign(words.en, {showPassword:'Show password', hidePassword:'Hide password', salary:'Salary', freelance:'Freelance', gift:'Gift', food:'Food', transport:'Transport', housing:'Housing', shopping:'Shopping', health:'Health'});
Object.assign(words.ru, {showPassword:'Показать пароль', hidePassword:'Скрыть пароль', salary:'Зарплата', freelance:'Фриланс', gift:'Подарок', food:'Еда', transport:'Транспорт', housing:'Жильё', shopping:'Покупки', health:'Здоровье'});
Object.assign(words.kk, {showPassword:'Құпиясөзді көрсету', hidePassword:'Құпиясөзді жасыру', salary:'Жалақы', freelance:'Фриланс', gift:'Сыйлық', food:'Азық-түлік', transport:'Көлік', housing:'Тұрғын үй', shopping:'Сатып алу', health:'Денсаулық'});
Object.assign(words.en, {project:'PROJECT', personalAccount:'Personal account', navOverview:'Overview', navTransactions:'Transactions', navStatistics:'Statistics', searchPlaceholder:'Search transactions…', dashboardEyebrow:'FINANCIAL DASHBOARD', financialOverview:'Financial overview', overviewHelp:'Your income, expenses and recent transactions.', selectedPeriod:'Selected period', cashFlowEyebrow:'CASH FLOW', cashFlow:'Cash flow', week:'This week', month:'This month', year:'This year', netPeriod:'Net for selected period', spendingEyebrow:'SPENDING BREAKDOWN', totalExpenses:'Total expenses', recentEyebrow:'YOUR ACTIVITY', descriptionShort:'DESCRIPTION', categoryShort:'CATEGORY', amountShort:'AMOUNT', manageEyebrow:'MANAGE', quickActions:'Quick actions', quickHelp:'Keep your finances up to date.', recordIncome:'Record income', recordExpense:'Record expense', tengeNote:'All amounts in tenge ₸', newOperation:'TRANSACTION', noMatches:'No matching transactions.', noPeriodData:'No transactions in this period.', noDescription:'No description'});
Object.assign(words.ru, {project:'ПРОЕКТ', personalAccount:'Личный аккаунт', navOverview:'Обзор', navTransactions:'Транзакции', navStatistics:'Статистика', searchPlaceholder:'Поиск транзакций…', dashboardEyebrow:'ФИНАНСОВАЯ ПАНЕЛЬ', financialOverview:'Обзор финансов', overviewHelp:'Ваши доходы, расходы и последние операции.', selectedPeriod:'Выбранный период', cashFlowEyebrow:'ДИНАМИКА СРЕДСТВ', cashFlow:'Движение средств', week:'Эта неделя', month:'Этот месяц', year:'Этот год', netPeriod:'Разница за выбранный период', spendingEyebrow:'СТРУКТУРА РАСХОДОВ', totalExpenses:'Всего расходов', recentEyebrow:'ВАШИ ОПЕРАЦИИ', descriptionShort:'ОПИСАНИЕ', categoryShort:'КАТЕГОРИЯ', amountShort:'СУММА', manageEyebrow:'УПРАВЛЕНИЕ', quickActions:'Быстрые действия', quickHelp:'Держите финансы под контролем.', recordIncome:'Записать поступление', recordExpense:'Записать трату', tengeNote:'Все суммы указаны в тенге ₸', newOperation:'ОПЕРАЦИЯ', noMatches:'Операции не найдены.', noPeriodData:'За этот период операций нет.', noDescription:'Без описания'});
Object.assign(words.kk, {project:'ЖОБА', personalAccount:'Жеке тіркелгі', navOverview:'Шолу', navTransactions:'Операциялар', navStatistics:'Статистика', searchPlaceholder:'Операцияларды іздеу…', dashboardEyebrow:'ҚАРЖЫЛЫҚ ПАНЕЛЬ', financialOverview:'Қаржы шолуы', overviewHelp:'Кірістеріңіз, шығыстарыңыз және соңғы операциялар.', selectedPeriod:'Таңдалған кезең', cashFlowEyebrow:'ҚАРЖЫ ҚОЗҒАЛЫСЫ', cashFlow:'Қаражат қозғалысы', week:'Осы апта', month:'Осы ай', year:'Осы жыл', netPeriod:'Кезең ішіндегі айырма', spendingEyebrow:'ШЫҒЫСТАР ҚҰРЫЛЫМЫ', totalExpenses:'Барлық шығыс', recentEyebrow:'СІЗДІҢ ОПЕРАЦИЯЛАРЫҢЫЗ', descriptionShort:'СИПАТТАМА', categoryShort:'САНАТ', amountShort:'СОМА', manageEyebrow:'БАСҚАРУ', quickActions:'Жылдам әрекеттер', quickHelp:'Қаржыңызды қадағалаңыз.', recordIncome:'Кірісті тіркеу', recordExpense:'Шығысты тіркеу', tengeNote:'Барлық сома теңгемен ₸', newOperation:'ОПЕРАЦИЯ', noMatches:'Операциялар табылмады.', noPeriodData:'Бұл кезеңде операциялар жоқ.', noDescription:'Сипаттамасыз'});
let language = localStorage.getItem('finance-language') || 'en';
if (!words[language]) language = 'en';
const t = key => words[language][key] || words.en[key] || key;
const page = document.body.dataset.page;
let csrf = null, items = [], editing = null;
const $ = id => document.getElementById(id);
function translate() {
 document.documentElement.lang = language;
 document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
 document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); el.setAttribute('aria-label',t(el.dataset.i18nPlaceholder)); });
 document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label',t(el.dataset.i18nAria)));
 $('language').value = language;
}
$('language').addEventListener('change', e => { language = e.target.value; localStorage.setItem('finance-language', language); translate(); document.dispatchEvent(new Event('finance-language-change')); });
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
function expire(error) { if (error.status !== 401) return false; items = []; document.querySelectorAll('#username,#profile,#balance-value,#income-value,#expense-value,#chart-total,#donut-total,#transaction-list,#chart,#chart-labels,#category-breakdown').forEach(el => { el.textContent = ''; }); sessionStorage.setItem('finance-notice','expired'); location.assign('/login'); return true; }

if (page === 'login' || page === 'register') {
 const passwordInput = $('password'), togglePassword = $('toggle-password');
 function updatePasswordToggle() { const shown = passwordInput.type === 'text', key = shown ? 'hidePassword' : 'showPassword'; togglePassword.setAttribute('aria-pressed', String(shown)); togglePassword.dataset.i18nAria = key; togglePassword.setAttribute('aria-label', t(key)); togglePassword.querySelector('.sr-only').textContent = t(key); }
 togglePassword.addEventListener('click', () => { passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password'; updatePasswordToggle(); });
 document.addEventListener('finance-language-change', updatePasswordToggle);
 const notice = sessionStorage.getItem('finance-notice');
 if (notice) { $('auth-error').textContent = t(notice); sessionStorage.removeItem('finance-notice'); }
 $('auth-form').addEventListener('submit', async e => {
  e.preventDefault(); const form = e.currentTarget, error = $('auth-error'), button = form.querySelector('.primary-button'); if (button.disabled) return; error.textContent = '';
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
 let allBalance = null;
 let submitting = false;
 function updateCategorySuggestions() { const keys = form.elements.type.value === 'income' ? ['salary','freelance','gift'] : ['food','transport','housing','shopping','health']; const datalist = $('category-suggestions'); datalist.replaceChildren(); for (const key of keys) { const option = document.createElement('option'); option.value = t(key); datalist.append(option); } }
 form.elements.type.addEventListener('change', updateCategorySuggestions);
 document.addEventListener('finance-language-change', updateCategorySuggestions);
 document.addEventListener('finance-language-change',()=>{ renderTransactions(); if(allBalance!==null) renderPeriod(); });
 function button(key, action, id) { const el=document.createElement('button'); el.type='button'; el.className='row-button'; el.textContent=t(key); el.addEventListener('click',()=>action(id)); return el; }
 function renderTransactions() {
  list.replaceChildren();
  const query=$('search-input').value.trim().toLocaleLowerCase();
  const shown=[...items].filter(item=>`${item.description || ''} ${item.category || ''}`.toLocaleLowerCase().includes(query)).sort((a,b)=>b.date.localeCompare(a.date) || (BigInt(a.id)<BigInt(b.id)?1:BigInt(a.id)>BigInt(b.id)?-1:0));
  if (!shown.length) { const p=document.createElement('p'); p.className='empty-state'; p.textContent=t(items.length?'noMatches':'empty'); list.append(p); return; }
  for (const item of shown) {
   const row=document.createElement('div'); row.className='transaction-row';
   const title=document.createElement('span'), category=document.createElement('span'), date=document.createElement('span'), amount=document.createElement('span'), actions=document.createElement('span');
   title.className='tx-name'; title.textContent=item.description || t('noDescription'); category.textContent=item.category || t('noCategory'); date.textContent=item.date;
   amount.className=`tx-amount ${item.type}`; amount.textContent=(item.type==='income'?'+':'−')+money(item.amount);
   actions.className='row-actions'; actions.append(button('edit',editItem,item.id),button('delete',deleteItem,item.id)); row.append(title,category,date,amount,actions); list.append(row);
  }
 }
 function localDate(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
 function periodItems() {
  const value=$('period-select').value; if(value==='all') return [...items];
  const today=new Date(), start=new Date(today.getFullYear(),today.getMonth(),today.getDate(),12), end=new Date(start);
  if(value==='week') { start.setDate(start.getDate()-(start.getDay()+6)%7); end.setTime(start.getTime()); end.setDate(end.getDate()+6); }
  if(value==='month') { start.setDate(1); end.setMonth(end.getMonth()+1,0); }
  if(value==='year') { start.setMonth(0,1); end.setMonth(11,31); }
  const from=localDate(start), to=localDate(end); return items.filter(item=>item.date>=from && item.date<=to);
 }
 function renderPeriod() {
  const selected=periodItems(), income=selected.reduce((sum,x)=>sum+(x.type==='income'?BigInt(x.amount):0n),0n), expense=selected.reduce((sum,x)=>sum+(x.type==='expense'?BigInt(x.amount):0n),0n);
  if (allBalance!==null) $('balance-value').textContent=money(allBalance);
  $('income-value').textContent=money(income); $('expense-value').textContent=money(expense); $('chart-total').textContent=money(income-expense); $('donut-total').textContent=money(expense);
  const chart=$('chart'), labels=$('chart-labels'), breakdown=$('category-breakdown'), donut=$('donut'); chart.replaceChildren(); labels.replaceChildren(); breakdown.replaceChildren();
  const categories=new Map(); for(const item of selected) if(item.type==='expense') { const name=item.category || t('noCategory'); categories.set(name,(categories.get(name)||0n)+BigInt(item.amount)); }
  const colors=['#8b58d3','#b99ae9','#dfb6e7','#ec8fac','#c5b3d7','#9c79b8'];
  if(!categories.size) { donut.style.background=''; const empty=document.createElement('p'); empty.className='empty-state'; empty.textContent=t('noExpenses'); breakdown.append(empty); }
  else { let cumulative=0n; const stops=[]; [...categories.entries()].sort((a,b)=>a[1]===b[1]?a[0].localeCompare(b[0]):a[1]>b[1]?-1:1).forEach(([name,value],i)=>{ const start=cumulative; cumulative+=value; const color=colors[i%colors.length]; stops.push(`${color} ${Number(start*36000n/expense)/100}deg ${Number(cumulative*36000n/expense)/100}deg`); const row=document.createElement('div'), dot=document.createElement('i'), label=document.createElement('span'), amount=document.createElement('b'); dot.className='cat-dot'; dot.style.backgroundColor=color; label.textContent=name; amount.textContent=money(value); row.append(dot,label,amount); breakdown.append(row); }); donut.style.background=`conic-gradient(${stops.join(',')})`; }
  if(!selected.length) { chart.setAttribute('aria-label',t('noPeriodData')); const p=document.createElement('p'); p.className='empty-state'; p.textContent=t('noPeriodData'); chart.append(p); return; }
  const days=new Map(); for(const item of selected) { const day=days.get(item.date)||{income:0n,expense:0n}; day[item.type]+=BigInt(item.amount); days.set(item.date,day); }
  const points=[...days.entries()].sort(([a],[b])=>a.localeCompare(b)); let max=0n; for(const [,v] of points) { if(v.income>max) max=v.income; if(v.expense>max) max=v.expense; } if(max===0n) max=1n;
  const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg'); svg.classList.add('chart-svg','dynamic-chart'); svg.setAttribute('viewBox','0 0 700 220'); svg.setAttribute('preserveAspectRatio','none');
  for(const kind of ['income','expense']) { const coords=points.map(([,v],i)=>`${points.length===1?350:Math.round(i*700/(points.length-1))},${210-Number(v[kind]*20000n/max)/100}`); const line=document.createElementNS(ns,'polyline'); line.setAttribute('points',coords.join(' ')); line.setAttribute('class',`line-${kind}`); svg.append(line); if(points.length===1){const circle=document.createElementNS(ns,'circle'); const [x,y]=coords[0].split(','); circle.setAttribute('cx',x); circle.setAttribute('cy',y); circle.setAttribute('r','4'); circle.setAttribute('class',`point-${kind}`); svg.append(circle);} }
  const plot=document.createElement('div'); plot.className='plot'; const grid=document.createElement('div'); grid.className='grid-lines'; for(let i=0;i<5;i++) grid.append(document.createElement('i')); plot.append(grid,svg); chart.append(plot); chart.setAttribute('aria-label',`${t('cashFlow')}: ${t('income')} ${money(income)}, ${t('expenses')} ${money(expense)}`);
  const first=document.createElement('span'),last=document.createElement('span'); first.textContent=points[0][0]; last.textContent=points.length>1?points[points.length-1][0]:''; labels.append(first,last);
 }
 async function refresh() {
  status.textContent=t('loading');
  try { const [user,balance,transactions]=await Promise.all([api('/api/auth/me'),api('/api/balance'),api('/api/transactions')]); $('username').textContent=user.username; $('profile').textContent=user.username.slice(0,1).toUpperCase(); allBalance=balance.balance; items=transactions; renderTransactions(); renderPeriod(); status.textContent=''; }
  catch(err) { if(!expire(err)) status.textContent=message(err); }
 }
 function openForm(type,item=null) { if (submitting) return; editing=item; form.reset(); $('form-error').textContent=''; $('form-title').textContent=t(item?'editTransaction':'addTransaction'); form.elements.type.value=item?item.type:type; updateCategorySuggestions(); form.elements.amount.value=item?item.amount:''; form.elements.category.value=item?.category||''; form.elements.description.value=item?.description||''; form.elements.date.value=item?.date||dateToday(); dialog.showModal(); }
 function editItem(id) { const item=items.find(x=>x.id===id); if(item) openForm(item.type,item); }
 async function deleteItem(id) { if(!confirm(t('deleteConfirm'))) return; try { await mutate(`/api/transactions/${encodeURIComponent(id)}`,'DELETE'); await refresh(); } catch(err) { if(!expire(err)) status.textContent=message(err); } }
 $('search-input').addEventListener('input',renderTransactions); $('period-select').addEventListener('change',renderPeriod);
 document.querySelectorAll('.nav-link').forEach(link=>link.addEventListener('click',()=>{ document.querySelectorAll('.nav-link').forEach(x=>x.classList.remove('active')); link.classList.add('active'); }));
 $('add-transaction').addEventListener('click',()=>openForm('expense')); $('add-income').addEventListener('click',()=>openForm('income')); $('add-expense').addEventListener('click',()=>openForm('expense')); $('close-dialog').addEventListener('click',()=>dialog.close());
 $('primary-income').addEventListener('click',()=>openForm('income')); $('primary-expense').addEventListener('click',()=>openForm('expense'));
 form.addEventListener('submit',async e=>{ e.preventDefault(); if(submitting) return; const error=$('form-error'), submit=form.querySelector('[type=submit]'); error.textContent=''; const amount=form.elements.amount.value.trim();
  if(!/^\d+$/.test(amount)||BigInt(amount)<1n||BigInt(amount)>9223372036854775807n){error.textContent=t('invalidAmount');return;}
  if(!form.elements.date.value||!form.elements.date.checkValidity()){error.textContent=t('invalidDate');return;}
  const fields={type:form.elements.type.value,category:form.elements.category.value||null,description:form.elements.description.value||null,date:form.elements.date.value}; if(!form.reportValidity()) return;
  const body=JSON.stringify(fields).slice(0,-1)+',"amount":'+BigInt(amount).toString()+'}'; submitting=true; setBusy(submit,true);
  try { await mutate(editing?`/api/transactions/${encodeURIComponent(editing.id)}`:'/api/transactions',editing?'PUT':'POST',body); dialog.close(); await refresh(); } catch(err){if(!expire(err)) error.textContent=message(err);} finally{submitting=false;setBusy(submit,false);}
 });
 $('logout').addEventListener('click',async e=>{setBusy(e.currentTarget,true);try{await mutate('/api/auth/logout','POST');csrf=null;items=[];location.assign('/login');}catch(err){if(!expire(err))status.textContent=message(err);}finally{setBusy(e.currentTarget,false);}});
 refresh();
}
